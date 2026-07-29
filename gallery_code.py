# Control Gallery -- infrastructure.
#
# The gallery's one idea: a specimen and the source that built it are the SAME
# lines. Every specimen in the .mast files is wrapped in markers:
#
#     # >>gallery: button_basic
#         on gui_message(gui_button("Fire")):
#             log("fired")
#     # <<gallery
#
# At runtime we read the mission's own .mast files, slice between the markers,
# dedent, and render the result next to the live control. The snippet cannot go
# stale, because it is the thing you are looking at.
#
# Everything here is CHROME. The teaching material lives in the .mast files.
#
# NOTE: names at module level in an `import x.py` land in the shared MAST global
# namespace, so everything is prefixed `gallery_` / `GALLERY_`.

from sbs_utils.procedural.gui import (
    gui_row, gui_text, gui_section, gui_clipboard_put, gui_list_box,
    gui_list_box_header)
from sbs_utils.helpers import gui_text_escape
from sbs_utils.fs import get_mission_dir_filename
from sbs_utils.procedural.execution import log


GALLERY_MARK_BEGIN = "# >>gallery:"
GALLERY_MARK_END = "# <<gallery"

# Files scanned for marked spans, in order. Both .mast and .py comment with
# '#', so the slicer is language-agnostic -- and a specimen that pairs a .mast
# listbox with a Python row template can mark BOTH under the same key, which
# concatenates them into one snippet. Add a file here when you add a category.
GALLERY_SOURCE_FILES = [
    "gallery.mast",
    "gallery_pages.mast",
    "gallery_specimens.py",
]

# key -> list[str], filled on first use.
GALLERY_SNIPPETS = {}


# ---------------------------------------------------------------------------
# Slicing
# ---------------------------------------------------------------------------

def gallery_dedent(lines):
    """Strip the common leading indent, so a span nested in a `match` case reads
    as if it were written at the top level."""
    indents = [len(ln) - len(ln.lstrip()) for ln in lines if ln.strip()]
    if not indents:
        return lines
    cut = min(indents)
    return [ln[cut:] if ln.strip() else "" for ln in lines]


def gallery_scan_file(filename):
    """Pull every marked span out of one mission file into GALLERY_SNIPPETS."""
    path = get_mission_dir_filename(filename)
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.read().split("\n")
    except OSError as e:
        log(f"gallery: cannot read {filename}: {e}", "gallery", "warning")
        return

    key = None
    span = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(GALLERY_MARK_BEGIN):
            key = stripped[len(GALLERY_MARK_BEGIN):].strip()
            span = []
        elif stripped.startswith(GALLERY_MARK_END):
            if key is not None:
                cut = gallery_dedent(span)
                if key in GALLERY_SNIPPETS:
                    # Same key in a second file: append, separated by a blank
                    # line, so a snippet can span .mast and .py.
                    GALLERY_SNIPPETS[key] = GALLERY_SNIPPETS[key] + [""] + cut
                else:
                    GALLERY_SNIPPETS[key] = cut
            key = None
            span = []
        elif key is not None:
            span.append(line.rstrip())

    if key is not None:
        log(f"gallery: unterminated span '{key}' in {filename}", "gallery", "warning")


def gallery_load_sources():
    """Scan every gallery source file once. Safe to call repeatedly."""
    if GALLERY_SNIPPETS:
        return
    for filename in GALLERY_SOURCE_FILES:
        gallery_scan_file(filename)
    log(f"gallery: loaded {len(GALLERY_SNIPPETS)} snippets", "gallery")


def gallery_source(key):
    """The dedented source lines for a specimen, or a one-line complaint."""
    gallery_load_sources()
    return GALLERY_SNIPPETS.get(key, [f"# no marked span '{key}' found"])


def gallery_source_text(key):
    return "\n".join(gallery_source(key))


def gallery_copy(key):
    """Put a specimen's source on the clipboard (Windows only; harmless if it
    fails, which is what it does under the headless mock)."""
    try:
        gui_clipboard_put(gallery_source_text(key))
        return True
    except Exception as e:
        log(f"gallery: clipboard unavailable: {e}", "gallery", "warning")
        return False


# ---------------------------------------------------------------------------
# Rendering code
#
# gui_text_area is NOT usable for this. Its mini-markdown eats source: a line
# starting with '#' -- a MAST comment -- becomes an h1, '-' becomes a bullet,
# and '$' / '=$' are style directives. So code renders as one gui_text per line.
#
# Two escapes are mandatory on every line:
#   * braces, because gui_text f-string-formats any props containing '{'.
#     '{{' survives compile_format_string as a literal '{'.
#   * ':' and ';', because they would otherwise inject style properties.
#     gui_text_escape() backtick-quotes the value (issue #569).
# ---------------------------------------------------------------------------

GALLERY_CODE_FONT = "gui-1"
GALLERY_CODE_INDENT_PX = 14

GALLERY_COLOR_CODE = "#cde"
GALLERY_COLOR_COMMENT = "#6a8"
GALLERY_COLOR_MARK = "#fc8"


def gallery_label(text):
    """Make ANY text safe to hand to gui_text as a $text: value.

    Two hazards, and authored prose hits both as readily as source code does:
      * ':' and ';' would inject style properties -- gui_text_escape backticks it.
      * '{' makes gui_text f-string-format the whole props string. A blurb saying
        "use data={}" is an empty format field and raises at present time. '{{'
        survives compile_format_string as a literal '{'.

    Use this for every dynamic value that reaches a style string, not just code
    (the blurb "Use data={} and read it back" is what taught us that).
    """
    return gui_text_escape(text).replace("{", "{{").replace("}", "}}")


# Source lines are just text with the same two hazards.
gallery_code_escape = gallery_label


def gallery_code_items(key):
    """Source lines as listbox items: indent measured, color decided."""
    items = []
    for line in gallery_source(key):
        stripped = line.strip()
        indent = (len(line) - len(line.lstrip())) if stripped else 0
        color = GALLERY_COLOR_COMMENT if stripped.startswith("#") else GALLERY_COLOR_CODE
        items.append({"text": stripped, "indent": indent, "color": color})
    return items


def gallery_code_row(item):
    """Listbox item template for one line of code.

    Sizes the ROW and returns None -- a template that returns a size leaves the
    item section degenerate. Indent is drawn as left padding rather than spaces,
    which the engine may trim out of a quoted value.
    """
    pad = GALLERY_CODE_INDENT_PX * item["indent"] // 4
    gui_row(f"row-height: 1em; font:{GALLERY_CODE_FONT};")
    gui_text(
        f"$text:{gallery_code_escape(item['text'])};font:{GALLERY_CODE_FONT};color:{item['color']};",
        f"padding: {pad}px, 0, 0, 0;")


# ---------------------------------------------------------------------------
# Chrome
# ---------------------------------------------------------------------------

GALLERY_PANEL_COLOR = "#8cf"


def gallery_frame(title, area, color=None):
    """Open a titled panel. The caller keeps adding rows into it."""
    if color is None:
        color = GALLERY_PANEL_COLOR
    gui_section(f"area: {area};")
    gui_row("row-height: 1.4em; font:gui-2;")
    gui_text(f"$text:{gallery_label(title)};font:gui-2;color:{color};")


def gallery_caption(text, color="#9ab"):
    """A what-to-watch-for line above a specimen. Deliberately OUTSIDE the marked
    spans, so it never turns up in the snippet."""
    gui_row("row-height: content; font:gui-1;")
    gui_text(f"$text:{gallery_label(text)};font:gui-1;color:{color};")


def gallery_prose(text):
    """Authored prose for gui_text_area. Braces must be doubled (a text area
    f-string-formats its props too), but NOTHING else is escaped: the markdown --
    `#` headings, `-` bullets -- is the point of using a text area for notes."""
    return (text or "").replace("{", "{{").replace("}", "}}")


def gallery_notes_panel(entry, area):
    """The NOTES panel: everything in the AMD record after the blurb line.

    Silent when a record has no notes, so the source panel can take the full
    width instead of sitting next to an empty box.
    """
    from sbs_utils.procedural.gui import gui_text_area
    notes = entry.get("notes") or ""
    if not notes.strip():
        return False
    gallery_frame("NOTES", area, "#9ab")
    gui_row("row-height: 1fr;")
    gui_text_area(gallery_prose(notes))
    return True


def gallery_source_panel(key, area, title, color):
    """A read-only source panel with no Copy button -- the BROKEN half of a trap.
    Only the fix is worth copying."""
    gallery_frame(title, area, color)
    gui_row("row-height: 1fr;")
    gui_list_box(gallery_code_items(key), "",
                 item_template=gallery_code_row, read_only=True)


# ---------------------------------------------------------------------------
# The index
#
# Entries are AUTHORED, not coded: gallery.amd holds one record per specimen and
# this reads it. The (key) is the join -- the same string as the `# >>gallery:`
# marker in the .mast/.py -- so adding an entry is one AMD record plus one marked
# span, and a record naming a marker that does not exist shows up in the source
# panel as "no marked span" rather than silently.
#
# FILE ORDER IS NAV ORDER; consecutive records sharing a Category collapse under
# one header.
#
# body: first line is the BLURB (header line), the rest is NOTES (gui_text_area,
# so its markdown works).
# ---------------------------------------------------------------------------

GALLERY_ENTRIES = []


def gallery_load_entries():
    """Read gallery.amd once into GALLERY_ENTRIES. Safe to call repeatedly."""
    if GALLERY_ENTRIES:
        return
    from sbs_utils.procedural.quest import document_get_amd_file
    from sbs_utils.procedural.amd_doc import amd_root_node, amd_records
    doc = document_get_amd_file(get_mission_dir_filename("gallery.amd"))
    # amd_root_node, NOT amd_section: with a single `# [Gallery](gallery)` title
    # heading the root node IS the section, and amd_section would look for a
    # child of it also keyed "gallery" and find nothing.
    for rec in amd_records(amd_root_node(doc)):
        body = rec.get("body") or ""
        parts = body.split(chr(10), 1)
        data = rec.get("data") or {}
        GALLERY_ENTRIES.append({
            "key": rec.get("key"),
            "label": rec.get("display") or rec.get("key"),
            "category": data.get("category", "Controls"),
            "kind": data.get("kind"),
            "blurb": parts[0].strip(),
            "notes": (parts[1].strip() if len(parts) > 1 else ""),
        })
    if not GALLERY_ENTRIES:
        log("gallery: gallery.amd produced no entries", "gallery", "warning")
    else:
        log(f"gallery: {len(GALLERY_ENTRIES)} entries", "gallery")


GALLERY_PAGE_DEFAULT = "page_engine_widget"


def gallery_is_page(key):
    return gallery_entry(key).get("kind") == "page"


# The full-page pick is STORY-WIDE, not per client.
#
# It was per-client at first, so two people browsing would not fight over one
# selection. That was wrong the moment the browser moved to the SERVER screen:
# the browser then runs as client 0 and the Gallery Viewer is a console with its
# own id, so the viewer never saw the pick and always drew the default. The
# picker and the viewer are different clients BY CONSTRUCTION here.
GALLERY_PAGE_PICK = [GALLERY_PAGE_DEFAULT]


def gallery_remember_page(key):
    """Record a full-page pick, for the Gallery Viewer console to draw."""
    if gallery_is_page(key):
        GALLERY_PAGE_PICK[0] = key


def gallery_current_page():
    return GALLERY_PAGE_PICK[0]


# ---------------------------------------------------------------------------
# The tour
#
# Walks the index in authoring order, narrating each stop through the overlay
# system's lower third -- the gallery introducing itself with the feature this
# mission was originally built to demo.
#
# State is story-wide for the same reason the page pick is: the tour is driven
# from whichever screen you are on, and the browser is usually the server.
# ---------------------------------------------------------------------------

GALLERY_TOUR = {"on": False, "at": 0}


def gallery_tour_running():
    return GALLERY_TOUR["on"]


def gallery_tour_start():
    gallery_load_entries()
    GALLERY_TOUR["on"] = True
    GALLERY_TOUR["at"] = 0
    return gallery_tour_key()


def gallery_tour_stop():
    GALLERY_TOUR["on"] = False


def gallery_tour_key():
    gallery_load_entries()
    if not GALLERY_ENTRIES:
        return None
    at = max(0, min(GALLERY_TOUR["at"], len(GALLERY_ENTRIES) - 1))
    return GALLERY_ENTRIES[at]["key"]


def gallery_tour_step(delta):
    """Move the tour and return the new key, or None when it walks off the end
    (which also ends the tour -- a tour that silently wraps forever never tells
    you that you have seen everything)."""
    gallery_load_entries()
    at = GALLERY_TOUR["at"] + delta
    if at < 0 or at >= len(GALLERY_ENTRIES):
        GALLERY_TOUR["on"] = False
        return None
    GALLERY_TOUR["at"] = at
    return GALLERY_ENTRIES[at]["key"]


def gallery_tour_position():
    gallery_load_entries()
    return f"{GALLERY_TOUR['at'] + 1} of {len(GALLERY_ENTRIES)}"


def gallery_tour_narration(key):
    """Title and body for the tour's lower third: the category and label, and
    the blurb. Clamped to one readable line, because a lower third is an
    attention layer -- the notes panel is the durable copy."""
    e = gallery_entry(key)
    title = f"{e.get('category', '')} -- {e.get('label', '')}".strip(" -")
    body = (e.get("blurb") or "").strip()
    if len(body) > 140:
        body = body[:137].rstrip() + "..."
    return title, body


def gallery_next_page(key):
    """The next full-page entry after `key`, wrapping -- so the viewer can be
    driven on its own, without the browser open on another screen."""
    gallery_load_entries()
    pages = [e["key"] for e in GALLERY_ENTRIES if e.get("kind") == "page"]
    if not pages:
        return key
    if key not in pages:
        return pages[0]
    return pages[(pages.index(key) + 1) % len(pages)]


def gallery_entry(key):
    gallery_load_entries()
    for e in GALLERY_ENTRIES:
        if e["key"] == key:
            return e
    # An unknown key (a stale pick, a typo) falls back to the first entry rather
    # than raising -- but an EMPTY index means gallery.amd failed to load, and a
    # blank screen with no explanation is worse than a visible complaint.
    if not GALLERY_ENTRIES:
        return {"key": key, "label": "gallery.amd did not load", "category": "Controls",
                "kind": None, "blurb": "No entries. Check gallery.amd parses.", "notes": ""}
    return GALLERY_ENTRIES[0]


def gallery_key_of(item):
    """The specimen key for a selected nav item, or None if it is a category
    header (headers are not selectable, but a selection is never trusted)."""
    if isinstance(item, dict) and "key" in item:
        return item["key"]
    return None


def gallery_nav_items():
    """Nav items with a header per category, for a collapsible listbox.

    Rebuilt per repaint, which is why the caller re-applies the selection with
    set_selected_index() -- the items are new objects each time.
    """
    gallery_load_entries()
    items = []
    seen = None
    for e in GALLERY_ENTRIES:
        if e["category"] != seen:
            seen = e["category"]
            items.append(gui_list_box_header(seen))
        items.append(e)
    return items


def gallery_nav_index(key):
    """Index of a specimen in the nav item list (headers included)."""
    i = 0
    for item in gallery_nav_items():
        if gallery_key_of(item) == key:
            return i
        i += 1
    return 0


def gallery_nav_row(item):
    """One nav row. A collapsible listbox calls the item template for CATEGORY
    HEADERS too, and a header is a LayoutListBoxHeader, not the dict -- treating
    every item as the dict is a TypeError on the first repaint."""
    if gallery_key_of(item) is None:
        gui_row("row-height: 1.8em; font:gui-2;")
        gui_text(f"$text:{gallery_label(getattr(item, 'label', ''))};font:gui-2;color:#8cf;")
        return
    gui_row("row-height: 1.6em; font:gui-2;")
    gui_text(f"$text:{gallery_label(item['label'])};font:gui-2;", "padding: 12px, 0, 0, 0;")


def gallery_nav_title():
    gui_row("row-height: 1.6em; font:gui-2;")
    gui_text("$text:`CONTROL GALLERY`;font:gui-2;color:#8cf;")
