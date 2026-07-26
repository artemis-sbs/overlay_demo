# Overlay Demo

A standalone showcase and **verification harness** for the sbs_utils **overlay system** —
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
real): launch Cosmos, pick **Overlay Demo** from the mission browser, start the map, and
connect consoles.

**In the browser mock** (cheap first pass for layout and fan-out):

```
sbs debug overlay_demo --map 0
```

then open `http://localhost:8765/client` — a second tab gets a second console.

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
story.mast      both consoles, the //overlay route, HUD watcher, signal bridge
overlays.amd    a declaratively-authored overlay (fired by key with overlay_amd)
quests.amd      a demo quest, for the quest lifecycle overlays
story.json      the packaged sbslib + LM mastlibs this mission loads
```

`media/` is deliberately **not** in the repo: it is a copy of LegendaryMissions' art,
already supplied by the media resource zip declared in `story.json`.
