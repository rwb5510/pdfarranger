# Task 14: Dogtail Coverage and Manual Windows Check

Implementation tracking for Task 14 of the tabbed documents feature plan (`docs/superpowers/plans/2026-10-22-tabbed-documents.md`).

## Status: Completed

## Tasks
- [x] Step 1: Update TestBatch09 and add TestBatch17:
  - [x] Add `_tab_labels` helper on `PdfArrangerTest` in `tests/test.py`
  - [x] Update `TestBatch09.test_03_open_again`, `test_04_quit`, and `test_05_quit` in `tests/test.py`
  - [x] Add `TestBatch17` covering startup merges, new tab import isolation, closing clean tab, and side by side in `tests/test.py`
  - [x] Update `TESTING.md` documenting `TestBatch09` and `TestBatch17`
- [x] Step 2: Run headless unit tests (`python -m unittest tests.test_session -v`) -> 90 tests passed
- [x] Step 3: Run or note GUI tests status (`tests.test.TestBatch09` and `tests.test.TestBatch17` - noted Dogtail/Linux requirement; skipped on Windows host)
- [x] Step 4: Record manual Windows checklist details
- [x] Step 5: Create walkthrough artifact (`docs/artifacts/walkthroughs/tabbed-documents-task-14.md`), update plan checkboxes, and commit
