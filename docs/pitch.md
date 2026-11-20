# Pitch notes for the GitHub README and release post

Lines and ideas collected while building xl-Cheeselooks, to use when writing
the README and the Reddit post. Not user documentation.

## What it themes, and how far it goes

> Full theming where the system allows it (GTK 3, plain GTK 4, Mint's
> libadwaita, Qt), colors plus opt-in full styling for Flatpak libadwaita
> apps, and robust CSS that doesn't depend on one version. That's about as
> far as a theme can reasonably go without fighting the platform.

(Chosen by xl_cheese, 20 Nov 2026. US spelling "colors", as in the app.)

Background, if the post needs it: libadwaita is deliberately not themeable
(GNOME gives app developers one fixed look to design against), and Flatpak
apps each bring their own libadwaita version. So the Tool themes everything
it can fully, gives Flatpak libadwaita apps your colors, and offers full
styling for them as an opt-in, written to work across libadwaita versions.

## Details people won't notice (the "Details" section)

See docs/design-spec.md, roadmap: "Release checklist: the README's Details
section" (before-and-after crops, and the numbers from
`tools/project-stats.py`).
