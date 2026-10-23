# Walkthrough: Task 7 - New Window and Moving Tabs Between Windows

## Overview
Task 7 enables in-process multi-window support and tab movement between windows:
- File → New Window (`win.new`) creates an `ArrangerWindow` inside the existing application process instead of launching a new external process.
- Dragging a tab outside of any tab strip detaches the document into a new window (`detach_document`).
- Dragging a tab onto another window's tab strip moves the document to that window (`accept_document`).
- If detaching a document leaves the source window empty, that window closes; otherwise the window remains open with its remaining tabs.
- Document IDs are coordinated per application process using `allocate_doc_id` so documents can be moved between windows without ID collisions.

## Key Changes

### 1. Pure Rules & Session (`pdfarranger/session.py`)
- Updated `WindowModel.__init__` to support `start_empty=True` (allowing a window model to start without an initial document when preparing to accept a transferred tab) and an optional `id_allocator`.
- Updated `WindowModel.add_document` to use `self._id_allocator()` when provided.

### 2. Application Process Lifecycle (`pdfarranger/pdfarranger.py`)
- Removed `Popen` and `DesktopAppInfo` process-spawning logic.
- Added `new_window(self)` to instantiate and track in-process `ArrangerWindow` objects.
- Added `new_window_for_document(self, document)` to construct a window around an already existing document.
- Added `allocate_doc_id(self)` to provide monotonic document IDs across all windows in the process.
- Added safeguard in `close_window` for environments without active GTK widgets.

### 3. Window & Tab DND (`pdfarranger/window.py`)
- `ArrangerWindow.__init__`: accepts `empty=True` parameter and connects to the application's doc ID allocator.
- Registered DND target `TAB_MOVE = 1005` (`application/x-pdfarranger-tab` with `SAME_APP`).
- Drag source on tab label and event box (`drag-begin`, `drag-data-get`, `drag-failed`, `drag-end`).
- On `drag-failed` with `Gtk.DragResult.NO_TARGET` (dropped outside tab strip), `detach_document(doc_id)` detaches the tab into a new window.
- Drag dest on `tab_strip` (`drag-data-received`): extracts source window ID and document ID, moves document via `detach_document(new_window=False)` and `accept_document`.
- Implemented `detach_document(doc_id, new_window=True)` and `accept_document(document)`.
- Wired `on_action_new` to call `self.app.new_window()`.

### 4. Tests (`tests/test_session.py`)
- Added `test_window_detach_document_creates_new_window`: verifies detaching a document creates a new window, keeps source open when other documents exist, and closes source when the last document is detached.
- Added `test_accept_document_across_existing_windows`: verifies moving a tab between two existing windows without ID conflicts.
- Added `NewWindowHelperTests`: verifies `detach` plan rules, `start_empty=False`, and `id_allocator` support in `WindowModel`.

## Verification Results
All 42 tests in `tests/test_session.py` passed:
```
Ran 42 tests in 0.003s
OK
```
