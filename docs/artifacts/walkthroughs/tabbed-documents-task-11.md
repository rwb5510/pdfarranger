# Walkthrough: Task 11 - Page Drags and File Drops Across Documents

## Overview
Task 11 enables cross-document drag-and-drop operations within the same `PdfArranger` application:
- Defined cross-document drag target `MODEL_ROW_SAME_APP = 1004` registered with `Gtk.TargetFlags.SAME_APP`.
- Added pure helper functions `page_drag_action_is_move`, `encode_page_drag`, and `decode_page_drag` in `pdfarranger/document.py`.
- Updated icon-view motion, get-data, and received-data handlers to support dragging pages between documents (with move vs copy determination, duplicate page insertion, undo commit, and removal from source document on move).
- Configured file drops (`text/uri-list`) onto tab box widgets to import files into the target document (`window.import_files(doc_id, paths)`).
- Configured file drops (`text/uri-list`) onto the tab strip and page area background to route to the focused document (`focused_document()`).

## Key Changes

### 1. Document & DnD Target Handling (`pdfarranger/document.py`, `pdfarranger/pdfarranger.py`)
- **Helper functions**:
  - `page_drag_action_is_move(os_name: str, ctrl_held: bool) -> bool`: returns `not ctrl_held` on Windows (`nt`), `True` on `posix`, or raises `ValueError`.
  - `encode_page_drag(doc_id: int, paths: list) -> bytes`: encodes source document ID and page paths into a newline-separated utf-8 payload.
  - `decode_page_drag(payload: bytes) -> tuple[int, list[str]]`: decodes the payload back to `(doc_id, paths)`.
- **Target Entries**:
  - Added `MODEL_ROW_SAME_APP = 1004` with `Gtk.TargetFlags.SAME_APP` to `TARGETS_IV` in both `Document` and `PdfArranger`.
- **IconView DnD Handlers**:
  - `iv_dnd_motion`: calculates action using `page_drag_action_is_move(os.name, is_ctrl_pressed() if os.name == "nt" else False)`.
  - `iv_dnd_get_data`: serializes selected pages with `encode_page_drag(self.id, [str(path) for path in selected])` when target is `MODEL_ROW_SAME_APP`.
  - `iv_dnd_received_data`:
    - Handles `MODEL_ROW_SAME_APP` across documents by looking up the source via `app.document_by_id(src_id)`.
    - Duplicates and inserts pages into destination model (preserving position `before`/`after`).
    - Merges any missing `pdfdoc` entries into the destination document's `pdfqueue` and re-indexes `page.nfile`.
    - Commits undo on destination as `"Move"` or `"Copy"`.
    - If `move` is True, removes moved pages from the source model under `source.render_lock()`, commits `"Move"` on source undo manager, and marks source unsaved.

### 2. Window File Drops (`pdfarranger/window.py`)
- Added `TEXT_URI_LIST = 1003` to `TARGETS_TAB`.
- Tab widgets (`tab_box`, `event_box`):
  - Set drag destination accepting both `TAB_MOVE` (`application/x-pdfarranger-tab`) and `TEXT_URI_LIST` (`text/uri-list`).
  - Added `_on_tab_box_drag_data_received`: on `text/uri-list`, parses URIs and invokes `self.import_files(doc_id, paths)`.
- Tab strip & Page area backgrounds:
  - Updated `_on_tab_strip_drag_data_received` and `_on_page_area_drag_data_received` to route `text/uri-list` drops to `self.focused_document()._add_paths(paths)`.
- `import_files(self, doc_id, paths)`:
  - Looks up document by ID and imports files using `_add_paths(paths)`.
- Enhanced `_add_paths` in `pdfarranger/window.py` to convert `file:` URIs with `get_file_path_from_uri(p)` when available.

### 3. Unit Tests (`tests/test_session.py`)
- Added `PageDragTests` covering:
  - `test_windows_moves_unless_ctrl_is_held`
  - `test_posix_moves`
  - `test_invalid_os_raises_value_error`
  - `test_same_app_payload_round_trip`
  - `test_target_constants`
  - `test_tab_box_uri_drop_calls_import_files`
  - `test_tab_strip_uri_drop_calls_add_paths_on_focused_document`
  - `test_page_area_uri_drop_calls_add_paths_on_focused_document`
  - `test_document_same_app_dnd_get_data`
  - `test_document_same_app_dnd_received_data_move`

## Verification Results
All 72 unit tests in `tests/test_session.py` passed:
```
Ran 72 tests in 2.096s
OK
```
