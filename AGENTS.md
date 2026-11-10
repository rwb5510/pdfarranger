# PDF Arranger

GTK 3 desktop app for merging, splitting, rotating, cropping, and rearranging PDF pages. Python package `pdfarranger`, pikepdf for PDF I/O. GPL-3. Upstream issue tracker and wiki: https://github.com/pdfarranger/pdfarranger

The installable version is the `version` field in `setup.py`. Change it only for a release.

## Commands

From the repository root, after the system packages in [README.md](README.md) (GTK 3, PyGObject, poppler-glib, gettext, libhandy) are installed:

```sh
python -m pip install -e ".[image]"
python setup.py build
python -m pdfarranger
```

`setup.py build` compiles `po/*.po` into `build/mo`. A source checkout reads UI from `data/` and translations from `build/mo`. Do not edit anything under `build/`.

Headless session tests, no display:

```sh
python -X tracemalloc -u -m unittest -v -f tests.test_session
```

PDF and page-model tests (need pikepdf, and PyGObject because `core.py` and `exporter.py` import GTK):

```sh
python -X tracemalloc -u -m unittest -v -f tests.test_core
python -X tracemalloc -u -m unittest -v -f tests.test_exporter
python -m pytest -v tests/test_exporter_outlines.py
```

`tests.test` is the dogtail GUI suite. It needs a Linux display (Xvfb in CI) and the app already built. `tests.test_pr_regressions` imports GTK. On Windows, check session and exporter tests here; check the dogtail suite on Linux or in CI. See [TESTING.md](TESTING.md), [Win32.md](Win32.md), and [macOS.md](macOS.md).

CI (`.github/workflows/install.yml`) installs `.[image]`, validates the AppStream and desktop files, then runs the dogtail, exporter, outline, and core suites.

## Layout

| Path | Role |
| --- | --- |
| `pdfarranger/pdfarranger.py` | `Gtk.Application`: process lifetime, windows, document ids, CLI, temp directory, single-instance handoff |
| `pdfarranger/window.py` | `ArrangerWindow`: header bar, menus, tab strip, side-by-side panes, close prompts |
| `pdfarranger/document.py` | One arrangement: icon view, page list, undo, zoom, search, save and export calls |
| `pdfarranger/session.py` | GTK-free decisions: open target, window model, close order, drop target, save gate |
| `pdfarranger/core.py` | `Page` / `LayerPage`, opening PDFs, thumbnail renderer thread |
| `pdfarranger/exporter.py` | pikepdf write path. Export runs in a spawned child process |
| `pdfarranger/exporter_outlines.py` | Bookmark and outline remapping |
| `pdfarranger/undo.py` | Per-document memento stack of the page list |
| `pdfarranger/win32ipc.py` | Second-launch handoff on Windows |
| `pdfarranger/config.py` | Preferences |
| `data/pdfarranger.ui`, `data/menu.ui` | GtkBuilder for the window and menus |
| `tests/exporter/` | QDF PDF fixtures. Readable as text; update only when an output change is intentional |

`docs/` holds local design notes and task writeups. Behavior in code and tests wins over those notes.

## Invariants

One process owns every window. Document ids come from `PdfArranger.allocate_doc_id`. A document is occupied when `pdfqueue` or `metadata` is non-empty (`session.document_occupied`).

Opening files fills the focused document when it is empty, and otherwise adds one tab. Several files in one Open or one drop merge into that single document. Import always adds pages to the focused document. A second launch with no files raises the last focused window and adds no tab. Linux and macOS use the GTK application id `com.github.jeromerobert.pdfarranger`. Windows always uses `Win32Handoff`. `PDFARRANGER_WIN32_IPC=1` forces that path.

Side by side is two panes at most. Save, zoom, find, undo, and page edits apply to the focused pane. Each document keeps its own undo stack, zoom, and search query. `undo.Manager.commit(label)` runs before the mutation. The stack stores duplicated `Page` objects, not PDF bytes.

`SaveGate` allows one save, export, or print in the process. Closing prompts the focused unsaved document first, then the others in tab order. Cancel aborts the whole close. Approved saves run serially through `save_documents_then` and must not block the GTK main loop. A failed or cancelled save leaves the documents open. Closing the last document in a window leaves one empty document. Closing the last window quits.

Page drags move on Windows unless Ctrl is held (`page_drag_action_is_move`). On POSIX they move. A move records undo on both documents. Paste goes to the focused document.

Do not add a preference that restores one process per document. Do not restore tabs across restarts unless that work is requested. Do not add a third pane.

## When you change behavior

Put a new open, close, drop, tab, or pane rule in `session.py` and cover it in `tests/test_session.py` without importing GTK. Call that function from `window.py` or `document.py`. Guard new UI code with the existing `Gtk is None` pattern so those modules still import in tests.

User-visible strings go through `_()` from gettext, including mnemonics (`_Save`). Add any module that gains `_()` strings to `po/POTFILES.in`. Leave `po/pdfarranger.pot` uncommitted unless the task is a translation update. Run `po/updatepo.sh LANG` only for that language, and do not commit unrelated `.po` churn.

New Python modules keep the GPL-3 header used by the neighboring file. Match the file you are editing: `session.py` uses type hints; older modules often do not. Export child-process arguments must stay picklable. The process temp directory is `app.tmp_dir` and is shared by every document.

Image import needs the `image` extra (`img2pdf`). Keep that path optional.
