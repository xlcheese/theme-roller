"""Spin buttons (a number field with − and + buttons), from the style's spin_gap.

GTK joins the field and its buttons into one box, as Mint-Y draws them. That
suits styles whose buttons are recessed like their fields (xl-Classic,
xl-Gummy). On styles whose buttons are raised with a drop shadow, the recessed
field and the raised buttons fought inside one box (xl_cheese, 22 Nov).

spin_gap = N (pixels, 1 or more) draws them apart instead: the field like any
other text field, and the − + like a joined pair of ordinary buttons.
0 (the default) keeps them joined. Horizontal spin buttons only; vertical
ones stay stacked.

Either way, disabled parts are drawn solid: their faded colors let whatever
was behind show through (a disabled − paler and bigger than the +, a disabled
field grey on dark themes).

GTK 3: spinbutton > entry, button.down, button.up
GTK 4: spinbutton > text, button.down, button.up
"""

from __future__ import annotations

from . import palette as pal

GAP_RANGE = (0, 12)

# Mint-Y's own spin button rules (base.css) are very specific (e.g.
# "spinbutton:not(.vertical) > entry + button:not(:active):hover"), and won
# over ours: the + lost its shadow, the − kept an accent edge beside a focused
# field, the field kept square corners on one side, and the + lost its
# raised edge at rest beside a disabled − (a rule six classes strong:
# "> button:disabled + button:not(:disabled):not(:active):not(:checked):not(:hover)").
# Classes no widget has, negated, raise ours above all of them (nine) without
# matching anything else.
STRONG = ("spinbutton:not(.vertical)" + "".join(f":not(.xl-{c})" for c in "abcdefgh"))


def _solid(over: str, color: str, amount: float) -> str:
    """color faded `amount` of the way over `over`, as one solid color (a
    color with transparency, e.g. a border, is used as it is)."""
    return pal.mix(over, color, amount) if color.startswith("#") else color


def css(t: dict[str, str], gap: int, gtk4: bool = False) -> str:
    sb = STRONG
    g = "g4_" if gtk4 else ""
    field = "text" if gtk4 else "entry"
    focus = ":focus-within" if gtk4 else ":focus"
    r = t["r"]
    border = t["w.button.border"]
    if gap <= 0:
        # joined: a disabled button keeps the button's outline, its face faded
        # toward the field, solid; a disabled field is a faded field, solid
        return f"""/* spin buttons: joined (the style's spin_gap is 0) */
{sb} > button:disabled {{
  border-color: {border};
  background-color: {pal.mix(t['base'], t['button'], 0.55)};
  background-image: none; }}
{sb}:disabled {{
  background-color: {pal.mix(t['bg'], t['base'], 0.55)}; }}
{sb}:disabled > {field} {{
  background-color: transparent; }}
"""

    def sh(state: str) -> str:                   # w.button.hover_g4_shadow, w.button.g4_shadow...
        return t[f"w.button.{state}{g}shadow"]

    def with_divider(shadow: str) -> str:       # the + has no left border: a line there instead
        line = f"inset 1px 0 {border}"
        return line if shadow == "none" else f"{line}, {shadow}"

    out = f"""/* spin buttons: the field and the − + apart (the style's spin_gap: {gap}px) */
{sb}, {sb}:hover, {sb}{focus}, {sb}:disabled {{
  padding: 0;
  border-color: transparent;
  background-color: transparent;
  background-image: none;
  box-shadow: none; }}
{sb} > {field}, {sb}:dir(ltr) > {field}, {sb}:dir(rtl) > {field} {{
  margin-right: {gap}px;
  border: 1px solid {t['w.entry.border']};
  border-radius: {r}px;
  background-color: {t['base']};
  box-shadow: {t[f'w.entry.{g}shadow']}; }}
{sb}{focus} > {field} {{
  border-color: {t['w.entry.focus_border']};
  box-shadow: {t[f'w.entry.focus_{g}shadow']}; }}
{sb}:disabled > {field} {{
  border-color: {_solid(t['bg'], t['w.entry.border'], 0.55)};
  background-color: {pal.mix(t['bg'], t['base'], 0.55)};
  box-shadow: none; }}
{sb} > button, {sb} > {field} + button, {sb} > {field}{focus} + button {{
  border: 1px solid {border};
  background-color: {t['button']};
  background-image: {t['button_grad']};
  box-shadow: {sh('')}; }}
{sb} > button + button {{
  border-left-style: none;
  box-shadow: {with_divider(sh(''))}; }}
{sb} > button:hover, {sb} > {field} + button:hover {{
  border-color: {t['w.button.hover_border']};
  background-color: {t['w.button.hover_color']};
  background-image: {t['w.button.hover_grad']};
  box-shadow: {sh('hover_')}; }}
{sb} > button + button:hover {{
  box-shadow: {with_divider(sh('hover_'))}; }}
{sb} > button:active, {sb} > button + button:active {{
  border-color: {t['w.button.pressed_border']};
  background-color: {t['pressed']};
  background-image: linear-gradient(to bottom, {t['pressed_bottom']}, {t['pressed_top']});
  box-shadow: {sh('pressed_')}; }}
{sb} > button:disabled, {sb} > {field} + button:disabled {{
  border-color: {border};
  background-color: {pal.mix(t['bg'], t['button'], 0.55)};
  background-image: none;
  box-shadow: none; }}
{sb} > button + button:disabled {{
  box-shadow: inset 1px 0 {border}; }}
{sb} > button.down, {sb}:dir(ltr) > button.down {{
  border-radius: {r}px 0 0 {r}px; }}
{sb} > button.up, {sb}:dir(ltr) > button.up {{
  border-radius: 0 {r}px {r}px 0; }}
"""
    if gtk4:
        out += f"""/* ...but not in libadwaita's spin rows, where the field is part of the row */
row.spin {sb} > text {{
  margin-right: 0;
  border-color: transparent;
  background-color: transparent;
  box-shadow: none; }}
row.spin {sb} > button, row.spin {sb} > button.up, row.spin {sb} > button.down {{
  border-left-style: solid;
  border-radius: {r}px; }}
"""
    return out
