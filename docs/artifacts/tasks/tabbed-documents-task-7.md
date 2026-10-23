# Task 7: New Window and Moving a Tab Between Windows

Implementation tracking for Task 7 of the tabbed documents feature plan (`docs/superpowers/plans/2026-10-22-tabbed-documents.md`).

## Status: Completed

## Tasks
- [x] Step 1: Write failing/regression test in `tests/test_session.py` (`NewWindowHelperTests`) and any additional unit tests for `new_window`, `new_window_for_document`, and tab moving
- [x] Step 2: Run test suite to verify test passes/fails as expected (`python -m unittest tests.test_session.NewWindowHelperTests -v`)
- [x] Step 3: Implement in-process windows:
  - [x] Update `WindowModel.__init__` in `pdfarranger/session.py` with `start_empty=True` parameter and `id_allocator`
  - [x] Add `PdfArranger.new_window()` and `PdfArranger.new_window_for_document(document)` in `pdfarranger/pdfarranger.py`
  - [x] Update `ArrangerWindow.__init__` to accept `empty=True`
  - [x] Implement `ArrangerWindow.detach_document(doc_id)` and `ArrangerWindow.accept_document(document)`
  - [x] Implement tab drag and drop support (`TAB_MOVE = 1005`, `application/x-pdfarranger-tab` with `SAME_APP`):
    - Tab drag source on tab widget
    - Tab drop destination on `tab-strip` (move tab between windows or reorder)
    - Tab drop outside any `tab-strip` to detach into a new window
  - [x] Ensure `win.new` calls `app.new_window()`
- [x] Step 4: Run test suite to verify everything passes (`python -m unittest tests.test_session -v`)
- [x] Step 5: Create walkthrough artifact (`docs/artifacts/walkthroughs/tabbed-documents-task-7.md`) and commit changes
