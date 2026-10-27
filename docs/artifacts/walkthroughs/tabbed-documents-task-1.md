# Walkthrough: Task 1 - Open target, tab text, and launch plan

## Summary
Completed Task 1 of the tabbed documents feature plan. Added the core pure rules in `pdfarranger/session.py` and corresponding unit tests in `tests/test_session.py`.

## Changes Made
1. **`pdfarranger/session.py`**:
   - `OpenTarget` enum with `FILL` and `NEW_TAB` members.
   - `document_occupied(pdfqueue_len, metadata_len)`: returns true if queue or metadata has items; raises `ValueError` if either length is negative.
   - `choose_open_target(occupied)`: returns `OpenTarget.NEW_TAB` if occupied, else `OpenTarget.FILL`.
   - `tab_label(save_basename, first_source_basename)`: selects save name if available, fallback to first source name, otherwise `"untitled"`.
   - `tab_tooltip(save_path, first_source_path)`: selects save full path if available, fallback to first source path, otherwise `""`.
   - `LaunchPlan` dataclass with `action` and `files`.
   - `plan_launch(remote, files, focused_occupied)`: decides whether to `"raise"`, `"fill"`, or `"new_tab"` on startup or remote invocations.

2. **`tests/test_session.py`**:
   - `OpenTargetTests`: tests for empty document occupation, queue/metadata checks, negative length validation, and open target selection.
   - `TabTextTests`: tests label preference hierarchy and tooltip full-path fallback.
   - `LaunchPlanTests`: tests startup with/without files and subsequent/remote launches with empty or occupied focused document.

## Verification
- Ran `python -m unittest tests.test_session -v`
- All 12 unit tests passed cleanly (0 errors, 0 failures).
