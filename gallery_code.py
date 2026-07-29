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
    gui_row, gui_text, gui_section, gui_clipboard_put, gui_list_box_header)
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


def gallery_code_escape(text):
    """Make one source line safe to hand to gui_text as a $text: value."""
    return gui_text_escape(text).replace("{", "{{").replace("}", "}}")


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
    gui_text(f"$text:{gui_text_escape(title)};font:gui-2;color:{color};")


# ---------------------------------------------------------------------------
# The index
#
# Phase 1 keeps this in Python. Phase 2 moves the prose (blurb / when to use /
# do / don't) into gallery.amd and leaves only the key -> label join here.
# ---------------------------------------------------------------------------

GALLERY_ENTRIES = [
    {"category": "Controls", "key": "text_basic", "label": "gui_text",
     "blurb": "One styled line. $text: comes first; justify:left is the default."},
    {"category": "Controls", "key": "text_live", "label": "gui_text (live)",
     "blurb": "Keep the handle and .update() the WHOLE style string on change."},
    {"category": "Controls", "key": "button_basic", "label": "gui_button",
     "blurb": "on gui_message fires when the value changes."},
    {"category": "Controls", "key": "checkbox_basic", "label": "gui_checkbox",
     "blurb": "State lives in your variable; the widget reflects it."},
    {"category": "Controls", "key": "drop_down_basic", "label": "gui_drop_down",
     "blurb": "list: is comma separated. var= binds the choice to a variable."},
    {"category": "Controls", "key": "slider_basic", "label": "gui_int_slider",
     "blurb": "low/high in the props; read .value in the handler."},
    {"category": "Controls", "key": "list_box_basic", "label": "gui_list_box",
     "blurb": "Every repeating list. item_template renders a row, title_template labels it."},
]


def gallery_entry(key):
    for e in GALLERY_ENTRIES:
        if e["key"] == key:
            return e
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
        gui_text(f"$text:{gui_text_escape(getattr(item, 'label', ''))};font:gui-2;color:#8cf;")
        return
    gui_row("row-height: 1.6em; font:gui-2;")
    gui_text(f"$text:{gui_text_escape(item['label'])};font:gui-2;", "padding: 12px, 0, 0, 0;")


def gallery_nav_title():
    gui_row("row-height: 1.6em; font:gui-2;")
    gui_text("$text:`CONTROL GALLERY`;font:gui-2;color:#8cf;")
