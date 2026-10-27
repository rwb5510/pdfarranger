# Master Task List: PDF Arranger Tabbed Documents

This document tracks all tasks, past, present, and future, for the **Tabbed Documents & Multi-Window Architecture** in PDF Arranger.

## Project Evolution: Tabbed Documents Feature

- [x] **Task 1: Open Target Pure Logic**
  - **Spec/Task:** [tabbed-documents-task-1.md](file:///m:/Richard/pdfarranger/docs/artifacts/tasks/tabbed-documents-task-1.md)
  - **Walkthrough:** [tabbed-documents-task-1.md](file:///m:/Richard/pdfarranger/docs/artifacts/walkthroughs/tabbed-documents-task-1.md)
  - **Status:** Completed
  - **Summary:** Established `choose_open_target` logic to determine whether an opened file should fill an empty document or spawn a new tab.

- [x] **Task 2: Document State Extracted to `Document` Class**
  - **Spec/Task:** [tabbed-documents-task-2.md](file:///m:/Richard/pdfarranger/docs/artifacts/tasks/tabbed-documents-task-2.md)
  - **Walkthrough:** [tabbed-documents-task-2.md](file:///m:/Richard/pdfarranger/docs/artifacts/walkthroughs/tabbed-documents-task-2.md)
  - **Status:** Completed
  - **Summary:** Extracted per-document state (page queue, undo manager, icon view, metadata, zoom) into dedicated `Document` instances.

- [x] **Task 3: Tab Label and Tooltip Pure Logic**
  - **Spec/Task:** [tabbed-documents-task-3.md](file:///m:/Richard/pdfarranger/docs/artifacts/tasks/tabbed-documents-task-3.md)
  - **Walkthrough:** [tabbed-documents-task-3.md](file:///m:/Richard/pdfarranger/docs/artifacts/walkthroughs/tabbed-documents-task-3.md)
  - **Status:** Completed
  - **Summary:** Implemented `tab_label` and `tab_tooltip` formatting rules respecting save filename, source filename, or "untitled".

- [x] **Task 4: Window Model Pure Logic**
  - **Spec/Task:** [tabbed-documents-task-4.md](file:///m:/Richard/pdfarranger/docs/artifacts/tasks/tabbed-documents-task-4.md)
  - **Walkthrough:** [tabbed-documents-task-4.md](file:///m:/Richard/pdfarranger/docs/artifacts/walkthroughs/tabbed-documents-task-4.md)
  - **Status:** Completed
  - **Summary:** Created headless `WindowModel` managing tab order, active pane, split toggle, and tab cycling.

- [x] **Task 5: Launch Plan Pure Logic**
  - **Spec/Task:** [tabbed-documents-task-5.md](file:///m:/Richard/pdfarranger/docs/artifacts/tasks/tabbed-documents-task-5.md)
  - **Walkthrough:** [tabbed-documents-task-5.md](file:///m:/Richard/pdfarranger/docs/artifacts/walkthroughs/tabbed-documents-task-5.md)
  - **Status:** Completed
  - **Summary:** Formalized single-instance command line planning for local startup vs remote launches.

- [x] **Task 6: Tab Strip & Opening into a Tab**
  - **Spec/Task:** [tabbed-documents-task-6.md](file:///m:/Richard/pdfarranger/docs/artifacts/tasks/tabbed-documents-task-6.md)
  - **Walkthrough:** [tabbed-documents-task-6.md](file:///m:/Richard/pdfarranger/docs/artifacts/walkthroughs/tabbed-documents-task-6.md)
  - **Status:** Completed
  - **Summary:** Built `ArrangerWindow` with scrollable tab strip, `Ctrl+T` shortcut, and tab switching.

- [x] **Task 7: Detaching and Moving Tabs Between Windows**
  - **Spec/Task:** [tabbed-documents-task-7.md](file:///m:/Richard/pdfarranger/docs/artifacts/tasks/tabbed-documents-task-7.md)
  - **Walkthrough:** [tabbed-documents-task-7.md](file:///m:/Richard/pdfarranger/docs/artifacts/walkthroughs/tabbed-documents-task-7.md)
  - **Status:** Completed
  - **Summary:** Implemented drag-to-detach tab into a new window and dragging tabs across windows in a single process.

- [x] **Task 8: Command-Line Single-Instance Hand-off (GTK Application ID)**
  - **Spec/Task:** [tabbed-documents-task-8.md](file:///m:/Richard/pdfarranger/docs/artifacts/tasks/tabbed-documents-task-8.md)
  - **Walkthrough:** [tabbed-documents-task-8.md](file:///m:/Richard/pdfarranger/docs/artifacts/walkthroughs/tabbed-documents-task-8.md)
  - **Status:** Completed
  - **Summary:** Removed `NON_UNIQUE` flag on Linux/macOS and handled command line hand-off through `command_line` signal.

- [x] **Task 9: Windows Single-Instance Fallback (Win32 Named Pipe IPC)**
  - **Spec/Task:** [tabbed-documents-task-9.md](file:///m:/Richard/pdfarranger/docs/artifacts/tasks/tabbed-documents-task-9.md)
  - **Walkthrough:** [tabbed-documents-task-9.md](file:///m:/Richard/pdfarranger/docs/artifacts/walkthroughs/tabbed-documents-task-9.md)
  - **Status:** Completed
  - **Summary:** Built `Win32IPC` server and client using Windows named pipes to hand off secondary launches to the primary instance.

- [x] **Task 10: Two-Pane Side-by-Side View**
  - **Spec/Task:** [tabbed-documents-task-10.md](file:///m:/Richard/pdfarranger/docs/artifacts/tasks/tabbed-documents-task-10.md)
  - **Walkthrough:** [tabbed-documents-task-10.md](file:///m:/Richard/pdfarranger/docs/artifacts/walkthroughs/tabbed-documents-task-10.md)
  - **Status:** Completed
  - **Summary:** Implemented View → Side by Side horizontal split, `F6` focus switcher, and blue outline styling on active pane.

- [x] **Task 11: Cross-Document Page Drag-and-Drop**
  - **Spec/Task:** [tabbed-documents-task-11.md](file:///m:/Richard/pdfarranger/docs/artifacts/tasks/tabbed-documents-task-11.md)
  - **Walkthrough:** [tabbed-documents-task-11.md](file:///m:/Richard/pdfarranger/docs/artifacts/walkthroughs/tabbed-documents-task-11.md)
  - **Status:** Completed
  - **Summary:** Enabled dragging pages between open documents (Move by default, `Ctrl` to Copy), dropping files onto tabs and panes.

- [x] **Task 12: Close Prompts and Save Gate**
  - **Spec/Task:** [tabbed-documents-task-12.md](file:///m:/Richard/pdfarranger/docs/artifacts/tasks/tabbed-documents-task-12.md)
  - **Walkthrough:** [tabbed-documents-task-12.md](file:///m:/Richard/pdfarranger/docs/artifacts/walkthroughs/tabbed-documents-task-12.md)
  - **Status:** Completed
  - **Summary:** Coordinated one save/export operation at a time, orderly close confirmation dialogs for unsaved documents.

- [x] **Task 13: Per-Document Search Isolation**
  - **Spec/Task:** [tabbed-documents-task-13.md](file:///m:/Richard/pdfarranger/docs/artifacts/tasks/tabbed-documents-task-13.md)
  - **Walkthrough:** [tabbed-documents-task-13.md](file:///m:/Richard/pdfarranger/docs/artifacts/walkthroughs/tabbed-documents-task-13.md)
  - **Status:** Completed
  - **Summary:** Isolated find bar query state (`Ctrl+F`) per document, restoring queries when switching tabs/panes.

- [x] **Task 14: Dogtail Test Suite & Verification**
  - **Spec/Task:** [tabbed-documents-task-14.md](file:///m:/Richard/pdfarranger/docs/artifacts/tasks/tabbed-documents-task-14.md)
  - **Walkthrough:** [tabbed-documents-task-14.md](file:///m:/Richard/pdfarranger/docs/artifacts/walkthroughs/tabbed-documents-task-14.md)
  - **Status:** Completed
  - **Summary:** Automated GUI tests (`TestBatch09`, `TestBatch17`) and verified 90 headless session tests.

---

## Current / In-Progress Tasks

- [x] **Task 15: Documentation & Visual Asset Synchronization**
  - **Status:** Completed
  - **Summary:** Updated README, ROADMAP, testing guides, metainfo, and generated authentic screenshots (`data/screenshot-tabs.png`, `data/screenshot-side-by-side.png`).

---

## Future Roadmap / Backlog

- [ ] **Tab Session Persistence / Restore:** Option to reopen tabs and windows from previous session on startup.
- [ ] **Custom Tab Coloring / Tagging:** Visual color coding for different tabs.
- [ ] **Vertical Split & Multi-Pane Layouts:** Support for vertical split in addition to horizontal two-pane view.
