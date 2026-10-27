# Walkthrough: Task 12 - Saving and Closing Across Tabs and Windows

## Overview
Task 12 coordinates saving, exporting, tab closure, window closure, and application quitting across multiple tabs and windows:
- Added `window_prompt_sequence` in `pdfarranger/session.py` to prioritize the focused window when prompting for unsaved changes during application quit.
- Added a global `SaveGate` instance (`self.save_gate`) on `PdfArranger` to ensure only one document saves or exports at a time.
- Integrated `Document.begin_export()`, `Document.finish_export()`, `Document.is_busy()`, and `Document.destroy()`.
- Guarded all editing actions (`delete`, `cut`, `paste`, `rotate`, `duplicate`, and drag-and-drop insertion) while a document is busy exporting.
- Updated `ArrangerWindow.show_model` to disable save, save-as, export, and print actions when the save gate is busy.
- Implemented `ArrangerWindow.close_document(doc_id)` with deferred close if busy (`post_action`), unsaved changes dialog, and `"emptied"` vs `"removed"` handling.
- Wired tab close button and tab middle-click (`button == 2`) to `close_document`.
- Implemented `ArrangerWindow.close_window() -> bool` with window-level deferred action (`post_action = "close-window"`), multi-document prompt resolution, batch saving, document cleanup, and last-window quit.
- Implemented `PdfArranger.quit_all()` utilizing `window_prompt_sequence`, collecting prompts across all windows before saving, and cleanly closing all windows.
- Wired Ctrl+Q (`win.quit`) to `quit_all()` and window close events (`delete-event`) to `close_window()`.

---

## Key Changes

### 1. Window Prompt Sequencing (`pdfarranger/session.py`)
- Implemented `window_prompt_sequence(windows: list, focused_window_id: int) -> list`:
  - Sorts windows so `focused_window_id` comes first.
  - Orders each window's unsaved documents using `prompt_order(focused_id, unsaved_ids, tab_order)`.
  - Returns `[(window_id, [doc_ids...]), ...]`.

### 2. Application-Level Save Gate & Quit Coordination (`pdfarranger/pdfarranger.py`)
- Instantiated `self.save_gate = SaveGate()` on `PdfArranger`.
- Implemented `PdfArranger.quit_all() -> None`:
  - Checks if any document across all windows is busy; if so, defers quit on that window with `window.post_action = "quit-all"`.
  - Prompts unsaved documents across all windows via `window_prompt_sequence`.
  - On cancel at any prompt, aborts the entire quit process without closing or saving anything.
  - Executes saves for documents marked for saving; aborts quit if any save fails.
  - Destroys all documents, closes all windows, and calls `self.quit()`.
- Updated `on_quit` handler to invoke `self.quit_all()`.

### 3. Document Export Gate & Busy Guarding (`pdfarranger/document.py`)
- Added:
  - `is_busy() -> bool`: checks if `app.save_gate.busy_id == self.id`.
  - `begin_export() -> bool`: starts export gate for `self.id`, allowing reentrant calls for the active document.
  - `finish_export() -> None`: finishes export gate if held by `self.id`.
  - `destroy() -> None`: cleans up temp files and frees resources.
- Wired `begin_export()` and `finish_export()` into `save()`, `export_finished()`, `choose_export_selection_pdf_name()`, `on_action_export_all()`, and `on_action_print()`.
- Added `if self.is_busy(): return` guards on editing handlers:
  - `on_action_delete`
  - `on_action_cut`
  - `on_action_paste`
  - `rotate_page_action`
  - `duplicate`
  - `iv_dnd_received_data`
  - `sw_dnd_received_data`

### 4. Window Close and Tab Interactions (`pdfarranger/window.py`)
- Initialized `self.post_action = None`.
- Updated `show_model()` to disable `save`, `save-as`, `export-selection`, `export-all`, and `print` actions while `app.save_gate.is_busy()`.
- Added `save_changes_dialog(msg)` wrapping GTK dialog and mapping responses to `PromptChoice.DISCARD`, `PromptChoice.SAVE`, or `PromptChoice.CANCEL`.
- Implemented `close_document(doc_id: int)`:
  - If gate is busy on `doc_id`, records `document.post_action = ("close", doc_id)` and returns.
  - If document is unsaved, prompts with `save_changes_dialog` and uses `single_close`.
  - Handles `"emptied"` (replaces last document in window with fresh empty document) vs `"removed"` (closes tab and destroys document).
- Wired tab close button and tab button-press/release events for middle-click (`event.button == 2`) to `close_document(doc_id)`.
- Implemented `close_window() -> bool`:
  - If any document in the window is busy, records `self.post_action = "close-window"` and returns `False`.
  - Prompts all unsaved documents in this window using `prompt_order`.
  - Aborts on cancel without modifying state.
  - Saves all documents marked for saving; aborts on failure.
  - Destroys all window documents and closes the window. If last window, calls `app.quit()`.
- Connected `on_delete_event` to `close_window()` and `win.quit` action to `app.quit_all()`.

### 5. Unit Tests (`tests/test_session.py`)
Added 14 comprehensive unit tests:
- `QuitOrderTests.test_quit_asks_the_focused_window_first`
- `SaveGateDocumentTests`:
  - `test_begin_and_finish_export`
  - `test_edit_actions_ignored_while_busy`
- `WindowClosePromptTests`:
  - `test_close_document_busy_sets_post_action`
  - `test_close_document_unsaved_cancel_aborts`
  - `test_close_document_unsaved_discard_closes`
  - `test_close_document_last_document_emptied`
  - `test_close_window_busy_sets_post_action`
  - `test_close_window_cancel_returns_false_and_keeps_docs`
  - `test_close_window_saves_and_closes`
  - `test_show_model_disables_actions_while_gate_busy`
- `QuitAllTests`:
  - `test_quit_all_busy_sets_post_action`
  - `test_quit_all_cancel_returns_without_quitting`
  - `test_quit_all_discards_and_quits`

---

## Verification Results
All 86 unit tests in `tests/test_session.py` passed:
```
Ran 86 tests in 2.112s
OK
```
