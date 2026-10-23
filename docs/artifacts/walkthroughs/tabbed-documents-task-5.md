# Walkthrough: Task 5 - Move Page Operations onto Document

## Summary
Completed Task 5 of the tabbed documents feature plan (`docs/superpowers/plans/2026-10-22-tabbed-documents.md`). Moved 107 page-editing, rendering, zoom, export, undo/redo, dnd, and dialog action methods from `PdfArranger` onto `Document`. Implemented `Document.build_view()` to instantiate `sw`, `model`, `undomanager`, `iconview`, and interaction helpers (`IconviewCursor`, `IconviewDragSelect`, `IconviewPanView`). Updated `PdfArranger` to initialize `self.doc = Document(self, 0)` and forward page actions, retaining full AST validity and test suite compatibility.

## Changes Made
1. **`tests/test_session.py`**:
   - Added `DocumentMethodTests` verifying that key page operations (`build_view`, `render`, `quit_rendering`, `set_unsaved`, `save_or_choose`, `paste_pages`, `iv_dnd_received_data`, `sw_dnd_received_data`, `on_action_zoom_in`, `clear_data`, `error_message_dialog`) are callable methods on `Document`.

2. **`pdfarranger/document.py`**:
   - Implemented `Document.build_view(sw_parent_unused=None)` setting up `model`, `undomanager`, `iconview`, `sw`, and navigation cursors with the document instance.
   - Moved all 107 page operation methods from `PdfArranger` onto `Document`:
     - Updated dialog parent references from `self.window` to `self.gtk_window`.
     - Updated application references `self.config`, `self.clipboard`, `self.quit_flag`, `self.disable_quit` to `self.app.*`.
     - Wrapped `error_message_dialog` and `confirm_dialog` to forward to `self.host`.
     - Updated `update_statusbar` to call `self.host.set_status(self, left_text, right_text)`.
     - Updated `set_unsaved` to set `self.is_unsaved = flag` and notify `self.host.refresh_document(self)`.
     - Replaced `self.retitle()` invocations with `self.host.refresh_document(self)`.
     - Added helper and static utilities (`process_pending_events`, `get_cnt_filename`, `set_text_renderer_cell_height`, `__create_filters`).

3. **`pdfarranger/pdfarranger.py`**:
   - Imported `Document` from `.document`.
   - In `__init__`: initialized `self.doc = Document(self, 0)`.
   - In `do_activate`: wired `self.doc.build_view()`, mapped `self.sw = self.doc.sw`, and updated search bar bindings.
   - In `__create_actions`: rewired action callbacks to invoke `self.doc.<method>`.
   - Delegated remaining window-level methods (`add_files`, `on_action_open`, `on_action_save`, `on_action_save_as`, `on_action_import`, `on_action_close`, `on_quit`, `close_application`, `retitle`, `window_configure_event`, `window_focus_in_out_event`) to use `self.doc.*`.
   - Added `refresh_document` and `set_status` methods, along with property forwarding and `__getattr__` delegation to `self.doc`.
   - Removed moved methods from `PdfArranger`.

4. **Plan and Tracking**:
   - Updated `docs/superpowers/plans/2026-10-22-tabbed-documents.md` marking Task 5 steps completed.
   - Updated `docs/artifacts/tasks/tabbed-documents-task-5.md`.

## Verification
- Validated `pdfarranger/pdfarranger.py` with `ast.parse`: syntax is valid.
- Executed `python -m unittest tests.test_session -v`: all 35 unit tests passed.
