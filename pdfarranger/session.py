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
