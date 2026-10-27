# Walkthrough: Task 10 - Side by Side Two-Pane View

## Overview
Task 10 implements the two-pane side-by-side view for `ArrangerWindow`, allowing users to view two documents concurrently in a horizontal split view, toggle the split via menu or dragging tabs, navigate focus between panes using F6 or mouse clicks, and adjust per-document zoom independently:
- Added `_Side by Side` menu item in `data/menu.ui` with action `win.side-by-side` under View after Fullscreen.
- Registered accelerator `('focus-other-pane', 'F6')` in `pdfarranger/config.py` with no accelerator for `side-by-side`.
- Added CSS styling for `.focused-pane` with a 2px blue solid outline (`#1c71d8`) in `PdfArranger.do_activate`.
- Implemented `ArrangerWindow.set_split_from_model()` to dynamically pack a horizontal `Gtk.Paned` in `page-area` when `model.split` is True, or single document scrolled window when False.
- Dynamically managed the `focused-pane` CSS class on scrolled windows to highlight only the active pane.
- Added actions `win.side-by-side` (toggling `model.toggle_split()`) and `win.focus-other-pane` (toggling `model.focus_other_pane()`), with action enablement synchronized with `model.can_split()` and `model.split`.
- Configured drag destination on `page-area` for `application/x-pdfarranger-tab` (`TAB_MOVE`): dragging onto the right half splits the tab to the right (`model.drag_tab_to_right`), while dragging onto the left half routes to normal tab strip insertion.
- Attached click handlers on document views to automatically shift model focus when clicking between panes.

## Key Changes

### 1. View Menu & Accelerators
- `data/menu.ui`: Added `_Side by Side` entry associated with `win.side-by-side`.
- `pdfarranger/config.py`: Added `('focus-other-pane', 'F6')` to `_DEFAULT_ACCELS`.

### 2. Styling (`pdfarranger/pdfarranger.py`)
- In `do_activate`, added `scrolledwindow.focused-pane` style rule:
  ```css
  scrolledwindow.focused-pane {
      border-width: 2px;
      border-style: solid;
      border-color: #1c71d8;
  }
  ```

### 3. Window & Panes (`pdfarranger/window.py`)
- `set_split_from_model(self)`:
  - Detaches current children of `page_area` and handles nested `Paned` cleanup.
  - When `model.split` is True and both left and right documents are present, packs a horizontal `Gtk.Paned` with `pack1(left.sw)` and `pack2(right.sw)`.
  - When `model.split` is False, packs `left.sw` directly into `page_area`.
  - Updates `focused-pane` CSS class on `sw` widgets, ensuring only the active document in split mode has the highlight.
- `show_model(self)`:
  - Invokes `set_split_from_model()`.
  - Updates `side-by-side` action enablement according to `model.can_split()`.
  - Updates `focus-other-pane` action enablement according to `model.split`.
  - Maintains thumbnail renderer release for non-visible tabs and silent rendering for visible tabs.
- `refresh_document(self, document)`:
  - Updates `side-by-side` and `focus-other-pane` action enablement states.
- `_on_page_area_drag_data_received`:
  - Determines if drop coordinate `x > half_width`.
  - If dropped on the right half, calls `model.drag_tab_to_right(doc_id)` and refreshes view.
  - If dropped on the left half, forwards to tab strip receiver.
- `_attach_doc_view` / `_on_pane_click`:
  - Listens for clicks on document views and updates focused pane in split mode without interrupting click event propagation.
- Actions:
  - Registered `side-by-side` and `focus-other-pane` actions with handlers `on_action_side_by_side` and `on_action_focus_other_pane`.

### 4. Tests (`tests/test_session.py`)
- Added `SplitEnablementTests`:
  - `test_split_action_is_enabled_only_with_two_documents`: verifies `can_split()` is True only when >= 2 documents exist.
- Added `SideBySideWindowTests`:
  - `test_menu_and_config_declarations`: verifies `data/menu.ui` and `pdfarranger/config.py` declarations.
  - `test_side_by_side_and_focus_actions_toggle_model`: verifies `on_action_side_by_side` and `on_action_focus_other_pane` actions update model state correctly.
  - `test_page_area_tab_drop_routes_to_drag_tab_to_right`: verifies page area DND routing on left vs right halves.

## Verification Results
All 62 unit tests in `tests/test_session.py` passed:
```
Ran 62 tests in 2.101s
OK
```
