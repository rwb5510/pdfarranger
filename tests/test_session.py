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

