# PDF Arranger Roadmap

This document outlines the project evolution, release history, and planned features for PDF Arranger.

**Current Version:** `1.14.0` (Development: `1.15.0-dev` on `feature/tabbed-documents`)

---

## Project Evolution

### v1.15.0 (In Development - Tabbed Documents)
- **Tabbed Document Architecture:**
  - Single-process multi-document workflow replacing the legacy process-per-window model.
  - Integrated tab strip under the header bar displaying document title, dirty status indicator (`*`), and individual close buttons.
  - Quick tab management shortcuts: `Ctrl+T` (New Tab), `Ctrl+W` (Close Tab), `Ctrl+Tab` and `Ctrl+Shift+Tab` (Cycle Tabs).
- **Two-Pane Side-by-Side View:**
  - View → Side by Side toggle splits the window horizontally into two independent document panes.
  - Distinctive active-pane highlight border (`#1c71d8`) indicating which pane receives zoom, search, undo, and editing commands.
  - Keyboard navigation between panes via `F6` or mouse click.
- **Cross-Document Drag-and-Drop:**
  - Drag pages between open tabs or between split panes. Default move behavior on Linux/macOS; Move by default with `Ctrl`+drag to copy on Windows.
  - Drag external PDF/image files directly onto individual tabs or specific panes to append pages.
- **Multi-Window & Tab Detachment:**
  - Seamless detachment: drag any tab out of the tab strip to spawn a new window within the same application process.
  - Drag tabs between windows to organize documents dynamically.
- **Single-Instance Application Hand-off:**
  - Linux/macOS: Primary instance receives external file launches via GTK Application ID and GApplication command line actions.
  - Windows: Robust local named-pipe IPC fallback (`win32ipc.py`) ensuring secondary command-line launches hand files to the running window without launching new processes.
- **Per-Document State Isolation & Safety:**
  - Independent undo/redo history, page queues, and find bar (`Ctrl+F`) query tracking per document.
  - Save Gate: Serialized save/export/print pipeline ensuring document safety and avoiding file corruption.
  - Coordinated close prompts with prompt-first ordering before performing batch saves and window closing.

### v1.14.0 (2026-05-23)
- Metadata preservation improvements with pikepdf backend.
- Enhanced outline bookmark tree importing and exporting.
- Localization updates across 30+ supported languages.
- Stability fixes for encrypted PDF handling and raster image text extraction.

### v1.13.0 (2026-02-01)
- Dark mode theme detection refinements on Windows and GNOME.
- Page margin and padding calculations overhaul.
- Upgraded libhandy header bar styling.

---

## Planned Features (Backlog)

- [ ] **Tab Session Persistence:**
  - Option to remember and reopen open tabs and window layouts across application restarts.
- [ ] **Vertical Split & Multi-Pane Layouts:**
  - Support for vertical split in addition to horizontal side-by-side view, with configurable pane dividers.
- [ ] **Tab Color Tagging & Grouping:**
  - Visual color tags or badges on tabs for organizing related PDF files.
- [ ] **Tab Pinning:**
  - Ability to pin essential reference PDFs to prevent accidental closure.
