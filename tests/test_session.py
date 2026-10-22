import unittest

from pdfarranger.session import (
    LaunchPlan,
    OpenTarget,
    choose_open_target,
    document_occupied,
    plan_launch,
    tab_label,
    tab_tooltip,
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
