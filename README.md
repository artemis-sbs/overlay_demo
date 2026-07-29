# Control Gallery

A browsable catalog of the Cosmos GUI, in the shape of Material Design's component
gallery — and, in its **Overlays** category, the original overlay verification harness
this mission started as.

**Start the map and it is already on the server screen** — no console to pick, no ship
required, which is what a tool should be. ("Main screen" in the header hands the screen
back to LegendaryMissions' own view.) The same browser is also a console, and the
**Gallery Viewer** console draws the full-page examples.

Left is the index; right is the live control, and under it **the source that built it** —
sliced out of `gallery.mast` at runtime between `# >>gallery: key` and `# <<gallery`.
The snippet cannot drift from the specimen, because it *is* the specimen. "Copy" puts it
on your clipboard.

The slicer is language-agnostic (`.mast` and `.py` both comment with `#`), so one key
can span both files: the `gui_list_box` entry shows the MAST line **and** the Python
`item_template` it points at — which is how real missions pair the two.

**"Take the tour"** walks all 37 entries in order, narrating each through the overlay
system's own lower third — the gallery introducing itself with the feature this mission
was built to demo. It ends at either end rather than looping, so it tells you when you
have seen everything.

| Category | What it holds |
|---|---|
| **Controls** | one entry per widget, live |
| **Layout** | `row-height` / `col-width` modes, size arithmetic, `overflow` — every box backgrounded, because the subject is where the edges land |
| **Recipes** | composed patterns: watch/repaint, a status line, a reusable style, and a shelf of four `item_template`s switched live |
| **Traps** | each trap runs **BROKEN and FIXED side by side**, with both snippets under the panel that drew them. Only the fix gets a Copy button |
| **Full page** | drawn on the **Gallery Viewer** console: an embedded engine view, a self-redrawing region, a master/detail console, and a **layout playground** whose dropdowns move the boxes under you |
| **Overlays** | the two consoles below — every overlay kind, and the audience/fan-out checklist |

## Adding an entry

Two things, joined by the key:

1. a record in **`gallery.amd`** — `## [Display](key)`, a `---` fence with `Category:`
   (and `Kind: trap` or `Kind: page`), then a body whose **first line is the blurb** and
   whose remainder is the notes panel. File order is nav order, and consecutive records
   sharing a `Category` collapse under one header — so the shape of that file is the
   shape of the menu.
2. a **marked span** with the same key in `gallery.mast`, `gallery_pages.mast` or
   `gallery_specimens.py`. A trap needs two: `<key>_broken` and `<key>_fixed`.

Nothing else. No code to touch for a new entry, and a record naming a key that has no
span shows up in the source panel rather than silently doing nothing.

Design and roadmap: `sbs_utils/GALLERY_PLAN.md`.

```
sbs debug overlay_demo --map 0        # browser: http://localhost:8765/server
```

Specimens are checked headless. A custom console is only reachable with
`--exercise-console`, and `on change` / watcher blocks only run with a long
`--exercise-dwell` — at the default the exerciser leaves a console in well under a
sim-second, so watcher code never executes at all:

```
--test 40 --map 0 --exercise --exercise-console gallery,gallery_viewer --exercise-dwell 30
```

`--exercise-click "Take the tour,Next"` drives the tour, so **one boot visits every
specimen** instead of one boot each — the mastlib compile is most of a run's cost.

---

## Overlays

The original **verification harness** for the sbs_utils **overlay system** —
screen-anchored surfaces (hero cards, lower thirds, banners, toasts, a modal choice, a
live HUD, letterbox / flash / credits) drawn *on top of* a console's page and its
embedded engine views, updated without repainting the page underneath.

Every overlay feature is one button away, so a change to the overlay layer can be
eyeballed in a real Cosmos session in about a minute.

- System design: `sbs_utils/OVERLAY_PLAN.md`
- When to use an overlay vs the info panel / comms: `sbs_utils/OVERLAY_ADOPTION_PLAN.md`
- API docs: `sbs_utils/mkdocs/docs/cosmos/overlays.md`

## Running it

**In the engine** (the only place draw order, input routing and region establishment are
real): launch Cosmos, pick **Control Gallery** from the mission browser, start the map,
and connect consoles.

**In the browser mock** (cheap first pass for layout and fan-out):

```
sbs debug overlay_demo --map 0
```

then open `http://localhost:8765/server` for the gallery, or `/client` for a console —
a second tab gets a second console.

> The mission loads the **packaged** `.sbslib`. After editing `sbs_utils`, rebuild it
> (`python sbs.pyz lib sbs_utils` from `data/missions`) or the engine silently runs the
> old library. The mock can use the working tree directly with `--use-working-tree`.

## The two consoles

### Overlay Demo — every kind

Each button fires one overlay **on the console you clicked**, over a live 3D view, so
you are looking at draw-layer stacking against a real engine widget: hero card, top
banner, corner toast (click repeatedly — toasts stack), lower third, modal choice
(returns an awaitable), sticky HUD with a live watcher and a toggle control, an overlay
declared in `overlays.amd`, a card built by a `//overlay/<kind>` MAST route, a quest
completion overlay, a signal-driven show, letterbox, flash, rolling credits, clear.

### Overlay Audience — who sees it

`to` is an **audience expression**, so this console targets ships and sides rather than
one console. **Connect two or more consoles, one of them a main screen** — with a single
console these are indistinguishable from targeting yourself.

| Button | Expected |
|---|---|
| 1. To my SHIP | banner on **every** console of your ship, no others |
| 2. MAINSCREEN only | hero on the main screen only; the console you clicked stays clear |
| 3. To my SIDE | banner on every console of every `tsn` ship |
| 4. To ALL player ships | toast everywhere (ships resolve to their consoles) |
| 5. To a STATION | **nothing** — plus one `resolved to no console` line in the log |
| 6. announce chapter | hero **and** a card in the info panel |
| 7. announce alert | banner **and** a card |
| 8. announce hail | lower third **and** a comms message from the station |
| 9. announce status | toast only — the info panel must stay empty |
| 10. long headline | banner is one clamped ASCII line; the card holds the full text |
| Clear (console / ship) | clears just yours, vs the whole ship |

Buttons 6-9 exercise `announce()`, which fires the overlay **and** leaves the durable
record. Check the info panel and comms too — a missing twin is the failure the pairing
exists to prevent.

## What to watch for

The overlay layer's historical failure modes, all engine-only:

- **Content landing at root instead of in the slot** — looks like "it rendered, just in
  the wrong place, and won't clear".
- **The first show of a slot** forces one page repaint to establish its sub-region: the
  page underneath must come back intact.
- **Re-showing a live slot** (click a button twice) is the region-ghosting path.
- **Clearing** must actually clear (an empty back buffer is not swapped forward, so a
  clear still emits an invisible placeholder).

If something doesn't draw, `overlay_debug_log(path)` writes the exact `send_gui_*`
command stream to a file you can read — the engine's `get_debug_gui_tree` is painted,
not copyable.

## Layout

```
gallery.amd            the index AND the prose: one record per entry
gallery.mast           the browser shell + the Controls, Layout, Recipes and Traps specimens
gallery_pages.mast     the Gallery Viewer console + the full-page specimens
gallery_specimens.py   the Python templates specimens reference (marked with the same keys)
gallery_code.py        chrome: the source slicer, the code view, the index loader, the tour

story.mast             the map, the two Overlays consoles, the //overlay route, signal bridge
overlays.amd           a declaratively-authored overlay (fired by key with overlay_amd)
quests.amd             a demo quest, for the quest lifecycle overlays
story.json             the packaged sbslib, LM mastlibs and media pack this mission loads
```

`media/` is deliberately **not** in the repo. The art comes from LegendaryMissions' media
pack, declared under `shared_media:` in `story.json` and resolved with `media_shared()` —
so the `gui_image` entry draws LM art this mission pins and never copies.
