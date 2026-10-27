# Walkthrough: Task 2 - Window Model for Tabs and Panes

## Summary
Completed Task 2 of the tabbed documents feature plan (`docs/superpowers/plans/2026-10-22-tabbed-documents.md`). Added pure window model rules (`Pane` and `WindowModel`) in `pdfarranger/session.py` to manage multi-document state, two-pane splits, tab navigation/cycling, drag-to-split, close, and detach/attach across windows.

## Changes Made
1. **`pdfarranger/session.py`**:
   - `Pane`: Enum with `LEFT` and `RIGHT`.
   - `WindowModel`: Pure class representing window tabs and split panes:
     - Maintains `order`, `left_id`, `right_id`, `focused` pane, `split` flag, and document ID generation.
     - `add_document() -> int`: allocates a new document ID and appends to `order`.
     - `focused_id() -> int`: returns the document ID active in the focused pane.
     - `showing(doc_id) -> bool` and `visible_ids() -> set[int]`: inspect which documents are currently rendered in panes.
     - `click_tab(doc_id)`: focuses the pane if visible or displays the tab in the focused pane.
     - `cycle_tab(backwards)`: cycles active tab following the click rule.
     - `open_files(occupied)`: reuses focused document if empty or adds and focuses a new tab.
     - `new_tab() -> int`: adds a new document and focuses it.
     - `can_split() -> bool` and `toggle_split()`: toggles side-by-side view with adjacent tab on the right.
     - `drag_tab_to_right(doc_id)`: splits the window putting the dragged tab into the right pane.
     - `focus_other_pane()`: switches focus between LEFT and RIGHT pane.
     - `close_document(doc_id) -> str`: removes document and repairs active panes, or creates a fresh empty document if the last one was closed (returning `"emptied"`).
     - `detach(doc_id) -> tuple[int, bool]`: removes tab and flags if the window should close (`len(order) == 0`).
     - `attach(doc_id)`: attaches a document transferred from another window into the focused pane.

2. **`tests/test_session.py`**:
   - Added `WindowModelTests` with 14 test cases covering:
     - Initial window state with 1 empty document.
     - Open on empty reusing focused document vs open on occupied creating new tab.
     - Clicking hidden tabs vs clicking visible right tabs.
     - Toggling side-by-side split and wrap-around behavior.
     - Split constraints when fewer than 2 documents exist.
     - Dragging hidden or focused tabs to the right pane.
     - Cycling tabs forward and backward.
     - Closing the last document resulting in an emptied state.
     - Detaching tabs and closing window when the last tab is detached.
     - Detaching and attaching across models.

3. **Plan and Tracking**:
   - Updated `docs/superpowers/plans/2026-10-22-tabbed-documents.md` marking Task 2 steps completed.
   - Updated `docs/artifacts/tasks/tabbed-documents-task-2.md`.

## Verification
- Executed `python -m unittest tests.test_session -v`
- All 26 tests passed (12 from Task 1 + 14 from Task 2).
