# Walkthrough: Task 13 - Find Bar Follows the Focused Document

## Overview
Task 13 ensures that the single search bar widget follows the focused document and retains search queries independently per document:
- Added `SearchBarWidget.bind_document(document)` in `pdfarranger/search.py` to bind search bar components (`iconview`, `pdfqueue`, `model`, `show_find_results`, `clear_find_results`) and update the search entry text to the document's `find_text`.
- Supported headless / non-GTK execution gracefully in `pdfarranger/search.py` so search bar logic and tests run across all platforms.
- Updated `ArrangerWindow.show_model` in `pdfarranger/window.py` to persist `searchbar.entry.get_text()` into the previously focused document's `find_text` before binding the newly focused document.
- Maintained clean lifecycle tracking with `self._bound_doc_id` in `ArrangerWindow`, clearing it on document closure, window closure, or detachment.
- Updated `ArrangerWindow._search_clear` signature to accept `unselect_all=False` matching `Document.clear_find_results`.

---

## Key Changes

### 1. Search Bar Widget & Document Binding (`pdfarranger/search.py`)
- Handled optional `gi` and `Gtk` imports with headless fallback to `object`.
- Implemented `SearchBarWidget.bind_document(document)`:
  - If `document is None`, clears `iconview`, `pdfqueue`, `model`, `show_find_results`, `clear_find_results`, search state, and resets `entry` text to `""`.
  - When a `document` is provided, binds:
    - `self.iconview = document.iconview`
    - `self.pdfqueue = document.pdfqueue`
    - `self.model = document.model` (or `iconview.get_model()`)
    - `self.show_find_results = document.show_find_results`
    - `self.clear_find_results = document.clear_find_results`
    - Resets page search tracking (`self.page = None`, `self.rectangles = []`, `self.nrect = 0`).
    - Sets `self.text_old` and `self.entry.set_text(find_text)` with `document.find_text`.
- Added defensive guards in `enable_actions`, `find_all`, `find_sequent`, `abort`, and `close`.

### 2. Window Search Bar Rebinding & Query Persistence (`pdfarranger/window.py`)
- Initialized `self._bound_doc_id = None` in `ArrangerWindow.__init__`.
- Updated `ArrangerWindow.show_model()`:
  - Detects if focused document changed from `self._bound_doc_id`.
  - If changing documents, stores `self.searchbar_widget.entry.get_text()` into the previously bound document's `find_text`.
  - Calls `self.searchbar_widget.bind_document(focused)` and updates `self._bound_doc_id = focused.id`.
  - If no focused document exists, calls `bind_document(None)` and resets `self._bound_doc_id = None`.
- In `close_document`, `close_window`, and `detach_document`:
  - Resets `self._bound_doc_id = None` if the closed or detached document was the bound document.
- In `_search_clear`:
  - Updated method signature to `_search_clear(self, unselect_all=False)` forwarding the argument to `doc.clear_find_results(unselect_all)`.

### 3. Unit Tests (`tests/test_session.py`)
- Added `FindTextMemoryTests` covering:
  - `test_each_document_keeps_its_query`: verifies independent `find_text` attributes across documents.
  - `test_searchbar_bind_document_wires_attributes_and_entry`: verifies `bind_document` binds iconview, pdfqueue, callbacks, and entry text.
  - `test_searchbar_bind_document_none`: verifies `bind_document(None)` safely clears attributes.
  - `test_show_model_persists_previous_query_and_switches`: verifies tab switching stores the edited query in the outgoing document and loads the query of the incoming document.

---

## Verification Results
All 90 unit tests in `tests/test_session.py` passed:
```
Ran 90 tests in 2.113s
OK
```
