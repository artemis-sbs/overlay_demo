# Control Gallery -- Python side of the specimens.
#
# Some controls take a template FUNCTION (item_template, title_template), which
# a .mast file cannot declare. Those live here, and they carry gallery markers
# too: the slicer is language-agnostic (both .mast and .py comment with '#'), so
# a specimen's snippet can be assembled from BOTH files under one key.
#
# This file is also the honest answer to "how do real missions do it" -- the LM
# casino, quest log and console pickers all pair a .mast listbox with a Python
# row template exactly like this.

from sbs_utils.procedural.gui import gui_row, gui_text, gui_icon, gui_icon_name
from sbs_utils.helpers import gui_text_escape


# >>gallery: list_box_basic
def gallery_ship_row(item):
    """One row of the listbox. Size the ROW; never return a size."""
    gui_row("row-height: 1.4em; font:gui-2;")
    gui_icon(f"icon_index: {item['icon']};color:#8cf;", "col-width: content;")
    gui_text(f"$text:{gui_text_escape(item['name'])};font:gui-2;", "col-width: content;")
    gui_text(f"$text:{gui_text_escape(item['note'])};font:gui-1;color:#9ab;justify:right;")


def gallery_ship_title(*args):
    """Label the listbox with title_template, not a text row above it."""
    gui_row("row-height: 1.6em; font:gui-2;")
    gui_text("$text:`Contacts`;font:gui-2;color:#8cf;")
# <<gallery


# >>gallery: page_master_detail
def gallery_fleet_row(item):
    gui_row("row-height: 1.8em; font:gui-2;")
    gui_text(f"$text:{gui_text_escape(item['name'])};font:gui-2;")
    gui_text(f"$text:`{item['hull']}`;font:gui-2;color:#8f8;justify:right;")


def gallery_fleet_title(*args):
    gui_row("row-height: 1.8em; font:gui-2;")
    gui_text("$text:`Fleet`;font:gui-2;color:#8cf;")
# <<gallery


# ---------------------------------------------------------------------------
# The item_template shelf -- four row layouts to start from.
#
# Every one of them SIZES THE ROW and returns None. A template that returns a
# size leaves the item section degenerate, which kills selection and the click
# region; the listbox only calls resize_to_content() when the template returns
# nothing.
# ---------------------------------------------------------------------------

# >>gallery: recipe_item_templates
def gallery_tmpl_plain(item):
    """One line. The floor: a name and a value, nothing else."""
    gui_row("row-height: 1.4em; font:gui-2;")
    gui_text(f"$text:{gui_text_escape(item['name'])};font:gui-2;")
    gui_text(f"$text:`{item['hull']}`;font:gui-2;color:#8f8;justify:right;")


def gallery_tmpl_banded(item):
    """A tinted band per row. Banding is a BACKGROUND on the row's cells, not a
    property of the listbox -- so the template decides it, per item."""
    tint = "#243" if item["hull"] >= 80 else "#432"
    gui_row("row-height: 1.6em; font:gui-2;")
    gui_text(f"$text:{gui_text_escape(item['name'])};font:gui-2;background:{tint};")
    gui_text(f"$text:`{item['hull']}`;font:gui-2;background:{tint};justify:right;")


def gallery_tmpl_icon_value(item):
    """Icon, label, value. col-width: content on the icon and the label lets the
    value column take everything left, so the numbers line up down the list."""
    gui_row("row-height: 1.8em; font:gui-2;")
    gui_icon_name(item["icon"], color="#8cf", style="col-width: content;")
    gui_text(f"$text:{gui_text_escape(item['name'])};font:gui-2;", "col-width: content;")
    gui_text(f"$text:`{item['hull']}`;font:gui-2;color:#8f8;justify:right;")


def gallery_tmpl_detail(item):
    """Two lines: a heading and a wrapping note under it. The note's row is
    `content`, so it grows with the text instead of being clipped."""
    gui_row("row-height: 1.6em; font:gui-2;")
    gui_text(f"$text:{gui_text_escape(item['name'])};font:gui-2;color:#8cf;")
    gui_row("row-height: content; font:gui-1;")
    gui_text(f"$text:{gui_text_escape(item['note'])};font:gui-1;color:#9ab;")


GALLERY_TEMPLATES = {
    "plain": gallery_tmpl_plain,
    "banded": gallery_tmpl_banded,
    "icon_value": gallery_tmpl_icon_value,
    "detail": gallery_tmpl_detail,
}


def gallery_template_by_name(name):
    return GALLERY_TEMPLATES.get(name, gallery_tmpl_plain)
# <<gallery
