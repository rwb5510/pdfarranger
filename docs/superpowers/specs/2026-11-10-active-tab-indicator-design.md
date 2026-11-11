# Active tab indicator

## Problem

Each open PDF is a tab in the strip under the header bar. The strip is a horizontal `Gtk.Box` of one box per document (`pdfarranger/window.py`, `_create_tab_widget`). Those boxes are not a `Gtk.Notebook`, so GTK never paints a selected tab.

The focused document is already `WindowModel.focused_id()`. The window title names that document. While side by side is on, `scrolledwindow.focused-pane` draws a 2px solid `#1c71d8` outline on the focused pane. With two or more tabs and one pane, the tabs look the same. The user cannot see which tab is the active document.

## Decision

Mark the tab whose document id equals `WindowModel.focused_id()` with the GTK theme’s selected colors and a bottom bar. Leave every other tab unmarked. Keep the existing pane outline.

This is not the roadmap item for user-assigned color tags or badges. There is no picker, no stored tag, and no new preference.

## Behavior

- The active tab is the focused document. There is one active tab, or none when `focused_id()` is `None`.
- A window with one document marks that tab active.
- Clicking a tab, Ctrl+Tab, Ctrl+Shift+Tab, opening a file into a new tab, New Tab, closing a tab, F6, and turning side by side on or off all change focus through `ArrangerWindow.show_model`. The active mark follows `focused_id()` after each of those.
- While side by side is on, the focused pane’s tab is active. The other visible document’s tab is inactive. The blue pane outline stays.

## Look

The mark has two parts so it is not color alone:

- The active tab uses the theme’s selected background and selected text color.
- Every tab reserves a 3px bottom border. The active tab’s border uses the selected background color. An inactive tab’s border is transparent, so switching tabs does not move the label.

Use these GTK symbolic colors: `@theme_selected_bg_color` and `@theme_selected_fg_color`. Adwaita, including its dark and high-contrast variants, defines them. Do not paint the tab with `#1c71d8`. That blue stays on the pane outline only.

Do not change the label weight. A bold label would change the tab width when focus moves.

The tab’s `Gtk.EventBox` must not paint its own window. GTK 3 gives an event box a visible window by default, and that window covers the box behind it. `set_visible_window(False)` leaves an input-only window, so clicks and tab drags still hit the event box, and the tab background stays visible. The close button keeps its existing “×” label. Its own background is cleared so it does not cover the selected color. The title label and the “×” label both use the selected text color when the tab is active.

Inactive tabs have no hover style in this change.

The class name is `active-tab`. The pure rule is:

```python
ACTIVE_TAB_CLASS = "active-tab"

def tab_css_classes(doc_id: int, focused_id: int | None) -> frozenset[str]:
    if focused_id is not None and doc_id == focused_id:
        return frozenset((ACTIVE_TAB_CLASS,))
    return frozenset()
```

The stylesheet fragment is `ACTIVE_TAB_CSS` in `pdfarranger/session.py`:

```css
box#tab-strip-box > box {
    background-color: transparent;
    border-radius: 4px 4px 0 0;
    border-width: 0 0 3px 0;
    border-style: solid;
    border-color: transparent;
    padding: 2px 6px;
}
box#tab-strip-box > box.active-tab {
    background-color: @theme_selected_bg_color;
    border-color: @theme_selected_bg_color;
}
box#tab-strip-box > box.active-tab label {
    color: @theme_selected_fg_color;
}
box#tab-strip-box > box button {
    background-color: transparent;
    background-image: none;
    border-style: none;
    box-shadow: none;
}
```

`PdfArranger.do_activate` loads one `Gtk.CssProvider` string from `application_css() -> str`. That string is the existing iconview, overshoot, and `scrolledwindow.focused-pane` rules, followed by `ACTIVE_TAB_CSS`. The pane rule stays `border-color: #1c71d8`.

`ArrangerWindow.sync_tab_active_classes()` adds `active-tab` to the focused tab’s style context and removes it from every other tab in `self.tab_widgets`. `show_model` calls it before the `if Gtk is None: return` line, so a headless test can inject fake tab boxes and see the class change. No click handler applies the class itself.

## Testing

`tests/test_session.py` covers `tab_css_classes` and `ACTIVE_TAB_CSS` without importing GTK. It also covers `sync_tab_active_classes` with fake style contexts, and it asserts that `show_model` calls that method. `application_css()` is asserted to contain the existing pane rule and `ACTIVE_TAB_CSS`. When GTK imports, the same file asserts that the tab event box returns false from `get_visible_window()`.

The automated gate on Windows is:

```sh
python -X tracemalloc -u -m unittest -v -f tests.test_session
```

A display check, when a display is available: open two documents, confirm the focused tab is filled with the theme selection and the other tab is not, click the other tab, press Ctrl+Tab, turn side by side on, press F6, and confirm the active tab matches the outlined pane.

The dogtail suite finds tab titles by the widget name `pdfarranger-tab-label`. That name and the label text stay as they are. This change does not add a dogtail test.

## Constraints

- The installable version is the `version` field in `setup.py`. Change it only for a release.
- Do not edit anything under `build/`.
- Put a new open, close, drop, tab, or pane rule in `session.py` and cover it in `tests/test_session.py` without importing GTK. Call that function from `window.py` or `document.py`. Guard new UI code with the existing `Gtk is None` pattern so those modules still import in tests.
- User-visible strings go through `_()` from gettext, including mnemonics (`_Save`). This change adds no `_()` string and does not edit `po/`.
- Do not add a preference that restores one process per document. Do not restore tabs across restarts unless that work is requested. Do not add a third pane.
- Side by side is two panes at most. The `scrolledwindow.focused-pane` outline stays `border-width: 2px`, `border-style: solid`, `border-color: #1c71d8`, and it is still applied only while the split is on.
- The active tab class is `active-tab`. The tab stylesheet uses `@theme_selected_bg_color` and `@theme_selected_fg_color`. It does not contain `#1c71d8` or `font-weight`.
- On Windows, check session tests here. Check the dogtail suite on Linux or in CI. The new tests do not require a display.

## Out of scope

User-assigned tab colors, a new preference, tab restore, a third pane, a `Gtk.Notebook` rewrite, a hover style, a change to the label text, and a new screenshot in `data/screenshot-tabs.png`.
