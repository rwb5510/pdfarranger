# Tabbed documents implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Open each PDF arrangement as a tab in one process, with an optional two-pane view and the ability to move a tab into its own window.

**Architecture:** Pure rules live in `pdfarranger/session.py` and are tested without GTK. A `Document` holds one arrangement (pages, undo, save path, zoom, renderer, view widget). An `ArrangerWindow` holds the header, the tab strip, and at most two panes, and calls the session rules instead of reimplementing them. `PdfArranger` stays the `Gtk.Application`: one process, many windows, one save at a time.

**Tech Stack:** Python 3, GTK 3, PyGObject, libhandy when present, pikepdf, unittest, dogtail on Linux.

**Spec:** `docs/superpowers/specs/2026-10-22-tabbed-documents-design.md`

## Global Constraints

- Remove `Gio.ApplicationFlags.NON_UNIQUE`. Keep `HANDLES_COMMAND_LINE`. Application id stays `com.github.jeromerobert.pdfarranger`.
- A document is occupied when `len(pdfqueue) > 0` or `len(metadata) > 0`.
- File → Open on an empty focused document fills it. File → Open on an occupied document adds one tab. Several files in that one Open merge into the selected document. On Windows, keep today’s reversed filename order before `PageAdder.addpages`.
- The command line that starts the process fills the first empty document. A later launch uses the Open rule on the focused document of the window that was used last. A later launch with no files raises that window and adds no tab.
- File paths from a command line are created with `command_line.create_file_for_arg`.
- Import from the menu adds pages to the focused document. A file drop on a pane adds to that pane’s document. A drop on a tab adds to that tab’s document. A drop on the rest of the window adds to the focused document. Several files in one drop merge into that one document.
- New strings go through `gettext` as `_("…")`.
- Ctrl+T is New Tab. Ctrl+N stays New Window and creates a window in this process. Ctrl+W, the tab close button, and middle-click close the focused document. Ctrl+Tab and Ctrl+Shift+Tab follow the tab-click rule. F6 moves focus to the other pane while the split is on. View → Side by Side has no extra shortcut.
- At most two panes. The blue outline is applied only while the split is on.
- On Windows, dragging pages moves them, and holding Ctrl copies them. On Linux and macOS, dragging pages moves them. A copy records undo only on the destination. A move records undo on both and marks both unsaved.
- One save, export, or print runs at a time in the process. Closing the busy document, its window, or the app waits until that operation finishes.
- Closing one document prompts immediately. Closing a window or quitting asks about every unsaved document before closing any of them. Cancel aborts the whole close. The last document in a window is replaced by one empty document. Detaching the last document closes that window. The app quits only when the last window closes.
- A new tab is inserted only after the first page has been added. Cancelling a password prompt before that leaves the window unchanged.
- Hidden documents stop thumbnail rendering.
- Out of scope: restoring tabs on startup, a third pane, and a preference that restores one process per document.
- Do not commit `.superpowers/`. This tree had no `.git` directory when the plan was written. Run the commit steps when the tree is a git checkout. Do not run `git init` unless the user asks.

## File structure

- Create `pdfarranger/session.py`. Pure open, tab, pane, close, drop, and save-gate rules. No GTK.
- Create `tests/test_session.py`. Unittest for `session.py`.
- Create `pdfarranger/document.py`. One arrangement and its icon view. `PageAdder` and `undo.Manager` are constructed with a `Document`.
- Create `pdfarranger/window.py`. Header, tab strip, panes, menus, and action forwarding.
- Create `pdfarranger/win32ipc.py`. Windows fallback used only when GLib is older than 2.44 or `PDFARRANGER_WIN32_IPC=1`.
- Modify `pdfarranger/pdfarranger.py`. Application lifecycle, command line, and the process-wide save gate. Page-editing methods leave this file.
- Modify `pdfarranger/config.py`. Accelerators for `new-tab` and `focus-other-pane`.
- Modify `data/menu.ui`. New Tab and Side by Side items.
- Modify `pdfarranger/search.py`. Rebind the one find bar to the focused document.
- Modify `tests/test.py`. `TestBatch09` expects one process and two tabs. `TestBatch17` covers the new window behavior that dogtail can drive.
- Modify `TESTING.md`. Note that `TestBatch09` expects tabs.

`pdfarranger.py` methods that move onto `Document` (current line numbers, find by name if they drift): `insert_blank_page` (507), `generate_booklet` (525), `split_booklet` (570), `on_action_print` (706), `set_cellrenderer_data` (990), `render` (993), `quit_rendering` (1010), `silent_render` (1020), `render_lock` (1029), `vscrollbar_value_changed` (1047), `set_iconview_visible` (1062), `set_save_file` (1074), `set_unsaved` (1079), `update_thumbnail` (1101), `redraw_cell` (1131), `get_visible_range2` (1140), `hide_horizontal_scrollbar` (1163), `update_iconview_geometry` (1172), `vadj_percent_handler` (1205), `iv_size_allocate` (1223), `set_adjustment_limits` (1232), `clear_data` (1285), `choose_export_pdf_name` (1372), `save_or_choose` (1512), `save` (1524), `save_warning_dialog` (1557), `export_finished` (1578), `set_export_state` (1604), `choose_export_selection_pdf_name` (1630), `on_action_export_all` (1646), `clear_selected` (1668), `scroll_to_path2` (1694), `copy_pages` (1708), `paste_pages` (1729), `paste_files` (1742), `paste_pages_interleave` (1753), `on_action_delete` (1789), `on_action_cut` (1794), `on_action_copy` (1801), `on_action_paste` (1807), `convert_page_data_to_layerpage_lists` (1862), `paste_as_layer_dialog` (1885), `paste_as_layer` (1902), `is_paste_layer_available` (1959), `read_from_clipboard` (1962), `deserialize` (2023), `set_paste_location` (2053), `get_nimages_in_page` (2080), `get_images_in_page` (2090), `get_text_in_page` (2108), `on_action_extract` (2117), `on_action_explode_into_images` (2149), `on_action_select` (2173), `iv_drag_begin` (2222), `iv_dnd_get_data` (2229), `_is_noop_move` (2251), `iv_dnd_received_data` (2259), `iv_dnd_data_delete` (2313), `iv_dnd_motion` (2335), `iv_autoscroll` (2400), `iv_dnd_leave_end` (2413), `iv_auto_scroll` (2420), `iv_motion` (2432), `iv_button_release_event` (2456), `iv_button_press_event` (2485), `iv_key_press_event` (2570), `iv_selection_changed` (2586), `sw_dnd_received_data` (2626), `sw_button_press_event` (2650), `sw_scroll_event` (2657), `scroll_iconview_one_row` (2686), `enable_zoom_buttons` (2705), `update_max_zoom_level` (2710), `zoom_set` (2720), `zoom_fit_path` (2743), `on_action_zoom_in` (2774), `on_action_zoom_out` (2777), `on_action_zoom_fit` (2780), `scroll_to_selection` (2811), `rotate_page_action` (2819), `rotate_page` (2828), `split_pages` (2846), `get_size_info` (2878), `merge_pages` (2887), `edit_metadata` (2936), `page_size_dialog` (2941), `range_select_dialog` (2967), `center_on_blank_page` (3019), `crop_dialog` (3042), `update_crop` (3048), `hide_dialog` (3057), `update_hide` (3065), `apply_hide_margins_on_pages` (3083), `apply_hide_margins_on_layerpages` (3106), `hide_layer_margins` (3121), `crop_white_borders` (3136), `crop` (3146), `duplicate` (3161), `reverse_order_available` (3183), `reverse_order` (3199), `swap_odd_even` (3218), `content_loss_warning` (3241), `show_find_results` (3339), `clear_find_results` (3349), `password_setup` (3359), `set_password` (3365), `set_password_from_input_files` (3374).

These stay off `Document`: `about_dialog`, `on_action_preferences`, `on_action_fullscreen`, `confirm_dialog`, `save_changes_dialog`, `error_message_dialog`, `open_dialog`, `set_title`, `retitle`, `do_command_line`, `do_activate`, `close_application`, `on_quit`. `on_action_new` is deleted. `on_action_open`, `on_action_close`, `on_action_import`, and `add_files` are rewritten on the window.

---

### Task 1: Open target, tab text, and launch plan

**Files:**
- Create: `pdfarranger/session.py`
- Test: `tests/test_session.py`

**Interfaces:**
- Consumes: nothing
- Produces:
  - `document_occupied(pdfqueue_len: int, metadata_len: int) -> bool`
  - `choose_open_target(occupied: bool) -> OpenTarget` with `OpenTarget.FILL` and `OpenTarget.NEW_TAB`
  - `tab_label(save_basename: str | None, first_source_basename: str | None) -> str`
  - `tab_tooltip(save_path: str | None, first_source_path: str | None) -> str`
  - `plan_launch(remote: bool, files: list[str], focused_occupied: bool) -> LaunchPlan`
  - `LaunchPlan.action` is `"fill"`, `"new_tab"`, or `"raise"`. `LaunchPlan.files` is a list of str.

- [x] **Step 1: Write the failing test**

Create `tests/test_session.py`:

```python
import unittest

from pdfarranger.session import (
    LaunchPlan,
    OpenTarget,
    choose_open_target,
    document_occupied,
    plan_launch,
    tab_label,
    tab_tooltip,
)


class OpenTargetTests(unittest.TestCase):
    def test_empty_document_is_not_occupied(self):
        self.assertFalse(document_occupied(0, 0))

    def test_queue_or_metadata_occupies_a_document(self):
        self.assertTrue(document_occupied(1, 0))
        self.assertTrue(document_occupied(0, 1))

    def test_negative_lengths_are_rejected(self):
        with self.assertRaises(ValueError):
            document_occupied(-1, 0)

    def test_empty_document_is_filled(self):
        self.assertIs(choose_open_target(False), OpenTarget.FILL)

    def test_occupied_document_opens_a_tab(self):
        self.assertIs(choose_open_target(True), OpenTarget.NEW_TAB)


class TabTextTests(unittest.TestCase):
    def test_label_prefers_save_name_then_source_then_untitled(self):
        self.assertEqual(tab_label("contract.pdf", "scan.pdf"), "contract.pdf")
        self.assertEqual(tab_label(None, "scan.pdf"), "scan.pdf")
        self.assertEqual(tab_label(None, None), "untitled")
        self.assertEqual(tab_label("", "scan.pdf"), "scan.pdf")

    def test_tooltip_uses_the_full_path(self):
        self.assertEqual(tab_tooltip(r"C:\a\contract.pdf", r"C:\b\scan.pdf"), r"C:\a\contract.pdf")
        self.assertEqual(tab_tooltip(None, r"C:\b\scan.pdf"), r"C:\b\scan.pdf")
        self.assertEqual(tab_tooltip(None, None), "")


class LaunchPlanTests(unittest.TestCase):
    def test_startup_with_files_fills_the_first_document(self):
        plan = plan_launch(False, ["a.pdf", "b.pdf"], False)
        self.assertEqual(plan, LaunchPlan("fill", ["a.pdf", "b.pdf"]))

    def test_startup_without_files_fills_nothing(self):
        plan = plan_launch(False, [], False)
        self.assertEqual(plan.action, "fill")
        self.assertEqual(plan.files, [])

    def test_later_launch_without_files_raises_the_window(self):
        plan = plan_launch(True, [], True)
        self.assertEqual(plan.action, "raise")
        self.assertEqual(plan.files, [])

    def test_later_launch_fills_an_empty_focused_document(self):
        plan = plan_launch(True, ["b.pdf", "c.pdf"], False)
        self.assertEqual(plan, LaunchPlan("fill", ["b.pdf", "c.pdf"]))

    def test_later_launch_adds_one_tab_when_the_document_is_occupied(self):
        plan = plan_launch(True, ["b.pdf", "c.pdf"], True)
        self.assertEqual(plan, LaunchPlan("new_tab", ["b.pdf", "c.pdf"]))
```

- [x] **Step 2: Run the test to verify it fails**

Run: `python -m unittest tests.test_session -v`

Expected: FAIL with `ModuleNotFoundError` or `ImportError` for `pdfarranger.session`.

- [x] **Step 3: Write the implementation**

Create `pdfarranger/session.py` with the project GPL header used by `pdfarranger/config.py`, then:

```python
from dataclasses import dataclass
from enum import Enum


class OpenTarget(Enum):
    FILL = "fill"
    NEW_TAB = "new_tab"


def document_occupied(pdfqueue_len: int, metadata_len: int) -> bool:
    if pdfqueue_len < 0 or metadata_len < 0:
        raise ValueError("lengths must be >= 0")
    return pdfqueue_len > 0 or metadata_len > 0


def choose_open_target(occupied: bool) -> OpenTarget:
    if occupied:
        return OpenTarget.NEW_TAB
    return OpenTarget.FILL


def tab_label(save_basename: str | None, first_source_basename: str | None) -> str:
    if save_basename:
        return save_basename
    if first_source_basename:
        return first_source_basename
    return "untitled"


def tab_tooltip(save_path: str | None, first_source_path: str | None) -> str:
    if save_path:
        return save_path
    if first_source_path:
        return first_source_path
    return ""


@dataclass(frozen=True)
class LaunchPlan:
    action: str
    files: list


def plan_launch(remote: bool, files: list, focused_occupied: bool) -> LaunchPlan:
    files = list(files)
    if remote and not files:
        return LaunchPlan("raise", [])
    if not remote:
        return LaunchPlan("fill", files)
    if choose_open_target(focused_occupied) is OpenTarget.FILL:
        return LaunchPlan("fill", files)
    return LaunchPlan("new_tab", files)
```

- [x] **Step 4: Run the test to verify it passes**

Run: `python -m unittest tests.test_session -v`

Expected: PASS

- [x] **Step 5: Commit**

```bash
git add pdfarranger/session.py tests/test_session.py
git commit -m "Add pure rules for opening a document into a tab"
```

---

### Task 2: Window model for tabs and panes

**Files:**
- Modify: `pdfarranger/session.py`
- Test: `tests/test_session.py`

**Interfaces:**
- Consumes: `choose_open_target`, `OpenTarget` from Task 1
- Produces:
  - `class Pane` with `LEFT` and `RIGHT`
  - `class WindowModel`
  - `WindowModel() -> model with one empty document id, split False, focused Pane.LEFT`
  - `add_document() -> int`
  - `focused_id() -> int`
  - `showing(doc_id: int) -> bool`
  - `click_tab(doc_id: int) -> None`
  - `cycle_tab(backwards: bool) -> None`
  - `open_files(occupied: bool) -> tuple[OpenTarget, int]` (NEW_TAB inserts the id and shows it in the focused pane)
  - `new_tab() -> int`
  - `can_split() -> bool`
  - `toggle_split() -> None`
  - `drag_tab_to_right(doc_id: int) -> None`
  - `focus_other_pane() -> None`
  - `close_document(doc_id: int) -> str` returning `"removed"` or `"emptied"`
  - `detach(doc_id: int) -> tuple[int, bool]` returning `(doc_id, close_window)`
  - `attach(doc_id: int) -> None` (doc id was allocated by the source model; this model must accept that id and show it in the focused pane)
  - `visible_ids() -> set[int]`

- [x] **Step 1: Write the failing test**

Append to `tests/test_session.py`:

```python
from pdfarranger.session import Pane, WindowModel


class WindowModelTests(unittest.TestCase):
    def test_new_model_has_one_empty_document(self):
        model = WindowModel()
        self.assertEqual(len(model.order), 1)
        self.assertEqual(model.focused_id(), model.order[0])
        self.assertFalse(model.split)

    def test_open_on_empty_reuses_the_focused_document(self):
        model = WindowModel()
        first = model.focused_id()
        target, receiver = model.open_files(False)
        self.assertIs(target, OpenTarget.FILL)
        self.assertEqual(receiver, first)
        self.assertEqual(model.order, [first])

    def test_open_on_occupied_inserts_one_tab_in_the_focused_pane(self):
        model = WindowModel()
        first = model.focused_id()
        target, receiver = model.open_files(True)
        self.assertIs(target, OpenTarget.NEW_TAB)
        self.assertEqual(model.order, [first, receiver])
        self.assertEqual(model.focused_id(), receiver)
        self.assertFalse(model.split)

    def test_click_hidden_tab_replaces_the_focused_pane(self):
        model = WindowModel()
        first = model.focused_id()
        _target, second = model.open_files(True)
        model.click_tab(first)
        self.assertEqual(model.focused_id(), first)
        self.assertFalse(model.showing(second))

    def test_click_visible_right_tab_focuses_that_pane(self):
        model = WindowModel()
        left = model.focused_id()
        _target, right = model.open_files(True)
        model.click_tab(left)
        model.toggle_split()
        model.click_tab(right)
        self.assertEqual(model.focused, Pane.RIGHT)
        self.assertEqual(model.left_id, left)
        self.assertEqual(model.right_id, right)

    def test_side_by_side_puts_the_next_tab_on_the_right(self):
        model = WindowModel()
        first = model.focused_id()
        _target, second = model.open_files(True)
        model.click_tab(first)
        model.toggle_split()
        self.assertTrue(model.split)
        self.assertEqual(model.left_id, first)
        self.assertEqual(model.right_id, second)
        self.assertEqual(model.focused, Pane.LEFT)
        model.toggle_split()
        self.assertFalse(model.split)
        self.assertIsNone(model.right_id)
        self.assertEqual(model.focused_id(), first)

    def test_side_by_side_wraps_from_the_last_tab(self):
        model = WindowModel()
        first = model.focused_id()
        _target, second = model.open_files(True)
        model.click_tab(second)
        model.toggle_split()
        self.assertEqual(model.left_id, second)
        self.assertEqual(model.right_id, first)

    def test_side_by_side_does_nothing_with_one_document(self):
        model = WindowModel()
        self.assertFalse(model.can_split())
        model.toggle_split()
        self.assertFalse(model.split)

    def test_drag_hidden_tab_to_the_right_edge(self):
        model = WindowModel()
        left = model.focused_id()
        _target, right = model.open_files(True)
        model.click_tab(left)
        model.drag_tab_to_right(right)
        self.assertTrue(model.split)
        self.assertEqual(model.left_id, left)
        self.assertEqual(model.right_id, right)

    def test_drag_focused_tab_to_the_right_keeps_documents_distinct(self):
        model = WindowModel()
        left = model.focused_id()
        _target, other = model.open_files(True)
        model.click_tab(left)
        model.drag_tab_to_right(left)
        self.assertEqual(model.right_id, left)
        self.assertEqual(model.left_id, other)
        self.assertNotEqual(model.left_id, model.right_id)

    def test_cycle_follows_the_click_rule(self):
        model = WindowModel()
        first = model.focused_id()
        _target, second = model.open_files(True)
        third = model.new_tab()
        model.click_tab(first)
        model.toggle_split()
        model.cycle_tab(False)
        self.assertEqual(model.focused, Pane.RIGHT)
        self.assertEqual(model.focused_id(), second)
        model.cycle_tab(False)
        self.assertEqual(model.right_id, third)
        model.cycle_tab(True)
        self.assertEqual(model.focused_id(), second)

    def test_close_last_document_leaves_one_empty_document(self):
        model = WindowModel()
        only = model.focused_id()
        result = model.close_document(only)
        self.assertEqual(result, "emptied")
        self.assertEqual(len(model.order), 1)
        self.assertNotEqual(model.focused_id(), only)
        self.assertFalse(model.split)

    def test_detach_last_document_closes_the_window(self):
        model = WindowModel()
        doc_id = model.focused_id()
        detached, close_window = model.detach(doc_id)
        self.assertEqual(detached, doc_id)
        self.assertTrue(close_window)
        self.assertEqual(model.order, [])

    def test_detach_and_attach_moves_a_tab(self):
        source = WindowModel()
        kept = source.focused_id()
        _target, moving = source.open_files(True)
        other = WindowModel()
        _detached, close_window = source.detach(moving)
        self.assertFalse(close_window)
        self.assertEqual(source.order, [kept])
        other.attach(moving)
        self.assertIn(moving, other.order)
        self.assertEqual(other.focused_id(), moving)
```

- [x] **Step 2: Run the test to verify it fails**

Run: `python -m unittest tests.test_session.WindowModelTests -v`

Expected: FAIL with `ImportError` for `WindowModel`.

- [x] **Step 3: Write the implementation**

Add to `pdfarranger/session.py`:

```python
class Pane(Enum):
    LEFT = "left"
    RIGHT = "right"


class WindowModel:
    def __init__(self):
        self.next_id = 1
        self.order = []
        self.left_id = None
        self.right_id = None
        self.focused = Pane.LEFT
        self.split = False
        self.add_document()

    def add_document(self) -> int:
        doc_id = self.next_id
        self.next_id += 1
        self.order.append(doc_id)
        if self.left_id is None:
            self.left_id = doc_id
        return doc_id

    def focused_id(self) -> int:
        if self.focused is Pane.RIGHT and self.split and self.right_id is not None:
            return self.right_id
        return self.left_id

    def showing(self, doc_id: int) -> bool:
        if doc_id == self.left_id:
            return True
        return self.split and doc_id == self.right_id

    def visible_ids(self) -> set:
        shown = {self.left_id}
        if self.split and self.right_id is not None:
            shown.add(self.right_id)
        return {doc_id for doc_id in shown if doc_id is not None}

    def _place_in_focused_pane(self, doc_id: int) -> None:
        if self.focused is Pane.RIGHT and self.split:
            self.right_id = doc_id
        else:
            self.left_id = doc_id
            self.focused = Pane.LEFT

    def click_tab(self, doc_id: int) -> None:
        if doc_id not in self.order:
            raise KeyError(doc_id)
        if doc_id == self.left_id:
            self.focused = Pane.LEFT
            return
        if self.split and doc_id == self.right_id:
            self.focused = Pane.RIGHT
            return
        self._place_in_focused_pane(doc_id)

    def cycle_tab(self, backwards: bool) -> None:
        current = self.focused_id()
        index = self.order.index(current)
        step = -1 if backwards else 1
        self.click_tab(self.order[(index + step) % len(self.order)])

    def open_files(self, occupied: bool):
        target = choose_open_target(occupied)
        if target is OpenTarget.FILL:
            return target, self.focused_id()
        doc_id = self.add_document()
        self._place_in_focused_pane(doc_id)
        return target, doc_id

    def new_tab(self) -> int:
        doc_id = self.add_document()
        self._place_in_focused_pane(doc_id)
        return doc_id

    def can_split(self) -> bool:
        return len(self.order) >= 2

    def _other_than(self, doc_id: int) -> int:
        for candidate in self.order:
            if candidate != doc_id:
                return candidate
        raise RuntimeError("no other document")

    def toggle_split(self) -> None:
        if not self.can_split():
            return
        if self.split:
            self.split = False
            self.right_id = None
            self.focused = Pane.LEFT
            return
        current = self.focused_id()
        self.left_id = current
        index = self.order.index(current)
        self.right_id = self.order[(index + 1) % len(self.order)]
        self.split = True
        self.focused = Pane.LEFT

    def drag_tab_to_right(self, doc_id: int) -> None:
        if doc_id not in self.order or not self.can_split():
            return
        if not self.split:
            viewing = self.focused_id()
        else:
            viewing = self.left_id
        if doc_id == viewing:
            viewing = self._other_than(doc_id)
        self.left_id = viewing
        self.right_id = doc_id
        self.split = True
        self.focused = Pane.LEFT

    def focus_other_pane(self) -> None:
        if not self.split:
            return
        if self.focused is Pane.LEFT:
            self.focused = Pane.RIGHT
        else:
            self.focused = Pane.LEFT

    def _repair_panes_after_removal(self, removed: int) -> None:
        if self.left_id == removed:
            self.left_id = self.order[0]
        if self.right_id == removed:
            replacement = next((doc_id for doc_id in self.order if doc_id != self.left_id), None)
            if replacement is None:
                self.split = False
                self.right_id = None
                self.focused = Pane.LEFT
            else:
                self.right_id = replacement
        if self.focused is Pane.RIGHT and not self.split:
            self.focused = Pane.LEFT

    def close_document(self, doc_id: int) -> str:
        if doc_id not in self.order:
            raise KeyError(doc_id)
        if len(self.order) == 1:
            self.order.remove(doc_id)
            self.left_id = None
            self.right_id = None
            self.split = False
            self.focused = Pane.LEFT
            self.add_document()
            return "emptied"
        self.order.remove(doc_id)
        self._repair_panes_after_removal(doc_id)
        return "removed"

    def detach(self, doc_id: int):
        if doc_id not in self.order:
            raise KeyError(doc_id)
        self.order.remove(doc_id)
        close_window = len(self.order) == 0
        if close_window:
            self.left_id = None
            self.right_id = None
            self.split = False
            self.focused = Pane.LEFT
        else:
            self._repair_panes_after_removal(doc_id)
        return doc_id, close_window

    def attach(self, doc_id: int) -> None:
        if doc_id in self.order:
            raise ValueError("document already in this window")
        self.order.append(doc_id)
        self.next_id = max(self.next_id, doc_id + 1)
        self._place_in_focused_pane(doc_id)
```

- [x] **Step 4: Run the test to verify it passes**

Run: `python -m unittest tests.test_session -v`

Expected: PASS

- [x] **Step 5: Commit**

```bash
git add pdfarranger/session.py tests/test_session.py
git commit -m "Add the window model for tabs and two panes"
```

---

### Task 3: Close prompts, drops, and the save gate

**Files:**
- Modify: `pdfarranger/session.py`
- Test: `tests/test_session.py`

**Interfaces:**
- Consumes: nothing from the window model beyond plain ints
- Produces:
  - `PromptChoice.SAVE`, `PromptChoice.DISCARD`, `PromptChoice.CANCEL`
  - `prompt_order(focused_id: int, unsaved_ids: list[int], tab_order: list[int]) -> list[int]`
  - `resolve_prompts(order: list[int], answers: list[PromptChoice]) -> CloseOutcome`
  - `CloseOutcome.aborted: bool`, `save_ids: list[int]`, `discard_ids: list[int]`
  - `single_close(answer: PromptChoice) -> str` returning `"save_then_close"`, `"discard"`, or `"abort"`
  - `class DropSite` with `PANE`, `TAB`, `WINDOW`
  - `drop_target(site: DropSite, pane_doc: int | None, tab_doc: int | None, focused_id: int) -> int`
  - `class SaveGate` with `can_start() -> bool`, `start(doc_id: int) -> None`, `finish() -> None`, `busy_id -> int | None`

- [x] **Step 1: Write the failing test**

Append to `tests/test_session.py`:

```python
from pdfarranger.session import (
    CloseOutcome,
    DropSite,
    PromptChoice,
    SaveGate,
    drop_target,
    prompt_order,
    resolve_prompts,
    single_close,
)


class ClosePromptTests(unittest.TestCase):
    def test_prompt_order_asks_the_focused_document_first(self):
        self.assertEqual(prompt_order(2, [1, 2, 3], [1, 2, 3]), [2, 1, 3])

    def test_cancel_aborts_before_anything_closes(self):
        outcome = resolve_prompts(
            [2, 1],
            [PromptChoice.SAVE, PromptChoice.CANCEL],
        )
        self.assertEqual(outcome, CloseOutcome(True, [], []))

    def test_saves_run_before_discards_are_recorded(self):
        outcome = resolve_prompts(
            [2, 1, 3],
            [PromptChoice.DISCARD, PromptChoice.SAVE, PromptChoice.DISCARD],
        )
        self.assertEqual(outcome, CloseOutcome(False, [1], [2, 3]))

    def test_single_close_answers(self):
        self.assertEqual(single_close(PromptChoice.SAVE), "save_then_close")
        self.assertEqual(single_close(PromptChoice.DISCARD), "discard")
        self.assertEqual(single_close(PromptChoice.CANCEL), "abort")


class DropTargetTests(unittest.TestCase):
    def test_drop_site_selects_the_document(self):
        self.assertEqual(drop_target(DropSite.PANE, 4, 5, 6), 4)
        self.assertEqual(drop_target(DropSite.TAB, 4, 5, 6), 5)
        self.assertEqual(drop_target(DropSite.WINDOW, None, None, 6), 6)


class SaveGateTests(unittest.TestCase):
    def test_only_one_save_runs(self):
        gate = SaveGate()
        self.assertTrue(gate.can_start())
        gate.start(3)
        self.assertFalse(gate.can_start())
        self.assertEqual(gate.busy_id, 3)
        with self.assertRaises(RuntimeError):
            gate.start(4)
        gate.finish()
        self.assertTrue(gate.can_start())
        self.assertIsNone(gate.busy_id)
```

- [x] **Step 2: Run the test to verify it fails**

Run: `python -m unittest tests.test_session.ClosePromptTests tests.test_session.DropTargetTests tests.test_session.SaveGateTests -v`

Expected: FAIL with `ImportError`.

- [x] **Step 3: Write the implementation**

Add to `pdfarranger/session.py`:

```python
class PromptChoice(Enum):
    SAVE = "save"
    DISCARD = "discard"
    CANCEL = "cancel"


@dataclass(frozen=True)
class CloseOutcome:
    aborted: bool
    save_ids: list
    discard_ids: list


def prompt_order(focused_id: int, unsaved_ids: list, tab_order: list) -> list:
    unsaved = set(unsaved_ids)
    ordered = [doc_id for doc_id in tab_order if doc_id in unsaved and doc_id != focused_id]
    if focused_id in unsaved:
        return [focused_id] + ordered
    return ordered


def resolve_prompts(order: list, answers: list) -> CloseOutcome:
    if len(order) != len(answers):
        raise ValueError("one answer per document")
    if any(answer is PromptChoice.CANCEL for answer in answers):
        return CloseOutcome(True, [], [])
    save_ids = [doc_id for doc_id, answer in zip(order, answers) if answer is PromptChoice.SAVE]
    discard_ids = [doc_id for doc_id, answer in zip(order, answers) if answer is PromptChoice.DISCARD]
    return CloseOutcome(False, save_ids, discard_ids)


def single_close(answer: PromptChoice) -> str:
    if answer is PromptChoice.SAVE:
        return "save_then_close"
    if answer is PromptChoice.DISCARD:
        return "discard"
    if answer is PromptChoice.CANCEL:
        return "abort"
    raise ValueError(answer)


class DropSite(Enum):
    PANE = "pane"
    TAB = "tab"
    WINDOW = "window"


def drop_target(site: DropSite, pane_doc, tab_doc, focused_id: int) -> int:
    if site is DropSite.PANE:
        if pane_doc is None:
            raise ValueError("pane drop needs a document")
        return pane_doc
    if site is DropSite.TAB:
        if tab_doc is None:
            raise ValueError("tab drop needs a document")
        return tab_doc
    return focused_id


class SaveGate:
    def __init__(self):
        self.busy_id = None

    def can_start(self) -> bool:
        return self.busy_id is None

    def start(self, doc_id: int) -> None:
        if self.busy_id is not None:
            raise RuntimeError("a save is already running")
        self.busy_id = doc_id

    def finish(self) -> None:
        self.busy_id = None
```

- [x] **Step 4: Run the test to verify it passes**

Run: `python -m unittest tests.test_session -v`

Expected: PASS

- [x] **Step 5: Commit**

```bash
git add pdfarranger/session.py tests/test_session.py
git commit -m "Add close, drop, and save-gate rules"
```

---

### Task 4: Document shell with independent state

**Files:**
- Create: `pdfarranger/document.py`
- Test: `tests/test_session.py`

**Interfaces:**
- Consumes: nothing
- Produces: `class Document` with independent `pdfqueue`, `metadata`, `save_file`, `is_unsaved`, `password`, `zoom_level`, `zoom_scale`, `zoom_fit`, `fit_one_page`, `find_text`, `id`, `app`, `gtk_window`. `occupied() -> bool` uses `document_occupied`. `release_renderer()` sets `rendering_thread.quit = True` when a thread exists. Properties `tmp_dir`, `import_directory`, and `export_directory` read and write `self.app`.

- [x] **Step 1: Write the failing test**

Append to `tests/test_session.py`:

```python
from pdfarranger.document import Document


class _AppDirs:
    def __init__(self):
        self.tmp_dir = "/tmp/pdfarranger-test"
        self.import_directory = None
        self.export_directory = "/home/export"


class DocumentShellTests(unittest.TestCase):
    def test_two_documents_do_not_share_state(self):
        app = _AppDirs()
        first = Document(app, 1)
        second = Document(app, 2)
        first.pdfqueue.append("doc")
        first.metadata["Title"] = "A"
        first.find_text = "hello"
        first.set_import_directory("/tmp/in")
        self.assertEqual(second.pdfqueue, [])
        self.assertEqual(second.metadata, {})
        self.assertEqual(second.find_text, "")
        self.assertEqual(second.import_directory, "/tmp/in")
        self.assertTrue(first.occupied())
        self.assertFalse(second.occupied())

    def test_release_renderer_asks_the_thread_to_quit(self):
        class Thread:
            def __init__(self):
                self.quit = False

        doc = Document(_AppDirs(), 1)
        doc.rendering_thread = Thread()
        doc.release_renderer()
        self.assertTrue(doc.rendering_thread.quit)
```

- [x] **Step 2: Run the test to verify it fails**

Run: `python -m unittest tests.test_session.DocumentShellTests -v`

Expected: FAIL with `ImportError` for `pdfarranger.document`.

- [x] **Step 3: Write the implementation**

Create `pdfarranger/document.py` with the GPL header and:

```python
from .session import document_occupied


class Document:
    def __init__(self, app, doc_id: int):
        self.app = app
        self.id = doc_id
        self.gtk_window = None
        self.model = None
        self.undomanager = None
        self.iconview = None
        self.sw = None
        self.cellthmb = None
        self.pdfqueue = []
        self.metadata = {}
        self.save_file = None
        self.export_file = None
        self.is_unsaved = False
        self.password = None
        self.zoom_level = None
        self.zoom_level_old = 0
        self.zoom_level_limits = [-10, 80]
        self.zoom_scale = None
        self.zoom_fit = False
        self.fit_one_page = True
        self.find_text = ""
        self.rendering_thread = None
        self.export_process = None
        self.post_action = None
        self.render_id = None
        self.nfile = 0
        self.layer_pos = (0.5, 0.5)
        self.drag_path = None
        self.drag_pos = None
        self.pressed_button = None
        self.click_path = None
        self.scroll_path = None
        self.vadj_percent = None
        self.target_is_intern = True
        self.id_scroll_to_sel = None
        self.iv_auto_scroll_timer = None
        self.set_iv_visible_id = None
        self.end_rubberbanding = False
        self.visible_range = None

    def occupied(self) -> bool:
        return document_occupied(len(self.pdfqueue), len(self.metadata))

    def release_renderer(self) -> None:
        thread = self.rendering_thread
        if thread is not None:
            thread.quit = True

    @property
    def tmp_dir(self):
        return self.app.tmp_dir

    @property
    def import_directory(self):
        return self.app.import_directory

    def set_import_directory(self, value):
        self.app.import_directory = value

    @import_directory.setter
    def import_directory(self, value):
        self.set_import_directory(value)

    @property
    def export_directory(self):
        return self.app.export_directory

    @export_directory.setter
    def export_directory(self, value):
        self.app.export_directory = value

    @property
    def window(self):
        """Dialog parent. PageAdder and PDFDoc already read app.window."""
        return self.gtk_window
```

- [x] **Step 4: Run the test to verify it passes**

Run: `python -m unittest tests.test_session tests.test_core -v`

Expected: PASS. `tests.test_core` does not need the new type and must stay green.

- [x] **Step 5: Commit**

```bash
git add pdfarranger/document.py tests/test_session.py
git commit -m "Add a document shell with its own page state"
```

---

### Task 5: Move page operations onto Document

**Files:**
- Modify: `pdfarranger/document.py`
- Modify: `pdfarranger/pdfarranger.py`
- Test: `tests/test_session.py`

**Interfaces:**
- Consumes: `Document` from Task 4. `PageAdder` and `undo.Manager` keep their constructors and receive a `Document` as `app`.
- Produces: every method named in the file-structure move list exists on `Document`. `Document.build_view(sw_parent_unused)` creates `model`, `undomanager`, `iconview`, and `sw` using the block that is today at `pdfarranger.py` lines 786–834. `Document.error_message_dialog` calls `self.host.error_message_dialog`. `self.host` is the `ArrangerWindow` set later. Until Task 6, `PdfArranger` still constructs one `Document`, assigns `self.doc = document`, and action callbacks call `self.doc.<method>`.

- [x] **Step 1: Write the failing test**

Append to `tests/test_session.py`:

```python
class DocumentMethodTests(unittest.TestCase):
    def test_page_operations_live_on_document(self):
        names = [
            "build_view",
            "render",
            "quit_rendering",
            "set_unsaved",
            "save_or_choose",
            "paste_pages",
            "iv_dnd_received_data",
            "sw_dnd_received_data",
            "on_action_zoom_in",
            "clear_data",
            "error_message_dialog",
        ]
        for name in names:
            self.assertTrue(callable(getattr(Document, name)), name)
```

- [x] **Step 2: Run the test to verify it fails**

Run: `python -m unittest tests.test_session.DocumentMethodTests -v`

Expected: FAIL because `build_view` is missing.

- [x] **Step 3: Move the methods**

Move each method named in the file-structure list from `class PdfArranger` into `class Document`. Keep the bodies. Change only these references:

- `self.window` used as a dialog parent becomes `self.gtk_window`.
- `self.config` becomes `self.app.config`.
- `self.clipboard` becomes `self.app.clipboard`.
- `self.quit_flag` becomes `self.app.quit_flag`.
- `self.disable_quit` becomes `self.app.disable_quit`.
- `error_message_dialog` on the document calls `self.host.error_message_dialog(msg)` if the dialog method was left on the window. Implement this wrapper on `Document` and do not copy the dialog widget code.
- `update_statusbar` reads the document and then calls `self.host.set_status(self, left_text, right_text)`.
- `set_unsaved` still sets `self.is_unsaved` and then calls `self.host.refresh_document(self)`.
- `retitle` is not moved. Delete calls to `self.retitle()` from moved methods and call `self.host.refresh_document(self)` instead.
- `PageAdder(self)` and `undo.Manager(self)` stay as `self`, because `self` is now the document.
- `IconviewCursor(self)`, `IconviewDragSelect(self)`, and `IconviewPanView(self)` are constructed from `build_view` with the document.

`build_view` is the current icon-view setup (`pdfarranger.py` 786–834) plus `self.model = Gtk.ListStore(GObject.TYPE_PYOBJECT, str)`, `self.undomanager = undo.Manager(self)`, and `self.sw = Gtk.ScrolledWindow()`. The scrolled window keeps the current drag destination setup (`TARGETS_SW`, `sw_dnd_received_data`). Do not pack `sw` into the UI file’s single `scrolledwindow`. The window packs `document.sw` in Task 6.

Leave `PdfArranger` able to import. Where a remaining method still says `self.model` or `self.iconview`, change it to `self.doc.model` or `self.doc.iconview` for this task only. Task 6 removes that single-document assumption.

After the move, this command prints nothing:

```bash
python -c "import ast,pathlib; src=pathlib.Path('pdfarranger/pdfarranger.py').read_text(encoding='utf-8'); tree=ast.parse(src); print('ok')"
```

- [x] **Step 4: Run the tests**

Run: `python -m unittest tests.test_session tests.test_core -v`

Expected: PASS

- [x] **Step 5: Commit**

```bash
git add pdfarranger/document.py pdfarranger/pdfarranger.py tests/test_session.py
git commit -m "Move page operations onto the document"
```

---

### Task 6: Tab strip and opening into a tab

**Files:**
- Create: `pdfarranger/window.py`
- Modify: `pdfarranger/pdfarranger.py`
- Modify: `pdfarranger/document.py`
- Modify: `data/menu.ui`
- Modify: `pdfarranger/config.py`
- Modify: `data/pdfarranger.ui` only if a container id is required; prefer packing in code into `main_box` above the existing status bars and below the header.

**Interfaces:**
- Consumes: `WindowModel`, `tab_label`, `tab_tooltip`, `OpenTarget`, `choose_open_target`
- Produces:
  - `class ArrangerWindow`
  - `ArrangerWindow.open_files(paths: list[str]) -> None`
  - `ArrangerWindow.new_tab() -> None`
  - `ArrangerWindow.focused_document() -> Document`
  - `ArrangerWindow.refresh_document(document) -> None` updates that tab’s label, asterisk, and tooltip, and the window title when the document is focused
  - `PdfArranger.windows: list`
  - `PdfArranger.active_window() -> ArrangerWindow`

- [x] **Step 1: Write the failing test**

Append to `tests/test_session.py`:

```python
class OpenFilesOrderTests(unittest.TestCase):
    def test_windows_reverses_multi_select_order(self):
        from pdfarranger.window import filenames_for_open
        import os
        names = ["a.pdf", "b.pdf", "c.pdf"]
        if os.name == "nt":
            self.assertEqual(filenames_for_open(names), ["c.pdf", "b.pdf", "a.pdf"])
        else:
            self.assertEqual(filenames_for_open(names), names)
```

- [x] **Step 2: Run the test to verify it fails**

Run: `python -m unittest tests.test_session.OpenFilesOrderTests -v`

Expected: FAIL with `ImportError` for `pdfarranger.window`.

- [x] **Step 3: Build the window and the open path**

`filenames_for_open`:

```python
import os


def filenames_for_open(filenames: list) -> list:
    filenames = list(filenames)
    if os.name == "nt":
        return list(reversed(filenames))
    return filenames
```

`ArrangerWindow.__init__(self, app)`:

- Call the existing main-window and menu builders, moved from `PdfArranger.__create_main_window` and `__create_menus`.
- Insert a `Gtk.ScrolledWindow` named `tab-strip` as the first child of `main_box`, at position 0. The existing `searchbar` stays immediately under it, then the page area, then the status bars. Horizontal policy `AUTOMATIC`, vertical policy `NEVER`. Its child is a horizontal `Gtk.Box` named `tab-strip-box`.
- Remove the UI file’s single `scrolledwindow` from `main_box`. Put a `Gtk.Box` named `page-area` in its place. That box’s one child is the focused document’s `sw`.
- Create the first `Document`, call `build_view()`, store it in `self.docs = {doc.id: doc}`, and bind `WindowModel` so the model’s first id matches `doc.id` (pass the id into `WindowModel` or set `document.id = model.order[0]` before any other document is created). The simplest match: `WindowModel.add_document` is not called a second time; construct the model, then `document.id = model.focused_id()`.
- Build one tab widget: a `Gtk.Box` with a `Gtk.Label` and a `Gtk.Button` whose label is `×`. The label text is `tab_label(...)`. The box tooltip is `tab_tooltip(...)`. When `document.is_unsaved`, prefix the visible label with `*` by appending `*` in `refresh_document` (`label + "*"` when unsaved). The label widget name is `pdfarranger-tab-label` so dogtail can find the text.
- Clicking the label calls `model.click_tab(doc_id)` then `show_model()`.
- The close button calls `self.close_document(doc_id)` (Task 12 implements the prompt; for this task closing a clean document calls `model.close_document` and drops the `Document`).
- `show_model()` packs `self.docs[model.left_id].sw` into `page-area` and hides every other document `sw`. Call `release_renderer()` on documents that are not in `model.visible_ids()`, and call `silent_render()` on documents that are visible and have pages.
- `open_files(paths)` uses `filenames_for_open`. It calls `choose_open_target(focused.occupied())`. For `FILL`, it adds pages to the focused document with `PageAdder`. For `NEW_TAB`, it creates a `Document` and adds pages there. It inserts the tab only if `len(model)` grew, which `PageAdder.commit` does by adding rows. If no page was added, discard the new `Document` and do not call `WindowModel.open_files`. If pages were added, call `model.open_files(True)` only when the target was `NEW_TAB`, and assign the pre-created document the id `open_files` returns. Do not call `open_files` twice. Practical sequence:

```python
target = choose_open_target(focused.occupied())
if target is OpenTarget.NEW_TAB:
    receiver = Document(self.app, 0)
    receiver.build_view()
else:
    receiver = focused
added = self._add_paths(receiver, paths)
if target is OpenTarget.NEW_TAB and not added:
    receiver.release_renderer()
    return
if target is OpenTarget.NEW_TAB:
    _target, doc_id = self.model.open_files(True)
    receiver.id = doc_id
    self.docs[doc_id] = receiver
self.refresh_document(receiver)
self.show_model()
```

`_add_paths` is the current `add_files` / `on_action_open` loop: `PageAdder`, stop on the first `addpages` failure, `commit` when at least one `addpages` returned true, then `set_password_from_input_files`.

- File → Open calls `open_files(chooser.get_filenames())` and does not call `subprocess` or `on_action_new`.
- Add menu item `_New Tab` with action `win.new-tab` directly after `_New Window` in `data/menu.ui`.
- Add `('new-tab', '<Primary>t')` to `_DEFAULT_ACCELS` in `pdfarranger/config.py`.
- `win.new-tab` calls `ArrangerWindow.new_tab()`, which creates an empty `Document`, calls `model.new_tab()`, stores it, and `show_model()`.
- In the window `key_press_event`, Ctrl+Tab calls `model.cycle_tab(False)` and Ctrl+Shift+Tab calls `model.cycle_tab(True)`, then `show_model()`. Return `Gdk.EVENT_STOP` so the icon view does not also move the cursor. Middle-click is wired in Task 12.
- `refresh_document` sets the tab label and, when that document is focused, calls the existing `retitle` logic using that document’s `save_file`, `is_unsaved`, and `pdfqueue`. Move `retitle` onto `ArrangerWindow` and read those fields from `focused_document()`.
- `do_activate` creates the first `ArrangerWindow`, appends it to `self.windows`, and shows it. Delete the in-class construction of `self.model` and `self.iconview`.
- Action callbacks registered on the window forward to `self.focused_document()`. Undo and redo actions are reset from the focused document’s `undomanager` inside `show_model()`.

- [x] **Step 4: Run the tests**

Run: `python -m unittest tests.test_session tests.test_core -v`

Expected: PASS

- [x] **Step 5: Commit**

```bash
git add pdfarranger/window.py pdfarranger/document.py pdfarranger/pdfarranger.py pdfarranger/config.py data/menu.ui tests/test_session.py
git commit -m "Open a second arrangement as a tab"
```

---

### Task 7: New window and moving a tab between windows

**Files:**
- Modify: `pdfarranger/window.py`
- Modify: `pdfarranger/pdfarranger.py`
- Modify: `data/menu.ui` (New Window already exists; point `win.new` at the in-process handler)

**Interfaces:**
- Consumes: `WindowModel.detach`, `WindowModel.attach`
- Produces:
  - `PdfArranger.new_window() -> ArrangerWindow`
  - `ArrangerWindow.detach_document(doc_id: int) -> None`
  - `ArrangerWindow.accept_document(document: Document) -> None`

- [ ] **Step 1: Write the failing test**

The session tests in Task 2 already cover detach and attach. Add one test that the application helper does not spawn a process. Append to `tests/test_session.py`:

```python
class NewWindowHelperTests(unittest.TestCase):
    def test_detach_plan_for_a_second_document_keeps_the_source_open(self):
        source = WindowModel()
        kept = source.focused_id()
        moving = source.new_tab()
        doc_id, close_window = source.detach(moving)
        self.assertEqual(doc_id, moving)
        self.assertFalse(close_window)
        self.assertEqual(source.order, [kept])
```

This test passes as soon as Task 2 is in place. Do not weaken it. The GTK work in this task has no separate pure function. Its check is the dogtail test in Task 14 and this regression test.

- [ ] **Step 2: Run the test**

Run: `python -m unittest tests.test_session.NewWindowHelperTests -v`

Expected: PASS (the helper already exists). If it fails, fix `WindowModel.detach` before touching GTK.

- [ ] **Step 3: Implement in-process windows**

Delete `PdfArranger.on_action_new` and every `subprocess.Popen` / `DesktopAppInfo.launch` path that starts another pdfarranger process.

```python
def new_window(self):
    window = ArrangerWindow(self)
    self.windows.append(window)
    window.present()
    return window
```

`win.new` calls `app.new_window()`.

Dragging a tab out of the strip (the tab box receives `drag-data-get` / motion, and a drop outside any `tab-strip` of this process creates a window):

```python
def detach_document(self, doc_id: int) -> None:
    document = self.docs.pop(doc_id)
    _doc_id, close_window = self.model.detach(doc_id)
    other = self.app.new_window_for_document(document)
    document.gtk_window = other.gtk_window
    document.host = other
    if close_window:
        self.app.close_window(self)
    else:
        self.show_model()
```

`ArrangerWindow.__init__` takes `empty=True`. `new_window()` uses the default and shows one empty document. `new_window_for_document` passes `empty=False`: it builds the chrome and a `WindowModel` with `order` cleared (`left_id` None, no initial document) before `accept_document`. Add `WindowModel.clear()` only if the constructor always calls `add_document`; the `empty=False` path should construct `WindowModel` and then set `order`, `left_id`, `right_id` to empty without calling `add_document`. Do that with a parameter `WindowModel(start_empty=False)` that skips `add_document()` in `__init__`. Update the Task 2 constructor to:

```python
def __init__(self, start_empty=True):
    self.next_id = 1
    self.order = []
    self.left_id = None
    self.right_id = None
    self.focused = Pane.LEFT
    self.split = False
    if start_empty:
        self.add_document()
```

The Task 2 tests call `WindowModel()` and still get one document. `new_window_for_document` then calls `accept_document`:

```python
def accept_document(self, document) -> None:
    self.model.attach(document.id)
    self.docs[document.id] = document
    document.host = self
    document.gtk_window = self.gtk_window
    self.refresh_document(document)
    self.show_model()
```

A tab dropped on another window’s `tab-strip` calls `source.detach_document` without `new_window`, then `target.accept_document`. If detach closes the source, close it after the accept.

The tab drag target id is `TAB_MOVE = 1005`, target name `application/x-pdfarranger-tab`, flags `Gtk.TargetFlags.SAME_APP`. The payload is `str(doc_id).encode()` plus the source window id. The app looks up the document. Do not serialize the pikepdf objects.

- [ ] **Step 4: Run the tests**

Run: `python -m unittest tests.test_session tests.test_core -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add pdfarranger/window.py pdfarranger/pdfarranger.py tests/test_session.py
git commit -m "Move tabs between windows in one process"
```

---

### Task 8: Single-instance command line

**Files:**
- Modify: `pdfarranger/pdfarranger.py`
- Test: `tests/test_session.py` (launch plan already tested)

**Interfaces:**
- Consumes: `plan_launch`, `LaunchPlan`, `ArrangerWindow.open_files`
- Produces: `PdfArranger.do_command_line(command_line) -> int` and `PdfArranger.open_launched_files(remote: bool, files: list[str]) -> None`

- [ ] **Step 1: Write the failing test**

`plan_launch` is already tested. Add a thin wrapper test that records the call the command-line handler must make. Append to `tests/test_session.py`:

```python
class CommandLineRoutingTests(unittest.TestCase):
    def test_remote_occupied_window_is_a_new_tab(self):
        plan = plan_launch(True, ["notes.pdf"], True)
        self.assertEqual(plan.action, "new_tab")
        self.assertEqual(plan.files, ["notes.pdf"])
```

- [ ] **Step 2: Run the test**

Run: `python -m unittest tests.test_session.CommandLineRoutingTests -v`

Expected: PASS if Task 1 is complete. If it fails, stop and fix `plan_launch`.

- [ ] **Step 3: Route launches through the running process**

In `PdfArranger.__init__`, set flags to `Gio.ApplicationFlags.HANDLES_COMMAND_LINE` only.

```python
def do_command_line(self, command_line):
    options = command_line.get_options_dict()
    if options.contains("version"):
        # keep the existing version printout
        return 0
    files = []
    remaining = options.lookup_value(GLib.OPTION_REMAINING)
    if remaining is not None:
        for item in remaining:
            files.append(command_line.create_file_for_arg(item).get_path())
    if not self.get_windows():
        self.activate()
    self.open_launched_files(command_line.get_is_remote(), files)
    return 0

def open_launched_files(self, remote: bool, files: list) -> None:
    window = self.active_window()
    occupied = window.focused_document().occupied() if window.docs else False
    plan = plan_launch(remote, files, occupied)
    if plan.action == "raise":
        window.present()
        return
    if plan.action == "fill" and not plan.files and not remote:
        window.present()
        return
    window.open_files(plan.files)
    window.present()
```

`active_window()` returns `self.last_focused_window` when it is still in `self.windows`, otherwise `self.windows[0]`. Set `last_focused_window` from the window `focus_in_event`.

`do_activate` returns immediately when `self.windows` is already non-empty, so a remote command line does not create a second empty window before `open_launched_files`.

Startup with files: `get_is_remote()` is false, `plan.action` is `"fill"`, and `open_files` fills the empty first document.

- [ ] **Step 4: Run the tests**

Run: `python -m unittest tests.test_session tests.test_core -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add pdfarranger/pdfarranger.py tests/test_session.py
git commit -m "Hand a second launch to the running window"
```

---

### Task 9: Windows single-instance fallback

**Files:**
- Create: `pdfarranger/win32ipc.py`
- Modify: `pdfarranger/pdfarranger.py`
- Test: `tests/test_session.py`

**Interfaces:**
- Consumes: `open_launched_files(remote=True, files)`
- Produces:
  - `gtk_unique_is_enough() -> bool` True when `os.name != "nt"`, or GLib is at least 2.44 and `PDFARRANGER_WIN32_IPC` is not `"1"`
  - `class Win32Handoff` with `start(callback)`, `submit(files: list[str]) -> bool`, `stop()`
  - `callback` is `callable(list[str])` and runs on the GLib main loop via `GLib.idle_add`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_session.py`:

```python
import socket
import threading

from pdfarranger.win32ipc import Win32Handoff, encode_files, decode_files


class Win32HandoffTests(unittest.TestCase):
    def test_round_trip_message(self):
        self.assertEqual(decode_files(encode_files(["a.pdf", "b.pdf"])), ["a.pdf", "b.pdf"])

    def test_second_client_delivers_files_to_the_first_server(self):
        received = []
        ready = threading.Event()
        handoff = Win32Handoff(lambda files: received.append(files), ready.set)
        handoff.start()
        self.assertTrue(ready.wait(2))
        self.assertTrue(handoff.submit(["second.pdf"]))
        handoff.wait_idle(2)
        handoff.stop()
        self.assertEqual(received, [["second.pdf"]])
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m unittest tests.test_session.Win32HandoffTests -v`

Expected: FAIL with `ImportError`.

- [ ] **Step 3: Implement the socket handoff**

`encode_files` / `decode_files` use `json.dumps` / `json.loads` of a list of strings, framed as one line ending in `\n`.

`Win32Handoff.start` binds `127.0.0.1` port 0, writes `host:port` to a lock file `%LOCALAPPDATA%/pdfarranger/instance.port` on Windows and `~/.local/share/pdfarranger/instance.port` elsewhere (tests pass an explicit directory). It listens on a daemon thread. Each connection reads one line and calls the callback. `submit` connects to the lock file address, writes one line, and returns True. It returns False when no lock file exists. `stop` closes the socket. `wait_idle` joins the last client handler.

In `PdfArranger.do_startup` (or the start of `do_command_line` before `activate`):

```python
def gtk_unique_is_enough() -> bool:
    if os.environ.get("PDFARRANGER_WIN32_IPC") == "1":
        return False
    if os.name != "nt":
        return True
    return GLib.MAJOR_VERSION > 2 or (GLib.MAJOR_VERSION == 2 and GLib.MINOR_VERSION >= 44)
```

When `gtk_unique_is_enough()` is false:

- Try `Win32Handoff.submit(files)` first. If it returns True, return 0 from `do_command_line` without activating.
- Otherwise `start` the server with callback `lambda files: self.open_launched_files(True, files)` and continue as the primary instance.

Linux and macOS do not construct `Win32Handoff` unless the env var is set. The unit test constructs it directly, so it runs on Windows too.

- [ ] **Step 4: Run the test to verify it passes**

Run: `python -m unittest tests.test_session.Win32HandoffTests tests.test_session.CommandLineRoutingTests -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add pdfarranger/win32ipc.py pdfarranger/pdfarranger.py tests/test_session.py
git commit -m "Add a Windows fallback for handing files to the first window"
```

---

### Task 10: Side by side

**Files:**
- Modify: `pdfarranger/window.py`
- Modify: `data/menu.ui`
- Modify: `pdfarranger/config.py`
- Modify: `data/pdfarranger.ui` is not required

**Interfaces:**
- Consumes: `WindowModel.toggle_split`, `drag_tab_to_right`, `focus_other_pane`, `can_split`, `visible_ids`
- Produces: `ArrangerWindow.set_split_from_model()`, action `win.side-by-side`, action `win.focus-other-pane`

- [ ] **Step 1: Write the failing test**

Task 2 already tests the model. Add the enablement rule the menu must follow. Append:

```python
class SplitEnablementTests(unittest.TestCase):
    def test_split_action_is_enabled_only_with_two_documents(self):
        model = WindowModel()
        self.assertFalse(model.can_split())
        model.new_tab()
        self.assertTrue(model.can_split())
```

- [ ] **Step 2: Run the test**

Run: `python -m unittest tests.test_session.SplitEnablementTests -v`

Expected: PASS after Task 2. If it fails, fix `can_split` before building the menu.

- [ ] **Step 3: Show two panes**

In the View menu, add `_Side by Side` with action `win.side-by-side` after Fullscreen.

Add `('focus-other-pane', 'F6')` to `_DEFAULT_ACCELS`. Do not add a shortcut for `side-by-side`.

`show_model()` when `model.split` is true:

- Pack a horizontal `Gtk.Paned` into `page-area`.
- Pack `docs[left_id].sw` on the left and `docs[right_id].sw` on the right.
- Add CSS class `focused-pane` only to the focused document’s scrolled window.

```css
scrolledwindow.focused-pane {
    border-width: 2px;
    border-style: solid;
    border-color: #1c71d8;
}
```

Load that CSS with the existing `Gtk.CssProvider` in `do_activate`. When `model.split` is false, remove `focused-pane` from every scrolled window and pack only the left document.

`win.side-by-side` calls `model.toggle_split()` then `show_model()`. Set the action enabled with `model.can_split()` inside `refresh_document` / `show_model`.

`win.focus-other-pane` calls `model.focus_other_pane()` then `show_model()`.

A tab dragged onto the right half of `page-area` calls `model.drag_tab_to_right(doc_id)` then `show_model()`. Use the same `TAB_MOVE` target as Task 7. If the drop x is greater than half of the page-area allocation, it is the right edge. Otherwise it is a move into this window’s strip (Task 7).

Call `release_renderer()` for every document id outside `model.visible_ids()`. Call `silent_render()` for visible documents that already have a renderer.

Zoom actions stay forwarded to `focused_document()`, so each pane keeps the zoom stored on its document.

- [ ] **Step 4: Run the tests**

Run: `python -m unittest tests.test_session tests.test_core -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add pdfarranger/window.py pdfarranger/config.py data/menu.ui tests/test_session.py
git commit -m "Add a two-pane view for the focused window"
```

---

### Task 11: Page drags and file drops across documents

**Files:**
- Modify: `pdfarranger/document.py`
- Modify: `pdfarranger/pdfarranger.py` (target constants can move to `document.py`)

**Interfaces:**
- Consumes: `drop_target`, `DropSite`, `SaveGate` is not used here
- Produces: drag target `MODEL_ROW_SAME_APP = 1004` with `Gtk.TargetFlags.SAME_APP`. Payload is `"{src_doc_id}\\n{path}\\n{path}"` encoded utf-8. `Document.iv_dnd_received_data` handles that target.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_session.py`:

```python
from pdfarranger.document import page_drag_action_is_move


class PageDragTests(unittest.TestCase):
    def test_windows_moves_unless_ctrl_is_held(self):
        self.assertTrue(page_drag_action_is_move("nt", ctrl_held=False))
        self.assertFalse(page_drag_action_is_move("nt", ctrl_held=True))

    def test_posix_moves(self):
        self.assertTrue(page_drag_action_is_move("posix", ctrl_held=False))
        self.assertTrue(page_drag_action_is_move("posix", ctrl_held=True))

    def test_same_app_payload_round_trip(self):
        from pdfarranger.document import encode_page_drag, decode_page_drag
        payload = encode_page_drag(7, ["0", "2"])
        self.assertEqual(decode_page_drag(payload), (7, ["0", "2"]))
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m unittest tests.test_session.PageDragTests -v`

Expected: FAIL with `ImportError`.

- [ ] **Step 3: Copy or move pages between icon views**

```python
def page_drag_action_is_move(os_name: str, ctrl_held: bool) -> bool:
    if os_name == "nt":
        return not ctrl_held
    if os_name == "posix":
        return True
    raise ValueError(os_name)


def encode_page_drag(doc_id: int, paths: list) -> bytes:
    body = str(doc_id) + "\n" + "\n".join(paths)
    return body.encode("utf-8")


def decode_page_drag(payload: bytes):
    text = payload.decode("utf-8")
    doc_id, *paths = text.split("\n")
    return int(doc_id), paths
```

Add `MODEL_ROW_SAME_APP` to the icon-view source and dest targets with `SAME_APP`. Keep `MODEL_ROW_INTERN` for a drag inside one icon view and `MODEL_ROW_EXTERN` for a real other process.

In `iv_dnd_motion`, choose MOVE or COPY with `page_drag_action_is_move(os.name, is_ctrl_pressed() if os.name == "nt" else False)`.

In `iv_dnd_get_data`, when the requested target is `MODEL_ROW_SAME_APP`, write `encode_page_drag(self.id, [str(path) for path in selected])`.

In `iv_dnd_received_data`, when the target is `MODEL_ROW_SAME_APP`:

- `src_id, paths = decode_page_drag(data)`
- Look up the source document through `self.host.app.document_by_id(src_id)`.
- Duplicate those pages and insert them with the existing before/after insert used by `MODEL_ROW_INTERN`.
- `self.undomanager.commit("Copy" if copy else "Move")` was already committed on the destination before the insert. Use `"Copy"` when the action is not MOVE, else `"Move"`.
- Mark the destination unsaved.
- When the action is MOVE, delete those paths from the source model inside `source.render_lock()`, `source.undomanager.commit("Move")`, and `source.set_unsaved(True)`.

File drops: `sw_dnd_received_data` adds URIs to `self`, the document that owns that scrolled window. That is `drop_target(DropSite.PANE, self.id, None, focused)`.

The tab box’s `drag-data-received` for `text/uri-list` calls `window.import_files(doc_id, paths)` which runs `_add_paths` on that document. The page-area background (drops that hit neither a tab nor an icon view) calls `_add_paths` on `focused_document()`. Several URIs go through one `PageAdder.commit`.

- [ ] **Step 4: Run the tests**

Run: `python -m unittest tests.test_session tests.test_core -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add pdfarranger/document.py pdfarranger/window.py tests/test_session.py
git commit -m "Drag pages and drop files between open documents"
```

---

### Task 12: Saving and closing

**Files:**
- Modify: `pdfarranger/window.py`
- Modify: `pdfarranger/document.py`
- Modify: `pdfarranger/pdfarranger.py`

**Interfaces:**
- Consumes: `SaveGate`, `prompt_order`, `resolve_prompts`, `single_close`, `PromptChoice`, `WindowModel.close_document`
- Produces:
  - `PdfArranger.save_gate: SaveGate`
  - `Document.begin_export() -> bool` returns False when the gate is busy
  - `ArrangerWindow.close_document(doc_id: int) -> None`
  - `ArrangerWindow.close_window() -> bool` True when the window did close
  - `PdfArranger.quit_all() -> None`

- [ ] **Step 1: Write the failing test**

The prompt tests in Task 3 are the contract. Add the window-level ordering the quit path must use. Append:

```python
class QuitOrderTests(unittest.TestCase):
    def test_quit_asks_the_focused_window_first(self):
        from pdfarranger.session import window_prompt_sequence
        # (window_id, focused_id, unsaved_ids, tab_order)
        windows = [
            (10, 1, [1], [1]),
            (11, 3, [2, 3], [2, 3]),
        ]
        self.assertEqual(
            window_prompt_sequence(windows, focused_window_id=11),
            [(11, [3, 2]), (10, [1])],
        )
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m unittest tests.test_session.QuitOrderTests -v`

Expected: FAIL with `ImportError` for `window_prompt_sequence`.

- [ ] **Step 3: Implement prompts and the save gate**

Add to `session.py`:

```python
def window_prompt_sequence(windows: list, focused_window_id: int) -> list:
    """windows items are (window_id, focused_id, unsaved_ids, tab_order)."""
    ordered = sorted(windows, key=lambda item: 0 if item[0] == focused_window_id else 1)
    sequence = []
    for window_id, focused_id, unsaved_ids, tab_order in ordered:
        docs = prompt_order(focused_id, unsaved_ids, tab_order)
        if docs:
            sequence.append((window_id, docs))
    return sequence
```

Wire it:

- `Document.save`, `on_action_export_all`, `choose_export_selection_pdf_name`, and `on_action_print` call `begin_export()` first. `begin_export` returns False when `app.save_gate.can_start()` is false. On success it calls `save_gate.start(self.id)`. `export_finished` and the print completion path call `save_gate.finish()` in a `finally`.
- While `save_gate.busy_id == self.id`, ignore edit actions (`delete`, `paste`, `rotate`, drop) by returning at the start of those handlers when `self.app.save_gate.busy_id == self.id`.
- Disable `save`, `save-as`, `export-selection`, `export-all`, and `print` on every document while the gate is busy. `show_model` applies that.
- `close_document`: if `save_gate.busy_id == doc_id`, return without closing. The existing `export_finished` continues a stored `post_action`. Set `document.post_action = ("close", doc_id)` and return. When the gate is free and the document is unsaved, call the existing `save_changes_dialog`. Map the current responses Don’t Save → `PromptChoice.DISCARD`, Cancel → `CANCEL`, Save → `SAVE`. Then `single_close`. `"abort"` returns. `"discard"` calls `model.close_document` and destroys the document. `"save_then_close"` calls `save_or_choose` and sets `post_action = ("close", doc_id)` so `export_finished` closes only after success.
- Closing the last document uses the model’s `"emptied"` result: destroy the old document, create a new empty one for the new id, and keep the window.
- Tab close button and middle-click (`button == 2`) call `close_document`.
- `close_window`: if the busy document is in this window, set a window-level `post_action = "close-window"` and return False. Otherwise `prompt_order` for this window’s unsaved docs. Ask each dialog before closing any document. On cancel, return False. Then save each id in `save_ids`. If a save fails, return False and leave the documents open. Then destroy every document and remove the window. If it was the last window, call `app.quit()`.
- `quit_all` uses `window_prompt_sequence` across `app.windows`, focused window first. Cancel returns. Saves run only after every window has answered. Then close every window and `app.quit()`.
- Ctrl+Q (`win.quit`) calls `quit_all`. The window delete event calls `close_window`.

- [ ] **Step 4: Run the tests**

Run: `python -m unittest tests.test_session tests.test_core -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add pdfarranger/session.py pdfarranger/window.py pdfarranger/document.py pdfarranger/pdfarranger.py tests/test_session.py
git commit -m "Close tabs and windows with one save at a time"
```

---

### Task 13: Find bar follows the focused document

**Files:**
- Modify: `pdfarranger/search.py`
- Modify: `pdfarranger/window.py`
- Modify: `pdfarranger/document.py`

**Interfaces:**
- Consumes: `Document.find_text`, `ArrangerWindow.show_model`
- Produces: `SearchBarWidget.bind_document(document) -> None`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_session.py`:

```python
class FindTextMemoryTests(unittest.TestCase):
    def test_each_document_keeps_its_query(self):
        app = _AppDirs()
        first = Document(app, 1)
        second = Document(app, 2)
        first.find_text = "alpha"
        second.find_text = "beta"
        self.assertEqual(first.find_text, "alpha")
        self.assertEqual(second.find_text, "beta")
```

- [ ] **Step 2: Run the test**

Run: `python -m unittest tests.test_session.FindTextMemoryTests -v`

Expected: PASS once Task 4 has `find_text`. If it fails, add the field before editing `SearchBarWidget`.

- [ ] **Step 3: Rebind the existing search bar**

There is one `SearchBarWidget` under the tab strip, in the same place `pdfarranger.ui` packs `searchbar` today.

```python
def bind_document(self, document) -> None:
    self.iconview = document.iconview
    self.pdfqueue = document.pdfqueue
    self.show_find_results = document.show_find_results
    self.clear_find_results = document.clear_find_results
    self.entry.set_text(document.find_text)
```

Before rebinding, `show_model` stores `searchbar.entry.get_text()` into the previously focused document’s `find_text`. Then it binds the newly focused document.

Find actions (`win.find`, `find_prev`, `find_next`, `find_all`) stay on the window and call the single search bar, which now points at the focused document.

- [ ] **Step 4: Run the tests**

Run: `python -m unittest tests.test_session tests.test_core -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add pdfarranger/search.py pdfarranger/window.py pdfarranger/document.py tests/test_session.py
git commit -m "Keep a separate find query for each document"
```

---

### Task 14: Dogtail coverage and the manual Windows check

**Files:**
- Modify: `tests/test.py`
- Modify: `TESTING.md`

**Interfaces:**
- Consumes: the running app from Tasks 6–13. Tab labels use widget name `pdfarranger-tab-label`.

- [ ] **Step 1: Update TestBatch09 and add TestBatch17**

Replace `TestBatch09.test_03_open_again` so it no longer waits for a second application:

```python
def test_03_open_again(self):
    """Open another file as a second tab in the same process."""
    self.assertEqual(len(self._apps()), 1)
    filechooser = self._import_file("tests/test.pdf", open_action=True)
    self._wait_cond(lambda: filechooser.dead)
    self.assertEqual(len(self._apps()), 1)
    self._wait_cond(lambda: len(self._tab_labels()) >= 2)
```

Add helper on `PdfArrangerTest`:

```python
def _tab_labels(self):
    return [
        node
        for node in self._find_by_role("label")
        if node.name == "pdfarranger-tab-label" or node.get_name() == "pdfarranger-tab-label"
    ]
```

Use whichever dogtail attribute this version exposes for the accessible name. The widget name set in Task 6 must be the one this helper reads. If `get_name` is the GTK widget name and dogtail exposes it as `name`, compare `node.name`.

Replace `test_04_quit` so Ctrl+W closes the second tab and one app remains, then `test_05_quit` quits the remaining window.

Add `TestBatch17`:

```python
class TestBatch17(PdfArrangerTest):
    """Tabs, side by side, and closing one document."""

    def test_01_startup_merges_two_files_into_one_tab(self):
        self._start(["tests/test.pdf"])
        one = len(self._icons())
        self.assertGreater(one, 0)
        self._quit()
        self._start(["tests/test.pdf", "tests/test.pdf"])
        self._wait_cond(lambda: len(self._icons()) == one * 2)
        self.assertEqual(len(self._apps()), 1)
        self.assertEqual(len(self._tab_labels()), 1)

    def test_02_new_tab_and_import_do_not_change_the_first_tab(self):
        self._start(["tests/test.pdf"])
        one = len(self._icons())
        self._mainmenu("New Tab")
        self._wait_cond(lambda: len(self._tab_labels()) == 2)
        self._import_file("tests/test.pdf", open_action=False)
        self._wait_cond(lambda: len(self._icons()) == one)
        self._tab_labels()[0].click()
        self._wait_cond(lambda: len(self._icons()) == one)

    def test_03_close_clean_second_tab(self):
        self._app().keyCombo("<ctrl>w")
        self._wait_cond(lambda: len(self._tab_labels()) == 1)

    def test_04_side_by_side(self):
        self._mainmenu("New Tab")
        self._import_file("tests/test.pdf", open_action=False)
        self._mainmenu(["View", "Side by Side"])
        self._wait_cond(lambda: len(self._find_by_role("icon view")) == 2)

    def test_05_quit(self):
        self._quit_without_saving()
```

`_icons` counts icon-view children of the whole app. `test_02` switches back to the first tab before asserting the original count. Adjust the click target if dogtail returns the label’s parent. The assertion that matters: after import into the second tab, the first tab still has `one` pages.

In `TESTING.md`, under the `test.py` bullet, add: `TestBatch09` opens a second file as another tab in the same process. `TestBatch17` covers startup merge, import into the focused tab, and side by side.

- [ ] **Step 2: Run the headless tests**

Run: `python -m unittest tests.test_session tests.test_core tests.test_exporter -v`

Expected: PASS

- [ ] **Step 3: Run the GUI tests on Linux**

Run, when dogtail and a display or Xvfb are available:

```bash
python -X tracemalloc -u -m unittest -v tests.test.TestBatch09 tests.test.TestBatch17
```

Expected: PASS. On Windows without dogtail, skip this command and record that it was not run.

- [ ] **Step 4: Manual Windows check**

On the MSYS2 build:

1. Start pdfarranger and open a PDF.
2. Launch pdfarranger again with a different PDF. Expect one window and two tabs.
3. Choose View → Side by Side. Expect both documents, and a blue border on the focused pane.
4. Drag a page from the right pane to the left. Expect the page to move. Hold Ctrl and drag. Expect a copy.
5. Drag a tab out of the strip. Expect a second window. Drag the tab back onto the first strip.
6. Close an unsaved tab. Expect the save prompt to use that tab’s name. Cancel. Expect the tab to stay.

- [ ] **Step 5: Commit**

```bash
git add tests/test.py TESTING.md
git commit -m "Cover tabs in the dogtail suite"
```
