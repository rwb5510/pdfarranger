# Task 12: Saving and Closing

Implementation tracking for Task 12 of the tabbed documents feature plan (`docs/superpowers/plans/2026-10-22-tabbed-documents.md`).

## Status: Completed

## Tasks
- [x] Step 1: Write failing test in `tests/test_session.py` (`QuitOrderTests`)
- [x] Step 2: Run test to verify it fails (`python -m unittest tests.test_session.QuitOrderTests -v`)
- [x] Step 3: Implement saving, closing, and save gate:
  - [x] Add `window_prompt_sequence` to `pdfarranger/session.py`
  - [x] Wire `save_gate: SaveGate` on `PdfArranger`
  - [x] Implement `Document.begin_export() -> bool` checking and setting `app.save_gate`, and ensure `export_finished` and print completion call `save_gate.finish()`
  - [x] Ignore edit actions (`delete`, `paste`, `rotate`, drop) while document is busy exporting (`save_gate.busy_id == self.id`)
  - [x] Disable save/export/print actions across documents while gate is busy (updated in `show_model` / `refresh_document`)
  - [x] Implement `ArrangerWindow.close_document(doc_id)` with busy gate handling (`post_action`), unsaved prompts (`save_changes_dialog` mapped to `PromptChoice`), `"emptied"` vs `"removed"` handling
  - [x] Wire tab close button and middle-click to `close_document`
  - [x] Implement `ArrangerWindow.close_window() -> bool` with busy gate deferral (`post_action = "close-window"`), prompt-order asking, bulk save execution, and window destruction
  - [x] Implement `PdfArranger.quit_all()` using `window_prompt_sequence`, batching prompts and saves across windows, then closing windows and calling `quit()`
  - [x] Route Ctrl+Q (`win.quit`) to `quit_all` and window delete event to `close_window`
- [x] Step 4: Run tests (`tests.test_session` and `tests.test_core`) to verify everything passes
- [x] Step 5: Create walkthrough artifact (`docs/artifacts/walkthroughs/tabbed-documents-task-12.md`), update plan checkboxes in `docs/superpowers/plans/2026-10-22-tabbed-documents.md`, and commit changes
