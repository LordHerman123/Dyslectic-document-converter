"""Clean-up of scanned pages before OCR (book scans, photocopies, phone photos).

Typical problems with book scans and what is done about them:

* two book pages on one sheet (a "spread")  -> find the gutter and split
* dark gutter shadow / grey or yellow paper -> flatten the illumination
* slightly rotated pages                    -> estimate the skew and straighten
* lines curving into the spine (book curl)  -> measure the curve strip by strip and straighten it
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


# ----------------------------------------------------------------------------- curved lines (book curl)

def _smooth1d(a: np.ndarray, k: int, axis: int = 0) -> np.ndarray:
    k = max(1, int(k)) | 1
    ker = np.ones(k) / k
    pad = k // 2
    return np.apply_along_axis(lambda v: np.convolve(np.pad(v, pad, mode="edge"), ker, mode="valid"), axis, a)


def line_spacing(ink: np.ndarray) -> Optional[int]:
    """Distance between text lines in pixels (autocorrelation of the row profile)."""
    prof = ink.sum(axis=1).astype(np.float64)
    prof -= prof.mean()
    if not prof.any():
        return None
    ac = np.correlate(prof, prof, mode="full")[len(prof) - 1:]
    lo, hi = 8, min(len(ac) - 1, 400)
    if hi <= lo:
        return None
    return lo + int(np.argmax(ac[lo:hi]))


def curl_field(ink: np.ndarray, win_lines: int = 6):
    """How far the text lines are displaced vertically, per strip and band of lines.

    Near the spine of a book the page curls away from the scanner and the lines bend. The page is cut
    into narrow vertical strips; for each band of a few lines, the row profile of each strip is matched
    with its neighbour, working outward from the flat middle, which gives the vertical shift of the
    lines in every strip. A real curl only grows toward the edge, so values that shrink again are
    matching errors and are dropped. Returns (shifts, strip x-centres, band y-centres, line spacing),
    or None for pages without enough text.
    """
    h, w = ink.shape
    L = line_spacing(ink)
    if not L or L < 12:
        return None
    strip = max(16, L)
    xs = list(range(0, max(1, w - strip + 1), strip))
    win = L * win_lines
    ys = list(range(0, max(1, h - win + 1), max(1, win // 2)))
    if len(xs) < 6 or not ys:
        return None
    prof = np.stack([ink[:, x:x + strip].sum(axis=1).astype(np.float64) for x in xs], axis=1)
    prof = _smooth1d(prof, max(3, L // 5), axis=0)
    maxd = max(2, L // 4)
    mid = len(xs) // 2
    S = np.zeros((len(ys), len(xs)))
    for j, y0 in enumerate(ys):
        seg = prof[y0:y0 + win]
        has = seg.sum(axis=0) > 0.002 * win * strip
        for rng in (range(mid + 1, len(xs)), range(mid - 1, -1, -1)):
            cur, prev = 0.0, mid
            for k in rng:
                if has[k] and has[prev]:
                    a, b = seg[:, prev], seg[:, k]
                    scores = [float(np.dot(a[:len(a) - d], b[d:])) if d >= 0 else float(np.dot(a[-d:], b[:len(b) + d]))
                              for d in range(-maxd, maxd + 1)]
                    cur += int(np.argmax(scores)) - maxd
                    prev = k
                S[j, k] = cur
    S = _smooth1d(S, 3, axis=1)
    if len(ys) >= 3:  # the curl changes smoothly down the page: one band that disagrees is a matching error
        padded = np.pad(S, ((1, 1), (0, 0)), mode="edge")
        S = np.median(np.stack([padded[:-2], padded[1:-1], padded[2:]]), axis=0)
    n = S.shape[1]
    S -= np.median(S[:, n // 4:3 * n // 4], axis=1, keepdims=True)
    for j in range(len(ys)):  # a curl grows monotonically toward each edge
        for part in (S[j, mid:], S[j, :mid + 1][::-1]):
            sign = 1.0 if part[-1] >= 0 else -1.0
            part[:] = sign * np.maximum.accumulate(np.clip(sign * part, 0, None))
    xc = np.array(xs, dtype=np.float64) + strip / 2
    yc = np.array(ys, dtype=np.float64) + win / 2
    return S, xc, yc, L


def _interp_extrapolate(x: np.ndarray, xp: np.ndarray, fp: np.ndarray) -> np.ndarray:
    y = np.interp(x, xp, fp)
    if len(xp) >= 2:
        lo, hi = x < xp[0], x > xp[-1]
        y[lo] = fp[0] + (x[lo] - xp[0]) * (fp[1] - fp[0]) / (xp[1] - xp[0])
        y[hi] = fp[-1] + (x[hi] - xp[-1]) * (fp[-1] - fp[-2]) / (xp[-1] - xp[-2])
    return y


def curl_displacement(ink: np.ndarray, min_lines: float = 0.15, grid: int = 24):
    """Vertical displacement that straightens curled lines, sampled on a grid, or None when the lines are
    straight. Returns (grid x positions, grid y positions, displacement[y, x])."""
    r = curl_field(ink)
    if r is None:
        return None
    S, xc, yc, L = r
    if float(np.abs(S).max()) < min_lines * L:
        return None
    h, w = ink.shape
    gx = np.unique(np.append(np.arange(0, w, grid), w)).astype(np.float64)
    gy = np.unique(np.append(np.arange(0, h, grid), h)).astype(np.float64)
    cols = np.stack([_interp_extrapolate(gx, xc, S[j]) for j in range(len(yc))])  # bands x gx
    if len(yc) == 1:
        D = np.repeat(cols, len(gy), axis=0)
    else:
        D = np.stack([np.interp(gy, yc, cols[:, i]) for i in range(len(gx))], axis=1)
    return gx, gy, D


def apply_displacement(img: Image.Image, field, fill) -> Image.Image:
    """Move pixels vertically by the displacement field (output (x, y) comes from (x, y + D)).

    Done with PIL's mesh transform: the field is smooth, so small grid cells mapped to quadrilaterals
    are exact enough and much faster than moving every pixel in NumPy.
    """
    gx, gy, D = field
    mesh = []
    for j in range(len(gy) - 1):
        y0, y1 = gy[j], gy[j + 1]
        for i in range(len(gx) - 1):
            x0, x1 = gx[i], gx[i + 1]
            mesh.append(((int(x0), int(y0), int(x1), int(y1)),
                         (x0, y0 + D[j, i], x0, y1 + D[j + 1, i], x1, y1 + D[j + 1, i + 1], x1, y0 + D[j, i + 1])))
    return img.transform(img.size, Image.MESH, mesh, resample=Image.BILINEAR, fillcolor=fill)


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


def _long_runs(line: np.ndarray, min_len: int) -> np.ndarray:
    """Mask of the runs of ink in a 1-D line that are at least ``min_len`` long."""
    edges = np.diff(np.concatenate([[0], line.astype(np.int8), [0]]))
    starts, ends = np.nonzero(edges == 1)[0], np.nonzero(edges == -1)[0]
    out = np.zeros(len(line), dtype=bool)
    for s0, e0 in zip(starts, ends):
        if e0 - s0 >= min_len:
            out[s0:e0] = True
    return out


def clear_edge_blobs(ink: np.ndarray, band: float = 0.06) -> np.ndarray:
    """Remove dark borders along the image edges (scanner lid, book edge, shadows).

    Within a band along each edge, a row/column that is mostly ink is a border or a ruled line, not
    text (a line of text is at most ~50% ink): only its long unbroken runs are removed, so letters
    that happen to sit in the same column survive. An edge band that is dense overall (a black scanner
    border) is cleared from the edge inward, as far as the columns/rows stay dense.
    """
    h, w = ink.shape
    out = ink.copy()
    bx, by = max(2, int(w * band)), max(2, int(h * band))
    row_frac = out.mean(axis=1)
    col_frac = out.mean(axis=0)
    for y in list(range(by)) + list(range(h - by, h)):
        if row_frac[y] > 0.5:
            out[y, _long_runs(out[y], max(20, w // 30))] = False
    for x in list(range(bx)) + list(range(w - bx, w)):
        if col_frac[x] > 0.5:
            out[_long_runs(out[:, x], max(20, h // 30)), x] = False
    for axis, n, size in ((0, bx, w), (1, by, h)):
        frac = out.mean(axis=axis)
        for idx in (range(n), range(size - 1, size - 1 - n, -1)):
            region = [i for i in idx]
            if out.take(region, axis=1 - axis).mean() <= 0.35:
                continue
            for i in region:  # from the edge inward while the border lasts
                if frac[i] < 0.2:
                    break
                if axis == 0:
                    out[:, i] = False
                else:
                    out[i, :] = False
    return out

# ----------------------------------------------------------------------------- pipeline

def prepare_page(rendered: Image.Image, dpi: int, split_spreads: bool = True,
                 deskew: bool = True, dewarp: bool = True) -> list[ScanPage]:
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
        white = (255, 255, 255) if photo.mode == "RGB" else 255
        clean = rotate(clean, angle, 255)
        photo = rotate(photo, angle, white)
        if dewarp:
            field = curl_displacement(binarize(np.asarray(clean, dtype=np.float32)))
            if field is not None:
                clean = apply_displacement(clean, field, 255)
                photo = apply_displacement(photo, field, white)
        c_ink = clear_edge_blobs(binarize(np.asarray(clean, dtype=np.float32)))
        bx0, by0, bx1, by1 = content_box(c_ink, margin=int(dpi * 0.15))
        clean = clean.crop((bx0, by0, bx1, by1))
        photo = photo.crop((bx0, by0, bx1, by1))
        out.append(ScanPage(clean, photo, dpi, angle, (x0 + bx0, by0), side))
    return out
