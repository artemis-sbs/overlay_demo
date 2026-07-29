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
    {"category": "Controls", "key": "table_basic", "label": "gui_table",
     "blurb": "A listbox with columns. Declarative form generates the row; auto columns size to the widest cell."},
    {"category": "Controls", "key": "property_list_box_basic", "label": "gui_property_list_box",
     "blurb": "Name/value rows from a dict, each value an expression evaluated at build time."},
    {"category": "Controls", "key": "text_area_basic", "label": "gui_text_area",
     "blurb": "Multi-line rich text with mini-markdown, and it scrolls itself. Not a bigger gui_text."},
    {"category": "Controls", "key": "icon_basic", "label": "gui_icon",
     "blurb": "By sheet index, or by NAME so a mission can re-skin it. An unknown name draws nothing."},
    {"category": "Controls", "key": "icon_button_basic", "label": "gui_icon_button",
     "blurb": "A clickable icon. Fires gui_click, not gui_message."},
    {"category": "Controls", "key": "radio_basic", "label": "gui_radio / gui_vradio",
     "blurb": "One of N, horizontal or vertical. var= binds the choice."},
    {"category": "Controls", "key": "input_basic", "label": "gui_input",
     "blurb": "Typed text. var= pre-fills it and takes the value back."},
    {"category": "Controls", "key": "slider_float", "label": "gui_slider",
     "blurb": "The float slider. min/max/label live in the props; gui_int_slider is the integer form."},
    {"category": "Controls", "key": "grid_basic", "label": "gui_grid",
     "blurb": "A context manager that wraps every N items to a new row -- no manual gui_row."},
    {"category": "Controls", "key": "face_basic", "label": "gui_face",
     "blurb": "A generated crew portrait from a face string."},
    {"category": "Controls", "key": "ship_basic", "label": "gui_ship",
     "blurb": "A hull rendered from its ship_data key."},
    {"category": "Controls", "key": "blank_hole", "label": "gui_blank / gui_hole",
     "blurb": "Spacers. blank fills a cell; hole reserves columns so the next item spans them."},

    # Layout. Every box is given a visible background, because the whole subject
    # is where the edges land -- an unfilled demo of sizing shows nothing.
    {"category": "Layout", "key": "layout_row_modes", "label": "row-height modes",
     "blurb": "1fr shares the leftover, content hugs the text, a fixed em/px is taken off the top."},
    {"category": "Layout", "key": "layout_col_modes", "label": "col-width modes",
     "blurb": "content is natural width, min-content the widest unbreakable word, max-content the unwrapped line."},
    {"category": "Layout", "key": "layout_arithmetic", "label": "size arithmetic",
     "blurb": "1em+10px and 62-25px both work. Before v1.4.0 the +/- term was silently dropped."},
    {"category": "Layout", "key": "layout_overflow", "label": "overflow",
     "blurb": "spill (default), shrink, ellipsis, hide -- for text that cannot fit at any size."},

    # Recipes are composed patterns rather than single widgets -- the shapes a
    # real console is actually made of. A new author copies one of these, not a
    # gui_text call.
    {"category": "Recipes", "key": "recipe_watch_repaint", "label": "watch / repaint",
     "blurb": "A sub-task polls state and calls gui_task_jump when it changes. The standard live panel."},
    {"category": "Recipes", "key": "recipe_status_line", "label": "status line",
     "blurb": "Confirmations must land on a surface that is actually shown. A console with no info panel drops them."},
    {"category": "Recipes", "key": "recipe_item_templates", "label": "item_template shelf",
     "blurb": "Four row templates to start from -- banded, two-column, icon+label+value, and a wrapping detail row."},
    {"category": "Recipes", "key": "recipe_style_def", "label": "reusable style",
     "blurb": "gui_style_def once, then hand it to every row -- one place to change the look."},

    # Some examples are a whole SCREEN, not a control -- an embedded engine view,
    # an absolutely-positioned region, a master/detail console. Squeezed into the
    # detail pane they would teach the wrong thing about proportion. These are
    # listed here but drawn full-bleed on the Gallery Viewer console; picking one
    # here is what the viewer then shows.
    {"category": "Full page", "kind": "page", "key": "page_engine_widget",
     "label": "engine widget + overlay strip",
     "blurb": "gui_layout_widget embeds a real engine view; your rows draw over it."},
    {"category": "Full page", "kind": "page", "key": "page_region",
     "label": "gui_region, updated in place",
     "blurb": "An absolutely-positioned region redraws by itself, without repainting the page under it."},
    {"category": "Full page", "kind": "page", "key": "page_master_detail",
     "label": "listbox + detail console",
     "blurb": "The settled console shape: a titled listbox on the left acting on a detail panel."},
    {"category": "Full page", "kind": "page", "key": "page_layout_playground",
     "label": "layout playground",
     "blurb": "Set row-height, col-width and font from dropdowns and watch the boxes move."},

    # Traps run BROKEN and FIXED side by side. Each needs two marked spans,
    # <key>_broken and <key>_fixed. Watching the broken one misbehave beats any
    # amount of prose about it.
    {"category": "Traps", "kind": "trap", "key": "trap_update_style",
     "label": "update() drops the style",
     "blurb": "update() REPLACES the whole style string -- pass only text and font, color and justify go with it."},
    {"category": "Traps", "kind": "trap", "key": "trap_loop_handler",
     "label": "handler in a for loop",
     "blurb": "An inline on-block in a loop captures the loop var at its LAST value. Use data={} and read it back."},
    {"category": "Traps", "kind": "trap", "key": "trap_row_em_font",
     "label": "1em under a bigger font",
     "blurb": "em is one line of the ROW's font, and an unfonted row is gui-2. Declare the font on the row."},
    {"category": "Traps", "kind": "trap", "key": "trap_padding_height",
     "label": "padding eats row height",
     "blurb": "Top and bottom padding come OUT of the row height. Add it back: 1em+10px."},
    {"category": "Traps", "kind": "trap", "key": "trap_content_starved",
     "label": "content row starved",
     "blurb": "A content row cannot invent space. Fill a section with fixed rows and it is correctly squeezed to nothing."},
]

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


def gallery_next_page(key):
    """The next full-page entry after `key`, wrapping -- so the viewer can be
    driven on its own, without the browser open on another screen."""
    pages = [e["key"] for e in GALLERY_ENTRIES if e.get("kind") == "page"]
    if not pages:
        return key
    if key not in pages:
        return pages[0]
    return pages[(pages.index(key) + 1) % len(pages)]


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
        gui_text(f"$text:{gallery_label(getattr(item, 'label', ''))};font:gui-2;color:#8cf;")
        return
    gui_row("row-height: 1.6em; font:gui-2;")
    gui_text(f"$text:{gallery_label(item['label'])};font:gui-2;", "padding: 12px, 0, 0, 0;")


def gallery_nav_title():
    gui_row("row-height: 1.6em; font:gui-2;")
    gui_text("$text:`CONTROL GALLERY`;font:gui-2;color:#8cf;")
