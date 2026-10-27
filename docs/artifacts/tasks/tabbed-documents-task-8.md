# Task 8: Single-Instance Command Line

Implementation tracking for Task 8 of the tabbed documents feature plan (`docs/superpowers/plans/2026-10-22-tabbed-documents.md`).

## Status: Completed

## Tasks
- [x] Step 1: Write test in `tests/test_session.py` (`CommandLineRoutingTests` and `PdfArrangerCommandLineTests` testing `open_launched_files` and `do_command_line`)
- [x] Step 2: Run test suite to verify test passes/fails as expected (`python -m unittest tests.test_session.CommandLineRoutingTests -v`)
- [x] Step 3: Route launches through the running process:
  - [x] Update `PdfArranger.__init__` in `pdfarranger/pdfarranger.py` to use `Gio.ApplicationFlags.HANDLES_COMMAND_LINE` only (remove `NON_UNIQUE`)
  - [x] Import `plan_launch` from `.session`
  - [x] Implement `do_command_line(self, command_line)` following plan specification
  - [x] Implement `open_launched_files(self, remote: bool, files: list)`
  - [x] Verify `active_window` and `do_activate` alignment
- [x] Step 4: Run test suite to verify everything passes (`python -m unittest tests.test_session -v`)
- [x] Step 5: Create walkthrough artifact (`docs/artifacts/walkthroughs/tabbed-documents-task-8.md`), update plan checkboxes, and commit changes
