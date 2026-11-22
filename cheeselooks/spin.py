"""Spin buttons (a number field with − and + buttons), from the style's spin_gap.

GTK joins the field and its buttons into one box, as Mint-Y draws them. That
suits styles whose buttons are recessed like their fields (xl-Classic,
xl-Gummy). On styles whose buttons are raised with a drop shadow, the recessed
field and the raised buttons fought inside one box, and a disabled button let
the field show through it, so it looked paler and bigger (xl_cheese, 22 Nov).

spin_gap = N (pixels, 1 or more) draws them apart instead: the field like any
other text field, and the − + pair like a joined pair of ordinary buttons.
0 (the default) keeps them joined. Horizontal spin buttons only; vertical
ones stay stacked.

GTK 3: spinbutton > entry, button.down, button.up
GTK 4: spinbutton > text, button.down, button.up
"""

from __future__ import annotations

from . import palette as pal

GAP_RANGE = (0, 12)


def css(t: dict[str, str], gap: int, gtk4: bool = False) -> str:
    if gap <= 0:
        # joined: a disabled button's faded face let the field show through it,
        # paler than its neighbour; faded over the window color instead, as any
        # other disabled button looks
        faded = pal.mix(t["bg"], t["button"], 0.55)      # solid: nothing shows through
        return ("/* spin buttons: joined (the style's spin_gap is 0) */\n"
                f"spinbutton:not(.vertical) > button:disabled {{\n"
                f"  border-color: {faded};\n"
                f"  background-color: {faded};\n"
                f"  background-image: none; }}\n")
    g = "g4_" if gtk4 else ""
    field = "text" if gtk4 else "entry"
    focus = ":focus-within" if gtk4 else ":focus"
    r = t["r"]
    t = {**t, "alpha_button_disabled": pal.rgba(t["button"], 0.55)}
    sb = "spinbutton:not(.vertical)"

    def sh(state: str) -> str:                   # w.button.hover_g4_shadow, w.button.g4_shadow...
        return t[f"w.button.{state}{g}shadow"]

    return f"""/* spin buttons: the field and the − + pair apart (the style's spin_gap: {gap}px) */
{sb}, {sb}:hover, spinbutton{focus}:not(.vertical) {{
  padding: 0;
  border-color: transparent;
  background-color: transparent;
  background-image: none;
  box-shadow: none; }}
{sb} > {field} {{
  margin-right: {gap}px;
  border: 1px solid {t['w.entry.border']};
  border-radius: {r}px;
  background-color: {t['base']};
  box-shadow: {t[f'w.entry.{g}shadow']}; }}
spinbutton{focus}:not(.vertical) > {field} {{
  border-color: {t['w.entry.focus_border']};
  box-shadow: {t[f'w.entry.focus_{g}shadow']}; }}
{sb} > button {{
  border: 1px solid {t['w.button.border']};
  background-color: {t['button']};
  background-image: {t['button_grad']};
  box-shadow: {sh('')}; }}
{sb} > button:hover {{
  border-color: {t['w.button.hover_border']};
  background-color: {t['w.button.hover_color']};
  background-image: {t['w.button.hover_grad']};
  box-shadow: {sh('hover_')}; }}
{sb} > button:active {{
  border-color: {t['w.button.pressed_border']};
  background-color: {t['pressed']};
  background-image: linear-gradient(to bottom, {t['pressed_bottom']}, {t['pressed_top']});
  box-shadow: {sh('pressed_')}; }}
{sb} > button:disabled {{           /* faded like any disabled button */
  border-color: {t['w.button.border']};
  background-color: transparent;
  background-image: image({t['alpha_button_disabled']});
  box-shadow: none; }}
{sb} > button.down {{
  border-radius: {r}px 0 0 {r}px; }}
{sb} > button.up {{
  border-left-style: none;
  border-radius: 0 {r}px {r}px 0; }}
""" + (f"""/* ...but not in libadwaita's spin rows, where the field is part of the row */
row.spin spinbutton > text {{
  margin-right: 0; }}
row.spin spinbutton > button, row.spin spinbutton > button.up, row.spin spinbutton > button.down {{
  border-left-style: solid;
  border-radius: {r}px; }}
""" if gtk4 else "")
