# Tabbed documents in one window

## Problem

PDF Arranger keeps one arrangement per process. The application is started with `Gio.ApplicationFlags.NON_UNIQUE`, and File → Open on a document that already has pages calls `on_action_new`, which starts another process. On Windows, opening a second PDF from Explorer does the same. Reviewing, comparing, and combining several PDFs becomes a pile of windows.

This design replaces that pile with tabs in one process, an optional two-pane view, and the ability to move a tab out into its own window. Import, and one Open of several files, still merge into a single arrangement. The feature is meant to be offered upstream as one behavior change, with no setting that keeps the old process-per-window mode.

## Terms

A document is occupied when it has entries in its PDF queue or it has metadata. That is the same test File → Open uses today before it starts another process. A document with neither is empty.

The focused document is the one in the pane that has focus. Save, Import, zoom, find, undo, and the page-editing actions apply to it.

## Architecture

Three objects share the work.

**Document** is one arrangement. It holds the page list, icon view, undo history, source PDFs, metadata, save path, unsaved flag, zoom, password, search query, in-progress export, and its own thumbnail renderer. The view widget stays with the document, so a window can place that same widget in the main area or in either pane. A document that is not on screen stops rendering thumbnails until it is shown again.

**Window** holds the header bar, the menus, the tab strip, and the content area. The header buttons stay where they are. The tab strip is a scrollable row directly under the header. Each tab shows the save filename, or the first source filename, or “untitled”, plus an asterisk when the document is unsaved, and a close button. The tooltip is the full path. When the tabs do not fit, the strip scrolls. The window title keeps today’s longer form for the focused document, including the folder and the list of source files. While side by side is on, a blue outline marks the focused pane. With one pane showing, the active tab and the window title identify the document.

**Application** is a single process. It owns settings, the temporary directory, the clipboard, and the windows. `NON_UNIQUE` is removed. A second launch is delivered to the running process through GTK’s application id. On a command line that comes from another working directory, file paths are created from that command line’s own arguments so the directory is correct. If the MSYS2 build cannot hand a second launch to the first, a Windows-only fallback calls the same “open these files” function. Linux and macOS stay on the GTK path.

A second launch with no files raises the window that was used last and adds no tab. A second launch with files uses the Open rule below on the focused document of that window.

File → New Window, and dragging a tab out of the strip, opens another window in this same process. The new window starts with the moved document, or with one empty document when the menu item is used. Dragging a tab onto another window’s strip moves the document there, undo history included. If the move leaves a window with no documents, that window closes. If it was the only window, the new window remains and the application stays running.

## Opening files

File → Open on an empty focused document fills that document. File → Open on an occupied document adds one tab, shows it in the focused pane, and fills that tab. Several files in that one Open are merged into the document it selected, in the same order as today.

The first window starts with one empty document. The files on the command line that starts the application fill that document, merged into it. A later launch is not a startup: its files use the Open rule on the focused document of the window that was used last.

The Import menu adds pages to the focused document. Dropping files onto a pane adds them to that pane’s document. Dropping files onto a tab adds them to that tab’s document. Dropping files on the rest of the window adds them to the focused document. Several files in one drop merge into that one document.

File → New Tab (Ctrl+T) adds an empty document and shows it in the focused pane.

A password prompt or an open error is modal to the window and belongs to the document being loaded. A new tab is created only once the first page has been added. Cancelling the password, or failing before any page is added, leaves the window as it was. If a later file in the same Open fails, the pages already added stay in that document.

## Tabs and the second pane

Clicking a tab that is already visible focuses its pane. Clicking a hidden tab shows that document in the focused pane. The document that was replaced stays open as a tab.

Ctrl+Tab and Ctrl+Shift+Tab follow that same rule.

The window shows one document until side by side is turned on. View → Side by Side is available once the window has two documents, and it toggles. Turning it on puts the next document in the strip on the right and leaves the focused document on the left. The strip wraps from the last tab to the first. Dragging a tab to the right edge does the same with the dragged document on the right. Dragging a tab to the right edge while the split is already on replaces the right-hand document and leaves the replaced document open as a tab. Turning Side by Side off hides the right pane and leaves both documents open. At most two panes.

F6 moves focus to the other pane while the split is on. Each pane keeps its own zoom. The find bar under the tab strip shows the focused document’s search and restores that document’s query when focus moves.

## Page drags

Page drags between panes and between windows of this application use the move-or-copy choice already used inside one document. On Windows the drag moves the pages, and holding Ctrl copies them. On Linux and macOS the drag moves the pages. A move removes the pages from the source document and adds them to the destination. A copy leaves the source unchanged. The destination records undo and is marked unsaved. A move also records undo on the source and marks the source unsaved.

Paste from the clipboard still pastes into the focused document.

## Saving and closing

One save, export, or print runs at a time in the process. The document being saved ignores edits until it finishes. Save, export, and print are disabled on the other documents meanwhile. Other documents can still be viewed. Closing the document that is saving, closing its window, and Quit wait until that save finishes, then continue with the prompts below.

Close (Ctrl+W), the tab’s close button, and a middle-click close the focused document. An unsaved document gets the current save prompt, using that document’s name. Don’t Save closes it. Cancel leaves it open. Save writes it, and the close finishes only after the save succeeds. Closing the last document in a window leaves the window open with one empty document.

Closing a window asks about each unsaved document in it before closing any of them, focused document first. Cancel aborts the close and leaves every document in that window open. When every prompt is Save or Don’t Save, the requested saves run first. The documents close only after those saves succeed. If a save fails, the window stays open. Clean documents close together with the ones the user chose not to save. Closing the last window quits the application.

Quit (Ctrl+Q) uses that same sequence for every window, starting with the focused window. Cancel aborts the quit and leaves every document open.

## Testing

The existing unittest and dogtail suite stays in place. Page editing, export contents, and the password dialog keep their current tests. `TestBatch09` currently opens a second file and expects a second process. It is updated to expect one process, one window, and a second tab.

New dogtail coverage on Linux:

- Open on an empty window fills the single tab. Open again adds a tab.
- One Open of two files fills one tab, and the page count is the sum of both files.
- Import adds pages only to the focused tab.
- Ctrl+W on a second clean tab leaves the first tab open. Closing an unsaved tab shows the save prompt with that tab’s name.
- Side by side shows both documents. Save and zoom apply to the pane with the blue outline.
- Dragging a page from one pane into the other adds it to the destination. The suite already drags pages, so this follows that pattern.

The rule that chooses “fill the empty document” or “add one tab” also has a plain unittest.

Windows is checked by hand on the MSYS2 build: start the app, launch it again with another PDF, and confirm one window and two tabs. Then drag a tab out into its own window and drag it back. macOS uses the same GTK single-instance path and has no separate automated run.

New user-visible strings go through gettext, in the same way as the existing menu labels.

## Out of scope

- Restoring tabs after a restart.
- More than two panes.
- A preference that brings back one process per document.
- Changing Import, or changing the rule that several files from a single Open merge into one document.
