# Task 10: Side by Side

Implementation tracking for Task 10 of the tabbed documents feature plan (`docs/superpowers/plans/2026-10-22-tabbed-documents.md`).

## Status: Completed

## Tasks
- [x] Step 1: Write test in `tests/test_session.py` (`SplitEnablementTests`)
- [x] Step 2: Run the test to verify it passes (`python -m unittest tests.test_session.SplitEnablementTests -v`)
- [x] Step 3: Implement Side by Side:
  - [x] Add `_Side by Side` menu item with action `win.side-by-side` in `data/menu.ui` after Fullscreen
  - [x] Add `('focus-other-pane', 'F6')` to `_DEFAULT_ACCELS` in `pdfarranger/config.py`
  - [x] Add CSS `scrolledwindow.focused-pane` to `do_activate` in `pdfarranger/pdfarranger.py`
  - [x] Add actions `win.side-by-side` and `win.focus-other-pane` in `pdfarranger/window.py`
  - [x] Implement `set_split_from_model()` or split view handling in `show_model()` in `pdfarranger/window.py`:
    - Pack horizontal `Gtk.Paned` into `page_area` when `model.split` is True
    - Pack `docs[left_id].sw` on left and `docs[right_id].sw` on right
    - Add/remove CSS class `focused-pane` according to focus and split state
    - Handle `release_renderer()` / `silent_render()` per `model.visible_ids()`
    - Enable/disable `win.side-by-side` action based on `model.can_split()`
  - [x] Implement tab drag to right half of `page-area` calling `model.drag_tab_to_right(doc_id)`
  - [x] Support clicking or focusing pane to update focused document in `ArrangerWindow`
- [x] Step 4: Run test suites (`tests.test_session`, `tests.test_core`) to verify everything passes
- [x] Step 5: Create walkthrough artifact (`docs/artifacts/walkthroughs/tabbed-documents-task-10.md`), update plan checkboxes in `docs/superpowers/plans/2026-10-22-tabbed-documents.md`, and commit changes
