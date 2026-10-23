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

import os
import sys
import gettext
from urllib.request import url2pathname

try:
    import gi
    gi.require_version('Gtk', '3.0')
    from gi.repository import Gtk, Gdk, GObject, GLib, Gio
    try:
        gi.require_version('Handy', '1')
        from gi.repository import Handy
    except ValueError:
        Handy = None
    from .core import img2pdf_supported_img, PageAdder, PDFDocError
    from .search import SearchBarWidget
except (ImportError, ValueError):
    Gtk = None
    Gdk = None
    GObject = None
    GLib = None
    Gio = None
    Handy = None
    img2pdf_supported_img = []
    PageAdder = None
    PDFDocError = Exception
    SearchBarWidget = None

from .session import (
    OpenTarget,
    WindowModel,
    choose_open_target,
    tab_label,
    tab_tooltip,
)
from .document import Document, get_file_path_from_uri

_ = gettext.gettext
DOMAIN = 'pdfarranger'
APPNAME = 'PDF Arranger'
ICON_ID = 'com.github.jeromerobert.' + DOMAIN


def filenames_for_open(filenames: list) -> list:
    filenames = list(filenames)
    if os.name == "nt":
        return list(reversed(filenames))
    return filenames


TAB_MOVE = 1005
TEXT_URI_LIST = 1003
if Gtk is not None:
    TARGETS_TAB = [
        Gtk.TargetEntry.new('application/x-pdfarranger-tab', Gtk.TargetFlags.SAME_APP, TAB_MOVE),
        Gtk.TargetEntry.new('text/uri-list', 0, TEXT_URI_LIST),
    ]
else:
    TARGETS_TAB = []


class ArrangerWindow:
    def __init__(self, app, empty=True):
        self.app = app
        self.empty = empty
        self.docs = {}
        self.tab_widgets = {}
        if app is not None:
            if hasattr(app, 'allocate_doc_id'):
                id_allocator = app.allocate_doc_id
            else:
                if not hasattr(app, '_next_doc_id'):
                    app._next_doc_id = 0
                def _allocator():
                    app._next_doc_id += 1
                    return app._next_doc_id
                id_allocator = _allocator
        else:
            id_allocator = None
        self.model = WindowModel(start_empty=empty, id_allocator=id_allocator)
        self.window = None
        self._dragging_tab = False
        self.header_bar = None
        self.status_bar = None
        self.status_bar2 = None
        self.main_box = None
        self.tab_strip = None
        self.tab_strip_box = None
        self.page_area = None
        self.searchbar_widget = None
        self.main_menu = None
        self.actions = []
        self.popup = None

        if Gtk is None:
            if empty:
                first_id = self.model.focused_id()
                doc = Document(self.app, first_id)
                doc.host = self
                self.docs[first_id] = doc
            return

        self.__create_main_window()
        self.__create_menus()

        # Wire tab-strip and page-area into main_box
        self.main_box = self.uiXML.get_object('main_box')
        self.header_bar = self.uiXML.get_object('header_bar')
        self.status_bar = self.uiXML.get_object('statusbar')
        self.status_bar2 = self.uiXML.get_object('statusbar2')

        self.tab_strip = Gtk.ScrolledWindow()
        self.tab_strip.set_name("tab-strip")
        self.tab_strip.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.NEVER)
        self.tab_strip_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.tab_strip_box.set_name("tab-strip-box")
        self.tab_strip.add(self.tab_strip_box)
        self.main_box.pack_start(self.tab_strip, False, True, 0)
        self.main_box.reorder_child(self.tab_strip, 0)

        self.tab_strip.drag_dest_set(
            Gtk.DestDefaults.ALL,
            TARGETS_TAB,
            Gdk.DragAction.MOVE
        )
        self.tab_strip.connect("drag-data-received", self._on_tab_strip_drag_data_received)

        self.tab_strip_box.drag_dest_set(
            Gtk.DestDefaults.ALL,
            TARGETS_TAB,
            Gdk.DragAction.MOVE
        )
        self.tab_strip_box.connect("drag-data-received", self._on_tab_strip_drag_data_received)

        ui_sw = self.uiXML.get_object('scrolledwindow')
        if ui_sw:
            self.main_box.remove(ui_sw)

        self.page_area = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.page_area.set_name("page-area")
        self.page_area.drag_dest_set(
            Gtk.DestDefaults.ALL,
            TARGETS_TAB,
            Gdk.DragAction.MOVE
        )
        self.page_area.connect("drag-data-received", self._on_page_area_drag_data_received)
        self.main_box.pack_start(self.page_area, True, True, 0)
        self.main_box.reorder_child(self.page_area, 2)

        # Wire searchbar
        searchbar = self.uiXML.get_object('searchbar')
        args = (self.window, None, [], self._search_show, self._search_clear)
        self.searchbar_widget = SearchBarWidget(*args)
        searchbar.pack_start(self.searchbar_widget, True, True, 0)

        # Setup main window settings
        self.set_title(APPNAME)
        self.window.set_border_width(0)
        self.window.set_application(self.app)
        if hasattr(self.app, 'config') and self.app.config:
            if self.app.config.maximized():
                self.window.maximize()
            self.window.set_default_size(*self.app.config.window_size())
        self.window.connect('delete_event', self.on_delete_event)
        self.window.connect('focus_in_event', self.window_focus_in_out_event)
        self.window.connect('focus_out_event', self.window_focus_in_out_event)
        self.window.connect('configure_event', self.window_configure_event)
        self.window.connect('key_press_event', self.window_key_press_event)

        self.__create_actions()

        if empty:
            # First document
            first_id = self.model.focused_id()
            doc = Document(self.app, first_id)
            doc.host = self
            doc.gtk_window = self.window
            doc.build_view()
            self.docs[first_id] = doc
            self._create_tab_widget(doc)

            self.refresh_document(doc)
            self.show_model()

    @property
    def gtk_window(self):
        return self.window

    def __resource_path(self, path):
        if hasattr(self.app, '_PdfArranger__resource_path'):
            return self.app._PdfArranger__resource_path(path)
        return path

    def __create_main_window(self):
        b = Gtk.Builder()
        b.set_translation_domain(DOMAIN)
        with open(self.__resource_path("pdfarranger.ui"), encoding="utf-8") as ff:
            s = ff.read()
            if Handy:
                Handy.init()
                s = s.replace("GtkHeaderBar", "HdyHeaderBar")
            b.add_from_string(s)
        self.uiXML = b
        self.window = self.uiXML.get_object('main_window')
        if Handy:
            if hasattr(self.app, 'set_color_scheme'):
                self.app.set_color_scheme()
            box = Gtk.Box()
            box.props.orientation = Gtk.Orientation.VERTICAL
            hd = self.uiXML.get_object("header_bar")
            mb = self.uiXML.get_object("main_box")
            self.window.remove(hd)
            self.window.remove(mb)
            self.window = Handy.ApplicationWindow()
            box.add(hd)
            mb.props.expand = True
            box.add(mb)
            self.window.add(box)
        self.window.set_default_icon_name(ICON_ID)

    def __create_menus(self):
        b = Gtk.Builder()
        b.set_translation_domain(DOMAIN)
        b.add_from_file(self.__resource_path("menu.ui"))
        if hasattr(self.app, 'config') and self.app.config:
            self.app.config.set_actions(b)
        main_menu = b.get_object('main_menu')
        self.uiXML.get_object("main_menu_button").set_menu_model(main_menu)
        self.popup = Gtk.Menu.new_from_model(b.get_object('popup_menu'))
        self.popup.attach_to_widget(self.window, None)

    def _create_tab_widget(self, doc):
        if Gtk is None:
            return
        tab_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        tab_box.set_name(f"tab-{doc.id}")

        event_box = Gtk.EventBox()
        label = Gtk.Label()
        label.set_name("pdfarranger-tab-label")
        event_box.add(label)

        event_box.drag_source_set(
            Gdk.ModifierType.BUTTON1_MASK,
            TARGETS_TAB,
            Gdk.DragAction.MOVE
        )
        event_box.connect("drag-begin", self._on_tab_drag_begin, doc.id)
        event_box.connect("drag-data-get", self._on_tab_drag_data_get, doc.id)
        event_box.connect("drag-failed", self._on_tab_drag_failed, doc.id)
        event_box.connect("drag-end", self._on_tab_drag_end, doc.id)

        event_box.connect("button-press-event", lambda _w, _e, d_id=doc.id: self._on_tab_button_press(d_id, _e))
        event_box.connect("button-release-event", lambda _w, _e, d_id=doc.id: self._on_tab_button_release(d_id, _e))
        tab_box.pack_start(event_box, True, True, 4)

        tab_box.drag_dest_set(
            Gtk.DestDefaults.ALL,
            TARGETS_TAB,
            Gdk.DragAction.MOVE | Gdk.DragAction.COPY
        )
        tab_box.connect("drag-data-received", self._on_tab_box_drag_data_received, doc.id)

        event_box.drag_dest_set(
            Gtk.DestDefaults.ALL,
            TARGETS_TAB,
            Gdk.DragAction.MOVE | Gdk.DragAction.COPY
        )
        event_box.connect("drag-data-received", self._on_tab_box_drag_data_received, doc.id)

        close_btn = Gtk.Button.new_with_label("×")
        close_btn.set_relief(Gtk.ReliefStyle.NONE)
        close_btn.connect("clicked", lambda _w, d_id=doc.id: self.close_document(d_id))
        tab_box.pack_start(close_btn, False, False, 0)

        tab_box.show_all()
        self.tab_widgets[doc.id] = (label, tab_box)
        self._attach_doc_view(doc)

    def _attach_doc_view(self, doc):
        if Gtk is None or getattr(doc, '_pane_click_connected', False):
            return
        doc._pane_click_connected = True
        if hasattr(doc, 'iconview') and doc.iconview:
            doc.iconview.connect('button-press-event', lambda _w, _e, d_id=doc.id: self._on_pane_click(d_id, _e))
        if hasattr(doc, 'sw') and doc.sw:
            doc.sw.connect('button-press-event', lambda _w, _e, d_id=doc.id: self._on_pane_click(d_id, _e))

    def _on_pane_click(self, doc_id, event):
        if self.model.split and self.model.focused_id() != doc_id:
            self.model.click_tab(doc_id)
            self.show_model()
        return Gdk.EVENT_PROPAGATE

    def _on_tab_button_press(self, doc_id, event):
        return Gdk.EVENT_PROPAGATE

    def _on_tab_button_release(self, doc_id, event):
        if event.button == 1:
            if not self._dragging_tab:
                self.model.click_tab(doc_id)
                self.show_model()
                return Gdk.EVENT_STOP
        return Gdk.EVENT_PROPAGATE

    def _on_tab_drag_begin(self, widget, context, doc_id):
        self._dragging_tab = True

    def _on_tab_drag_data_get(self, widget, context, selection_data, info, time, doc_id):
        if info == TAB_MOVE:
            payload = f"{id(self)}:{doc_id}".encode("utf-8")
            selection_data.set(selection_data.get_target(), 8, payload)

    def _on_tab_drag_failed(self, widget, context, result, doc_id):
        self._dragging_tab = False
        if result == Gtk.DragResult.NO_TARGET:
            self.detach_document(doc_id)
            return True
        return False

    def _on_tab_drag_end(self, widget, context, doc_id):
        self._dragging_tab = False

    def _on_tab_box_drag_data_received(self, widget, context, x, y, selection_data, info, time, doc_id):
        target = ""
        if hasattr(selection_data, 'get_target') and selection_data.get_target():
            t = selection_data.get_target()
            target = t.name() if hasattr(t, 'name') else str(t)
        if target == 'text/uri-list' or info == TEXT_URI_LIST:
            uris = selection_data.get_uris()
            if uris:
                paths = [get_file_path_from_uri(u) for u in uris]
                self.import_files(doc_id, paths)
                context.finish(True, False, time)
                return
            context.finish(False, False, time)
            return
        elif info == TAB_MOVE or target == 'application/x-pdfarranger-tab':
            self._on_tab_strip_drag_data_received(widget, context, x, y, selection_data, info, time)

    def _on_tab_strip_drag_data_received(self, widget, context, x, y, selection_data, info, time):
        target = ""
        if hasattr(selection_data, 'get_target') and selection_data.get_target():
            t = selection_data.get_target()
            target = t.name() if hasattr(t, 'name') else str(t)
        if target == 'text/uri-list' or info == TEXT_URI_LIST:
            uris = selection_data.get_uris()
            if uris:
                paths = [get_file_path_from_uri(u) for u in uris]
                focused = self.focused_document()
                if focused:
                    self._add_paths(focused, paths)
                    self.refresh_document(focused)
                    self.show_model()
                context.finish(True, False, time)
                return
            context.finish(False, False, time)
            return

        if info == TAB_MOVE or target == 'application/x-pdfarranger-tab':
            data = selection_data.get_data()
            if not data:
                context.finish(False, False, time)
                return
            try:
                src_win_id_str, doc_id_str = data.decode("utf-8").split(":", 1)
                src_win_id = int(src_win_id_str)
                doc_id = int(doc_id_str)
            except Exception:
                context.finish(False, False, time)
                return

            src_win = next((w for w in getattr(self.app, 'windows', []) if id(w) == src_win_id), None)
            if src_win is None:
                context.finish(False, False, time)
                return

            if src_win == self:
                context.finish(True, False, time)
                self.show_model()
                return

            doc, close_source = src_win.detach_document(doc_id, new_window=False)
            self.accept_document(doc)
            if close_source and hasattr(self.app, 'close_window'):
                self.app.close_window(src_win)
            context.finish(True, False, time)

    def _on_page_area_drag_data_received(self, widget, context, x, y, selection_data, info, time):
        target = ""
        if hasattr(selection_data, 'get_target') and selection_data.get_target():
            t = selection_data.get_target()
            target = t.name() if hasattr(t, 'name') else str(t)
        if target == 'text/uri-list' or info == TEXT_URI_LIST:
            uris = selection_data.get_uris()
            if uris:
                paths = [get_file_path_from_uri(u) for u in uris]
                focused = self.focused_document()
                if focused:
                    self._add_paths(focused, paths)
                    self.refresh_document(focused)
                    self.show_model()
                context.finish(True, False, time)
                return
            context.finish(False, False, time)
            return

        if info == TAB_MOVE or target == 'application/x-pdfarranger-tab':
            alloc = self.page_area.get_allocation()
            half_width = alloc.width / 2.0
            if x > half_width:
                data = selection_data.get_data()
                if not data:
                    context.finish(False, False, time)
                    return
                try:
                    src_win_id_str, doc_id_str = data.decode("utf-8").split(":", 1)
                    src_win_id = int(src_win_id_str)
                    doc_id = int(doc_id_str)
                except Exception:
                    context.finish(False, False, time)
                    return

                src_win = next((w for w in getattr(self.app, 'windows', []) if id(w) == src_win_id), None)
                if src_win is None:
                    context.finish(False, False, time)
                    return

                if src_win != self:
                    doc, close_source = src_win.detach_document(doc_id, new_window=False)
                    self.accept_document(doc)
                    if close_source and hasattr(self.app, 'close_window'):
                        self.app.close_window(src_win)
                    doc_id = doc.id

                self.model.drag_tab_to_right(doc_id)
                self.show_model()
                context.finish(True, False, time)
            else:
                self._on_tab_strip_drag_data_received(widget, context, x, y, selection_data, info, time)

    def focused_document(self) -> Document:
        return self.docs.get(self.model.focused_id())

    def present(self):
        if self.window:
            self.window.present()

    def show(self):
        if self.window:
            self.window.show_all()

    def set_title(self, title, subtitle=None):
        if hasattr(self, 'header_bar') and self.header_bar:
            self.header_bar.set_title(title)
            self.header_bar.set_subtitle(subtitle)
        elif hasattr(self, 'window') and self.window and hasattr(self.window, 'set_title'):
            self.window.set_title(title)

    def retitle(self):
        doc = self.focused_document()
        if not doc:
            return
        subtitle = None
        if doc.save_file:
            subtitle, title = os.path.split(doc.save_file)
        else:
            title = _('untitled')
        if doc.is_unsaved:
            title += '*'

        all_files = set(os.path.splitext(d.basename)[0] for d in doc.pdfqueue)
        all_files.discard('')
        if len(all_files) > 0:
            title += ' [' + ', '.join(sorted(all_files)) + ']'

        title += ' – ' + APPNAME
        self.set_title(title, subtitle)

    def refresh_document(self, document):
        if document.id in self.tab_widgets:
            label_widget, tab_box = self.tab_widgets[document.id]
            first_basename = document.pdfqueue[0].basename if document.pdfqueue else None
            first_path = document.pdfqueue[0].filename if document.pdfqueue else None
            save_base = os.path.basename(document.save_file) if document.save_file else None

            lbl = tab_label(save_base, first_basename)
            if document.is_unsaved:
                lbl = lbl + "*"
            label_widget.set_text(lbl)
            tab_box.set_tooltip_text(tab_tooltip(document.save_file, first_path))

        if document == self.focused_document():
            self.retitle()

        if self.window:
            act_split = self.window.lookup_action('side-by-side')
            if act_split:
                act_split.set_enabled(self.model.can_split())
            act_focus = self.window.lookup_action('focus-other-pane')
            if act_focus:
                act_focus.set_enabled(self.model.split)

    def set_split_from_model(self):
        if Gtk is None or self.page_area is None:
            return

        def _detach(w):
            if w is not None and hasattr(w, 'get_parent'):
                parent = w.get_parent()
                if parent is not None:
                    parent.remove(w)

        for child in list(self.page_area.get_children()):
            if isinstance(child, Gtk.Paned):
                _detach(child.get_child1())
                _detach(child.get_child2())
            self.page_area.remove(child)

        left_doc = self.docs.get(self.model.left_id)
        right_doc = self.docs.get(self.model.right_id) if self.model.right_id is not None else None

        if self.model.split and left_doc and left_doc.sw and right_doc and right_doc.sw:
            paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
            _detach(left_doc.sw)
            _detach(right_doc.sw)
            paned.pack1(left_doc.sw, resize=True, shrink=False)
            paned.pack2(right_doc.sw, resize=True, shrink=False)
            self.page_area.pack_start(paned, True, True, 0)
            paned.show_all()
        else:
            if left_doc and left_doc.sw:
                _detach(left_doc.sw)
                self.page_area.pack_start(left_doc.sw, True, True, 0)
                left_doc.sw.show_all()

        focused_id = self.model.focused_id()
        for doc_id, doc in self.docs.items():
            if doc and hasattr(doc, 'sw') and doc.sw:
                style_ctx = doc.sw.get_style_context()
                if self.model.split and doc_id == focused_id:
                    if not style_ctx.has_class("focused-pane"):
                        style_ctx.add_class("focused-pane")
                else:
                    if style_ctx.has_class("focused-pane"):
                        style_ctx.remove_class("focused-pane")

    def show_model(self):
        if Gtk is None:
            return
        # Sync tab order in tab_strip_box
        for child in self.tab_strip_box.get_children():
            self.tab_strip_box.remove(child)
        for doc_id in self.model.order:
            if doc_id in self.tab_widgets:
                _lbl, tab_box = self.tab_widgets[doc_id]
                self.tab_strip_box.pack_start(tab_box, False, False, 2)
        self.tab_strip_box.show_all()

        # Update page area and split view
        self.set_split_from_model()

        if self.window:
            act_split = self.window.lookup_action('side-by-side')
            if act_split:
                act_split.set_enabled(self.model.can_split())
            act_focus = self.window.lookup_action('focus-other-pane')
            if act_focus:
                act_focus.set_enabled(self.model.split)

        visible_ids = set(self.model.visible_ids())
        for doc_id, doc in self.docs.items():
            if doc_id not in visible_ids:
                doc.release_renderer()
            else:
                if len(doc.model) > 0:
                    doc.silent_render()

        focused = self.focused_document()
        if focused:
            self.retitle()
            if focused.undomanager and self.window:
                focused.undomanager.set_actions(
                    self.window.lookup_action('undo'),
                    self.window.lookup_action('redo')
                )
            if hasattr(self, 'searchbar_widget') and self.searchbar_widget:
                self.searchbar_widget.iconview = focused.iconview
                self.searchbar_widget.pdfqueue = focused.pdfqueue
            focused.update_statusbar()
            focused.iv_selection_changed()

    def new_tab(self):
        doc_id = self.model.new_tab()
        doc = Document(self.app, doc_id)
        doc.host = self
        doc.gtk_window = self.window
        doc.build_view()
        self.docs[doc_id] = doc
        self._create_tab_widget(doc)
        self.refresh_document(doc)
        self.show_model()

    def close_document(self, doc_id: int):
        doc = self.docs.get(doc_id)
        outcome = self.model.close_document(doc_id)
        if outcome == "emptied":
            new_id = self.model.focused_id()
            if doc:
                doc.release_renderer()
            new_doc = Document(self.app, new_id)
            new_doc.host = self
            new_doc.gtk_window = self.window
            new_doc.build_view()
            self.docs.clear()
            self.tab_widgets.clear()
            self.docs[new_id] = new_doc
            self._create_tab_widget(new_doc)
            self.refresh_document(new_doc)
        else:
            if doc:
                doc.release_renderer()
                del self.docs[doc_id]
            if doc_id in self.tab_widgets:
                _lbl, tab_box = self.tab_widgets.pop(doc_id)
                if tab_box.get_parent():
                    tab_box.get_parent().remove(tab_box)
        self.show_model()

    def detach_document(self, doc_id: int, new_window: bool = True):
        document = self.docs.pop(doc_id)
        if hasattr(document, 'sw') and document.sw and document.sw.get_parent():
            document.sw.get_parent().remove(document.sw)
        if hasattr(document, 'sw') and document.sw:
            style_ctx = document.sw.get_style_context()
            if style_ctx.has_class("focused-pane"):
                style_ctx.remove_class("focused-pane")
        if doc_id in self.tab_widgets:
            _lbl, tab_box = self.tab_widgets.pop(doc_id)
            if tab_box.get_parent():
                tab_box.get_parent().remove(tab_box)
        _doc_id, close_window = self.model.detach(doc_id)
        if new_window:
            other = self.app.new_window_for_document(document)
            document.gtk_window = other.window
            document.host = other
            if close_window:
                if hasattr(self.app, 'close_window'):
                    self.app.close_window(self)
            else:
                self.show_model()
            return None
        else:
            if not close_window:
                self.show_model()
            return document, close_window

    def accept_document(self, document: Document) -> None:
        self.model.attach(document.id)
        if hasattr(self.app, '_next_doc_id'):
            self.app._next_doc_id = max(self.app._next_doc_id, document.id)
        self.docs[document.id] = document
        document.host = self
        document.gtk_window = self.window
        self._create_tab_widget(document)
        self.refresh_document(document)
        self.show_model()

    def _add_paths(self, receiver: Document, paths: list) -> bool:
        if PageAdder is None or receiver is None:
            return False
        adder = PageAdder(receiver)
        any_added = False
        load_password = (len(receiver.pdfqueue) == 0) and receiver.password is None
        for p in paths:
            filepath = p.get_path() if hasattr(p, 'get_path') else str(p)
            if filepath.startswith("file:"):
                filepath = get_file_path_from_uri(filepath)
            added = adder.addpages(filepath)
            if not added:
                break
            any_added = True
        if any_added:
            adder.commit(select_added=False, add_to_undomanager=True)
            if load_password:
                receiver.set_password_from_input_files()
        return any_added

    def import_files(self, doc_id: int, paths: list) -> bool:
        doc = self.docs.get(doc_id)
        if doc is None:
            return False
        cleaned = [get_file_path_from_uri(p) if str(p).startswith("file:") else (p.get_path() if hasattr(p, 'get_path') else str(p)) for p in paths]
        added = self._add_paths(doc, cleaned)
        if added:
            self.refresh_document(doc)
            self.show_model()
        return added

    def open_files(self, paths: list):
        paths = filenames_for_open(paths)
        focused = self.focused_document()
        target = choose_open_target(focused.occupied())
        if target is OpenTarget.NEW_TAB:
            receiver = Document(self.app, 0)
            receiver.host = self
            receiver.gtk_window = self.window
            receiver.build_view()
        else:
            receiver = focused
        added = self._add_paths(receiver, paths)
        if target is OpenTarget.NEW_TAB and not added:
            receiver.release_renderer()
            return
        if target is OpenTarget.NEW_TAB:
            _target, doc_id = self.model.open_files(True)
            receiver.id = doc_id
            self.docs[doc_id] = receiver
            self._create_tab_widget(receiver)
        self.refresh_document(receiver)
        self.show_model()

    def _forward(self, method_name, *args):
        doc = self.focused_document()
        if doc and hasattr(doc, method_name):
            return getattr(doc, method_name)(*args)

    def __create_actions(self):
        self.actions = [
            ('rotate', lambda a, p, u: self._forward('rotate_page_action', a, p, u), 'i'),
            ('delete', lambda a, p, u: self._forward('on_action_delete', a, p, u)),
            ('duplicate', lambda a, p, u: self._forward('duplicate', a, p, u)),
            ('page-size', lambda a, p, u: self._forward('page_size_dialog', a, p, u)),
            ('crop', lambda a, p, u: self._forward('crop_dialog', a, p, u)),
            ('hide', lambda a, p, u: self._forward('hide_dialog', a, p, u)),
            ('crop-white-borders', lambda a, p, u: self._forward('crop_white_borders', a, p, u)),
            ('export-selection', lambda a, p, u: self._forward('choose_export_selection_pdf_name', a, p, u), 'i'),
            ('export-all', lambda a, p, u: self._forward('on_action_export_all', a, p, u)),
            ('reverse-order', lambda a, p, u: self._forward('reverse_order', a, p, u)),
            ('swap-odd-even', lambda a, p, u: self._forward('swap_odd_even', a, p, u)),
            ('save', lambda a, p, u: self._forward('save_or_choose')),
            ('save-as', lambda a, p, u: self._forward('choose_export_pdf_name', 'ALL_TO_SINGLE')),
            ('new', self.on_action_new),
            ('new-tab', self.on_action_new_tab),
            ('open', self.on_action_open),
            ('import', self.on_action_import),
            ('zoom-in', lambda a, p, u: self._forward('on_action_zoom_in', a, p, u)),
            ('zoom-out', lambda a, p, u: self._forward('on_action_zoom_out', a, p, u)),
            ('zoom-fit', lambda a, p, u: self._forward('on_action_zoom_fit', a, p, u), 'i'),
            ('fullscreen', self.on_action_fullscreen),
            ('side-by-side', self.on_action_side_by_side),
            ('focus-other-pane', self.on_action_focus_other_pane),
            ('close', self.on_action_close),
            ('quit', lambda a, p, u: self.app.on_quit(a, p, u)),
            ('undo', lambda a, p, u: self.focused_document().undomanager.undo()),
            ('redo', lambda a, p, u: self.focused_document().undomanager.redo()),
            ('split', lambda a, p, u: self._forward('split_pages', a, p, u)),
            ('merge', lambda a, p, u: self._forward('merge_pages', a, p, u)),
            ('metadata', lambda a, p, u: self._forward('edit_metadata', a, p, u)),
            ('cut', lambda a, p, u: self._forward('on_action_cut', a, p, u)),
            ('copy', lambda a, p, u: self._forward('on_action_copy', a, p, u)),
            ('explode-images', lambda a, p, u: self._forward('on_action_explode_into_images', a, p, u)),
            ('extract', lambda a, p, u: self._forward('on_action_extract', a, p, u), 'i'),
            ('paste', lambda a, p, u: self._forward('on_action_paste', a, p, u), 'i'),
            ('select', lambda a, p, u: self._forward('on_action_select', a, p, u), 'i'),
            ('select-same-file', lambda a, p, u: self._forward('on_action_select', a, p, u), 'i'),
            ('select-same-format', lambda a, p, u: self._forward('on_action_select', a, p, u), 'i'),
            ('about', self.about_dialog),
            ("insert-blank-page", lambda a, p, u: self._forward('insert_blank_page', a, p, u)),
            ("generate-booklet", lambda a, p, u: self._forward('generate_booklet', a, p, u)),
            ("split-booklet", lambda a, p, u: self._forward('split_booklet', a, p, u)),
            ("preferences", self.on_action_preferences),
            ("print", lambda a, p, u: self._forward('on_action_print', a, p, u)),
            ("find", self.searchbar_widget.find),
            ("find_prev", self.searchbar_widget.find_prev),
            ("find_next", self.searchbar_widget.find_next),
            ("find_all", self.searchbar_widget.find_all)
        ]
        self.window.add_action_entries(self.actions)

        password_toggle = Gio.SimpleAction.new_stateful("password-setup", None, GLib.Variant.new_boolean(False))
        password_toggle.connect("change-state", lambda act, val: self._forward('password_setup', act, val, None))
        self.window.add_action(password_toggle)

        self.main_menu = self.uiXML.get_object("main_menu_button")
        self.window.add_action(Gio.PropertyAction.new("main-menu", self.main_menu, "active"))
        for a, k in self.app.config.get_accels():
            self.app.set_accels_for_action("win." + a, [k] if isinstance(k, str) else k)

        doc = self.focused_document()
        if doc and doc.undomanager:
            doc.undomanager.set_actions(self.window.lookup_action('undo'),
                                        self.window.lookup_action('redo'))
        self.searchbar_widget.enable_actions()

    def on_action_new(self, _action=None, _param=None, _unknown=None):
        if hasattr(self.app, 'new_window'):
            self.app.new_window()

    def on_action_new_tab(self, _action=None, _param=None, _unknown=None):
        self.new_tab()

    def open_dialog(self, title=_('Open…')):
        chooser = Gtk.FileChooserNative.new(title=title,
                                            parent=self.window,
                                            action=Gtk.FileChooserAction.OPEN,
                                            accept_label=_("_Open"),
                                            cancel_label=_("_Cancel"))
        if self.app.import_directory is not None:
            chooser.set_current_folder(self.app.import_directory)
        chooser.set_select_multiple(True)
        file_type_list = ['all', 'pdf']
        if len(img2pdf_supported_img) > 0:
            file_type_list = ['all', 'img2pdf', 'pdf']
        filter_list = Document._Document__create_filters(file_type_list)
        for f in filter_list:
            chooser.add_filter(f)

        return chooser.run(), chooser

    def on_action_open(self, _action=None, _param=None, _unknown=None):
        response, chooser = self.open_dialog(_('Open…'))
        if response == Gtk.ResponseType.ACCEPT:
            filenames = chooser.get_filenames()
            self.open_files(filenames)
        chooser.destroy()

    def on_action_import(self, _action=None, _param=None, _unknown=None):
        response, chooser = self.open_dialog(_('Import…'))
        if response == Gtk.ResponseType.ACCEPT:
            filenames = chooser.get_filenames()
            focused = self.focused_document()
            if focused:
                self._add_paths(focused, filenames_for_open(filenames))
                self.refresh_document(focused)
                self.show_model()
        chooser.destroy()

    def on_action_close(self, _action=None, _param=None, _unknown=None):
        focused = self.focused_document()
        if focused:
            self.close_document(focused.id)

    def on_action_fullscreen(self, _action, _param, _unknown):
        is_fullscreen = self.window.get_window().get_state() & Gdk.WindowState.FULLSCREEN
        if is_fullscreen:
            self.window.unfullscreen()
        else:
            self.window.fullscreen()

    def on_action_side_by_side(self, _action=None, _param=None, _unknown=None):
        self.model.toggle_split()
        self.show_model()

    def on_action_focus_other_pane(self, _action=None, _param=None, _unknown=None):
        self.model.focus_other_pane()
        self.show_model()

    def on_action_preferences(self, _action, _option, _unknown):
        handy_available = True if Handy else False
        self.app.config.preferences_dialog(self.window, handy_available)
        self.app.set_color_scheme()

    def about_dialog(self, _action, _param, _unknown):
        about_dialog = Gtk.AboutDialog(
            transient_for=self.window,
            modal=True,
            program_name=APPNAME,
            version=getattr(self.app, 'VERSION', '1.14.0'),
            comments=_(
                "PDF Arranger is a small python-gtk application, which helps the "
                "user to merge or split pdf documents and rotate, crop and rearrange "
                "their pages using an interactive and intuitive graphical interface. "
                "It is a frontend for pikepdf."
            )
        )
        about_dialog.set_authors(['Konstantinos Poulios'])
        about_dialog.add_credit_section(_('Maintainers and contributors'), [
            'https://github.com/pdfarranger/pdfarranger/graphs/contributors'])
        about_dialog.set_website('https://github.com/pdfarranger/pdfarranger')
        about_dialog.set_website_label('https://github.com/pdfarranger/pdfarranger')
        about_dialog.set_logo_icon_name(ICON_ID)
        about_dialog.set_license(_('GNU General Public License (GPL) Version 3.'))
        about_dialog.connect('response', lambda w, *args: w.destroy())
        about_dialog.connect('delete_event', lambda w, *args: w.destroy())
        about_dialog.show_all()

    def error_message_dialog(self, msg):
        if Gtk is None or not self.window:
            return
        error_msg_dlg = Gtk.MessageDialog(flags=Gtk.DialogFlags.MODAL,
                                          type=Gtk.MessageType.ERROR, parent=self.window,
                                          message_format=str(msg),
                                          buttons=Gtk.ButtonsType.OK)
        response = error_msg_dlg.run()
        if response == Gtk.ResponseType.OK:
            error_msg_dlg.destroy()

    def confirm_dialog(self, msg, action):
        if Gtk is None or not self.window:
            return False
        d = Gtk.MessageDialog(self.window, 0, Gtk.MessageType.WARNING, Gtk.ButtonsType.NONE, msg)
        d.add_buttons(action, 1, _('_Cancel'), 2)
        response = d.run()
        d.destroy()
        return response == 1

    def set_status(self, doc, left_text, right_text=""):
        if doc == self.focused_document() and self.status_bar:
            ctxt_id = self.status_bar.get_context_id("selected_pages")
            self.status_bar.push(ctxt_id, left_text)

    def on_delete_event(self, _widget, _event):
        return self.app.on_quit(_widget, _event)

    def window_focus_in_out_event(self, _widget=None, _event=None):
        if hasattr(self.app, 'last_focused_window'):
            self.app.last_focused_window = self
        doc = self.focused_document()
        text = self.app.clipboard.wait_is_text_available() if self.app.clipboard else False
        image = len(img2pdf_supported_img) > 0 and (self.app.clipboard.wait_is_image_available() if self.app.clipboard else False)
        if self.window and self.window.lookup_action("paste"):
            if doc and doc.sw and doc.sw.is_sensitive():
                self.window.lookup_action("paste").set_enabled(text or image)

    def window_configure_event(self, _window, event):
        doc = self.focused_document()
        if not doc:
            return
        if hasattr(self, 'window_width_old') and self.window_width_old not in [0, event.width] and len(doc.model) > 0:
            if doc.set_iv_visible_id:
                GObject.source_remove(doc.set_iv_visible_id)
            doc.set_iv_visible_id = GObject.timeout_add(500, doc.set_iconview_visible)
            doc.iconview.set_visible(False)
        self.window_width_old = event.width
        if len(doc.model) > 1:
            doc.silent_render()

    def window_key_press_event(self, window, event):
        if event.state & Gdk.ModifierType.CONTROL_MASK:
            if event.keyval in (Gdk.KEY_ISO_Left_Tab, Gdk.KEY_Tab):
                shift = bool(event.state & Gdk.ModifierType.SHIFT_MASK) or event.keyval == Gdk.KEY_ISO_Left_Tab
                self.model.cycle_tab(shift)
                self.show_model()
                return Gdk.EVENT_STOP
        if hasattr(self, 'searchbar_widget') and self.searchbar_widget:
            handled = self.searchbar_widget.handle_event(event)
            if handled:
                return Gdk.EVENT_STOP
        return Gdk.EVENT_PROPAGATE

    def _search_show(self, npage, rectangles):
        doc = self.focused_document()
        if doc:
            doc.show_find_results(npage, rectangles)

    def _search_clear(self):
        doc = self.focused_document()
        if doc:
            doc.clear_find_results()
