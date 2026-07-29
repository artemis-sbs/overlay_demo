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

from sbs_utils.procedural.gui import gui_row, gui_text, gui_icon
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
