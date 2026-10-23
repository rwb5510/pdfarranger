# Walkthrough - Task 6: Tab Strip and Opening into a Tab

## Overview
Task 6 implements the `ArrangerWindow` class and migrates `PdfArranger` to manage multiple windows (`self.windows`), decoupling window-specific UI/event handling from the core application shell while supporting tabbed documents within each window.

## Key Changes Implemented

### 1. `pdfarranger/window.py`
- Implemented `ArrangerWindow` managing:
  - Tab strip (`Gtk.ScrolledWindow` with horizontal `Gtk.Box` holding document tab widgets).
  - Page area (`Gtk.Box`) swapping visible `Document.sw` scrolled window based on `WindowModel`.
  - Tab cycle shortcuts (Ctrl+Tab, Ctrl+Shift+Tab) and new tab shortcut (`<Primary>t`).
  - Document lifecycle: `new_tab()`, `close_document(doc_id)`, `focused_document()`, `refresh_document(document)`, and `show_model()`.
  - Multi-file open order normalization (`filenames_for_open`) reversing Windows multi-select order on `nt`.
  - Safe headless fallback initialization so non-GTK/Windows test runners can instantiate windows cleanly.

### 2. `pdfarranger/pdfarranger.py`
- Refactored `PdfArranger` application shell:
  - Replaced single-document state (`self.doc`, `self.model`, `self.iconview`) with `self.windows = []` and `self.last_focused_window = None`.
  - Added `active_window()` resolving the most recently focused window or falling back to `windows[0]`.
  - Updated `do_activate()` to instantiate `ArrangerWindow` and append to `self.windows`.
  - Delegated `add_files()` to `self.active_window().open_files(...)`.
  - Updated application close/quit handlers (`on_quit`, `close_application`) to iterate across documents in all managed windows.

### 3. UI and Config Updates
- **`data/menu.ui`**: Added `_New Tab` (`win.new-tab`) menu item directly after `_New Window`.
- **`pdfarranger/config.py`**: Added `('new-tab', '<Primary>t')` to `_DEFAULT_ACCELS`.

### 4. Test Suite Enhancements
- **`tests/test_session.py`**:
  - `OpenFilesOrderTests`: Tests `filenames_for_open` multi-select order reversal on Windows (`nt`).
  - `ArrangerWindowInterfaceTests`: Validates headless `ArrangerWindow` initialization, document tracking, `new_tab`, `close_document`, and `active_window` resolution.

## Verification Results

### Unit Test Execution
Ran the comprehensive session test suite:
```
python -m unittest tests.test_session -v
```

Output:
```
test_window_model_and_tabs (tests.test_session.ArrangerWindowInterfaceTests.test_window_model_and_tabs) ... ok
test_cancel_aborts_before_anything_closes (tests.test_session.ClosePromptTests.test_cancel_aborts_before_anything_closes) ... ok
test_prompt_order_asks_the_focused_document_first (tests.test_session.ClosePromptTests.test_prompt_order_asks_the_focused_document_first) ... ok
test_saves_run_before_discards_are_recorded (tests.test_session.ClosePromptTests.test_saves_run_before_discards_are_recorded) ... ok
test_single_close_answers (tests.test_session.ClosePromptTests.test_single_close_answers) ... ok
test_page_operations_live_on_document (tests.test_session.DocumentMethodTests.test_page_operations_live_on_document) ... ok
test_release_renderer_asks_the_thread_to_quit (tests.test_session.DocumentShellTests.test_release_renderer_asks_the_thread_to_quit) ... ok
test_two_documents_do_not_share_state (tests.test_session.DocumentShellTests.test_two_documents_do_not_share_state) ... ok
test_drop_site_selects_the_document (tests.test_session.DropTargetTests.test_drop_site_selects_the_document) ... ok
test_later_launch_adds_one_tab_when_the_document_is_occupied (tests.test_session.LaunchPlanTests.test_later_launch_adds_one_tab_when_the_document_is_occupied) ... ok
test_later_launch_fills_an_empty_focused_document (tests.test_session.LaunchPlanTests.test_later_launch_fills_an_empty_focused_document) ... ok
test_later_launch_without_files_raises_the_window (tests.test_session.LaunchPlanTests.test_later_launch_without_files_raises_the_window) ... ok
test_startup_with_files_fills_the_first_document (tests.test_session.LaunchPlanTests.test_startup_with_files_fills_the_first_document) ... ok
test_startup_without_files_fills_nothing (tests.test_session.LaunchPlanTests.test_startup_without_files_fills_nothing) ... ok
test_windows_reverses_multi_select_order (tests.test_session.OpenFilesOrderTests.test_windows_reverses_multi_select_order) ... ok
test_empty_document_is_filled (tests.test_session.OpenTargetTests.test_empty_document_is_filled) ... ok
test_empty_document_is_not_occupied (tests.test_session.OpenTargetTests.test_empty_document_is_not_occupied) ... ok
test_negative_lengths_are_rejected (tests.test_session.OpenTargetTests.test_negative_lengths_are_rejected) ... ok
test_occupied_document_opens_a_tab (tests.test_session.OpenTargetTests.test_occupied_document_opens_a_tab) ... ok
test_queue_or_metadata_occupies_a_document (tests.test_session.OpenTargetTests.test_queue_or_metadata_occupies_a_document) ... ok
test_only_one_save_runs (tests.test_session.SaveGateTests.test_only_one_save_runs) ... ok
test_label_prefers_save_name_then_source_then_untitled (tests.test_session.TabTextTests.test_label_prefers_save_name_then_source_then_untitled) ... ok
test_tooltip_uses_the_full_path (tests.test_session.TabTextTests.test_tooltip_uses_the_full_path) ... ok
test_click_hidden_tab_replaces_the_focused_pane (tests.test_session.WindowModelTests.test_click_hidden_tab_replaces_the_focused_pane) ... ok
test_click_visible_right_tab_focuses_that_pane (tests.test_session.WindowModelTests.test_click_visible_right_tab_focuses_that_pane) ... ok
test_close_last_document_leaves_one_empty_document (tests.test_session.WindowModelTests.test_close_last_document_leaves_one_empty_document) ... ok
test_cycle_follows_the_click_rule (tests.test_session.WindowModelTests.test_cycle_follows_the_click_rule) ... ok
test_detach_and_attach_moves_a_tab (tests.test_session.WindowModelTests.test_detach_and_attach_moves_a_tab) ... ok
test_detach_last_document_closes_the_window (tests.test_session.WindowModelTests.test_detach_last_document_closes_the_window) ... ok
test_drag_focused_tab_to_the_right_keeps_documents_distinct (tests.test_session.WindowModelTests.test_drag_focused_tab_to_the_right_keeps_documents_distinct) ... ok
test_drag_hidden_tab_to_the_right_edge (tests.test_session.WindowModelTests.test_drag_hidden_tab_to_the_right_edge) ... ok
test_new_model_has_one_empty_document (tests.test_session.WindowModelTests.test_new_model_has_one_empty_document) ... ok
test_open_on_empty_reuses_the_focused_document (tests.test_session.WindowModelTests.test_open_on_empty_reuses_the_focused_document) ... ok
test_open_on_occupied_inserts_one_tab_in_the_focused_pane (tests.test_session.WindowModelTests.test_open_on_occupied_inserts_one_tab_in_the_focused_pane) ... ok
test_side_by_side_does_nothing_with_one_document (tests.test_session.WindowModelTests.test_side_by_side_does_nothing_with_one_document) ... ok
test_side_by_side_puts_the_next_tab_on_the_right (tests.test_session.WindowModelTests.test_side_by_side_puts_the_next_tab_on_the_right) ... ok
test_side_by_side_wraps_from_the_last_tab (tests.test_session.WindowModelTests.test_side_by_side_wraps_from_the_last_tab) ... ok

----------------------------------------------------------------------
Ran 37 tests in 0.002s

OK
```
