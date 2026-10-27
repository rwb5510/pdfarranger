# Task 9: Windows Single-Instance Fallback

Implementation tracking for Task 9 of the tabbed documents feature plan (`docs/superpowers/plans/2026-10-22-tabbed-documents.md`).

## Status: Completed

## Tasks
- [x] Step 1: Write the failing tests in `tests/test_session.py` (`Win32HandoffTests` and `GtkUniqueCheckTests`)
- [x] Step 2: Run the test to verify it fails (`python -m unittest tests.test_session.Win32HandoffTests -v`)
- [x] Step 3: Implement the socket handoff:
  - [x] Create `pdfarranger/win32ipc.py` with `encode_files`, `decode_files`, `gtk_unique_is_enough`, and `Win32Handoff`
  - [x] Implement lock file handling (%LOCALAPPDATA%/pdfarranger/instance.port on Windows or ~/.local/share/pdfarranger/instance.port elsewhere, allowing custom directory for tests)
  - [x] Integrate fallback in `pdfarranger/pdfarranger.py` (`do_command_line` / `close_application`)
- [x] Step 4: Run unit test suites to verify everything passes:
  - [x] `python -m unittest tests.test_session.Win32HandoffTests tests.test_session.CommandLineRoutingTests -v`
  - [x] `python -m unittest tests.test_session -v`
- [x] Step 5: Create walkthrough artifact (`docs/artifacts/walkthroughs/tabbed-documents-task-9.md`), update plan checkboxes in `docs/superpowers/plans/2026-10-22-tabbed-documents.md`, and commit changes
