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

**"Take the tour"** walks all 54 entries in order, narrating each through the overlay
system's own lower third — the gallery introducing itself with the feature this mission
was built to demo. It ends at either end rather than looping, so it tells you when you
have seen everything.

54 entries in six categories:

| Category | Entries | What it holds |
|---|---|---|
| **Controls** | 20 | one entry per widget, live |
| **Layout** | 4 | `row-height` / `col-width` modes, size arithmetic, `overflow` — every box backgrounded, because the subject is where the edges land |
| **Recipes** | 4 | composed patterns: watch/repaint, a status line, a reusable style, and a shelf of four `item_template`s switched live |
| **Traps** | 5 | each trap runs **BROKEN and FIXED side by side**, with both snippets under the panel that drew them. Only the fix gets a Copy button |
| **Full page** | 4 | drawn on the **Gallery Viewer** console: an embedded engine view, a self-redrawing region, a master/detail console, and a **layout playground** whose dropdowns move the boxes under you |
| **Overlays** | 17 | every overlay kind, plus `announce()` and the audience/fan-out rules — see below |

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
sbs debug control_gallery --map 0        # browser: http://localhost:8765/server
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

That visits every specimen but only *draws* them: `--exercise` clicks nothing on these
screens by itself, so a green run without an explicit label list proves the specimens
built, not that any handler ran. To fire the overlay specimens, name their buttons in
`--exercise-click`. (The flag is comma-separated, so a button label containing a comma
cannot be driven.)

---

## Running it

**In the engine** (the only place draw order, input routing and region establishment are
real): launch Cosmos, pick **Control Gallery** from the mission browser, start the map,
and connect consoles.

**In the browser mock** (cheap first pass for layout and fan-out):

```
sbs debug control_gallery --map 0
```

then open `http://localhost:8765/server` for the gallery, or `/client` for a console —
a second tab gets a second console.

> The mission loads the **packaged** `.sbslib`. After editing `sbs_utils`, rebuild it
> (`python sbs.pyz lib sbs_utils` from `data/missions`) or the engine silently runs the
> old library. The mock can use the working tree directly with `--use-working-tree`.

## The Overlays category

The mission started as the overlay system's **verification harness**: two consoles and
31 buttons. Those consoles are gone — every one of them is now a gallery specimen, which
means each gets a source panel and a notes panel like everything else. A button that
fires an overlay never showed you the call that fired it, which was the whole complaint
the gallery answers.

### The audience dial

Twelve of those 31 buttons differed only in their `to=` argument — the one thing you
cannot see from a button. There is now **one dial** at the top of every overlay
specimen, and the line under it says what your pick **resolves to**:

| Pick | Resolves to | Expect |
|---|---|---|
| this screen | `to=client_id` | only the screen you are reading |
| gallery viewer | `to=role("gallery_viewer")` | the other surface — **nobody** until you open that console |
| my ship | `to=my_ship` | **every** console of that ship |
| mainscreen only | `to=my_ship, consoles="mainscreen"` | the main screen only; the console you clicked stays clear |
| my side | `to="tsn"` | every console of every `tsn` ship |
| all players | `to=role("__player__")` | everywhere (ships resolve to their consoles) |
| a station | `to=role("station")` | **nothing** — no console is aboard one |

That is the lesson of the category: `to=` takes ordinary values — a client id, a role
set, a ship id, a side name — and there is no overlay-specific addressing to learn.
`consoles=` is a *second* narrowing applied after `to=`, not an alternative to it.

Two picks legitimately reach nobody, and both are worth firing on purpose: an overlay
that does not appear is nearly always an audience that resolved to nothing.

### One console, morphed

The audience specimens need two surfaces, one of them a main screen. Rather than leave
the whole crew set on the selection screen, the **Gallery Viewer** morphs into any of
seven consoles ("morph the viewer"), so the mission offers exactly two consoles:
`gallery` and `gallery_viewer`. Turning a console off removes it from the selection
screen but does **not** unregister it, which is what makes that work.

The morph sets the console **role** as well as `CONSOLE_TYPE`. Audience narrowing goes
through `any_role()`, so a screen with the type and no role is invisible to overlays,
`announce()` and comms targeting — and the message is dropped in silence. It also clears
that client's overlays first: a hero card left from the gallery page has no business on
a mainscreen.

### announce()

Four specimens cover `announce()`, which fires the overlay **and** leaves the durable
record — the one to reach for by default:

| level | overlay | record |
|---|---|---|
| `chapter` | hero card | info-panel card |
| `alert` | top banner | info-panel card |
| `hail` | lower third | comms message (from `sender=`) |
| `status` | corner toast | none — the deliberate exception |

Check the info panel and comms as well as the overlay: a missing twin is the failure the
pairing exists to prevent.

- System design: `sbs_utils/OVERLAY_PLAN.md`
- When to use an overlay vs the info panel / comms: `sbs_utils/OVERLAY_ADOPTION_PLAN.md`
- API docs: `sbs_utils/mkdocs/docs/cosmos/overlays.md`

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

story.mast             the map, and the plumbing specimens use but do not own:
                       the //overlay custom-kind route, the modal and HUD-watcher
                       labels, and the signal bridge
overlays.amd           a declaratively-authored overlay (fired by key with overlay_amd)
quests.amd             a demo quest, for the quest lifecycle overlays
story.json             the packaged sbslib, LM mastlibs and media pack this mission loads
```

`media/` is deliberately **not** in the repo. The art comes from LegendaryMissions' media
pack, declared under `shared_media:` in `story.json` and resolved with `media_shared()` —
so the `gui_image` entry draws LM art this mission pins and never copies.
