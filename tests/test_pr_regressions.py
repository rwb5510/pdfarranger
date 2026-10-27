"""Regressions for document extraction and asynchronous close/save behavior."""
import ast
import inspect
import textwrap
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import gi
gi.require_version('Gtk', '3.0')
from pdfarranger import document, window, pdfarranger
from pdfarranger.session import SaveGate, WindowModel


def callback_for(name, host):
    tree = ast.parse(textwrap.dedent(inspect.getsource(window.ArrangerWindow._ArrangerWindow__create_actions)))
    for node in ast.walk(tree):
        if isinstance(node, ast.Tuple) and len(node.elts) > 1 and isinstance(node.elts[0], ast.Constant) and node.elts[0].value == name:
            return eval(compile(ast.Expression(node.elts[1]), '<action>', 'eval'), {'self': host})
    raise AssertionError(name)


class ExtractionTests(unittest.TestCase):
    def test_undo_redo_callbacks_forward_arguments(self):
        class Manager:
            def undo(self, action, param, unknown):
                calls.append(('undo', action, param, unknown))
            def redo(self, action, param, unknown):
                calls.append(('redo', action, param, unknown))
        calls = []
        host = SimpleNamespace(focused_document=lambda: SimpleNamespace(undomanager=Manager()))
        # Compile the real callbacks with the host as their captured self.
        for name in ('undo', 'redo'):
            func = callback_for(name, host)
            func(1, 2, 3)
        self.assertEqual(calls, [('undo', 1, 2, 3), ('redo', 1, 2, 3)])

    def test_print_operation_gets_application_config(self):
        config = SimpleNamespace(scale_mode=lambda: 'PRINTABLE', auto_rotate=lambda: False)
        doc = document.Document(SimpleNamespace(config=config), 1)
        doc.iconview = SimpleNamespace(get_selected_items=lambda: [])
        operation = document.exporter.PrintOperation(doc)
        self.assertEqual(operation.scale_mode, 'PRINTABLE')

    def test_password_action_signature_and_dialog(self):
        host = window.ArrangerWindow.__new__(window.ArrangerWindow)
        doc = document.Document(None, 1)
        host.focused_document = lambda: doc
        doc.set_password = Mock()
        # Exercise the lambda from the actual action wiring.
        tree = ast.parse(textwrap.dedent(inspect.getsource(window.ArrangerWindow._ArrangerWindow__create_actions)))
        node = next(n for n in ast.walk(tree) if isinstance(n, ast.Lambda) and isinstance(n.body, ast.Call) and any(isinstance(a, ast.Constant) and a.value == 'password_setup' for a in n.body.args))
        action = eval(compile(ast.Expression(node), '<password-action>', 'eval'), {'self': host})
        with patch.object(document, 'EncryptionPasswordDialog', create=True) as dialog:
            dialog.return_value.get_password.return_value = 'secret'
            action(None, SimpleNamespace(get_boolean=lambda: True))
        doc.set_password.assert_called_once_with('secret')

    def test_booklet_helpers_are_available(self):
        doc = document.Document(None, 1)
        doc.iconview = SimpleNamespace(get_selected_items=lambda: [SimpleNamespace(get_indices=lambda: (0,)), SimpleNamespace(get_indices=lambda: (2,))])
        doc.error_message_dialog = Mock()
        doc.split_booklet(None, None, None)
        doc.error_message_dialog.assert_called_once()
        self.assertTrue(document.is_same_page_size([SimpleNamespace(size_in_points=lambda: (10, 20))]))


class PaneRemovalTests(unittest.TestCase):
    def test_remove_left_pane_never_duplicates_right(self):
        for detach in (False, True):
            for count in (2, 3):
                with self.subTest(detach=detach, count=count):
                    model = WindowModel()
                    left = model.focused_id()
                    for _ in range(count - 1):
                        model.new_tab()
                    model.click_tab(left)
                    model.toggle_split()
                    (model.detach if detach else model.close_document)(left)
                    self.assertEqual(model.split, count > 2)
                    if model.split:
                        self.assertNotEqual(model.left_id, model.right_id)


class SaveCompletionTests(unittest.TestCase):
    def setUp(self):
        self.app = SimpleNamespace(save_gate=SaveGate(), windows=[], config=SimpleNamespace(show_save_warnings=lambda: False))
        self.doc = document.Document(self.app, 1)
        self.doc.set_export_state = Mock()
        self.doc.set_unsaved = lambda flag: setattr(self.doc, 'is_unsaved', flag)
        self.doc.error_message_dialog = Mock()
        self.doc.export_process = SimpleNamespace(is_alive=lambda: False, exitcode=0)
        self.doc.is_unsaved = True
        self.app.save_gate.start(1)

    def complete(self):
        self.doc.export_finished('ALL_TO_SINGLE', SimpleNamespace(empty=lambda: True))

    def test_gate_is_free_when_close_continuation_runs(self):
        seen = []
        self.doc.host = SimpleNamespace(close_document=lambda _: seen.append(self.app.save_gate.busy_id))
        self.doc.post_action = ('close', 1)
        self.complete()
        self.assertEqual(seen, [None])

    def test_gate_is_free_when_quit_continuation_runs(self):
        seen = []
        self.app.quit_all = lambda: seen.append(self.app.save_gate.busy_id)
        self.doc.post_action = ('quit-all',)
        self.complete()
        self.assertEqual(seen, [None])

    def test_gate_is_free_when_window_close_continuation_runs(self):
        seen = []
        self.doc.host = SimpleNamespace(
            post_action='close-window',
            close_window=lambda: seen.append(self.app.save_gate.busy_id),
        )
        self.complete()
        self.assertEqual(seen, [None])

    def test_failure_cancels_close_continuation(self):
        self.doc.host = SimpleNamespace(close_document=Mock())
        self.doc.export_process.exitcode = 1
        self.doc.post_action = ('close', 1)
        self.complete()
        self.doc.host.close_document.assert_not_called()
        self.assertIsNone(self.app.save_gate.busy_id)


class ClosePlanTests(unittest.TestCase):
    def setUp(self):
        self.app = SimpleNamespace(save_gate=SaveGate(), windows=[], config=SimpleNamespace(show_save_warnings=lambda: False))
        with patch.object(window, 'Gtk', None):
            self.win = window.ArrangerWindow(self.app)
        self.app.windows.append(self.win)
        self.win.show_model = Mock()
        self.app._quit_without_prompts = lambda: pdfarranger.PdfArranger._quit_without_prompts(self.app)
        self.app.active_window = lambda: self.win
        self.app.document_by_id = lambda doc_id: self.win.docs.get(doc_id)
        self.app.close_window = Mock()
        self.app.close_application = Mock()
        self.win.save_changes_dialog = Mock(return_value=3)
        self.docs = [self.win.focused_document()]
        second = document.Document(self.app, self.win.model.new_tab())
        second.host = self.win
        self.win.docs[second.id] = second
        self.docs.append(second)
        for doc in self.docs:
            doc.is_unsaved = True
            doc.save_file = '/tmp/regression.pdf'
            doc.set_export_state = Mock()
            doc.set_unsaved = lambda flag, d=doc: setattr(d, 'is_unsaved', flag)
            doc.destroy = Mock()
            doc.error_message_dialog = Mock()
            def save(*args, d=doc):
                self.assertIsNone(self.app.save_gate.busy_id)
                self.app.save_gate.start(d.id)
                d.export_process = SimpleNamespace(is_alive=lambda: False, exitcode=0, join=Mock(side_effect=AssertionError('GTK thread must not join')))
                self.started.append(d)
            doc.save = save
        self.started = []

    def test_window_closes_after_both_saves_without_reprompting(self):
        self.assertFalse(self.win.close_window())
        self.assertEqual(len(self.started), 1)
        self.started[0].export_finished('ALL_TO_SINGLE', SimpleNamespace(empty=lambda: True))
        self.assertEqual(len(self.started), 2)
        self.started[1].export_finished('ALL_TO_SINGLE', SimpleNamespace(empty=lambda: True))
        self.app.close_window.assert_called_once_with(self.win)
        self.assertEqual(self.win.save_changes_dialog.call_count, 2)

    def test_quit_finishes_after_both_saves(self):
        pdfarranger.PdfArranger.quit_all(self.app)
        self.assertEqual(len(self.started), 1)
        self.started[0].export_finished('ALL_TO_SINGLE', SimpleNamespace(empty=lambda: True))
        self.started[1].export_finished('ALL_TO_SINGLE', SimpleNamespace(empty=lambda: True))
        self.app.close_application.assert_called_once()

    def test_failed_save_aborts_remaining_plan(self):
        self.win.close_window()
        self.started[0].export_process.exitcode = 1
        self.started[0].export_finished('ALL_TO_SINGLE', SimpleNamespace(empty=lambda: True))
        self.assertEqual(len(self.started), 1)
        self.app.close_window.assert_not_called()

    def test_cancelled_second_save_as_aborts_after_first_save(self):
        second = self.docs[0]  # The focused document is saved first.
        second.save_file = None
        second.choose_export_pdf_name = lambda _: None
        self.assertFalse(self.win.close_window())
        self.started[0].export_finished('ALL_TO_SINGLE', SimpleNamespace(empty=lambda: True))
        self.assertEqual(len(self.started), 1)
        self.app.close_window.assert_not_called()
        self.assertIsNone(second._save_callback)
        self.assertIsNone(self.app.save_gate.busy_id)

    def test_cancelled_save_as_keeps_window_open(self):
        first = self.win.focused_document()
        first.save_file = None
        first.choose_export_pdf_name = lambda _: None
        self.assertFalse(self.win.close_window())
        self.assertEqual(self.started, [])
        self.app.close_window.assert_not_called()


if __name__ == '__main__':
    unittest.main()
