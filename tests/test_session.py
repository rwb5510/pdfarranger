import os
import unittest

from pdfarranger.session import (
    LaunchPlan,
    OpenTarget,
    choose_open_target,
    document_occupied,
    plan_launch,
    tab_label,
    tab_tooltip,
    Pane,
    WindowModel,
    CloseOutcome,
    DropSite,
    PromptChoice,
    SaveGate,
    drop_target,
    prompt_order,
    resolve_prompts,
    single_close,
)


class OpenTargetTests(unittest.TestCase):
    def test_empty_document_is_not_occupied(self):
        self.assertFalse(document_occupied(0, 0))

    def test_queue_or_metadata_occupies_a_document(self):
        self.assertTrue(document_occupied(1, 0))
        self.assertTrue(document_occupied(0, 1))

    def test_negative_lengths_are_rejected(self):
        with self.assertRaises(ValueError):
            document_occupied(-1, 0)

    def test_empty_document_is_filled(self):
        self.assertIs(choose_open_target(False), OpenTarget.FILL)

    def test_occupied_document_opens_a_tab(self):
        self.assertIs(choose_open_target(True), OpenTarget.NEW_TAB)


class TabTextTests(unittest.TestCase):
    def test_label_prefers_save_name_then_source_then_untitled(self):
        self.assertEqual(tab_label("contract.pdf", "scan.pdf"), "contract.pdf")
        self.assertEqual(tab_label(None, "scan.pdf"), "scan.pdf")
        self.assertEqual(tab_label(None, None), "untitled")
        self.assertEqual(tab_label("", "scan.pdf"), "scan.pdf")

    def test_tooltip_uses_the_full_path(self):
        self.assertEqual(tab_tooltip(r"C:\a\contract.pdf", r"C:\b\scan.pdf"), r"C:\a\contract.pdf")
        self.assertEqual(tab_tooltip(None, r"C:\b\scan.pdf"), r"C:\b\scan.pdf")
        self.assertEqual(tab_tooltip(None, None), "")


class LaunchPlanTests(unittest.TestCase):
    def test_startup_with_files_fills_the_first_document(self):
        plan = plan_launch(False, ["a.pdf", "b.pdf"], False)
        self.assertEqual(plan, LaunchPlan("fill", ["a.pdf", "b.pdf"]))

    def test_startup_without_files_fills_nothing(self):
        plan = plan_launch(False, [], False)
        self.assertEqual(plan.action, "fill")
        self.assertEqual(plan.files, [])

    def test_later_launch_without_files_raises_the_window(self):
        plan = plan_launch(True, [], True)
        self.assertEqual(plan.action, "raise")
        self.assertEqual(plan.files, [])

    def test_later_launch_fills_an_empty_focused_document(self):
        plan = plan_launch(True, ["b.pdf", "c.pdf"], False)
        self.assertEqual(plan, LaunchPlan("fill", ["b.pdf", "c.pdf"]))

    def test_later_launch_adds_one_tab_when_the_document_is_occupied(self):
        plan = plan_launch(True, ["b.pdf", "c.pdf"], True)
        self.assertEqual(plan, LaunchPlan("new_tab", ["b.pdf", "c.pdf"]))


class WindowModelTests(unittest.TestCase):
    def test_new_model_has_one_empty_document(self):
        model = WindowModel()
        self.assertEqual(len(model.order), 1)
        self.assertEqual(model.focused_id(), model.order[0])
        self.assertFalse(model.split)

    def test_open_on_empty_reuses_the_focused_document(self):
        model = WindowModel()
        first = model.focused_id()
        target, receiver = model.open_files(False)
        self.assertIs(target, OpenTarget.FILL)
        self.assertEqual(receiver, first)
        self.assertEqual(model.order, [first])

    def test_open_on_occupied_inserts_one_tab_in_the_focused_pane(self):
        model = WindowModel()
        first = model.focused_id()
        target, receiver = model.open_files(True)
        self.assertIs(target, OpenTarget.NEW_TAB)
        self.assertEqual(model.order, [first, receiver])
        self.assertEqual(model.focused_id(), receiver)
        self.assertFalse(model.split)

    def test_click_hidden_tab_replaces_the_focused_pane(self):
        model = WindowModel()
        first = model.focused_id()
        _target, second = model.open_files(True)
        model.click_tab(first)
        self.assertEqual(model.focused_id(), first)
        self.assertFalse(model.showing(second))

    def test_click_visible_right_tab_focuses_that_pane(self):
        model = WindowModel()
        left = model.focused_id()
        _target, right = model.open_files(True)
        model.click_tab(left)
        model.toggle_split()
        model.click_tab(right)
        self.assertEqual(model.focused, Pane.RIGHT)
        self.assertEqual(model.left_id, left)
        self.assertEqual(model.right_id, right)

    def test_side_by_side_puts_the_next_tab_on_the_right(self):
        model = WindowModel()
        first = model.focused_id()
        _target, second = model.open_files(True)
        model.click_tab(first)
        model.toggle_split()
        self.assertTrue(model.split)
        self.assertEqual(model.left_id, first)
        self.assertEqual(model.right_id, second)
        self.assertEqual(model.focused, Pane.LEFT)
        model.toggle_split()
        self.assertFalse(model.split)
        self.assertIsNone(model.right_id)
        self.assertEqual(model.focused_id(), first)

    def test_side_by_side_wraps_from_the_last_tab(self):
        model = WindowModel()
        first = model.focused_id()
        _target, second = model.open_files(True)
        model.click_tab(second)
        model.toggle_split()
        self.assertEqual(model.left_id, second)
        self.assertEqual(model.right_id, first)

    def test_side_by_side_does_nothing_with_one_document(self):
        model = WindowModel()
        self.assertFalse(model.can_split())
        model.toggle_split()
        self.assertFalse(model.split)

    def test_drag_hidden_tab_to_the_right_edge(self):
        model = WindowModel()
        left = model.focused_id()
        _target, right = model.open_files(True)
        model.click_tab(left)
        model.drag_tab_to_right(right)
        self.assertTrue(model.split)
        self.assertEqual(model.left_id, left)
        self.assertEqual(model.right_id, right)

    def test_drag_focused_tab_to_the_right_keeps_documents_distinct(self):
        model = WindowModel()
        left = model.focused_id()
        _target, other = model.open_files(True)
        model.click_tab(left)
        model.drag_tab_to_right(left)
        self.assertEqual(model.right_id, left)
        self.assertEqual(model.left_id, other)
        self.assertNotEqual(model.left_id, model.right_id)

    def test_cycle_follows_the_click_rule(self):
        model = WindowModel()
        first = model.focused_id()
        _target, second = model.open_files(True)
        third = model.new_tab()
        model.click_tab(first)
        model.toggle_split()
        model.cycle_tab(False)
        self.assertEqual(model.focused, Pane.RIGHT)
        self.assertEqual(model.focused_id(), second)
        model.cycle_tab(False)
        self.assertEqual(model.right_id, third)
        model.cycle_tab(True)
        self.assertEqual(model.focused_id(), second)

    def test_close_last_document_leaves_one_empty_document(self):
        model = WindowModel()
        only = model.focused_id()
        result = model.close_document(only)
        self.assertEqual(result, "emptied")
        self.assertEqual(len(model.order), 1)
        self.assertNotEqual(model.focused_id(), only)
        self.assertFalse(model.split)

    def test_detach_last_document_closes_the_window(self):
        model = WindowModel()
        doc_id = model.focused_id()
        detached, close_window = model.detach(doc_id)
        self.assertEqual(detached, doc_id)
        self.assertTrue(close_window)
        self.assertEqual(model.order, [])

    def test_detach_and_attach_moves_a_tab(self):
        source = WindowModel()
        kept = source.focused_id()
        _target, moving = source.open_files(True)
        other = WindowModel()
        _detached, close_window = source.detach(moving)
        self.assertFalse(close_window)
        self.assertEqual(source.order, [kept])
        other.attach(moving)
        self.assertIn(moving, other.order)
        self.assertEqual(other.focused_id(), moving)


class ClosePromptTests(unittest.TestCase):
    def test_prompt_order_asks_the_focused_document_first(self):
        self.assertEqual(prompt_order(2, [1, 2, 3], [1, 2, 3]), [2, 1, 3])

    def test_cancel_aborts_before_anything_closes(self):
        outcome = resolve_prompts(
            [2, 1],
            [PromptChoice.SAVE, PromptChoice.CANCEL],
        )
        self.assertEqual(outcome, CloseOutcome(True, [], []))

    def test_saves_run_before_discards_are_recorded(self):
        outcome = resolve_prompts(
            [2, 1, 3],
            [PromptChoice.DISCARD, PromptChoice.SAVE, PromptChoice.DISCARD],
        )
        self.assertEqual(outcome, CloseOutcome(False, [1], [2, 3]))

    def test_single_close_answers(self):
        self.assertEqual(single_close(PromptChoice.SAVE), "save_then_close")
        self.assertEqual(single_close(PromptChoice.DISCARD), "discard")
        self.assertEqual(single_close(PromptChoice.CANCEL), "abort")


class DropTargetTests(unittest.TestCase):
    def test_drop_site_selects_the_document(self):
        self.assertEqual(drop_target(DropSite.PANE, 4, 5, 6), 4)
        self.assertEqual(drop_target(DropSite.TAB, 4, 5, 6), 5)
        self.assertEqual(drop_target(DropSite.WINDOW, None, None, 6), 6)


class SaveGateTests(unittest.TestCase):
    def test_only_one_save_runs(self):
        gate = SaveGate()
        self.assertTrue(gate.can_start())
        gate.start(3)
        self.assertFalse(gate.can_start())
        self.assertEqual(gate.busy_id, 3)
        with self.assertRaises(RuntimeError):
            gate.start(4)
        gate.finish()
        self.assertTrue(gate.can_start())
        self.assertIsNone(gate.busy_id)


from pdfarranger.document import Document


class _AppDirs:
    def __init__(self):
        self.tmp_dir = "/tmp/pdfarranger-test"
        self.import_directory = None
        self.export_directory = "/home/export"


class DocumentShellTests(unittest.TestCase):
    def test_two_documents_do_not_share_state(self):
        app = _AppDirs()
        first = Document(app, 1)
        second = Document(app, 2)
        first.pdfqueue.append("doc")
        first.metadata["Title"] = "A"
        first.find_text = "hello"
        first.set_import_directory("/tmp/in")
        self.assertEqual(second.pdfqueue, [])
        self.assertEqual(second.metadata, {})
        self.assertEqual(second.find_text, "")
        self.assertEqual(second.import_directory, "/tmp/in")
        self.assertTrue(first.occupied())
        self.assertFalse(second.occupied())

    def test_release_renderer_asks_the_thread_to_quit(self):
        class Thread:
            def __init__(self):
                self.quit = False

        doc = Document(_AppDirs(), 1)
        doc.rendering_thread = Thread()
        doc.release_renderer()
        self.assertTrue(doc.rendering_thread.quit)


class DocumentMethodTests(unittest.TestCase):
    def test_page_operations_live_on_document(self):
        names = [
            "build_view",
            "render",
            "quit_rendering",
            "set_unsaved",
            "save_or_choose",
            "paste_pages",
            "iv_dnd_received_data",
            "sw_dnd_received_data",
            "on_action_zoom_in",
            "clear_data",
            "error_message_dialog",
        ]
        for name in names:
            self.assertTrue(callable(getattr(Document, name)), name)


class OpenFilesOrderTests(unittest.TestCase):
    def test_windows_reverses_multi_select_order(self):
        from pdfarranger.window import filenames_for_open
        import os
        names = ["a.pdf", "b.pdf", "c.pdf"]
        if os.name == "nt":
            self.assertEqual(filenames_for_open(names), ["c.pdf", "b.pdf", "a.pdf"])
        else:
            self.assertEqual(filenames_for_open(names), names)


class ArrangerWindowInterfaceTests(unittest.TestCase):
    def test_window_model_and_tabs(self):
        from pdfarranger.window import ArrangerWindow

        class DummyApp:
            def __init__(self):
                self.config = None
                self.import_directory = None
                self.export_directory = None
                self.windows = []
                self.last_focused_window = None

            def active_window(self):
                if self.last_focused_window is not None and self.last_focused_window in self.windows:
                    return self.last_focused_window
                return self.windows[0] if self.windows else None

            def new_window(self):
                w = ArrangerWindow(self)
                self.windows.append(w)
                return w

            def new_window_for_document(self, document):
                w = ArrangerWindow(self, empty=False)
                self.windows.append(w)
                w.accept_document(document)
                return w

            def close_window(self, w):
                if w in self.windows:
                    self.windows.remove(w)

        app = DummyApp()
        win = ArrangerWindow(app)
        app.windows.append(win)
        self.assertIs(app.active_window(), win)
        self.assertIsNotNone(win.focused_document())
        self.assertEqual(len(win.docs), 1)

        win.new_tab()
        self.assertEqual(len(win.docs), 2)
        self.assertEqual(win.focused_document().id, win.model.focused_id())

        doc_id = win.model.focused_id()
        win.close_document(doc_id)
        self.assertEqual(len(win.docs), 1)

    def test_window_detach_document_creates_new_window(self):
        from pdfarranger.window import ArrangerWindow

        class DummyApp:
            def __init__(self):
                self.windows = []

            def new_window(self):
                w = ArrangerWindow(self)
                self.windows.append(w)
                return w

            def new_window_for_document(self, document):
                w = ArrangerWindow(self, empty=False)
                self.windows.append(w)
                w.accept_document(document)
                return w

            def close_window(self, w):
                if w in self.windows:
                    self.windows.remove(w)

        app = DummyApp()
        win = app.new_window()
        first_id = win.model.focused_id()
        win.new_tab()
        second_id = win.model.focused_id()
        self.assertEqual(len(win.docs), 2)

        # Detach second document: source window stays open
        win.detach_document(second_id)
        self.assertEqual(len(win.docs), 1)
        self.assertEqual(win.model.order, [first_id])
        self.assertEqual(len(app.windows), 2)
        new_win = app.windows[1]
        self.assertEqual(list(new_win.docs.keys()), [second_id])
        self.assertIs(new_win.focused_document().host, new_win)

        # Detach last remaining document: source window is closed
        win.detach_document(first_id)
        self.assertNotIn(win, app.windows)
        self.assertEqual(len(app.windows), 2)  # new_win from earlier + brand new window for first_id

    def test_accept_document_across_existing_windows(self):
        from pdfarranger.window import ArrangerWindow

        class DummyApp:
            def __init__(self):
                self.windows = []

            def new_window(self):
                w = ArrangerWindow(self)
                self.windows.append(w)
                return w

            def close_window(self, w):
                if w in self.windows:
                    self.windows.remove(w)

        app = DummyApp()
        win1 = app.new_window()
        win2 = app.new_window()
        doc2_id = win2.model.focused_id()
        doc2 = win2.docs[doc2_id]

        detached_doc, close_source = win2.detach_document(doc2_id, new_window=False)
        self.assertIs(detached_doc, doc2)
        self.assertTrue(close_source)

        win1.accept_document(detached_doc)
        if close_source:
            app.close_window(win2)

        self.assertIn(doc2_id, win1.docs)
        self.assertEqual(len(win1.docs), 2)
        self.assertIs(detached_doc.host, win1)
        self.assertNotIn(win2, app.windows)


class NewWindowHelperTests(unittest.TestCase):
    def test_detach_plan_for_a_second_document_keeps_the_source_open(self):
        source = WindowModel()
        kept = source.focused_id()
        moving = source.new_tab()
        doc_id, close_window = source.detach(moving)
        self.assertEqual(doc_id, moving)
        self.assertFalse(close_window)
        self.assertEqual(source.order, [kept])

    def test_window_model_start_empty_false(self):
        model = WindowModel(start_empty=False)
        self.assertEqual(model.order, [])
        self.assertIsNone(model.left_id)
        self.assertIsNone(model.right_id)
        self.assertIsNone(model.focused_id())

    def test_window_model_with_id_allocator(self):
        ids = iter([10, 20, 30])
        model = WindowModel(id_allocator=lambda: next(ids))
        self.assertEqual(model.order, [10])
        second = model.new_tab()
        self.assertEqual(second, 20)
        self.assertEqual(model.order, [10, 20])


class CommandLineRoutingTests(unittest.TestCase):
    def test_remote_occupied_window_is_a_new_tab(self):
        plan = plan_launch(True, ["notes.pdf"], True)
        self.assertEqual(plan.action, "new_tab")
        self.assertEqual(plan.files, ["notes.pdf"])


class PdfArrangerCommandLineTests(unittest.TestCase):
    def setUp(self):
        from pdfarranger.pdfarranger import PdfArranger

        class FakeDoc:
            def __init__(self, occupied=False):
                self._occupied = occupied

            def occupied(self):
                return self._occupied

        class FakeWindow:
            def __init__(self, occupied=False):
                self.doc = FakeDoc(occupied)
                self.docs = {1: self.doc}
                self.opened = []
                self.presented = False

            def focused_document(self):
                return self.doc

            def open_files(self, files):
                self.opened.append(list(files))

            def present(self):
                self.presented = True

        self.FakeDoc = FakeDoc
        self.FakeWindow = FakeWindow
        self.app = PdfArranger()
        self.app.windows = []
        self.activated = False
        self.app.activate = lambda: setattr(self, 'activated', True)

    def tearDown(self):
        if getattr(self.app, 'handoff', None):
            self.app.handoff.stop()
        if hasattr(self.app, 'tmp_dir') and os.path.isdir(self.app.tmp_dir):
            import shutil
            shutil.rmtree(self.app.tmp_dir, ignore_errors=True)

    def test_open_launched_files_raise_when_remote_and_no_files(self):
        win = self.FakeWindow(occupied=True)
        self.app.windows = [win]
        self.app.open_launched_files(remote=True, files=[])
        self.assertTrue(win.presented)
        self.assertEqual(win.opened, [])

    def test_open_launched_files_startup_no_files_just_presents(self):
        win = self.FakeWindow(occupied=False)
        self.app.windows = [win]
        self.app.open_launched_files(remote=False, files=[])
        self.assertTrue(win.presented)
        self.assertEqual(win.opened, [])

    def test_open_launched_files_routes_files_to_open_files(self):
        win = self.FakeWindow(occupied=True)
        self.app.windows = [win]
        self.app.open_launched_files(remote=True, files=["a.pdf", "b.pdf"])
        self.assertTrue(win.presented)
        self.assertEqual(win.opened, [["a.pdf", "b.pdf"]])

    def test_do_command_line_version_returns_zero_without_activating(self):
        from unittest.mock import patch

        class FakeOptions:
            def contains(self, key):
                return key == "version"

        class FakeCommandLine:
            def get_options_dict(self):
                return FakeOptions()

        with patch('builtins.print'):
            ret = self.app.do_command_line(FakeCommandLine())
        self.assertEqual(ret, 0)
        self.assertFalse(self.activated)

    def test_do_command_line_activates_if_no_windows(self):
        class FakeFile:
            def __init__(self, path):
                self._path = path

            def get_path(self):
                return self._path

        class FakeOptions:
            def contains(self, key):
                return False

            def lookup_value(self, key):
                return ["doc1.pdf", "doc2.pdf"]

        class FakeCommandLine:
            def get_options_dict(self):
                return FakeOptions()

            def create_file_for_arg(self, arg):
                return FakeFile("/absolute/" + arg)

            def get_is_remote(self):
                return False

        win = self.FakeWindow(occupied=False)
        def mock_activate():
            self.activated = True
            self.app.windows.append(win)

        self.app.activate = mock_activate
        ret = self.app.do_command_line(FakeCommandLine())
        self.assertEqual(ret, 0)
        self.assertTrue(self.activated)
        self.assertEqual(win.opened, [["/absolute/doc1.pdf", "/absolute/doc2.pdf"]])
        self.assertTrue(win.presented)

    def test_do_command_line_remote_does_not_activate_if_window_exists(self):
        class FakeFile:
            def __init__(self, path):
                self._path = path

            def get_path(self):
                return self._path

        class FakeOptions:
            def contains(self, key):
                return False

            def lookup_value(self, key):
                return ["remote.pdf"]

        class FakeCommandLine:
            def get_options_dict(self):
                return FakeOptions()

            def create_file_for_arg(self, arg):
                return FakeFile("/remote/" + arg)

            def get_is_remote(self):
                return True

        win = self.FakeWindow(occupied=True)
        self.app.windows = [win]
        ret = self.app.do_command_line(FakeCommandLine())
        self.assertEqual(ret, 0)
        self.assertFalse(self.activated)
        self.assertEqual(win.opened, [["/remote/remote.pdf"]])
        self.assertTrue(win.presented)

    def test_do_command_line_win32ipc_submits_without_activating(self):
        class FakeFile:
            def __init__(self, path):
                self._path = path

            def get_path(self):
                return self._path

        class FakeOptions:
            def contains(self, key):
                return False

            def lookup_value(self, key):
                return ["client.pdf"]

        class FakeCommandLine:
            def get_options_dict(self):
                return FakeOptions()

            def create_file_for_arg(self, arg):
                return FakeFile("/submitted/" + arg)

            def get_is_remote(self):
                return False

        with patch("pdfarranger.pdfarranger.gtk_unique_is_enough", return_value=False):
            with patch("pdfarranger.pdfarranger.Win32Handoff.submit", return_value=True) as mock_submit:
                ret = self.app.do_command_line(FakeCommandLine())
                self.assertEqual(ret, 0)
                mock_submit.assert_called_once_with(["/submitted/client.pdf"])
                self.assertFalse(self.activated)

    def test_do_command_line_win32ipc_starts_handoff_when_primary(self):
        class FakeFile:
            def __init__(self, path):
                self._path = path

            def get_path(self):
                return self._path

        class FakeOptions:
            def contains(self, key):
                return False

            def lookup_value(self, key):
                return ["first.pdf"]

        class FakeCommandLine:
            def get_options_dict(self):
                return FakeOptions()

            def create_file_for_arg(self, arg):
                return FakeFile("/primary/" + arg)

            def get_is_remote(self):
                return False

        with patch("pdfarranger.pdfarranger.gtk_unique_is_enough", return_value=False):
            with patch("pdfarranger.pdfarranger.Win32Handoff.submit", return_value=False):
                with patch("pdfarranger.pdfarranger.Win32Handoff.start") as mock_start:
                    win = self.FakeWindow(occupied=False)
                    self.app.activate = lambda: self.app.windows.append(win)
                    ret = self.app.do_command_line(FakeCommandLine())
                    self.assertEqual(ret, 0)
                    mock_start.assert_called_once()
                    self.assertIsNotNone(self.app.handoff)
                    self.assertEqual(win.opened, [["/primary/first.pdf"]])



import socket
import tempfile
import threading
from unittest.mock import patch

from pdfarranger.win32ipc import (
    Win32Handoff,
    decode_files,
    default_lock_dir,
    encode_files,
    gtk_unique_is_enough,
)


class GtkUniqueCheckTests(unittest.TestCase):
    def test_env_var_forces_fallback(self):
        with patch.dict(os.environ, {"PDFARRANGER_WIN32_IPC": "1"}):
            self.assertFalse(gtk_unique_is_enough())

    def test_non_windows_defaults_to_true(self):
        with patch.dict(os.environ, {}, clear=False):
            if "PDFARRANGER_WIN32_IPC" in os.environ:
                del os.environ["PDFARRANGER_WIN32_IPC"]
            with patch("pdfarranger.win32ipc.os.name", "posix"):
                self.assertTrue(gtk_unique_is_enough())

    def test_windows_glib_version_check(self):
        class FakeGLib:
            def __init__(self, major, minor):
                self.MAJOR_VERSION = major
                self.MINOR_VERSION = minor

        with patch.dict(os.environ, {}, clear=False):
            if "PDFARRANGER_WIN32_IPC" in os.environ:
                del os.environ["PDFARRANGER_WIN32_IPC"]
            with patch("pdfarranger.win32ipc.os.name", "nt"):
                with patch("pdfarranger.win32ipc.GLib", FakeGLib(2, 42)):
                    self.assertFalse(gtk_unique_is_enough())
                with patch("pdfarranger.win32ipc.GLib", FakeGLib(2, 44)):
                    self.assertTrue(gtk_unique_is_enough())
                with patch("pdfarranger.win32ipc.GLib", FakeGLib(3, 0)):
                    self.assertTrue(gtk_unique_is_enough())
                with patch("pdfarranger.win32ipc.GLib", None):
                    self.assertFalse(gtk_unique_is_enough())


class Win32HandoffTests(unittest.TestCase):
    def test_round_trip_message(self):
        self.assertEqual(decode_files(encode_files(["a.pdf", "b.pdf"])), ["a.pdf", "b.pdf"])

    def test_second_client_delivers_files_to_the_first_server(self):
        received = []
        ready = threading.Event()
        handoff = Win32Handoff(lambda files: received.append(files), ready.set)
        handoff.start()
        self.assertTrue(ready.wait(2))
        self.assertTrue(handoff.submit(["second.pdf"]))
        handoff.wait_idle(2)
        handoff.stop()
        self.assertEqual(received, [["second.pdf"]])

    def test_submit_returns_false_when_no_server_running(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            self.assertFalse(Win32Handoff.submit(["missing.pdf"], directory=tmpdir))

    def test_stale_lock_file_cleaned_up_on_failed_connect(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            lock_file = os.path.join(tmpdir, "instance.port")
            with open(lock_file, "w", encoding="utf-8") as f:
                f.write("127.0.0.1:59999\n")
            self.assertFalse(Win32Handoff.submit(["doc.pdf"], directory=tmpdir))
            self.assertFalse(os.path.exists(lock_file))


class SplitEnablementTests(unittest.TestCase):
    def test_split_action_is_enabled_only_with_two_documents(self):
        model = WindowModel()
        self.assertFalse(model.can_split())
        model.new_tab()
        self.assertTrue(model.can_split())


class SideBySideWindowTests(unittest.TestCase):
    def test_menu_and_config_declarations(self):
        import ast
        import xml.etree.ElementTree as ET

        # Config accels via AST
        config_path = os.path.join(os.path.dirname(__file__), "..", "pdfarranger", "config.py")
        with open(config_path, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read())
        accels = []
        for node in tree.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "_DEFAULT_ACCELS":
                        accels = [ast.literal_eval(elt) for elt in node.value.elts]

        self.assertIn(('focus-other-pane', 'F6'), accels)
        accel_names = [a[0] for a in accels]
        self.assertNotIn('side-by-side', accel_names)

        # menu.ui
        menu_path = os.path.join(os.path.dirname(__file__), "..", "data", "menu.ui")
        tree = ET.parse(menu_path)
        root = tree.getroot()
        side_by_side_found = False
        for item in root.findall(".//item"):
            action = item.find("attribute[@name='action']")
            if action is not None and action.text == "win.side-by-side":
                label = item.find("attribute[@name='label']")
                self.assertIsNotNone(label)
                self.assertEqual(label.text, "_Side by Side")
                side_by_side_found = True
                break
        self.assertTrue(side_by_side_found)

    def test_side_by_side_and_focus_actions_toggle_model(self):
        from pdfarranger.window import ArrangerWindow

        class DummyApp:
            def __init__(self):
                self.windows = []

        app = DummyApp()
        win = ArrangerWindow(app)
        doc1_id = win.model.focused_id()

        # Cannot split with only 1 document
        win.on_action_side_by_side()
        self.assertFalse(win.model.split)

        # Add second document
        win.new_tab()
        doc2_id = win.model.focused_id()
        self.assertEqual(len(win.docs), 2)
        self.assertTrue(win.model.can_split())

        # Select tab 1 to be focused
        win.model.click_tab(doc1_id)
        self.assertEqual(win.model.focused_id(), doc1_id)

        # Toggle split on
        win.on_action_side_by_side()
        self.assertTrue(win.model.split)
        self.assertEqual(win.model.left_id, doc1_id)
        self.assertEqual(win.model.right_id, doc2_id)
        self.assertEqual(win.model.focused_id(), doc1_id)

        # Focus other pane
        win.on_action_focus_other_pane()
        self.assertEqual(win.model.focused_id(), doc2_id)

        # Toggle split off
        win.on_action_side_by_side()
        self.assertFalse(win.model.split)

    def test_page_area_tab_drop_routes_to_drag_tab_to_right(self):
        from pdfarranger.window import ArrangerWindow

        class DummyApp:
            def __init__(self):
                self.windows = []

        app = DummyApp()
        win = ArrangerWindow(app)
        app.windows.append(win)
        doc1_id = win.model.focused_id()
        win.new_tab()
        doc2_id = win.model.focused_id()

        class DummyAllocation:
            width = 400

        class DummyPageArea:
            def get_allocation(self):
                return DummyAllocation()

        class DummySelectionData:
            def get_data(self):
                return f"{id(win)}:{doc2_id}".encode("utf-8")

        class DummyContext:
            def finish(self, success, delete, time):
                pass

        win.page_area = DummyPageArea()

        # Drop on left half (x = 100 <= 200): does not split to right
        win._on_page_area_drag_data_received(
            None, DummyContext(), 100, 0, DummySelectionData(), 1005, 0
        )
        self.assertFalse(win.model.split)

        # Drop on right half (x = 300 > 200): triggers drag_tab_to_right
        win._on_page_area_drag_data_received(
            None, DummyContext(), 300, 0, DummySelectionData(), 1005, 0
        )
        self.assertTrue(win.model.split)
        self.assertEqual(win.model.right_id, doc2_id)


from pdfarranger.document import page_drag_action_is_move


class PageDragTests(unittest.TestCase):
    def test_windows_moves_unless_ctrl_is_held(self):
        self.assertTrue(page_drag_action_is_move("nt", ctrl_held=False))
        self.assertFalse(page_drag_action_is_move("nt", ctrl_held=True))

    def test_posix_moves(self):
        self.assertTrue(page_drag_action_is_move("posix", ctrl_held=False))
        self.assertTrue(page_drag_action_is_move("posix", ctrl_held=True))

    def test_same_app_payload_round_trip(self):
        from pdfarranger.document import encode_page_drag, decode_page_drag
        payload = encode_page_drag(7, ["0", "2"])
        self.assertEqual(decode_page_drag(payload), (7, ["0", "2"]))

    def test_invalid_os_raises_value_error(self):
        with self.assertRaises(ValueError):
            page_drag_action_is_move("darwin", ctrl_held=False)

    def test_target_constants(self):
        from pdfarranger.document import MODEL_ROW_SAME_APP, Document
        from pdfarranger.pdfarranger import PdfArranger
        self.assertEqual(MODEL_ROW_SAME_APP, 1004)
        self.assertEqual(Document.MODEL_ROW_SAME_APP, 1004)
        self.assertEqual(PdfArranger.MODEL_ROW_SAME_APP, 1004)

    def test_tab_box_uri_drop_calls_import_files(self):
        from pdfarranger.window import ArrangerWindow

        class DummyApp:
            def __init__(self):
                self.windows = []

        app = DummyApp()
        win = ArrangerWindow(app)
        doc1_id = win.model.focused_id()
        win.new_tab()
        doc2_id = win.model.focused_id()

        imported = []
        win.import_files = lambda d_id, paths: imported.append((d_id, list(paths)))

        class DummySelectionData:
            def get_target(self):
                class Target:
                    def name(self):
                        return "text/uri-list"
                return Target()

            def get_uris(self):
                return ["file:///path/to/doc.pdf"]

        class DummyContext:
            def __init__(self):
                self.finished = False

            def finish(self, success, delete, time):
                self.finished = True

        ctx = DummyContext()
        win._on_tab_box_drag_data_received(None, ctx, 0, 0, DummySelectionData(), 1003, 0, doc1_id)
        self.assertTrue(ctx.finished)
        self.assertEqual(len(imported), 1)
        self.assertEqual(imported[0][0], doc1_id)
        self.assertTrue(imported[0][1][0].endswith("doc.pdf"))

    def test_page_area_uri_drop_calls_add_paths_on_focused_document(self):
        from pdfarranger.window import ArrangerWindow

        class DummyApp:
            def __init__(self):
                self.windows = []

        app = DummyApp()
        win = ArrangerWindow(app)
        doc1_id = win.model.focused_id()

        added = []
        win._add_paths = lambda doc, paths: added.append((doc.id, list(paths)))

        class DummySelectionData:
            def get_target(self):
                class Target:
                    def name(self):
                        return "text/uri-list"
                return Target()

            def get_uris(self):
                return ["file:///path/to/drop_page_area.pdf"]

        class DummyContext:
            def __init__(self):
                self.finished = False

            def finish(self, success, delete, time):
                self.finished = True

        ctx = DummyContext()
        win._on_page_area_drag_data_received(None, ctx, 0, 0, DummySelectionData(), 1003, 0)
        self.assertTrue(ctx.finished)
        self.assertEqual(len(added), 1)
        self.assertEqual(added[0][0], doc1_id)
        self.assertTrue(added[0][1][0].endswith("drop_page_area.pdf"))

    def test_tab_strip_uri_drop_calls_add_paths_on_focused_document(self):
        from pdfarranger.window import ArrangerWindow

        class DummyApp:
            def __init__(self):
                self.windows = []

        app = DummyApp()
        win = ArrangerWindow(app)
        doc1_id = win.model.focused_id()

        added = []
        win._add_paths = lambda doc, paths: added.append((doc.id, list(paths)))

        class DummySelectionData:
            def get_target(self):
                class Target:
                    def name(self):
                        return "text/uri-list"
                return Target()

            def get_uris(self):
                return ["file:///path/to/drop_tab_strip.pdf"]

        class DummyContext:
            def __init__(self):
                self.finished = False

            def finish(self, success, delete, time):
                self.finished = True

        ctx = DummyContext()
        win._on_tab_strip_drag_data_received(None, ctx, 0, 0, DummySelectionData(), 1003, 0)
        self.assertTrue(ctx.finished)
        self.assertEqual(len(added), 1)
        self.assertEqual(added[0][0], doc1_id)
        self.assertTrue(added[0][1][0].endswith("drop_tab_strip.pdf"))

    def test_document_same_app_dnd_get_data(self):
        from pdfarranger.document import Document

        class DummyIconView:
            def get_selected_items(self):
                class Path:
                    def __init__(self, idx):
                        self.idx = idx
                    def get_indices(self):
                        return [self.idx]
                return [Path(3), Path(1)]

        doc = Document(None, 42)
        doc.iconview = DummyIconView()

        class DummyTarget:
            def name(self):
                return "MODEL_ROW_SAME_APP"

        class DummySelectionData:
            def __init__(self):
                self.data = None

            def get_target(self):
                return DummyTarget()

            def set(self, target, format_val, payload):
                self.data = payload

        sel = DummySelectionData()
        doc.iv_dnd_get_data(doc.iconview, None, sel, 1004, 0)
        from pdfarranger.document import decode_page_drag
        self.assertEqual(decode_page_drag(sel.data), (42, ["1", "3"]))

    def test_document_same_app_dnd_received_data_move(self):
        from pdfarranger.document import Document, encode_page_drag

        class DummyPage:
            def __init__(self, name, nfile=1):
                self.name = name
                self.description = name
                self.nfile = nfile
                self.layerpages = []

            def duplicate(self):
                return DummyPage(self.name, self.nfile)

            def width_in_pixel(self):
                return 100

        class DummyModel:
            def __init__(self, items):
                self.items = list(items)

            def __len__(self):
                return len(self.items)

            def __iter__(self):
                for item in self.items:
                    yield [item, item.description]

            def __getitem__(self, idx):
                return [self.items[idx], self.items[idx].description]

            def get_iter(self, path):
                return path

            def get_value(self, it, col):
                return self.items[int(str(it))]

            def append(self, row):
                self.items.append(row[0])
                return len(self.items) - 1

            def get_path(self, it):
                return str(it)

            def remove(self, it):
                idx = int(str(it))
                if 0 <= idx < len(self.items):
                    self.items.pop(idx)

        class DummyIconView:
            def __init__(self, model):
                self.model = model
                self.selected = []

            def get_model(self):
                return self.model

            def get_direction(self):
                return 0

            def select_path(self, path):
                self.selected.append(path)

            def get_selected_items(self):
                return []

        class DummyUndoManager:
            def __init__(self):
                self.actions = []

            def commit(self, action):
                self.actions.append(action)

        class DummyApp:
            def __init__(self, docs):
                self.docs = docs

            def document_by_id(self, doc_id):
                return self.docs.get(doc_id)

        source_doc = Document(None, 1)
        dest_doc = Document(None, 2)
        source_doc.update_iconview_geometry = lambda: None
        dest_doc.update_iconview_geometry = lambda: None
        app = DummyApp({1: source_doc, 2: dest_doc})
        source_doc.app = app
        dest_doc.app = app

        class DummyPdfDoc:
            def __init__(self):
                self.password = None

        source_model = DummyModel([DummyPage("p0"), DummyPage("p1"), DummyPage("p2")])
        source_doc.model = source_model
        source_doc.iconview = DummyIconView(source_model)
        source_doc.undomanager = DummyUndoManager()
        source_doc.pdfqueue = [DummyPdfDoc()]

        dest_model = DummyModel([])
        dest_doc.model = dest_model
        dest_doc.iconview = DummyIconView(dest_model)
        dest_doc.undomanager = DummyUndoManager()
        dest_doc.pdfqueue = []

        class DummyContext:
            def get_selected_action(self):
                # Gdk.DragAction.MOVE = 4
                return 4

        class DummyTarget:
            def name(self):
                return "MODEL_ROW_SAME_APP"

        class DummySelectionData:
            def get_target(self):
                return DummyTarget()

            def get_data(self):
                return encode_page_drag(1, ["1"])

        dest_doc.drag_path = None
        dest_doc.drag_pos = 0

        # Run iv_dnd_received_data
        dest_doc.iv_dnd_received_data(dest_doc.iconview, DummyContext(), 0, 0, DummySelectionData(), 1004, 0)

        # Dest received p1
        self.assertEqual(len(dest_model.items), 1)
        self.assertEqual(dest_model.items[0].name, "p1")
        self.assertEqual(dest_doc.undomanager.actions, ["Move"])
        self.assertTrue(dest_doc.is_unsaved)
        self.assertEqual(len(dest_doc.pdfqueue), 1)

        # Source removed p1
        self.assertEqual(len(source_model.items), 2)
        self.assertEqual(source_doc.undomanager.actions, ["Move"])
        self.assertTrue(source_doc.is_unsaved)

