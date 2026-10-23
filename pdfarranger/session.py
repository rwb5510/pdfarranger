# Copyright (C) 2026 pdfarranger contributors
#
# pdfarranger is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

from dataclasses import dataclass
from enum import Enum


class OpenTarget(Enum):
    FILL = "fill"
    NEW_TAB = "new_tab"


def document_occupied(pdfqueue_len: int, metadata_len: int) -> bool:
    if pdfqueue_len < 0 or metadata_len < 0:
        raise ValueError("lengths must be >= 0")
    return pdfqueue_len > 0 or metadata_len > 0


def choose_open_target(occupied: bool) -> OpenTarget:
    if occupied:
        return OpenTarget.NEW_TAB
    return OpenTarget.FILL


def tab_label(save_basename: str | None, first_source_basename: str | None) -> str:
    if save_basename:
        return save_basename
    if first_source_basename:
        return first_source_basename
    return "untitled"


def tab_tooltip(save_path: str | None, first_source_path: str | None) -> str:
    if save_path:
        return save_path
    if first_source_path:
        return first_source_path
    return ""


@dataclass(frozen=True)
class LaunchPlan:
    action: str
    files: list


def plan_launch(remote: bool, files: list, focused_occupied: bool) -> LaunchPlan:
    files = list(files)
    if remote and not files:
        return LaunchPlan("raise", [])
    if not remote:
        return LaunchPlan("fill", files)
    if choose_open_target(focused_occupied) is OpenTarget.FILL:
        return LaunchPlan("fill", files)
    return LaunchPlan("new_tab", files)


class Pane(Enum):
    LEFT = "left"
    RIGHT = "right"


class WindowModel:
    def __init__(self, start_empty=True, id_allocator=None):
        self._id_allocator = id_allocator
        self.next_id = 1
        self.order = []
        self.left_id = None
        self.right_id = None
        self.focused = Pane.LEFT
        self.split = False
        if start_empty:
            self.add_document()

    def add_document(self) -> int:
        if self._id_allocator is not None:
            doc_id = self._id_allocator()
        else:
            doc_id = self.next_id
            self.next_id += 1
        self.order.append(doc_id)
        if self.left_id is None:
            self.left_id = doc_id
        return doc_id

    def focused_id(self) -> int:
        if self.focused is Pane.RIGHT and self.split and self.right_id is not None:
            return self.right_id
        return self.left_id

    def showing(self, doc_id: int) -> bool:
        if doc_id == self.left_id:
            return True
        return self.split and doc_id == self.right_id

    def visible_ids(self) -> set:
        shown = {self.left_id}
        if self.split and self.right_id is not None:
            shown.add(self.right_id)
        return {doc_id for doc_id in shown if doc_id is not None}

    def _place_in_focused_pane(self, doc_id: int) -> None:
        if self.focused is Pane.RIGHT and self.split:
            self.right_id = doc_id
        else:
            self.left_id = doc_id
            self.focused = Pane.LEFT

    def click_tab(self, doc_id: int) -> None:
        if doc_id not in self.order:
            raise KeyError(doc_id)
        if doc_id == self.left_id:
            self.focused = Pane.LEFT
            return
        if self.split and doc_id == self.right_id:
            self.focused = Pane.RIGHT
            return
        self._place_in_focused_pane(doc_id)

    def cycle_tab(self, backwards: bool) -> None:
        current = self.focused_id()
        index = self.order.index(current)
        step = -1 if backwards else 1
        self.click_tab(self.order[(index + step) % len(self.order)])

    def open_files(self, occupied: bool):
        target = choose_open_target(occupied)
        if target is OpenTarget.FILL:
            return target, self.focused_id()
        doc_id = self.add_document()
        self._place_in_focused_pane(doc_id)
        return target, doc_id

    def new_tab(self) -> int:
        doc_id = self.add_document()
        self._place_in_focused_pane(doc_id)
        return doc_id

    def can_split(self) -> bool:
        return len(self.order) >= 2

    def _other_than(self, doc_id: int) -> int:
        for candidate in self.order:
            if candidate != doc_id:
                return candidate
        raise RuntimeError("no other document")

    def toggle_split(self) -> None:
        if not self.can_split():
            return
        if self.split:
            self.split = False
            self.right_id = None
            self.focused = Pane.LEFT
            return
        current = self.focused_id()
        self.left_id = current
        index = self.order.index(current)
        self.right_id = self.order[(index + 1) % len(self.order)]
        self.split = True
        self.focused = Pane.LEFT

    def drag_tab_to_right(self, doc_id: int) -> None:
        if doc_id not in self.order or not self.can_split():
            return
        if not self.split:
            viewing = self.focused_id()
        else:
            viewing = self.left_id
        if doc_id == viewing:
            viewing = self._other_than(doc_id)
        self.left_id = viewing
        self.right_id = doc_id
        self.split = True
        self.focused = Pane.LEFT

    def focus_other_pane(self) -> None:
        if not self.split:
            return
        if self.focused is Pane.LEFT:
            self.focused = Pane.RIGHT
        else:
            self.focused = Pane.LEFT

    def _repair_panes_after_removal(self, removed: int) -> None:
        if self.left_id == removed:
            self.left_id = self.order[0]
        if self.right_id == removed:
            replacement = next((doc_id for doc_id in self.order if doc_id != self.left_id), None)
            if replacement is None:
                self.split = False
                self.right_id = None
                self.focused = Pane.LEFT
            else:
                self.right_id = replacement
        if self.focused is Pane.RIGHT and not self.split:
            self.focused = Pane.LEFT

    def close_document(self, doc_id: int) -> str:
        if doc_id not in self.order:
            raise KeyError(doc_id)
        if len(self.order) == 1:
            self.order.remove(doc_id)
            self.left_id = None
            self.right_id = None
            self.split = False
            self.focused = Pane.LEFT
            self.add_document()
            return "emptied"
        self.order.remove(doc_id)
        self._repair_panes_after_removal(doc_id)
        return "removed"

    def detach(self, doc_id: int):
        if doc_id not in self.order:
            raise KeyError(doc_id)
        self.order.remove(doc_id)
        close_window = len(self.order) == 0
        if close_window:
            self.left_id = None
            self.right_id = None
            self.split = False
            self.focused = Pane.LEFT
        else:
            self._repair_panes_after_removal(doc_id)
        return doc_id, close_window

    def attach(self, doc_id: int) -> None:
        if doc_id in self.order:
            raise ValueError("document already in this window")
        self.order.append(doc_id)
        self.next_id = max(self.next_id, doc_id + 1)
        self._place_in_focused_pane(doc_id)


class PromptChoice(Enum):
    SAVE = "save"
    DISCARD = "discard"
    CANCEL = "cancel"


@dataclass(frozen=True)
class CloseOutcome:
    aborted: bool
    save_ids: list
    discard_ids: list


def prompt_order(focused_id: int, unsaved_ids: list, tab_order: list) -> list:
    unsaved = set(unsaved_ids)
    ordered = [doc_id for doc_id in tab_order if doc_id in unsaved and doc_id != focused_id]
    if focused_id in unsaved:
        return [focused_id] + ordered
    return ordered


def resolve_prompts(order: list, answers: list) -> CloseOutcome:
    if len(order) != len(answers):
        raise ValueError("one answer per document")
    if any(answer is PromptChoice.CANCEL for answer in answers):
        return CloseOutcome(True, [], [])
    save_ids = [doc_id for doc_id, answer in zip(order, answers) if answer is PromptChoice.SAVE]
    discard_ids = [doc_id for doc_id, answer in zip(order, answers) if answer is PromptChoice.DISCARD]
    return CloseOutcome(False, save_ids, discard_ids)


def single_close(answer: PromptChoice) -> str:
    if answer is PromptChoice.SAVE:
        return "save_then_close"
    if answer is PromptChoice.DISCARD:
        return "discard"
    if answer is PromptChoice.CANCEL:
        return "abort"
    raise ValueError(answer)


class DropSite(Enum):
    PANE = "pane"
    TAB = "tab"
    WINDOW = "window"


def drop_target(site: DropSite, pane_doc, tab_doc, focused_id: int) -> int:
    if site is DropSite.PANE:
        if pane_doc is None:
            raise ValueError("pane drop needs a document")
        return pane_doc
    if site is DropSite.TAB:
        if tab_doc is None:
            raise ValueError("tab drop needs a document")
        return tab_doc
    return focused_id


class SaveGate:
    def __init__(self):
        self.busy_id = None

    def can_start(self) -> bool:
        return self.busy_id is None

    def start(self, doc_id: int) -> None:
        if self.busy_id is not None:
            raise RuntimeError("a save is already running")
        self.busy_id = doc_id

    def finish(self) -> None:
        self.busy_id = None


def window_prompt_sequence(windows: list, focused_window_id: int) -> list:
    """windows items are (window_id, focused_id, unsaved_ids, tab_order)."""
    ordered = sorted(windows, key=lambda item: 0 if item[0] == focused_window_id else 1)
    sequence = []
    for window_id, focused_id, unsaved_ids, tab_order in ordered:
        docs = prompt_order(focused_id, unsaved_ids, tab_order)
        if docs:
            sequence.append((window_id, docs))
    return sequence

