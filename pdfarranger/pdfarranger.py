# Copyright (C) 2008-2017 Konstantinos Poulios, 2018-2019 Jerome Robert
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
import platform
import ctypes

if os.name == 'nt':
    try:
        ctypes.windll.kernel32.SetDefaultDllDirectories(0x1000)
    except AttributeError:
        # Windows too old KB2533623
        pass

import shutil  # for file operations like whole directory deletion
import sys  # for processing of command line args
import tempfile
import signal
import mimetypes
import multiprocessing
import locale  # for multilanguage support
import gettext
import gc
import subprocess
import pikepdf
import hashlib
from urllib.request import url2pathname
from functools import lru_cache
from math import log


sharedir = os.path.join(sys.prefix, 'share')
basedir = '.'
if getattr(sys, 'frozen', False):
    multiprocessing.freeze_support()
    basedir = os.path.dirname(sys.executable)
    sharedir = os.path.join(basedir, 'share')
elif sys.argv[0]:
    execdir = os.path.dirname(os.path.realpath(sys.argv[0]))
    basedir = os.path.dirname(execdir)
    sharedir = os.path.join(basedir, 'share')
    if not os.path.exists(sharedir):
        sharedir = basedir
localedir = os.path.join(sharedir, 'locale')
if not os.path.exists(localedir):
    # Assume we are in development mode
    localedir = os.path.join(basedir, 'build', 'mo')

try:
    locale.setlocale(locale.LC_ALL, '')
except locale.Error:
    pass  # Gtk already prints a warning

DOMAIN = 'pdfarranger'
ICON_ID = 'com.github.jeromerobert.' + DOMAIN

def get_libintl_path():
    if os.name == 'nt':
        return 'libintl-8'
    if platform.system() == 'Darwin':
        return 'libintl.8.dylib'
    return 'libintl.so.8'

if hasattr(locale, 'bindtextdomain'):
    # glibc
    locale.bindtextdomain(DOMAIN, localedir)
    # https://docs.gtk.org/glib/i18n.html
    locale.bind_textdomain_codeset(DOMAIN, 'UTF-8')
else:
    libintl = ctypes.cdll[get_libintl_path()]
    libintl.bindtextdomain(DOMAIN.encode(), localedir.encode(sys.getfilesystemencoding()))
    libintl.bind_textdomain_codeset(DOMAIN.encode(), 'UTF-8'.encode())
    del libintl

APPNAME = 'PDF Arranger'
VERSION = '1.14.0'
WEBSITE = 'https://github.com/pdfarranger/pdfarranger'

if os.name == 'nt':
    from winreg import HKEY_CURRENT_USER, QueryValueEx, OpenKey
    # Add support for dnd to other instance and insert file at drop location in Windows
    os.environ['GDK_WIN32_USE_EXPERIMENTAL_OLE2_DND'] = 'true'
    # Use client side decorations. Will also enable window moving with Win + left/right
    os.environ['GTK_CSD'] = '1'

import gi

# check that we don't need GObject.threads_init()
gi.check_version('3.10.2')
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
try:
    gi.require_version('Handy', '1')
    from gi.repository import Handy
except ValueError:
    Handy = None

if Gtk.check_version(3, 20, 0):
    raise Exception('You do not have the required version of GTK+ installed. ' +
                    'Installed GTK+ version is ' +
                    '.'.join([str(Gtk.get_major_version()),
                              str(Gtk.get_minor_version()),
                              str(Gtk.get_micro_version())]) +
                    '. Required GTK+ version is 3.20 or higher.')

from gi.repository import Gdk
from gi.repository import GObject  # for using custom signals
from gi.repository import Gio  # for inquiring mime types information
from gi.repository import GLib
from gi.repository import Pango

from .config import Config
from .core import Dims, Sides, _img_to_pdf, IMG2PDF_VERSION, POPPLER_VERSION

PIKEPDF_VERSION = pikepdf.__version__
LIBQPDF_VERSION = pikepdf.__libqpdf_version__
GTK_VERSION = "{}.{}.{}".format(
    Gtk.get_major_version(), Gtk.get_minor_version(), Gtk.get_micro_version())
PYTHON_VERSION = "{}.{}.{}".format(
    sys.version_info.major, sys.version_info.minor, sys.version_info.micro)

def check_gtk_schema_exists():
    # subprocess.run() would slow down the start of the application, so we only check it on Darwin
    #   See https://github.com/pdfarranger/pdfarranger/pull/1045#issuecomment-1970287378
    if platform.system() != 'Darwin':
        return True
    try:
        schemas = subprocess.run(["gsettings", "list-recursively"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            check=True,
            text=True)
        return 'org.gtk.Settings.ColorChooser' in schemas.stdout
    except FileNotFoundError as e:
        print(e)
        print('ERROR: gsettings failed. Please check GTK depencencies.')
        return False

if not check_gtk_schema_exists():
    print('ERROR: Found no schema files. You may need to set GSETTINGS_SCHEMA_DIR.', file=sys.stderr)

def _set_language_locale():
    lang = Config(DOMAIN).language()
    if os.name == 'nt':
        if not lang:
            winlang = ctypes.windll.kernel32.GetUserDefaultUILanguage()
            lang = locale.windows_locale[winlang]
        os.environ['LANG'] = lang
    elif lang:
        if locale.getlocale(locale.LC_MESSAGES)[0] is None and lang != 'en':
            print('LC_MESSAGES = "C" or not valid. Translations may not work properly.')
        os.environ['LANGUAGE'] = lang


_set_language_locale()

gettext.bindtextdomain(DOMAIN, localedir)
gettext.textdomain(DOMAIN)
_ = gettext.gettext

from . import undo
from . import exporter
from . import metadata
from . import pageutils
from . import splitter
from .search import SearchBarWidget
from .iconview import CellRendererImage, IconviewCursor, IconviewDragSelect, IconviewPanView
from .document import Document
from .core import img2pdf_supported_img, PageAdder, PDFDocError, PDFRenderer
if 'image/png' in img2pdf_supported_img and 'image/jpeg' in img2pdf_supported_img:
    from .image_exporter import ImageExporter
else:
    ImageExporter = None
GObject.type_register(CellRendererImage)


def _install_workaround_bug29():
    """ Install a workaround for https://gitlab.gnome.org/GNOME/pygobject/issues/29 """
    try:
        gi.check_version('3.29.2')
    except ValueError:
        def func(self, entries):
            # simplified version of https://gitlab.gnome.org/GNOME/pygobject/commit/d0b219c
            for d in entries:
                param_type = None if len(d) < 3 else GLib.VariantType.new(d[2])
                action = Gio.SimpleAction(name=d[0], parameter_type=param_type)
                action.connect("activate", d[1], None)
                self.add_action(action)

        Gtk.ApplicationWindow.add_action_entries = func


_install_workaround_bug29()


def malloc_trim():
    """Release free memory from the heap."""
    if os.name == 'nt':
        return
    mtrim = malloc_trim_available()
    if mtrim:
        mtrim()


@lru_cache()
def malloc_trim_available():
    try:
        ctypes.CDLL('libc.so.6').malloc_trim(0)
    except (FileNotFoundError, AttributeError, OSError):
        print('malloc_trim not available. Application may not release memory properly.')
        return None
    def mtrim():
        ctypes.CDLL('libc.so.6').malloc_trim(0)
    return mtrim


def get_file_path_from_uri(uri):
    """Extracts the path from an uri"""
    uri = uri[5:]  # remove 'file:'
    path = url2pathname(uri)  # escape special chars
    path = path.strip('\r\n\x00\x2F')  # remove \r\n and NULL and \
    if os.name == 'posix':
        path = '/' + path
    return path


@staticmethod
def is_ctrl_pressed():
    """Read if control key is pressed on Windows"""
    VK_CONTROL = 0x11
    return bool(ctypes.windll.user32.GetAsyncKeyState(VK_CONTROL) & 0x8000)


class PdfArranger(Gtk.Application):
    # Drag and drop ID for pages coming from the same pdfarranger instance
    MODEL_ROW_INTERN = 1001
    # Drag and drop ID for pages coming from an other pdfarranger instance
    MODEL_ROW_EXTERN = 1002
    # Drag and drop ID for pages coming from a non-pdfarranger application
    TEXT_URI_LIST = 1003
    TARGETS_IV = [Gtk.TargetEntry.new('MODEL_ROW_INTERN', Gtk.TargetFlags.SAME_WIDGET,
                                      MODEL_ROW_INTERN),
                  Gtk.TargetEntry.new('MODEL_ROW_EXTERN', Gtk.TargetFlags.OTHER_APP,
                                      MODEL_ROW_EXTERN)]
    TARGETS_SW = [Gtk.TargetEntry.new('text/uri-list', 0, TEXT_URI_LIST),
                  Gtk.TargetEntry.new('MODEL_ROW_EXTERN', Gtk.TargetFlags.OTHER_APP,
                                      MODEL_ROW_EXTERN)]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, application_id="com.github.jeromerobert.pdfarranger",
                         flags=Gio.ApplicationFlags.NON_UNIQUE |
                            Gio.ApplicationFlags.HANDLES_COMMAND_LINE,
                         **kwargs)

        GLib.set_application_name(APPNAME)
        GLib.set_prgname('com.github.jeromerobert.pdfarranger')

        # Create the temporary directory
        self.tmp_dir = tempfile.mkdtemp(DOMAIN)
        os.chmod(self.tmp_dir, 0o700)

        # Defining instance attributes

        # The None values will be set later in do_activate
        self.config = Config(DOMAIN)
        self.uiXML = None
        self.window = None
        self.sw = None
        self.model = None
        self.undomanager = None
        self.iconview = None
        self.cellthmb = None
        self.status_bar = None
        self.popup = None
        self.is_unsaved = False
        self.zoom_level = None
        self.zoom_level_old = 0
        self.zoom_level_limits = [-10, 80]
        self.zoom_scale = None
        self.zoom_fit = False
        self.fit_one_page = True
        self.render_id = None
        self.id_scroll_to_sel = None
        self.target_is_intern = True

        self.export_directory = os.path.expanduser('~')
        self.import_directory = None
        self.nfile = 0
        self.iv_auto_scroll_timer = None
        self.pdfqueue = []
        self.metadata = {}
        self.pressed_button = None
        self.click_path = None
        self.scroll_path = None
        self.rendering_thread = None
        self.export_process = None
        self.post_action = None
        self.save_file = None
        self.export_file = None
        self.drag_path = None
        self.drag_pos = Gtk.IconViewDropPosition.DROP_RIGHT
        self.window_width_old = 0
        self.set_iv_visible_id = None
        self.vadj_percent = None
        self.end_rubberbanding = False
        self.disable_quit = False
        multiprocessing.set_start_method('spawn')
        self.quit_flag = multiprocessing.Event()
        self.layer_pos = 0.5, 0.5
        self.password = None
        self.password_toggle = None

        # Clipboard for cut copy paste
        self.clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)

        # Construct single document for Task 5
        self.doc = Document(self, 0)
        self.doc.host = self

        self.add_arguments()

    def add_arguments(self):
        self.set_option_context_summary(_(
           "PDF Arranger is a small python-gtk application, which helps the "
           "user to merge or split pdf documents and rotate, crop and rearrange "
           "their pages using an interactive and intuitive graphical interface. "
           "It is a frontend for pikepdf."
        ))

        self.add_main_option(
            "version",
            ord("v"),
            GLib.OptionFlags.NONE,
            GLib.OptionArg.NONE,
            _("Print the version of PDF Arranger and exit"),
            None,
        )
        self.add_main_option(
            GLib.OPTION_REMAINING,
            0,
            GLib.OptionFlags.NONE,
            GLib.OptionArg.STRING_ARRAY,
            _("File(s) to open"),
            "[FILES]",
        )

    @staticmethod
    def __resource_path(path):
        """ Return the path of a resource file """
        # TODO: May be we could use Application.set_resource_base_path and
        # get_menu_by_id in place of that
        # Trying different possible locations
        f = os.path.join(basedir, 'share', DOMAIN, path)
        if not os.path.exists(f):
            f = os.path.join(basedir, 'data', path)
        if not os.path.exists(f):
            f = '/usr/share/{}/{}'.format(DOMAIN, path)
        if not os.path.exists(f):
            f = '/usr/local/share/{}/{}'.format(DOMAIN, path)
        return f

    def set_color_scheme(self):
        if Handy:
            win_dark = False
            if os.name == 'nt':
                # Read from Registry whether Windows use dark theme
                try:
                    key = OpenKey(
                        HKEY_CURRENT_USER,
                        "Software\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize"
                        )
                    win_dark = QueryValueEx(key, "AppsUseLightTheme")[0] == 0
                except FileNotFoundError:
                    # Use light
                    pass
            try:
                scheme = Handy.ColorScheme.PREFER_LIGHT
                if os.name == 'nt' and win_dark:
                    scheme = Handy.ColorScheme.PREFER_DARK
                theme = self.config.theme()
                if theme == 'dark':
                    scheme = Handy.ColorScheme.FORCE_DARK
                elif theme == 'light':
                    scheme = Handy.ColorScheme.FORCE_LIGHT
                Handy.StyleManager.get_default().set_color_scheme(scheme)
            except AttributeError:
                # This libhandy is too old. 1.5.90 needed ?
                pass

    def __create_main_window(self):
        """Create the Gtk.ApplicationWindow or Handy.ApplicationWindow"""
        b = Gtk.Builder()
        b.set_translation_domain(DOMAIN)
        with open(self.__resource_path(DOMAIN + ".ui")) as ff:
            s = ff.read()
            if Handy:
                Handy.init()
                s = s.replace("GtkHeaderBar", "HdyHeaderBar")
            b.add_from_string(s)
        b.connect_signals(self)
        self.uiXML = b
        self.window = self.uiXML.get_object("main_window")
        if Handy:
            self.set_color_scheme()
            # Add an intermediate vertical box
            box = Gtk.Box()
            box.props.orientation = Gtk.Orientation.VERTICAL
            hd = self.uiXML.get_object("header_bar")
            mb = self.uiXML.get_object("main_box")
            self.window.remove(hd)
            self.window.remove(mb)
            # Replace the Gtk.ApplicationWindow by the Handy one
            self.window = Handy.ApplicationWindow()
            box.add(hd)
            mb.props.expand = True
            box.add(mb)
            self.window.add(box)
        self.window.set_default_icon_name(ICON_ID)
        return b

    def __create_menus(self):
        b = Gtk.Builder()
        b.set_translation_domain(DOMAIN)
        b.add_from_file(self.__resource_path("menu.ui"))
        b.connect_signals(self)
        self.config.set_actions(b)
        self.popup = Gtk.Menu.new_from_model(b.get_object("popup_menu"))
        self.popup.attach_to_widget(self.window, None)
        main_menu = self.uiXML.get_object("main_menu_button")
        main_menu.set_menu_model(b.get_object("main_menu"))

    def __create_actions(self):
        # Both Handy.ApplicationWindow and Gtk.Application are Gio.ActionMap. Some action are window
        # related some other are application related. As pdfarrager is a single window app does not
        # matter that much.
        self.actions = [
            ('rotate', self.doc.rotate_page_action, 'i'),
            ('delete', self.doc.on_action_delete),
            ('duplicate', self.doc.duplicate),
            ('page-size', self.doc.page_size_dialog),
            ('crop', self.doc.crop_dialog),
            ('hide', self.doc.hide_dialog),
            ('crop-white-borders', self.doc.crop_white_borders),
            ('export-selection', self.doc.choose_export_selection_pdf_name, 'i'),
            ('export-all', self.doc.on_action_export_all),
            ('reverse-order', self.doc.reverse_order),
            ('swap-odd-even', self.doc.swap_odd_even),
            ('save', self.on_action_save),
            ('save-as', self.on_action_save_as),
            ('new', self.on_action_new),
            ('open', self.on_action_open),
            ('import', self.on_action_import),
            ('zoom-in', self.doc.on_action_zoom_in),
            ('zoom-out', self.doc.on_action_zoom_out),
            ('zoom-fit', self.doc.on_action_zoom_fit, 'i'),
            ('fullscreen', self.on_action_fullscreen),
            ('close', self.on_action_close),
            ('quit', self.on_quit),
            ('undo', self.doc.undomanager.undo),
            ('redo', self.doc.undomanager.redo),
            ('split', self.doc.split_pages),
            ('merge', self.doc.merge_pages),
            ('metadata', self.doc.edit_metadata),
            ('cut', self.doc.on_action_cut),
            ('copy', self.doc.on_action_copy),
            ('explode-images', self.doc.on_action_explode_into_images),
            ('extract', self.doc.on_action_extract, 'i'),
            ('paste', self.doc.on_action_paste, 'i'),
            ('select', self.doc.on_action_select, 'i'),
            ('select-same-file', self.doc.on_action_select, 'i'),
            ('select-same-format', self.doc.on_action_select, 'i'),
            ('about', self.about_dialog),
            ("insert-blank-page", self.doc.insert_blank_page),
            ("generate-booklet", self.doc.generate_booklet),
            ("split-booklet", self.doc.split_booklet),
            ("preferences", self.on_action_preferences),
            ("print", self.doc.on_action_print),
            ("find", self.searchbar_widget.find),
            ("find_prev", self.searchbar_widget.find_prev),
            ("find_next", self.searchbar_widget.find_next),
            ("find_all", self.searchbar_widget.find_all)
        ]
        self.window.add_action_entries(self.actions)

        password_toggle = Gio.SimpleAction.new_stateful("password-setup", None, GLib.Variant.new_boolean(False))
        password_toggle.connect("change-state", self.doc.password_setup)
        self.window.add_action(password_toggle)

        self.main_menu = self.uiXML.get_object("main_menu_button")
        self.window.add_action(Gio.PropertyAction.new("main-menu", self.main_menu, "active"))
        for a, k in self.config.get_accels():
            self.set_accels_for_action("win." + a, [k] if isinstance(k, str) else k)
        # Disable actions
        self.doc.iv_selection_changed()
        self.window_focus_in_out_event()
        self.doc.undomanager.set_actions(self.window.lookup_action('undo'),
                                         self.window.lookup_action('redo'))
        self.searchbar_widget.enable_actions()




    def on_action_preferences(self, _action, _option, _unknown):
        handy_available = True if Handy else False
        self.config.preferences_dialog(self.window, handy_available)
        self.set_color_scheme()


    @staticmethod
    def __create_filters(file_type_list):
        filter_list = []
        f_supported = Gtk.FileFilter()
        f_supported.set_name(_('All supported files'))
        filter_list.append(f_supported)
        if 'pdf' in file_type_list:
            f_pdf = Gtk.FileFilter()
            f_pdf.set_name(_('PDF files'))
            for f in [f_pdf, f_supported]:
                f.add_pattern('*.pdf')
                if os.name != 'nt':
                    f.add_mime_type('application/pdf')
            filter_list.append(f_pdf)
        if 'png' in file_type_list:
            f_png = Gtk.FileFilter()
            f_png.set_name(_('PNG images'))
            for f in [f_png, f_supported]:
                f.add_pattern('*.png')
                if os.name != 'nt':
                    f.add_mime_type('image/png')
            filter_list.append(f_png)
        if 'jpeg' in file_type_list:
            f_jpeg = Gtk.FileFilter()
            f_jpeg.set_name(_('JPEG images'))
            for f in [f_jpeg, f_supported]:
                f.add_pattern('*.jpeg')
                f.add_pattern('*.jpg')
                if os.name != 'nt':
                    f.add_mime_type('image/jpeg')
            filter_list.append(f_jpeg)
        if 'all' in file_type_list:
            f = Gtk.FileFilter()
            f.set_name(_('All files'))
            f.add_pattern('*')
            filter_list.append(f)
        if 'img2pdf' in file_type_list:
            f_img = Gtk.FileFilter()
            f_img.set_name(_('Supported image files'))
            for f in [f_img, f_supported]:
                for mime in img2pdf_supported_img:
                    if os.name != 'nt':
                        f.add_mime_type(mime)
                    for extension in mimetypes.guess_all_extensions(mime, strict=False):
                        f.add_pattern('*' + extension)
            filter_list.append(f_img)
        return filter_list

    def set_title(self, title, subtitle = None):
        self.uiXML.get_object('header_bar').set_title(title)
        self.uiXML.get_object('header_bar').set_subtitle(subtitle)

    def do_activate(self):
        """ https://lazka.github.io/pgi-docs/Gio-2.0/classes/Application.html#Gio.Application.do_activate """
        # TODO: huge method that should be split

        iconsdir = os.path.join(sharedir, 'icons')
        if not os.path.exists(iconsdir):
            iconsdir = os.path.join(sharedir, 'data', 'icons')
        Gtk.IconTheme.get_default().append_search_path(iconsdir)
        self.__create_main_window()
        self.set_title(APPNAME)
        self.window.set_border_width(0)
        self.window.set_application(self)
        if self.config.maximized():
            self.window.maximize()
        self.window.set_default_size(*self.config.window_size())
        self.window.connect('delete_event', self.on_quit)
        self.window.connect('focus_in_event', self.window_focus_in_out_event)
        self.window.connect('focus_out_event', self.window_focus_in_out_event)
        self.window.connect('configure_event', self.window_configure_event)
        self.window.connect('key_press_event', self.window_key_press_event)

        if hasattr(GLib, "unix_signal_add"):
            GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGINT, self.close_application)

        # Initialize Document view for Task 5
        self.doc.gtk_window = self.window
        self.doc.build_view()
        self.sw = self.doc.sw
        self.model = self.doc.model
        self.iconview = self.doc.iconview
        self.undomanager = self.doc.undomanager
        self.cellthmb = self.doc.cellthmb

        ui_sw = self.uiXML.get_object('scrolledwindow')
        if ui_sw:
            parent = ui_sw.get_parent()
            if parent:
                parent.remove(ui_sw)
                parent.pack_start(self.sw, True, True, 0)

        # Status bar to the left
        self.status_bar = self.uiXML.get_object('statusbar')

        # Status bar to the right
        self.status_bar2 = self.uiXML.get_object('statusbar2')

        # Vertical scrollbar handled in Document.build_view

        searchbar = self.uiXML.get_object('searchbar')
        args = (self.window, self.doc.iconview, self.doc.pdfqueue,
                self.doc.show_find_results, self.doc.clear_find_results)
        self.searchbar_widget = SearchBarWidget(*args)
        searchbar.pack_start(self.searchbar_widget, True, True, 0)

        self.window.show_all()

        # Change iconview color background
        style_context_sw = self.sw.get_style_context()
        color_selected = self.iconview.get_style_context() \
            .get_background_color(Gtk.StateFlags.SELECTED)
        color_prelight = color_selected.copy()
        color_prelight.alpha = 0.3
        for state in (Gtk.StateFlags.NORMAL, Gtk.StateFlags.ACTIVE):
            self.iconview.override_background_color(
                state, style_context_sw.get_background_color(state))
        self.iconview.override_background_color(Gtk.StateFlags.SELECTED,
                                                color_selected)
        self.iconview.override_background_color(Gtk.StateFlags.PRELIGHT,
                                                color_prelight)

        # Set cursor look and hide overshoot gradient
        style_provider = Gtk.CssProvider()
        css_data = """
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
        """
        style_provider.load_from_data(bytes(css_data.encode()))
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            style_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        GObject.type_register(PDFRenderer)
        GObject.signal_new('update_thumbnail', PDFRenderer, GObject.SignalFlags.RUN_FIRST, None,
                           [GObject.TYPE_PYOBJECT, GObject.TYPE_PYOBJECT, GObject.TYPE_PYOBJECT,
                            GObject.TYPE_PYOBJECT, GObject.TYPE_BOOLEAN])
        self.doc.set_unsaved(False)
        self.__create_actions()
        self.__create_menus()

        self.doc.set_password(None)

        # iv_cursor created in Document.build_view
        # iv_drag_select created in Document.build_view
        # iv_pan_view created in Document.build_view

        if self.config.content_loss_warning():
            self.doc.content_loss_warning()

    @staticmethod
    def get_os_version():
        """get the OS version"""
        os_type = platform.system()
        if os_type == 'Linux':
            return platform.freedesktop_os_release()["PRETTY_NAME"]
        elif os_type == 'Windows':
            realease, version = platform.win32_ver()[0:2]
            return realease + ' ' + version
        elif os_type == 'Darwin':  # macOS
            return str(platform.mac_ver())
        return str(platform.version())

    @staticmethod
    def get_platform():
        """get the platform"""
        os_type = platform.system()
        try:
            if os_type == 'Linux':
                return platform.freedesktop_os_release()["PRETTY_NAME"]
            elif os_type == 'Windows':
                return platform.platform()
            elif os_type == 'Darwin':
                return platform.platform()
        except Exception:
            # Ignore possible exception(s)
            return 'Unknown (error)'
        return 'Unknown'

    def do_command_line(self, command_line):
        options = command_line.get_options_dict()

        # Print PDF Arranger version and exit
        if options.contains("version"):
            print(APPNAME + "-" + VERSION)
            print("pikepdf-" + PIKEPDF_VERSION)
            print("libqpdf-" + LIBQPDF_VERSION)
            print("img2pdf-" + IMG2PDF_VERSION)
            print("Poppler-" + POPPLER_VERSION)
            print("Gtk-" + GTK_VERSION)
            print("Python-" + PYTHON_VERSION)
            print("OS-" + platform.platform())
            print("OS_Version-" + self.get_os_version())
            return 0

        self.activate()

        if options.lookup_value(GLib.OPTION_REMAINING):
            files = [Gio.File.new_for_commandline_arg(i)
                    for i in options.lookup_value(GLib.OPTION_REMAINING)]

            GObject.idle_add(self.add_files, files)

        return 0

    def add_files(self, files):
        """Add files passed as command line arguments."""
        a = PageAdder(self.doc)
        for f in files:
            p = f.get_path() if hasattr(f, 'get_path') else f
            added = a.addpages(p)
            if not added:
                break

        a.commit(select_added=False, add_to_undomanager=True)
        self.doc.set_password_from_input_files()

    @staticmethod
    def set_text_renderer_cell_height(iconview):
        """Update text renderer cell height on style update.

        Having a fixed height will improve speed.
        Cell height is: "number of rows" * "text height" + 2 * padding
        At start cell will have the height of 1 row + paddings.
        """
        cell_text_renderer = iconview.get_cells()[1]
        cell_text_renderer.set_fixed_size(-1, -1)
        paddy = cell_text_renderer.get_padding()[1]
        natural_height = cell_text_renderer.get_preferred_height(iconview)[1]
        text = cell_text_renderer.props.text
        height = 2 * (natural_height - paddy) if text is None else natural_height
        cell_text_renderer.set_fixed_size(-1, height)







    def window_configure_event(self, _window, event):
        """Handle window size changes."""
        if self.window_width_old not in [0, event.width] and len(self.doc.model) > 0:
            if self.doc.set_iv_visible_id:
                GObject.source_remove(self.doc.set_iv_visible_id)
            self.doc.set_iv_visible_id = GObject.timeout_add(500, self.doc.set_iconview_visible)
            self.doc.iconview.set_visible(False)
        self.window_width_old = event.width
        if len(self.doc.model) > 1: # Don't trigger extra render after first page is inserted
            self.doc.silent_render()




    def retitle(self):
        subtitle = None
        if self.doc.save_file:
            subtitle, title = os.path.split(self.doc.save_file)
        else:
            title = _('untitled')
        if self.doc.is_unsaved:
            title += '*'

        all_files = set(os.path.splitext(doc.basename)[0] for doc in self.doc.pdfqueue)
        all_files.discard('')
        if len(all_files) > 0:
            title += ' [' + ', '.join(sorted(all_files)) + ']'

        title += ' – ' + APPNAME
        self.set_title(title, subtitle)
        return False









    def confirm_dialog(self, msg, action):
        """A dialog for confirmation of an action."""
        d = Gtk.MessageDialog(self.window, 0, Gtk.MessageType.WARNING, Gtk.ButtonsType.NONE, msg)
        d.add_buttons(action, 1, _('_Cancel'), 2)
        response = d.run()
        d.destroy()
        return response == 1

    def save_changes_dialog(self, msg):
        """A dialog which ask if changes should be saved."""
        d = Gtk.MessageDialog(self.window, 0, Gtk.MessageType.WARNING, Gtk.ButtonsType.NONE, msg)
        d.format_secondary_markup(_("Your changes will be lost if you don’t save them."))
        d.add_buttons(_('Do_n’t Save'), 1, _('_Cancel'), 2, _('_Save'), 3)
        response = d.run()
        d.destroy()
        return response

    def on_action_close(self, _action, _param, _unknown):
        """Close all files and restore initial state."""
        if self.is_unsaved:
            if len(self.model) == 0:
                msg = _('Discard changes and close?')
                confirm = self.confirm_dialog(msg, action=_('_Close'))
                if not confirm:
                    return
            else:
                if self.save_file:
                    msg = _('Save changes to “{}” before closing?')
                    msg = msg.format(os.path.basename(self.save_file))
                else:
                    msg = _('Save changes before closing?')
                response = self.save_changes_dialog(msg)
                if response == 3:
                    self.post_action = 'CLEAR_DATA'
                    self.save_or_choose()
                    return
                elif response != 1:
                    return
        self.clear_data()


    def on_quit(self, _action, _param=None, _unknown=None):
        if self.disable_quit:
            return Gdk.EVENT_STOP
        elif self.is_unsaved:
            if len(self.model) == 0:
                msg = _('Discard changes and quit?')
                confirm = self.confirm_dialog(msg, action=_('_Quit'))
                if not confirm:
                    return Gdk.EVENT_STOP
            else:
                if self.save_file:
                    msg = _('Save changes to “{}” before quitting?')
                    msg = msg.format(os.path.basename(self.save_file))
                else:
                    msg = _('Save changes before quitting?')
                response = self.save_changes_dialog(msg)
                if response == 3:
                    self.post_action = 'CLOSE_APPLICATION'
                    self.save_or_choose()
                    return Gdk.EVENT_STOP
                elif response != 1:
                    return Gdk.EVENT_STOP
        self.close_application()
        return Gdk.EVENT_STOP

    def close_application(self, _widget=None, _event=None, _data=None):
        """Termination"""
        self.quit_flag.set()
        if self.rendering_thread:
            self.rendering_thread.quit = True
            self.rendering_thread.join()
            self.rendering_thread.pdfqueue = []

        if self.export_process:
            self.export_process.join(timeout=2)
            if self.export_process.is_alive():
                self.export_process.terminate()
                self.export_process.join()

        # Prevent gtk errors when closing with everything selected
        self.iconview.unselect_all()
        self.iconview.get_model().clear()

        # Release Poppler.Document instances to unlock all temporary files
        self.pdfqueue.clear()
        gc.collect()
        if self.config.save_window_geometry():
            self.config.set_window_size(self.window.get_size())
            self.config.set_maximized(self.window.is_maximized())
            self.config.set_zoom_level(round(self.zoom_level))
        self.config.save()
        if os.path.isdir(self.tmp_dir):
            shutil.rmtree(self.tmp_dir)
        self.quit()

    @staticmethod
    def get_cnt_filename(f, need_cnt=False):
        """Get a filename where the value at end is incremented by 1."""
        shortname, ext = os.path.splitext(f)
        cnt = ""
        for char in reversed(shortname):
            if char.isdigit():
                cnt = char + cnt
            else:
                break
        if cnt != "":
            name_part = shortname[:-len(cnt)]
            cnt_part = str(int(cnt) + 1).zfill(len(cnt))
            f = name_part + cnt_part + ext
        elif need_cnt:
            f = shortname + "-002" + ext
        return f


    def open_dialog(self, title):
        chooser = Gtk.FileChooserNative.new(title=title,
                                        parent=self.window,
                                        action=Gtk.FileChooserAction.OPEN,
                                        accept_label=_("_Open"),
                                        cancel_label=_("_Cancel"))
        if self.import_directory is not None:
            chooser.set_current_folder(self.import_directory)
        chooser.set_select_multiple(True)
        file_type_list = ['all', 'pdf']
        if len(img2pdf_supported_img) > 0:
            file_type_list = ['all', 'img2pdf', 'pdf']
        filter_list = self.__create_filters(file_type_list)
        for f in filter_list:
            chooser.add_filter(f)

        return chooser.run(), chooser

    def on_action_new(self, _action=None, _param=None, _unknown=None, filenames=None):
        """Start a new instance."""
        filenames = filenames or []
        if os.name == 'nt':
            args = [str(sys.executable)]
            for filename in filenames:
                args.append(filename)
            if sys.executable.find('python3.exe') != -1:
                args.insert(1, '-mpdfarranger')
            subprocess.Popen(args)
        else:
            display = Gdk.Display.get_default()
            launch_context = display.get_app_launch_context()
            desktop_file = "%s.desktop"%(self.get_application_id())
            try:
                app_info = Gio.DesktopAppInfo.new(desktop_file)
                launch_files = []
                for filename in filenames:
                    launch_file = Gio.File.new_for_path(filename)
                    launch_files.append(launch_file)
                app_info.launch(launch_files, launch_context)
            except TypeError:
                args = [str(sys.executable), '-mpdfarranger']
                for filename in filenames:
                    args.append(filename)
                subprocess.Popen(args)

    def on_action_open(self, _action, _param, _unknown):
        """Open new file(s)."""
        response, chooser = self.open_dialog(_('Open…'))

        if response == Gtk.ResponseType.ACCEPT:
            if self.doc.occupied():
                self.on_action_new(filenames=chooser.get_filenames())
            else:
                adder = PageAdder(self.doc)
                filenames = chooser.get_filenames()
                filenames = reversed(filenames) if os.name == 'nt' else filenames
                for filename in filenames:
                    added = adder.addpages(filename)
                    if not added:
                        break
                adder.commit(select_added=False, add_to_undomanager=True)
                if self.doc.password is None:
                    self.doc.set_password_from_input_files()

        chooser.destroy()

    def on_action_save(self, _action, _param, _unknown):
        self.doc.save_or_choose()


    def on_action_save_as(self, _action, _param, _unknown):
        self.doc.choose_export_pdf_name('ALL_TO_SINGLE')







    def on_action_import(self, _action, _param, _unknown):
        """Import doc"""
        response, chooser = self.open_dialog(_('Import…'))

        if response == Gtk.ResponseType.ACCEPT:
            adder = PageAdder(self.doc)
            filenames = chooser.get_filenames()
            filenames = reversed(filenames) if os.name == 'nt' else filenames
            load_password = (len(self.doc.pdfqueue) == 0) and self.doc.password is None
            for filename in filenames:
                added = adder.addpages(filename)
                if not added:
                    break
            adder.commit(select_added=False, add_to_undomanager=True)
            # Try to set a password from the input files if no pdf was already opened
            if load_password:
                self.doc.set_password_from_input_files()
        chooser.destroy()






















    @staticmethod
    def process_pending_events():
        while Gtk.events_pending():
            Gtk.main_iteration()

















    def window_focus_in_out_event(self, _widget=None, _event=None):
        """Keyboard focus enter or leave window."""
        # Enable or disable paste actions based on clipboard content
        text = self.clipboard.wait_is_text_available()
        image = len(img2pdf_supported_img) > 0 and self.clipboard.wait_is_image_available()
        if self.window.lookup_action("paste"):  # Prevent error when closing with Alt+F4
            if self.doc.sw and self.doc.sw.is_sensitive():
                self.window.lookup_action("paste").set_enabled(text or image)












    def on_action_fullscreen(self, _action, _param, _unknown):
        """Toggle fullscreen mode."""
        header_bar = self.uiXML.get_object('header_bar')
        if header_bar.get_visible():
            self.window.fullscreen()
            header_bar.hide()
        else:
            self.window.unfullscreen()
            header_bar.show()


























    def about_dialog(self, _action, _parameter, _unknown):
        about_dialog = Gtk.AboutDialog()
        about_dialog.set_transient_for(self.window)
        about_dialog.set_modal(True)
        about_dialog.set_name(APPNAME)
        about_dialog.set_program_name(APPNAME)
        about_dialog.set_version(VERSION)
        about_dialog.set_comments(
            "".join(
                (
                    _("%s is a tool for rearranging and modifying PDF files.")
                    % APPNAME,
                    "\n \n",
                    _("Software versions:") + "\n" +
                    "pikepdf %s, libqpdf %s, img2pdf %s, Poppler %s, GTK %s, Python %s"
                    % (PIKEPDF_VERSION,
                       LIBQPDF_VERSION,
                       IMG2PDF_VERSION,
                       POPPLER_VERSION,
                       GTK_VERSION,
                       PYTHON_VERSION),
                    "\n \n",
                    _("Running on %s") % self.get_platform(),
                )
            )
        )
        about_dialog.set_authors(['Konstantinos Poulios'])
        about_dialog.add_credit_section(_('Maintainers and contributors'), [
            'https://github.com/pdfarranger/pdfarranger/graphs/contributors'])
        about_dialog.set_website(WEBSITE)
        about_dialog.set_website_label(WEBSITE)
        about_dialog.set_logo_icon_name(ICON_ID)
        about_dialog.set_license(_('GNU General Public License (GPL) Version 3.'))
        about_dialog.connect('response', lambda w, *args: w.destroy())
        about_dialog.connect('delete_event', lambda w, *args: w.destroy())
        about_dialog.show_all()

    def update_statusbar(self):
        selection = self.iconview.get_selected_items()
        selected_pages = sorted([p.get_indices()[0] + 1 for p in selection])
        # Compact the representation of the selected page range
        jumps = [[l, r] for l, r in zip(selected_pages, selected_pages[1:])
                    if l + 1 < r]
        ranges = list(selected_pages[0:1] + sum(jumps, []) + selected_pages[-1:])
        display = []
        for lo, hi in zip(ranges[::2], ranges[1::2]):
            range_str = '{}-{}'.format(lo,hi) if lo < hi else '{}'.format(lo)
            display.append(range_str)
        ctxt_id = self.status_bar.get_context_id("selected_pages")
        num_pages = len(self.model)
        msg = _("Selected pages: ") + ", ".join(display) + " / " + str(num_pages)
        if len(selection) == 1:
            model = self.iconview.get_model()
            pagesize = model[selection[0]][0].size_in_points()
            w, h = [x * 25.4 / 72 for x in pagesize]
            msg += f' | {_("Page Size:")} {w:.1f} {_("mm")} \u00D7 {h:.1f} {_("mm")}'
        self.status_bar.push(ctxt_id, msg)

        for a in ["save", "save-as", "select", "export-all", "zoom-fit", "print", "find"]:
            self.window.lookup_action(a).set_enabled(num_pages > 0)

    def error_message_dialog(self, msg):
        error_msg_dlg = Gtk.MessageDialog(flags=Gtk.DialogFlags.MODAL,
                                          type=Gtk.MessageType.ERROR, parent=self.window,
                                          message_format=str(msg),
                                          buttons=Gtk.ButtonsType.OK)
        response = error_msg_dlg.run()
        if response == Gtk.ResponseType.OK:
            error_msg_dlg.destroy()

    def window_key_press_event(self, _window, event):
        handled = self.searchbar_widget.handle_event(event)
        return Gdk.EVENT_STOP if handled else Gdk.EVENT_PROPAGATE






class EncryptionPasswordDialog(Gtk.Dialog):
    def __init__(self, parent, password=None):
        super().__init__(
            title=_("Set Password"),
            parent=parent,
            flags=Gtk.DialogFlags.MODAL,
            buttons=(
                _("_Cancel"),
                Gtk.ResponseType.CANCEL,
                _("_OK"),
                Gtk.ResponseType.OK,
            ),
        )
        self.password = password
        self.set_default_response(Gtk.ResponseType.OK)
        self.entry = Gtk.Entry()
        self.entry.set_visibility(False)
        self.entry.set_activates_default(True)
        self.entry.set_width_chars(30)
        self.vbox.pack_start(self.entry, False, False, 0)
        action_area = self.get_action_area()
        action_area.set_layout(Gtk.ButtonBoxStyle.EXPAND)
        action_area.set_homogeneous(True)
        self.set_resizable(False)

    def get_password(self):
        self.show_all()
        result = self.run()
        text = self.entry.props.text
        self.destroy()
        if result == Gtk.ResponseType.OK:
            return text
        else:
            return self.password

def is_same_page_size(pages):
    p1w, p1h = pages[0].size_in_points()
    for page in pages[1:]:
        pw, ph = page.size_in_points()
        if abs(p1w-pw) > 1e-2 or abs(p1h-ph) > 1e-2:
            return False
    return True

# Sort selection in-place and return page numbers
def sorted_selection_indices(selected_items):
    selected_items.sort(key=lambda x: x.get_indices()[0])
    return [ x.get_indices()[0] for x in selected_items ]

# Checks whether selected pages are contiguous
def is_selection_contiguous(selected_page_numbers):
    return len(selected_page_numbers) == selected_page_numbers[-1] - selected_page_numbers[0] + 1

def main():
    PdfArranger().run(sys.argv)


    def refresh_document(self, doc=None):
        GObject.idle_add(self.retitle)

    def set_status(self, doc, left_text, right_text=""):
        if self.status_bar:
            ctxt_id = self.status_bar.get_context_id("selected_pages")
            self.status_bar.push(ctxt_id, left_text)

    @property
    def model(self):
        return self.doc.model if hasattr(self, 'doc') and self.doc else None

    @model.setter
    def model(self, val):
        if hasattr(self, 'doc') and self.doc:
            self.doc.model = val

    @property
    def iconview(self):
        return self.doc.iconview if hasattr(self, 'doc') and self.doc else None

    @iconview.setter
    def iconview(self, val):
        if hasattr(self, 'doc') and self.doc:
            self.doc.iconview = val

    @property
    def undomanager(self):
        return self.doc.undomanager if hasattr(self, 'doc') and self.doc else None

    @undomanager.setter
    def undomanager(self, val):
        if hasattr(self, 'doc') and self.doc:
            self.doc.undomanager = val

    @property
    def pdfqueue(self):
        return self.doc.pdfqueue if hasattr(self, 'doc') and self.doc else []

    @property
    def metadata(self):
        return self.doc.metadata if hasattr(self, 'doc') and self.doc else {}

    @property
    def save_file(self):
        return self.doc.save_file if hasattr(self, 'doc') and self.doc else None

    @save_file.setter
    def save_file(self, val):
        if hasattr(self, 'doc') and self.doc:
            self.doc.save_file = val

    @property
    def is_unsaved(self):
        return self.doc.is_unsaved if hasattr(self, 'doc') and self.doc else False

    @is_unsaved.setter
    def is_unsaved(self, val):
        if hasattr(self, 'doc') and self.doc:
            self.doc.is_unsaved = val

    def __getattr__(self, name):
        if hasattr(self, 'doc') and self.doc is not None and hasattr(self.doc, name):
            return getattr(self.doc, name)
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")
