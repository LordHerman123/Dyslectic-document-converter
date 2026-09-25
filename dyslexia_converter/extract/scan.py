"""Clean-up of scanned pages before OCR (book scans, photocopies, phone photos).

Typical problems with book scans and what is done about them:

* two book pages on one sheet (a "spread")  -> find the gutter and split
* dark gutter shadow / grey or yellow paper -> flatten the illumination
* slightly rotated pages                    -> estimate the skew and straighten
* black scanner borders                     -> removed with the illumination step and cropping
* pages scanned sideways                    -> the PDF page rotation is honoured; OSD as a fallback

All functions work on greyscale NumPy arrays (0 = black, 255 = white) and
are pure, so they can be tested and reused on other platforms.
"""
from __future__ import annotations

import io
from dataclasses import dataclass
from typing import Optional

import numpy as np
from PIL import Image, ImageFilter


@dataclass
class ScanPage:
    """One (half) page ready for OCR."""

    image: Image.Image  # cleaned greyscale image for OCR
    photo: Image.Image  # straightened original (colour kept) for cropping figures
    dpi: int
    skew: float  # degrees corrected
    origin: tuple[int, int]  # top-left of this half inside the full rendered page (pixels, before deskew)
    side: str  # "full", "left" or "right"

    @property
    def width_pt(self) -> float:
        return self.image.width * 72.0 / self.dpi

    @property
    def height_pt(self) -> float:
        return self.image.height * 72.0 / self.dpi

    def png(self) -> bytes:
        buf = io.BytesIO()
        self.image.save(buf, format="PNG")
        return buf.getvalue()


# ----------------------------------------------------------------------------- basics

def to_gray(img: Image.Image) -> np.ndarray:
    return np.asarray(img.convert("L"), dtype=np.float32)


def flatten_illumination(gray: np.ndarray, radius: int = 25) -> np.ndarray:
    """Divide by an estimate of the paper brightness.

    Removes gutter shadows, uneven lighting and tinted paper while keeping
    ink dark. The background is estimated with a max-filter (removes the
    thin dark ink strokes) followed by a blur, on a reduced image for speed.
    """
    h, w = gray.shape
    k = max(1, min(h, w) // 600)  # work at roughly 600 px on the short side
    small = Image.fromarray(gray.astype(np.uint8)).resize((max(1, w // k), max(1, h // k)))
    r = max(3, radius // k)
    size = r | 1  # MaxFilter needs an odd size
    bg = small.filter(ImageFilter.MaxFilter(size)).filter(ImageFilter.GaussianBlur(r))
    bg = np.asarray(bg.resize((w, h)), dtype=np.float32)
    out = gray / np.maximum(bg, 1.0) * 255.0
    return np.clip(out, 0, 255)


def binarize(gray: np.ndarray, level: Optional[float] = None) -> np.ndarray:
    """Boolean ink mask (True = ink). Otsu threshold when ``level`` is None."""
    if level is None:
        hist, _ = np.histogram(gray, bins=256, range=(0, 256))
        total = gray.size
        cum = np.cumsum(hist)
        cum_mean = np.cumsum(hist * np.arange(256))
        mean_all = cum_mean[-1] / total
        w0 = cum / total
        w1 = 1 - w0
        with np.errstate(divide="ignore", invalid="ignore"):
            between = (mean_all * w0 - cum_mean / total) ** 2 / (w0 * w1)
        best = np.nanmax(between)
        # a perfectly two-tone image has a plateau of equally good thresholds: take its middle
        level = float(np.mean(np.nonzero(between >= best * 0.999)[0]))
        level = min(max(level, 1.0), 200.0)
    return gray < level


# ----------------------------------------------------------------------------- spreads

def find_gutter(ink: np.ndarray) -> Optional[int]:
    """x position of the gutter if the image shows two facing pages, else None.

    Text columns produce many ink transitions per pixel column; the gutter
    (blank or a smooth shadow, flattened away) produces few. A spread has a
    low-activity band near the middle with substantial text on both sides.
    """
    h, w = ink.shape
    if w < h * 1.15:  # portrait: a single page
        return None
    rows = slice(int(h * 0.08), int(h * 0.92))
    activity = np.abs(np.diff(ink[rows].astype(np.int8), axis=0)).sum(axis=0).astype(np.float32)
    k = max(1, w // 200)
    smooth = np.convolve(activity, np.ones(k * 3) / (k * 3), mode="same")
    lo, hi = int(w * 0.35), int(w * 0.65)
    x = lo + int(np.argmin(smooth[lo:hi]))
    left = smooth[int(w * 0.1):int(w * 0.4)]
    right = smooth[int(w * 0.6):int(w * 0.9)]
    if len(left) == 0 or len(right) == 0:
        return None
    text_level = min(np.median(left), np.median(right))
    if text_level <= 0:
        return None
    return x if smooth[x] < 0.12 * text_level else None


# ----------------------------------------------------------------------------- skew

def estimate_skew(ink: np.ndarray, max_angle: float = 4.0, step: float = 0.1) -> float:
    """Skew in degrees (positive = text rises to the right), by projection profiles.

    Text lines give the sharpest row profile when they are horizontal; the
    angle maximising the variance of row sums is the skew.
    """
    h, w = ink.shape
    ink = ink[int(h * 0.05):int(h * 0.95), int(w * 0.05):int(w * 0.95)]  # ignore borders
    h, w = ink.shape
    k = max(1, w // 700)
    small = ink[::k, ::k]
    ys, xs = np.nonzero(small)
    if len(ys) < 500:
        return 0.0
    if len(ys) > 60000:
        idx = np.random.default_rng(0).choice(len(ys), 60000, replace=False)
        ys, xs = ys[idx], xs[idx]
    xs = xs - small.shape[1] / 2

    def score(angle: float) -> float:
        t = np.tan(np.radians(angle))
        rows = np.round(ys + xs * t).astype(np.int64)
        rows -= rows.min()
        hist = np.bincount(rows)
        return float((hist.astype(np.float64) ** 2).sum())

    angles = np.arange(-max_angle, max_angle + 1e-9, 0.5)
    best = max(angles, key=score)
    fine = np.arange(best - 0.5, best + 0.5 + 1e-9, step)
    best = max(fine, key=score)
    return float(round(best, 2))


def rotate(img: Image.Image, angle: float, fill) -> Image.Image:
    if abs(angle) < 0.05:
        return img
    return img.rotate(-angle, resample=Image.BICUBIC, expand=False, fillcolor=fill)


# ----------------------------------------------------------------------------- cropping

def content_box(ink: np.ndarray, margin: int) -> tuple[int, int, int, int]:
    """Bounding box of the ink, ignoring thin specks along the image edges."""
    h, w = ink.shape
    cols = ink.sum(axis=0)
    rows = ink.sum(axis=1)
    col_on = np.nonzero(cols > max(2, h * 0.002))[0]
    row_on = np.nonzero(rows > max(2, w * 0.002))[0]
    if len(col_on) == 0 or len(row_on) == 0:
        return 0, 0, w, h
    x0, x1 = max(0, col_on[0] - margin), min(w, col_on[-1] + margin)
    y0, y1 = max(0, row_on[0] - margin), min(h, row_on[-1] + margin)
    return int(x0), int(y0), int(x1), int(y1)


def clear_edge_blobs(ink: np.ndarray, band: float = 0.06) -> np.ndarray:
    """Remove dark borders along the image edges (scanner lid, book edge, shadows).

    Within a band along each edge, rows/columns that are mostly ink are
    borders, not text (a line of text is at most ~50% ink), as are edge
    bands that are dense overall.
    """
    h, w = ink.shape
    out = ink.copy()
    bx, by = max(2, int(w * band)), max(2, int(h * band))
    row_frac = out.mean(axis=1)
    col_frac = out.mean(axis=0)
    for y in list(range(by)) + list(range(h - by, h)):
        if row_frac[y] > 0.5:
            out[y, :] = False
    for x in list(range(bx)) + list(range(w - bx, w)):
        if col_frac[x] > 0.5:
            out[:, x] = False
    for sl in (np.s_[:, :bx], np.s_[:, w - bx:], np.s_[:by, :], np.s_[h - by:, :]):
        region = out[sl]
        if region.size and region.mean() > 0.35:
            out[sl] = False
    return out


# ----------------------------------------------------------------------------- pipeline

def prepare_page(rendered: Image.Image, dpi: int, split_spreads: bool = True,
                 deskew: bool = True) -> list[ScanPage]:
    """Clean a rendered scan and return one or two pages ready for OCR."""
    gray = to_gray(rendered)
    flat = flatten_illumination(gray, radius=max(15, dpi // 12))
    raw_ink = binarize(flat)
    ink = clear_edge_blobs(raw_ink)
    border = raw_ink & ~ink
    if border.any():
        # whiten scanner borders in the cleaned image so they never look like pictures
        grown = Image.fromarray((border * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(7))
        flat = np.where(np.asarray(grown) > 0, 255.0, flat)
    halves: list[tuple[int, int, str]] = [(0, gray.shape[1], "full")]
    if split_spreads:
        g = find_gutter(ink)
        if g is not None:
            halves = [(0, g, "left"), (g, gray.shape[1], "right")]
    out: list[ScanPage] = []
    for x0, x1, side in halves:
        part_flat = flat[:, x0:x1]
        part_ink = ink[:, x0:x1]
        angle = estimate_skew(part_ink) if deskew else 0.0
        clean = Image.fromarray(part_flat.astype(np.uint8))
        photo = rendered.crop((x0, 0, x1, rendered.height))
        clean = rotate(clean, angle, 255)
        photo = rotate(photo, angle, (255, 255, 255) if photo.mode == "RGB" else 255)
        c_ink = clear_edge_blobs(binarize(np.asarray(clean, dtype=np.float32)))
        bx0, by0, bx1, by1 = content_box(c_ink, margin=int(dpi * 0.15))
        clean = clean.crop((bx0, by0, bx1, by1))
        photo = photo.crop((bx0, by0, bx1, by1))
        out.append(ScanPage(clean, photo, dpi, angle, (x0 + bx0, by0), side))
    return out
