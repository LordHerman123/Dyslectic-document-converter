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

MIN_GUTTER = 5.0  # points (equation pictures are cropped with a little room)
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


def _rows_left_to_right(items: list[T], bbox_of) -> list[T]:
    """Top to bottom, and left to right within a row: things side by side (figure panels) that start
    a point higher or lower are still read in order."""
    rows: list[list[T]] = []
    for it in sorted(items, key=lambda it: (bbox_of(it)[1], bbox_of(it)[0])):
        b = bbox_of(it)
        h = b[3] - b[1]
        for row in rows:
            r = bbox_of(row[0])
            overlap = min(r[3], b[3]) - max(r[1], b[1])
            side_by_side = all(bbox_of(o)[2] <= b[0] + 1 or b[2] <= bbox_of(o)[0] + 1 for o in row)
            tall = h >= 20 and r[3] - r[1] >= 20  # pictures and tables; text lines keep top-to-bottom order
            if tall and side_by_side and overlap > 0.6 * min(h, r[3] - r[1]) \
                    and abs(r[1] - b[1]) < 0.25 * max(h, r[3] - r[1]):
                row.append(it)
                break
        else:
            rows.append([it])
    out: list[T] = []
    for row in rows:
        out += sorted(row, key=lambda it: bbox_of(it)[0])
    return out


def _shared_gutter(a: list, b: list, bbox_of) -> bool:
    """Whether two groups of items share a column gap (then they are columns of one layout)."""
    if len(a) < 2 or len(b) < 2:
        return False
    boxes = [bbox_of(it) for it in a + b]
    gaps = _gaps([(x[0], x[2]) for x in boxes], MIN_GUTTER)
    for g0, g1 in gaps:
        mid = (g0 + g1) / 2
        if all(sum(1 for it in part if bbox_of(it)[2] <= mid) >= 1 for part in (a, b)) and \
                sum(1 for x in boxes if x[0] >= mid) >= 2 and sum(1 for x in boxes if x[2] <= mid) >= 2:
            return True
    return False


def reading_order(items: Sequence[T], bbox_of=lambda it: it.bbox) -> list[T]:
    """Items (lines, figures) sorted into reading order: columns left to right, top to bottom within each (recursive
    XY-cut).
    """
    items = list(items)
    if len(items) <= 1:
        return items
    return _xycut(items, bbox_of, depth=0)


def _xycut(items: list[T], bbox_of, depth: int) -> list[T]:
    """Split the items at the widest gap (between columns, then between rows) and order each part; ``depth`` guards
    against endless splitting.
    """
    if len(items) <= 1 or depth > 40:
        return _rows_left_to_right(items, bbox_of)
    boxes = [bbox_of(it) for it in items]

    # 1) vertical gutter -> columns. A page number or other tiny mark at the very top or bottom may sit on
    # the gutter; it must not hide the columns
    top, bottom = min(b[1] for b in boxes), max(b[3] for b in boxes)
    region_w = max(b[2] for b in boxes) - min(b[0] for b in boxes)

    def stray(b) -> bool:
        """Whether a box is a tiny mark at the very top or bottom (a page number) that should not hide a column
        gap.
        """
        return b[2] - b[0] < max(20.0, 0.05 * region_w) and b[3] - b[1] < 15 and (b[1] - top < 1 or bottom - b[3] < 1)
    x_gaps = _gaps([(b[0], b[2]) for b in boxes if not stray(b)], MIN_GUTTER)
    if x_gaps:
        region_h = max(b[3] for b in boxes) - min(b[1] for b in boxes)
        # choose the widest gutter whose both sides hold real text columns
        best = None
        for g0, g1 in sorted(x_gaps, key=lambda g: g[1] - g[0], reverse=True):
            mid = (g0 + g1) / 2
            left = [b for b in boxes if b[2] <= mid and not stray(b)]
            right = [b for b in boxes if b[0] >= mid and not stray(b)]
            tall_l = max((b[3] for b in left), default=0) - min((b[1] for b in left), default=0)
            tall_r = max((b[3] for b in right), default=0) - min((b[1] for b in right), default=0)
            if (len(left) >= 2 and len(right) >= 2) or (tall_l > region_h * 0.3 and tall_r > region_h * 0.3):
                best = mid
                break
        if best is not None:
            left = [it for it in items if (bbox_of(it)[0] + bbox_of(it)[2]) / 2 <= best]
            right = [it for it in items if (bbox_of(it)[0] + bbox_of(it)[2]) / 2 > best]
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
        # two columns where one runs longer than the other leave white space across the page; bands that
        # share one gutter are still one pair of columns
        merged_bands: list[list[T]] = []
        for band in bands:
            if merged_bands and _shared_gutter(merged_bands[-1], band, bbox_of):
                merged_bands[-1] = merged_bands[-1] + band
            else:
                merged_bands.append(band)
        bands = merged_bands
        if len(bands) > 1:
            out: list[T] = []
            for band in bands:
                out += _xycut(band, bbox_of, depth + 1)
            return out

    return _rows_left_to_right(items, bbox_of)


def interleaved(ordered: Sequence[T], bbox_of=lambda it: it.bbox, text_of=lambda it: getattr(it, "text", None),
                min_steps: int = 3) -> bool:
    """Whether the reading order probably mixes two columns: again and again a line of prose is followed by a
    line of prose beside it at the same height. Correctly read columns never do that (their lines follow each
    other downwards); it happens when a box or a quote across the column gap hides the columns. Short text
    (chart labels, table cells, author lists) does not count.
    """
    lines = [it for it in ordered if isinstance(text_of(it), str)]
    steps = 0
    for a, b in zip(lines, lines[1:]):
        ba, bb = bbox_of(a), bbox_of(b)
        overlap = min(ba[3], bb[3]) - max(ba[1], bb[1])
        beside = bb[0] >= ba[2] - 1 or ba[0] >= bb[2] - 1
        prose = len(text_of(a).split()) >= 5 and len(text_of(b).split()) >= 5
        if beside and prose and overlap > 0.5 * min(ba[3] - ba[1], bb[3] - bb[1]):
            steps += 1
    return steps >= min_steps


def pieces(items: Sequence[T], bbox_of=lambda it: it.bbox, text_of=lambda it: getattr(it, "text", None),
           block_of=lambda it: getattr(it, "block_no", None), size_of=lambda it: getattr(it, "size", 0.0)
           ) -> list[list[T]]:
    """A page's items grouped into pieces that can be put in order as a whole (for the optional AI layout
    check): lines of one PDF text block in the same font size that follow each other downwards form a piece
    (a block holding lines side by side is split); every figure or table is its own piece. The pieces are
    numbered in the local reading order, so the same page always gives the same pieces.
    """
    rank = {id(it): n for n, it in enumerate(reading_order(items, bbox_of))}
    groups: list[list[T]] = []
    # lines top to bottom: each joins the piece of its own block and size whose last line is right above it
    for it in sorted(items, key=lambda it: (bbox_of(it)[1], bbox_of(it)[0])):
        if not isinstance(text_of(it), str):
            groups.append([it])
            continue
        b = bbox_of(it)
        h = max(1.0, b[3] - b[1])
        best, best_gap = None, None
        for group in groups:
            last = group[-1]
            if not isinstance(text_of(last), str) or block_of(last) != block_of(it) \
                    or abs(size_of(last) - size_of(it)) > 0.5:
                continue
            lb = bbox_of(last)
            overlap_x = min(lb[2], b[2]) - max(lb[0], b[0])
            gap = b[1] - lb[3]  # line boxes of tightly set text overlap a little
            if overlap_x > 0.3 * min(lb[2] - lb[0], b[2] - b[0]) and -0.6 * h <= gap < 2 * h \
                    and b[1] > lb[1] + 0.3 * h and (best_gap is None or gap < best_gap):
                best, best_gap = group, gap
        if best is not None:
            best.append(it)
        else:
            groups.append([it])
    return sorted(groups, key=lambda g: min(rank[id(it)] for it in g))


def column_order(groups: Sequence[Sequence[T]], bbox_of=lambda it: it.bbox,
                 text_of=lambda it: getattr(it, "text", None), size_of=lambda it: getattr(it, "size", 0.0)
                 ) -> list[int]:
    """A reading order for the pieces of a page whose columns got mixed up (used only on such pages): the
    columns are found from the running text alone (the box or quote that hid them is left out), each is read
    from top to bottom, left column first; titles above the columns come first, and anything lying across the
    column gap (a pull quote, a box, an advert) comes after the columns. Every piece appears exactly once.
    """
    boxes = [(min(bbox_of(it)[0] for it in g), min(bbox_of(it)[1] for it in g),
              max(bbox_of(it)[2] for it in g), max(bbox_of(it)[3] for it in g)) for g in groups]
    texts = [[text_of(it) for it in g if isinstance(text_of(it), str)] for g in groups]
    sizes: dict[float, int] = {}
    for g in groups:
        for it in g:
            if isinstance(text_of(it), str):
                sizes[round(size_of(it))] = sizes.get(round(size_of(it)), 0) + len(text_of(it))
    body = max(sizes, key=sizes.get) if sizes else 0
    running = [n for n, g in enumerate(groups) if texts[n] and all(abs(size_of(it) - body) <= 1.5 for it in g
                                                                   if isinstance(text_of(it), str))]
    # the column gaps: white space between the running text only (pieces of several lines: a centred byline or
    # a one-line caption may cross the gap)
    columns_text = [n for n in running if len(texts[n]) >= 2]
    gaps = _gaps([(boxes[n][0], boxes[n][2]) for n in columns_text], MIN_GUTTER)
    cuts = [(g0 + g1) / 2 for g0, g1 in gaps]
    if not cuts:
        return list(range(len(groups)))
    top = min(boxes[n][1] for n in columns_text)

    def column(n: int) -> int:
        """Which column a piece is in (by its middle)."""
        mid = (boxes[n][0] + boxes[n][2]) / 2
        return sum(1 for c in cuts if mid > c)

    def across(n: int) -> bool:
        """Whether a piece lies across a column gap."""
        return any(boxes[n][0] < c - MIN_GUTTER < c + MIN_GUTTER < boxes[n][2] for c in cuts)

    head, cols, after = [], {}, []
    for n in range(len(groups)):
        if boxes[n][3] <= top + 1:
            head.append(n)  # above the columns: title, standfirst, byline, opening picture
        elif across(n) and n not in running:
            after.append(n)  # pull quote, box, advert across the gap
        else:
            cols.setdefault(column(n), []).append(n)
    order = sorted(head, key=lambda n: (boxes[n][1], boxes[n][0]))
    for c in sorted(cols):
        order += sorted(cols[c], key=lambda n: (boxes[n][1], boxes[n][0]))
    return order + sorted(after, key=lambda n: (boxes[n][1], boxes[n][0]))



def untangle(ordered: Sequence[T], bbox_of=lambda it: it.bbox, text_of=lambda it: getattr(it, "text", None),
             size_of=lambda it: getattr(it, "size", 0.0), font_of=lambda it: getattr(it, "font", "")) -> list[T]:
    """Text wrapped around a pull quote inside a column: the order goes line by line from the short text lines
    to the quote beside them and back ("and the", "“Simplicity", "ways in which they", "is a virtue in"...).
    Such a run (two or more lines on each side, the two sides in a different type size or typeface) is put back in
    order: the text lines, on to the end of their sentence, then the quote."""
    out = list(ordered)

    def is_text(it) -> bool:
        return isinstance(text_of(it), str)

    def beside(a, b) -> bool:
        ba, bb = bbox_of(a), bbox_of(b)
        overlap = min(ba[3], bb[3]) - max(ba[1], bb[1])
        return (bb[0] >= ba[2] - 1 or ba[0] >= bb[2] - 1) and overlap > 0.15 * min(ba[3] - ba[1], bb[3] - bb[1])

    def same_side(a, b) -> bool:
        ba, bb = bbox_of(a), bbox_of(b)
        return min(ba[2], bb[2]) - max(ba[0], bb[0]) > 0.5 * min(ba[2] - ba[0], bb[2] - bb[0])

    i = 0
    while i < len(out) - 3:
        j = i
        while j + 1 < len(out) and is_text(out[j]) and is_text(out[j + 1]) and beside(out[j], out[j + 1]) \
                and (j == i or same_side(out[j - 1], out[j + 1])):
            j += 1
        run = out[i:j + 1]
        if len(run) < 4:
            i += 1
            continue
        a, b = run[0::2], run[1::2]
        sa = sorted(size_of(x) for x in a)[len(a) // 2]
        sb = sorted(size_of(x) for x in b)[len(b) // 2]
        fa = {font_of(x) for x in a}
        fb = {font_of(x) for x in b}
        if abs(sa - sb) < 0.5 and (fa & fb or not (fa and fb)):
            i = j + 1  # the same type: not a quote (two columns read across are handled elsewhere)
            continue
        before = out[i - 1] if i > 0 and is_text(out[i - 1]) else None
        if before is not None:
            main_a = abs(sa - size_of(before)) <= abs(sb - size_of(before))
        else:
            main_a = sa < sb
        main, quote = (a, b) if main_a else (b, a)
        main_size = sa if main_a else sb
        # the text goes on after the run to the end of its sentence; the quote comes after that
        k = j + 1
        if not str(text_of(main[-1])).rstrip().endswith((".", "!", "?", "”", "\"")):
            while k < len(out) and is_text(out[k]) and abs(size_of(out[k]) - main_size) < 0.5:
                k += 1
                if str(text_of(out[k - 1])).rstrip().endswith((".", "!", "?")):
                    break
        out[i:k] = main + out[j + 1:k] + quote
        i = k
    return out
