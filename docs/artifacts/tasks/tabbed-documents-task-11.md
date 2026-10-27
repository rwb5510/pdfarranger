# Task 11: Page Drags and File Drops Across Documents

Implementation tracking for Task 11 of the tabbed documents feature plan (`docs/superpowers/plans/2026-10-22-tabbed-documents.md`).

## Status: Completed

## Tasks
- [x] Step 1: Write failing test in `tests/test_session.py` (`PageDragTests`)
- [x] Step 2: Run test to verify it fails (`python -m unittest tests.test_session.PageDragTests -v`)
- [x] Step 3: Implement page drags and file drops across documents:
  - [x] Implement `page_drag_action_is_move`, `encode_page_drag`, and `decode_page_drag` in `pdfarranger/document.py`
  - [x] Define `MODEL_ROW_SAME_APP = 1004` with `Gtk.TargetFlags.SAME_APP` and add to icon-view drag source & dest targets
  - [x] Implement MOVE vs COPY logic in `iv_dnd_motion` using `page_drag_action_is_move` (and `is_ctrl_pressed()` on Windows)
  - [x] Implement payload creation in `iv_dnd_get_data` for `MODEL_ROW_SAME_APP` using `encode_page_drag`
  - [x] Implement payload handling in `iv_dnd_received_data` for `MODEL_ROW_SAME_APP` across documents:
    - Look up source doc via `app.document_by_id(src_id)`
    - Duplicate and insert pages into destination
    - Commit undo as "Copy" or "Move"
    - If MOVE, remove pages from source doc with render lock, undo commit, and mark unsaved
  - [x] Ensure `sw_dnd_received_data` handles file drops onto scrolled window/document
  - [x] Ensure tab box drag-data-received handles file drops (`text/uri-list`) calling `window.import_files(doc_id, paths)` / `_add_paths`
  - [x] Ensure page area background handles file drops routing to `focused_document()`
- [x] Step 4: Run tests (`tests.test_session`) to verify everything passes
- [x] Step 5: Create walkthrough artifact (`docs/artifacts/walkthroughs/tabbed-documents-task-11.md`), update plan checkboxes in `docs/superpowers/plans/2026-10-22-tabbed-documents.md`, and commit changes
