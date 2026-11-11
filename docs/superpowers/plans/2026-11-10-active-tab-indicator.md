# Active Tab Indicator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Paint the tab of the focused PDF so the user can see which document is active.

**Architecture:** `tab_css_classes` in `session.py` decides that the only active tab is `WindowModel.focused_id()`. `ACTIVE_TAB_CSS` in the same file is the theme-colored tab rule. `application_css()` appends that rule to the stylesheet `PdfArranger.do_activate` already loads. `ArrangerWindow.sync_tab_active_classes()` adds or removes the `active-tab` class, and `show_model` calls it on every focus change.

**Tech Stack:** Python 3, GTK 3, PyGObject, unittest. No new dependency.

**Spec:** `docs/superpowers/specs/2026-11-10-active-tab-indicator-design.md`

## Global Constraints

- The installable version is the `version` field in `setup.py`. Change it only for a release.
- Do not edit anything under `build/`.
- Put a new open, close, drop, tab, or pane rule in `session.py` and cover it in `tests/test_session.py` without importing GTK. Call that function from `window.py` or `document.py`. Guard new UI code with the existing `Gtk is None` pattern so those modules still import in tests.
- User-visible strings go through `_()` from gettext, including mnemonics (`_Save`). This change adds no `_()` string and does not edit `po/`.
- Do not add a preference that restores one process per document. Do not restore tabs across restarts unless that work is requested. Do not add a third pane.
- Side by side is two panes at most. The `scrolledwindow.focused-pane` outline stays `border-width: 2px`, `border-style: solid`, `border-color: #1c71d8`, and it is still applied only while the split is on.
- The active tab class is `active-tab`. The tab stylesheet uses `@theme_selected_bg_color` and `@theme_selected_fg_color`. It does not contain `#1c71d8` or `font-weight`.
- On Windows, check session tests here. Check the dogtail suite on Linux or in CI. The new tests do not require a display.

---

## File structure

- Modify `pdfarranger/session.py`. Add `ACTIVE_TAB_CLASS`, `tab_css_classes`, and `ACTIVE_TAB_CSS` next to `tab_label` and `tab_tooltip`. This file stays GTK-free.
- Modify `tests/test_session.py`. Cover the rule, the stylesheet text, the class sync, and the `show_model` call.
- Modify `pdfarranger/pdfarranger.py`. Add `application_css()` and load it from the existing `Gtk.CssProvider` in `do_activate`.
- Modify `pdfarranger/window.py`. Make the tab event box input-only, and add or remove `active-tab` from `show_model`.

No new module. The tab strip stays a `Gtk.Box`. Do not convert it to a `Gtk.Notebook`.

`show_model` is already called after tab click, pane click, New Tab, close, Ctrl+Tab, F6, open, and drop. One call to `sync_tab_active_classes` inside `show_model` covers those paths. Do not also set the class from the click handlers.

## Task 1: Active-tab rule and stylesheet text

**Files:**
- Modify: `pdfarranger/session.py` (insert after `tab_tooltip`, which ends at line 51)
- Test: `tests/test_session.py` (import block at lines 4–22, and a new `ActiveTabTests` class after `TabTextTests`)

**Interfaces:**
- Consumes: `WindowModel.focused_id() -> int | None`, `WindowModel.new_tab() -> int`, `WindowModel.click_tab(doc_id: int) -> None`, `WindowModel.cycle_tab(backwards: bool) -> None`, `WindowModel.toggle_split() -> None`, `WindowModel.focus_other_pane() -> None`, `WindowModel.close_document(doc_id: int) -> str`. These already exist in `pdfarranger/session.py`.
- Produces: `ACTIVE_TAB_CLASS: str` with value `"active-tab"`. `tab_css_classes(doc_id: int, focused_id: int | None) -> frozenset[str]`. `ACTIVE_TAB_CSS: str`, the exact stylesheet fragment below. Task 2 imports these three names.

- [ ] **Step 1: Write the failing test**

In `tests/test_session.py`, add `ACTIVE_TAB_CLASS`, `ACTIVE_TAB_CSS`, and `tab_css_classes` to the existing `pdfarranger.session` import. Then add this class after `TabTextTests`:

```python
class ActiveTabTests(unittest.TestCase):
    def test_the_focused_document_is_the_only_active_tab(self):
        self.assertEqual(tab_css_classes(1, 1), frozenset({ACTIVE_TAB_CLASS}))
        self.assertEqual(tab_css_classes(2, 1), frozenset())

    def test_no_tab_is_active_when_nothing_is_focused(self):
        self.assertEqual(tab_css_classes(1, None), frozenset())

    def test_a_single_tab_is_active(self):
        model = WindowModel()
        only = model.focused_id()
        self.assertEqual(
            tab_css_classes(only, model.focused_id()),
            frozenset({ACTIVE_TAB_CLASS}),
        )

    def test_click_cycle_and_split_move_the_active_class(self):
        model = WindowModel()
        first = model.focused_id()
        second = model.new_tab()
        self.assertEqual(model.focused_id(), second)
        self.assertEqual(tab_css_classes(second, model.focused_id()), frozenset({ACTIVE_TAB_CLASS}))
        self.assertEqual(tab_css_classes(first, model.focused_id()), frozenset())

        model.click_tab(first)
        self.assertEqual(tab_css_classes(first, model.focused_id()), frozenset({ACTIVE_TAB_CLASS}))
        self.assertEqual(tab_css_classes(second, model.focused_id()), frozenset())

        model.cycle_tab(False)
        self.assertEqual(model.focused_id(), second)
        self.assertEqual(tab_css_classes(second, model.focused_id()), frozenset({ACTIVE_TAB_CLASS}))
        self.assertEqual(tab_css_classes(first, model.focused_id()), frozenset())

        model.click_tab(first)
        model.toggle_split()
        self.assertTrue(model.split)
        self.assertEqual(model.focused_id(), first)
        self.assertEqual(tab_css_classes(first, model.focused_id()), frozenset({ACTIVE_TAB_CLASS}))
        self.assertEqual(tab_css_classes(second, model.focused_id()), frozenset())

        model.focus_other_pane()
        self.assertEqual(model.focused_id(), second)
        self.assertEqual(tab_css_classes(second, model.focused_id()), frozenset({ACTIVE_TAB_CLASS}))
        self.assertEqual(tab_css_classes(first, model.focused_id()), frozenset())

    def test_closing_the_focused_tab_activates_the_remaining_tab(self):
        model = WindowModel()
        first = model.focused_id()
        second = model.new_tab()
        self.assertEqual(model.focused_id(), second)
        self.assertEqual(model.close_document(second), "removed")
        self.assertEqual(model.focused_id(), first)
        self.assertEqual(tab_css_classes(first, model.focused_id()), frozenset({ACTIVE_TAB_CLASS}))
        self.assertEqual(tab_css_classes(second, model.focused_id()), frozenset())

    def test_active_tab_css_uses_the_theme_selection_and_a_reserved_bar(self):
        self.assertEqual(ACTIVE_TAB_CLASS, "active-tab")
        self.assertIn("." + ACTIVE_TAB_CLASS, ACTIVE_TAB_CSS)
        self.assertIn("@theme_selected_bg_color", ACTIVE_TAB_CSS)
        self.assertIn("@theme_selected_fg_color", ACTIVE_TAB_CSS)
        self.assertIn("border-color: transparent", ACTIVE_TAB_CSS)
        self.assertIn("border-color: @theme_selected_bg_color", ACTIVE_TAB_CSS)
        self.assertEqual(ACTIVE_TAB_CSS.count("border-width:"), 1)
        self.assertIn("border-width: 0 0 3px 0", ACTIVE_TAB_CSS)
        self.assertNotIn("#1c71d8", ACTIVE_TAB_CSS)
        self.assertNotIn("font-weight", ACTIVE_TAB_CSS)
        self.assertNotIn(":hover", ACTIVE_TAB_CSS)
```

- [ ] **Step 2: Run the test to verify it fails**

Run from the repository root:

```sh
python -X tracemalloc -u -m unittest -v tests.test_session.ActiveTabTests
```

Expected: ERROR during import, `ImportError: cannot import name 'tab_css_classes' from 'pdfarranger.session'`.

- [ ] **Step 3: Write the minimal implementation**

In `pdfarranger/session.py`, insert this immediately after `tab_tooltip` (the function that returns `""`):

```python
ACTIVE_TAB_CLASS = "active-tab"


def tab_css_classes(doc_id: int, focused_id: int | None) -> frozenset[str]:
    if focused_id is not None and doc_id == focused_id:
        return frozenset((ACTIVE_TAB_CLASS,))
    return frozenset()


ACTIVE_TAB_CSS = """
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
"""
```

Leave `WindowModel` unchanged. `focused_id()` is already the active document.

- [ ] **Step 4: Run the test to verify it passes**

Run:

```sh
python -X tracemalloc -u -m unittest -v tests.test_session.ActiveTabTests
```

Expected: `Ran 6 tests` and `OK`. The stylesheet is not on screen yet. Task 2 loads it and applies the class.

- [ ] **Step 5: Commit**

```sh
git add pdfarranger/session.py tests/test_session.py
git commit -m "Decide which document tab is active."
```

## Task 2: Paint the active tab

**Files:**
- Modify: `pdfarranger/pdfarranger.py` (session import near line 197, new `application_css` before `class PdfArranger` at line 298, `do_activate` CSS load near lines 497–517)
- Modify: `pdfarranger/window.py` (session import at lines 45–55, `_create_tab_widget` at lines 259–268, `show_model` at lines 584–605)
- Test: `tests/test_session.py` (add methods to `ActiveTabTests`)

**Interfaces:**
- Consumes: `ACTIVE_TAB_CLASS: str`, `tab_css_classes(doc_id: int, focused_id: int | None) -> frozenset[str]`, and `ACTIVE_TAB_CSS: str` from Task 1. `ArrangerWindow.tab_widgets` maps `doc_id` to `(label, tab_box)`. `ArrangerWindow.show_model()` already refreshes the strip after focus changes. `WindowModel.focused_id() -> int | None`.
- Produces: `application_css() -> str` in `pdfarranger/pdfarranger.py`. `ArrangerWindow.sync_tab_active_classes() -> None`. The tab event box is created with `set_visible_window(False)`.

- [ ] **Step 1: Write the failing tests**

Append these methods to `ActiveTabTests` in `tests/test_session.py`:

```python
    def test_application_css_keeps_the_pane_outline_and_adds_the_tab_rules(self):
        from pdfarranger.pdfarranger import application_css

        css = application_css()
        self.assertIn("scrolledwindow.focused-pane", css)
        self.assertIn("border-color: #1c71d8", css)
        self.assertIn(ACTIVE_TAB_CSS, css)

    def test_sync_tab_active_classes_marks_only_the_focused_tab(self):
        from pdfarranger.window import ArrangerWindow

        class FakeStyle:
            def __init__(self):
                self.classes = set()

            def has_class(self, name):
                return name in self.classes

            def add_class(self, name):
                self.classes.add(name)

            def remove_class(self, name):
                self.classes.discard(name)

        class FakeBox:
            def __init__(self, classes):
                self.style = FakeStyle()
                self.style.classes.update(classes)

            def get_style_context(self):
                return self.style

        class DummyApp:
            def __init__(self):
                self.windows = []

        win = ArrangerWindow(DummyApp())
        first = win.model.focused_id()
        second = win.model.new_tab()
        first_box = FakeBox(set())
        second_box = FakeBox({ACTIVE_TAB_CLASS})
        win.tab_widgets[first] = (None, first_box)
        win.tab_widgets[second] = (None, second_box)

        win.sync_tab_active_classes()
        self.assertEqual(first_box.style.classes, set())
        self.assertEqual(second_box.style.classes, {ACTIVE_TAB_CLASS})

        win.sync_tab_active_classes()
        self.assertEqual(second_box.style.classes, {ACTIVE_TAB_CLASS})

        win.model.click_tab(first)
        win.sync_tab_active_classes()
        self.assertEqual(first_box.style.classes, {ACTIVE_TAB_CLASS})
        self.assertEqual(second_box.style.classes, set())

    def test_show_model_syncs_the_active_tab(self):
        from pdfarranger.window import ArrangerWindow

        class DummyApp:
            def __init__(self):
                self.windows = []

        win = ArrangerWindow(DummyApp())
        calls = []
        original = win.sync_tab_active_classes

        def wrapped():
            calls.append(win.model.focused_id())
            original()

        win.sync_tab_active_classes = wrapped
        win.show_model()
        self.assertEqual(calls, [win.model.focused_id()])

    def test_tab_event_box_is_input_only(self):
        from pdfarranger.window import Gtk, ArrangerWindow

        if Gtk is None:
            self.skipTest("GTK is not importable")

        class DummyApp:
            def __init__(self):
                self.windows = []

        win = ArrangerWindow(DummyApp())
        _label, tab_box = win.tab_widgets[win.model.focused_id()]
        event_box = tab_box.get_children()[0]
        self.assertFalse(event_box.get_visible_window())
```

`test_sync_tab_active_classes_marks_only_the_focused_tab` calls `sync_tab_active_classes` directly. It does not call `show_model`, because `show_model` would pack the fake boxes into the real strip when GTK is available. The second test checks the `show_model` call with the real widgets left in place.

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```sh
python -X tracemalloc -u -m unittest -v tests.test_session.ActiveTabTests.test_application_css_keeps_the_pane_outline_and_adds_the_tab_rules tests.test_session.ActiveTabTests.test_sync_tab_active_classes_marks_only_the_focused_tab tests.test_session.ActiveTabTests.test_show_model_syncs_the_active_tab tests.test_session.ActiveTabTests.test_tab_event_box_is_input_only
```

Expected, without `-f`: `test_application_css_keeps_the_pane_outline_and_adds_the_tab_rules` ERRORs with `AttributeError: module 'pdfarranger.pdfarranger' has no attribute 'application_css'`. The two sync tests ERROR with `AttributeError` naming `sync_tab_active_classes`. When GTK imports, `test_tab_event_box_is_input_only` FAILS because `get_visible_window()` is true. When GTK does not import, that test skips.

- [ ] **Step 3: Write the minimal implementation**

In `pdfarranger/pdfarranger.py`, change the session import from:

```python
from .session import plan_launch, SaveGate, window_prompt_sequence
```

to:

```python
from .session import ACTIVE_TAB_CSS, plan_launch, SaveGate, window_prompt_sequence
```

Add this function immediately above `class PdfArranger`:

```python
def application_css() -> str:
    return """
            iconview {
                outline-color: alpha(currentColor, 0.8);
                outline-style: dashed;
                outline-offset: -2px;
                outline-width: 2px;
                -gtk-outline-radius: 2px;
            }
            scrolledwindow overshoot {
                background: none;
            }
            scrolledwindow.focused-pane {
                border-width: 2px;
                border-style: solid;
                border-color: #1c71d8;
            }
            """ + ACTIVE_TAB_CSS
```

In `do_activate`, delete the `css_data = """..."""` assignment (the iconview, overshoot, and focused-pane rules). Keep the provider. Load the function instead:

```python
            style_provider = Gtk.CssProvider()
            style_provider.load_from_data(bytes(application_css().encode()))
            Gtk.StyleContext.add_provider_for_screen(
                Gdk.Screen.get_default(),
                style_provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
```

In `pdfarranger/window.py`, add `ACTIVE_TAB_CLASS` and `tab_css_classes` to the existing session import:

```python
from .session import (
    ACTIVE_TAB_CLASS,
    OpenTarget,
    PromptChoice,
    WindowModel,
    choose_open_target,
    prompt_order,
    resolve_prompts,
    single_close,
    tab_css_classes,
    tab_label,
    tab_tooltip,
)
```

In `_create_tab_widget`, the event box currently starts as `event_box = Gtk.EventBox()`. Give it an input-only window before the label is added. A visible event-box window would paint over the tab color. Clicks and tab drags still arrive because the window is input-only:

```python
        event_box = Gtk.EventBox()
        event_box.set_visible_window(False)
        label = Gtk.Label()
```

Add this method immediately above `show_model`:

```python
    def sync_tab_active_classes(self) -> None:
        focused_id = self.model.focused_id()
        for doc_id, widgets in self.tab_widgets.items():
            _label, tab_box = widgets
            if tab_box is None or not hasattr(tab_box, "get_style_context"):
                continue
            style = tab_box.get_style_context()
            wanted = ACTIVE_TAB_CLASS in tab_css_classes(doc_id, focused_id)
            has = style.has_class(ACTIVE_TAB_CLASS)
            if wanted and not has:
                style.add_class(ACTIVE_TAB_CLASS)
            elif has and not wanted:
                style.remove_class(ACTIVE_TAB_CLASS)
```

In `show_model`, call it after the search-bar block and before the GTK return. The search-bar block ends by setting `self._bound_doc_id = None` in the `focused is None` branch, then the method currently does `if Gtk is None: return`. Insert the call so both branches of that search-bar block fall through to it:

```python
                self._bound_doc_id = None

        self.sync_tab_active_classes()

        if Gtk is None:
            return
```

Do not set the class in `_on_tab_button_release`, `_on_pane_click`, or the key handler. Those paths already call `show_model`.

- [ ] **Step 4: Run the tests to verify they pass**

Run the new class, then the whole session suite. `show_model` is shared with find, close, and the save gate, so the class run is not enough:

```sh
python -X tracemalloc -u -m unittest -v tests.test_session.ActiveTabTests
python -X tracemalloc -u -m unittest -v -f tests.test_session
```

Expected: both end with `OK`. `ActiveTabTests` runs 10 tests. `test_tab_event_box_is_input_only` is skipped only when GTK cannot be imported, and the run is still `OK`.

- [ ] **Step 5: Check the strip on a display**

Skip this step when no display is available. Do not describe the colors as seen in that case. When a display is available, install the checkout and open the app with two PDFs:

```sh
python -m pip install -e ".[image]"
python -m pdfarranger
```

Open a second document with Ctrl+T or File → Open so two tabs are visible. Confirm:

- The focused tab is filled with the theme selection color, and its title and “×” use the theme’s selected text color.
- The other tab is unfilled and its 3px bottom edge is empty.
- Clicking the other tab swaps that fill.
- Ctrl+Tab swaps it again.
- View → Side by Side still draws the blue outline on one pane. The outlined pane’s tab is the filled tab. F6 moves the fill to the other tab and moves the outline with it.
- The tab titles do not jump sideways when the fill moves.

- [ ] **Step 6: Commit**

```sh
git add pdfarranger/pdfarranger.py pdfarranger/window.py tests/test_session.py
git commit -m "Paint the active document tab with the theme selection colors."
```

Do not commit `po/`, `build/`, or `data/screenshot-tabs.png`.
