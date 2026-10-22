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

from .session import document_occupied


class Document:
    def __init__(self, app, doc_id: int):
        self.app = app
        self.id = doc_id
        self.gtk_window = None
        self.model = None
        self.undomanager = None
        self.iconview = None
        self.sw = None
        self.cellthmb = None
        self.pdfqueue = []
        self.metadata = {}
        self.save_file = None
        self.export_file = None
        self.is_unsaved = False
        self.password = None
        self.zoom_level = None
        self.zoom_level_old = 0
        self.zoom_level_limits = [-10, 80]
        self.zoom_scale = None
        self.zoom_fit = False
        self.fit_one_page = True
        self.find_text = ""
        self.rendering_thread = None
        self.export_process = None
        self.post_action = None
        self.render_id = None
        self.nfile = 0
        self.layer_pos = (0.5, 0.5)
        self.drag_path = None
        self.drag_pos = None
        self.pressed_button = None
        self.click_path = None
        self.scroll_path = None
        self.vadj_percent = None
        self.target_is_intern = True
        self.id_scroll_to_sel = None
        self.iv_auto_scroll_timer = None
        self.set_iv_visible_id = None
        self.end_rubberbanding = False
        self.visible_range = None

    def occupied(self) -> bool:
        return document_occupied(len(self.pdfqueue), len(self.metadata))

    def release_renderer(self) -> None:
        thread = self.rendering_thread
        if thread is not None:
            thread.quit = True

    @property
    def tmp_dir(self):
        return self.app.tmp_dir

    @property
    def import_directory(self):
        return self.app.import_directory

    def set_import_directory(self, value):
        self.app.import_directory = value

    @import_directory.setter
    def import_directory(self, value):
        self.set_import_directory(value)

    @property
    def export_directory(self):
        return self.app.export_directory

    @export_directory.setter
    def export_directory(self, value):
        self.app.export_directory = value

    @property
    def window(self):
        """Dialog parent. PageAdder and PDFDoc already read app.window."""
        return self.gtk_window
