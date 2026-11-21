#!/usr/bin/env python3
"""Draw the Claude folder style: a file pocket, turned the other way.

    python3 tools/make-claude-folder.py

Claude's design (21 Nov, xl_cheese asked for one of its own, "turned the
other way to set it apart from the Linux ones"): a card portfolio. A back
panel with a tab, a front pocket with a thumb notch at the top, a sheet of
paper showing in it, and a stitched edge round the pocket. Seen from below
and to the right, so its right edge shows (xl-Big Baddy shows its left; the
Linux styles face you).

Drawn in true perspective from 3D at 32px and up, Mint-Y's pictures (CC BY-SA
4.0) on the pocket, centred, by the same projection (affine over their box).
At 16, 22 and 24px straight on, on whole pixels, Mint-Y's picture at its own
size; no stitching there (it would be a smudge). Open (drag-accept): the
sheets pulled up out of the pocket.

Placeholder colours (cheeselooks/icons.py):
    #c1a0d1 the pocket (your folder color)     #c1a0d3 its edge (the pocket, darker)
    #c1a0d2 the back panel (second color)      #c1a0d4 the picture (emblem)
"""
from __future__ import annotations

import math
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import smallsize  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "icons" / "claude" / "places"
SVG, XLINK = smallsize.SVG, smallsize.XLINK
FRONT, BACK, EDGE, EMBLEM = "#c1a0d1", "#c1a0d2", "#c1a0d3", "#c1a0d4"
PAPER, PAPER_SHADE, STITCH = "#F7F4EE", "#E6E1D8", "#FFFFFF"
SIZES = (16, 22, 24, 32, 48, 64, 96, 128)
SMALL = (16, 22, 24)

W, H = 96.0, 80.0             # the back panel (u right, v up); the tab rises above
POCKET = 54.0                 # the pocket's height at its sides
T = 6.0                       # the folder's thickness
NOTCH = (W / 2, 26.0, 7.0)    # thumb notch: centre, width, depth
YAW, PITCH, CAM = math.radians(-34), math.radians(-13), 210.0
PIC = 30.0
FIT = 112.0


def project(u, v, z):
    x, y, zz = u - W / 2, v - H / 2, z + T / 2
    x, zz = x * math.cos(YAW) + zz * math.sin(YAW), -x * math.sin(YAW) + zz * math.cos(YAW)
    y, zz = y * math.cos(PITCH) - zz * math.sin(PITCH), y * math.sin(PITCH) + zz * math.cos(PITCH)
    k = CAM / (CAM - zz)
    return x * k, -y * k


def d(pts3, close=True):
    p = [project(*q) for q in pts3]
    return "M" + " L".join(f"{x:.2f} {y:.2f}" for x, y in p) + (" Z" if close else "")


def rounded(x0, y0, x1, y1, r, corners="tl tr br bl", n=6):
    pts = []
    for name, cx, cy, a0 in (("tl", x0 + r, y1 - r, 180), ("tr", x1 - r, y1 - r, 90),
                             ("br", x1 - r, y0 + r, 0), ("bl", x0 + r, y0 + r, 270)):
        if name in corners:
            pts += [(cx + r * math.cos(math.radians(a0 - 90 * i / n)),
                     cy + r * math.sin(math.radians(a0 - 90 * i / n))) for i in range(n + 1)]
        else:
            pts.append({"tl": (x0, y1), "tr": (x1, y1), "br": (x1, y0), "bl": (x0, y0)}[name])
    return pts


def pocket_outline(inset=0.0, n=14):
    """The pocket, going round: bottom corners rounded, the top with its notch."""
    top = POCKET - inset
    cu, nw, nd = NOTCH
    pts = rounded(inset, inset, W - inset, top, 7 - inset * 0.5, "br bl")
    # rounded() goes tl, tr, br, bl: insert the notch between tl and tr
    tl, rest = pts[0], pts[1:]
    notch = []
    for i in range(n + 1):
        t = i / n
        u = cu - nw / 2 + nw * t
        notch.append((u, top - (nd - inset * 0.3) * math.sin(math.pi * t) ** 1.4))
    return [tl] + notch + rest


def front(pts, z=0.0):
    return [(u, v, z) for u, v in pts]


def picture3d(name: str, size: int) -> list:
    found = smallsize.compose.mint_picture(name, size)
    if found is None:
        return monitor3d() if name == "user-desktop" else []
    pic, (x0, y0, x1, y1) = found
    k = PIC / max(x1 - x0, y1 - y0)
    cu, cv = W / 2, POCKET * 0.44

    def to_pocket(x, y):
        return (cu + (x - (x0 + x1) / 2) * k, cv - (y - (y0 + y1) / 2) * k)
    (ax, ay), (bx, by), (cx, cy) = (project(*to_pocket(x, y), 0.05) for x, y in ((x0, y0), (x1, y0), (x0, y1)))
    a, b = (bx - ax) / (x1 - x0), (by - ay) / (x1 - x0)
    c, dd = (cx - ax) / (y1 - y0), (cy - ay) / (y1 - y0)
    e, f = ax - a * x0 - c * y0, ay - b * x0 - dd * y0
    inner = re.sub(smallsize.MINT_EMBLEM, EMBLEM, ET.tostring(pic, encoding="unicode"), flags=re.I)
    g = ET.Element(f"{{{SVG}}}g", {"transform": f"matrix({a:.5f} {b:.5f} {c:.5f} {dd:.5f} {e:.4f} {f:.4f})"})
    for child in list(ET.fromstring(inner)):
        g.append(child)
    return [ET.tostring(g, encoding="unicode")]


def monitor3d() -> list:
    cu, cv = W / 2, POCKET * 0.44
    w, h = PIC, PIC * 0.66
    top = cv + h / 2 + 3
    outer = rounded(cu - w / 2, top - h, cu + w / 2, top, 2.5)
    inner = rounded(cu - w / 2 + 3, top - h + 3, cu + w / 2 - 3, top - 3, 1)
    stand = [(cu - 3, top - h), (cu + 3, top - h), (cu + 4, top - h - 4), (cu + 9, top - h - 4),
             (cu + 9, top - h - 6.5), (cu - 9, top - h - 6.5), (cu - 9, top - h - 4), (cu - 4, top - h - 4)]
    return [f'<path fill="{EMBLEM}" fill-rule="evenodd" d="{d(front(outer, 0.05))} {d(front(inner[::-1], 0.05))}"/>',
            f'<path fill="{EMBLEM}" d="{d(front(stand, 0.05))}"/>']


def folder3d(name: str, size: int, opened: bool = False) -> str:
    parts = []
    # the back panel, with its tab at the top left, and its edge on the right
    back = rounded(0, 0, W, H, 5, "tr br bl")
    tab = [(0, H - 4), (0, H + 6), (4, H + 9), (30, H + 9), (35, H + 5), (40, H + 1), (42, H)]
    panel = [(u, v) for u, v in back[:1]] + tab + back[1:]
    parts.append(f'<path fill="{BACK}" d="{d([(W, v, z) for v, z in ((0, -T), (H - 5, -T), (H - 5, -T + 1.5), (0, -T + 1.5))])}"/>')
    parts.append(f'<path fill="{BACK}" d="{d(front(panel, -T))}"/>')
    parts.append(f'<path fill="#fff" fill-opacity="0.18" d="{d(front([(4, H + 8), (30, H + 8), (30, H + 9), (4, H + 9)], -T + 0.05))}"/>')
    # the papers: a sheet showing over the pocket (pulled up when open)
    lift = 16 if opened else 0
    sheets = ((7, W - 9, POCKET + 14 + lift * 0.7, -T * 0.66, PAPER_SHADE), (5, W - 5, POCKET + 18 + lift, -T * 0.4, PAPER))
    for u0, u1, top, z, colour in sheets:
        parts.append(f'<path fill="{colour}" d="{d(front(rounded(u0, 3, u1, top, 2, "tl tr"), z))}"/>')
    for i in range(3):     # a few lines of writing on the top sheet
        v = POCKET + 14 + lift - i * 4.5
        parts.append(f'<path fill="{PAPER_SHADE}" d="{d(front([(12, v), (W - 20 - i * 9, v), (W - 20 - i * 9, v + 1.3), (12, v + 1.3)], -T * 0.4 + 0.05))}"/>')
    # the pocket's right edge (its thickness), then the pocket
    outline = pocket_outline()
    right = [(u, v) for u, v in outline if u >= W - 0.01]
    v_top = max(v for _u, v in right)
    parts.append(f'<path fill="{EDGE}" d="{d([(W, 0.5, 0), (W, v_top, 0), (W, v_top, -1.6), (W, 0.5, -1.6)])}"/>')
    parts.append(f'<path fill="{FRONT}" d="{d(front(outline))}"/>')
    # the pocket's top edge catches the light; a shade under the notch
    parts.append(f'<path fill="none" stroke="#fff" stroke-opacity="0.35" stroke-width="1.6" '
                 f'd="{d(front([q for q in outline[:16]], 0.03), close=False)}"/>')
    # the stitching round it
    stitch = pocket_outline(4.2)
    parts.append(f'<path fill="none" stroke="{STITCH}" stroke-opacity="0.7" stroke-width="1.5" stroke-dasharray="4.5 3.5" '
                 f'd="{d(front(stitch, 0.04))}"/>')
    # fit by the folder alone (the picture's own coordinates would mislead)
    nums = [(float(a), float(b)) for a, b in re.findall(r"(-?\d+\.\d+) (-?\d+\.\d+)", "".join(parts))]
    parts += picture3d(name, size)
    body = "".join(parts)
    bx0, bx1 = min(p[0] for p in nums), max(p[0] for p in nums)
    by0, by1 = min(p[1] for p in nums), max(p[1] for p in nums)
    s = min(FIT / (bx1 - bx0), 122 / (by1 - by0))
    tx, ty = 64 - s * (bx0 + bx1) / 2, 64 - s * (by0 + by1) / 2
    k = size / 128
    return (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="{XLINK}" width="{size}" height="{size}" '
            f'viewBox="0 0 {size} {size}" version="1.1"><g transform="matrix({s * k:.5f} 0 0 {s * k:.5f} '
            f'{tx * k:.4f} {ty * k:.4f})" stroke-linejoin="round" stroke-linecap="round">{body}</g></svg>\n')


# ------------------------------------------------------------------ small, straight on
SMALL_GEO = {   # size: x0, x1 (pocket), back top, pocket top, bottom, notch half-width
    16: (1, 15, 2, 6, 15, 2),
    22: (2, 20, 3, 10, 19, 3),
    24: (2, 22, 3, 11, 21, 3),
}


def folder_small(name: str, size: int, opened: bool = False) -> str:
    x0, x1, bt, pt, bot, nh = SMALL_GEO[size]
    parts = []
    # the back panel with its tab, its right edge a shade
    tab_w = (x1 - x0) * 2 // 5
    parts.append(f'<path fill="{BACK}" d="M{x0} {bt} h{tab_w} l1 1 H{x1 - 1} q1 0 1 1 V{bot} H{x0} Z"/>')
    # paper: a sheet over the pocket's top (higher when open)
    up = 2 if opened else 0
    parts.append(f'<rect x="{x0 + 1}" y="{bt + 2 - up}" width="{x1 - x0 - 2}" height="{pt - bt}" fill="{PAPER}"/>')
    if size > 16:
        parts.append(f'<rect x="{x0 + 3}" y="{bt + 4 - up}" width="{x1 - x0 - 8}" height="1" fill="{PAPER_SHADE}"/>')
    # the pocket, its notch at the top centre
    cx = (x0 + x1) / 2
    parts.append(f'<path fill="{FRONT}" d="M{x0} {pt} H{cx - nh} Q{cx} {pt + nh * 0.9} {cx + nh} {pt} H{x1} '
                 f'V{bot - 1} q0 1 -1 1 H{x0 + 1} q-1 0 -1 -1 Z"/>')
    parts.append(f'<rect x="{x1 - 1}" y="{pt + 1}" width="1" height="{bot - pt - 2}" fill="{EDGE}"/>')
    pic = smallsize.mint_picture(name, size, cx - 0.5, (pt + bot) / 2 + 0.5, EMBLEM)
    extra = ""
    if pic is not None:
        extra = ET.tostring(pic, encoding="unicode")
    elif name == "user-desktop":
        mw, mh = (7, 5) if size == 16 else (9, 6)
        mx, my = round(cx - mw / 2), round((pt + bot) / 2 - mh / 2)
        extra = (f'<path fill="{EMBLEM}" fill-rule="evenodd" d="M{mx} {my} h{mw} v{mh} h{-mw} Z '
                 f'M{mx + 1} {my + 1} v{mh - 2} h{mw - 2} v{-(mh - 2)} Z"/>'
                 f'<rect fill="{EMBLEM}" x="{mx + mw // 2 - 1}" y="{my + mh}" width="{3 if mw > 7 else 2}" height="1"/>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="{XLINK}" width="{size}" height="{size}" '
            f'viewBox="0 0 {size} {size}" version="1.1">{"".join(parts)}{extra}</svg>\n')


def main() -> int:
    ET.register_namespace("", SVG)
    ET.register_namespace("xlink", XLINK)
    count = 0
    for size in SIZES:
        for name in smallsize.mint_names():
            opened = name == "folder-drag-accept"
            svg = (folder_small if size in SMALL else folder3d)(name, size, opened)
            f = OUT / str(size) / f"{name}.svg"
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(svg, encoding="utf-8")
            count += 1
    print(f"{count} icons written to {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
