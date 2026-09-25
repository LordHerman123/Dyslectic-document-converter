"""Reading-order reconstruction (multi-column aware).

Uses a recursive XY-cut: a region is split at a vertical gutter when one
exists (columns are read left to right, each top to bottom); otherwise it is
split at horizontal white space (bands are read top to bottom). This gives
``column 1 -> column 2`` order for academic two-column layouts while keeping
full-width titles and figures in their natural place.
"""
from __future__ import annotations

from typing import Sequence, TypeVar

T = TypeVar("T")

MIN_GUTTER = 7.0  # points
MIN_HGAP = 3.0


def _gaps(intervals: list[tuple[float, float]], min_gap: float) -> list[tuple[float, float]]:
    """White-space gaps in the union of 1-D intervals."""
    if not intervals:
        return []
    intervals = sorted(intervals)
    gaps = []
    cur_end = intervals[0][1]
    for s, e in intervals[1:]:
        if s - cur_end >= min_gap:
            gaps.append((cur_end, s))
        cur_end = max(cur_end, e)
    return gaps


def reading_order(items: Sequence[T], bbox_of=lambda it: it.bbox) -> list[T]:
    items = list(items)
    if len(items) <= 1:
        return items
    return _xycut(items, bbox_of, depth=0)


def _xycut(items: list[T], bbox_of, depth: int) -> list[T]:
    if len(items) <= 1 or depth > 40:
        return sorted(items, key=lambda it: (bbox_of(it)[1], bbox_of(it)[0]))
    boxes = [bbox_of(it) for it in items]

    # 1) vertical gutter -> columns
    x_gaps = _gaps([(b[0], b[2]) for b in boxes], MIN_GUTTER)
    if x_gaps:
        region_h = max(b[3] for b in boxes) - min(b[1] for b in boxes)
        # choose the widest gutter whose both sides hold real text columns
        best = None
        for g0, g1 in sorted(x_gaps, key=lambda g: g[1] - g[0], reverse=True):
            mid = (g0 + g1) / 2
            left = [b for b in boxes if b[2] <= mid]
            right = [b for b in boxes if b[0] >= mid]
            tall_l = max((b[3] for b in left), default=0) - min((b[1] for b in left), default=0)
            tall_r = max((b[3] for b in right), default=0) - min((b[1] for b in right), default=0)
            if (len(left) >= 2 and len(right) >= 2) or (tall_l > region_h * 0.3 and tall_r > region_h * 0.3):
                best = mid
                break
        if best is not None:
            left = [it for it in items if bbox_of(it)[2] <= best]
            right = [it for it in items if bbox_of(it)[0] >= best]
            return _xycut(left, bbox_of, depth + 1) + _xycut(right, bbox_of, depth + 1)

    # 2) horizontal white space -> bands
    y_gaps = _gaps([(b[1], b[3]) for b in boxes], MIN_HGAP)
    if y_gaps:
        # Cut only at the widest gaps. Cutting at every inter-line gap would
        # slice a two-column band into rows and interleave the columns.
        widest = max(g1 - g0 for g0, g1 in y_gaps)
        cuts = [(g0 + g1) / 2 for g0, g1 in y_gaps if g1 - g0 >= widest * 0.75]
        bands: list[list[T]] = [[] for _ in range(len(cuts) + 1)]
        for it in items:
            b = bbox_of(it)
            cy = (b[1] + b[3]) / 2
            idx = sum(1 for c in cuts if cy > c)
            bands[idx].append(it)
        bands = [b for b in bands if b]
        if len(bands) > 1:
            out: list[T] = []
            for band in bands:
                out += _xycut(band, bbox_of, depth + 1)
            return out

    return sorted(items, key=lambda it: (bbox_of(it)[1], bbox_of(it)[0]))
