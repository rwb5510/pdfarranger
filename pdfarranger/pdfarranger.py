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
    try:
        libintl = ctypes.cdll[get_libintl_path()]
        libintl.bindtextdomain(DOMAIN.encode(), localedir.encode(sys.getfilesystemencoding()))
        libintl.bind_textdomain_codeset(DOMAIN.encode(), 'UTF-8'.encode())
        del libintl
    except (FileNotFoundError, AttributeError, OSError):
        pass

APPNAME = 'PDF Arranger'
VERSION = '1.14.0'
WEBSITE = 'https://github.com/pdfarranger/pdfarranger'

if os.name == 'nt':
    from winreg import HKEY_CURRENT_USER, QueryValueEx, OpenKey
    # Add support for dnd to other instance and insert file at drop location in Windows
    os.environ['GDK_WIN32_USE_EXPERIMENTAL_OLE2_DND'] = 'true'
    # Use client side decorations. Will also enable window moving with Win + left/right
    os.environ['GTK_CSD'] = '1'

try:
    import gi
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
    from gi.repository import GObject
    from gi.repository import Gio
    from gi.repository import GLib
    from gi.repository import Pango
    GTK_VERSION = "{}.{}.{}".format(
        Gtk.get_major_version(), Gtk.get_minor_version(), Gtk.get_micro_version())
except (ImportError, ValueError):
    gi = None
    Gtk = None
    Handy = None
    Gdk = None
    GObject = None
    Gio = None
    GLib = None
    Pango = None
    GTK_VERSION = "0.0.0"

try:
    from .config import Config
except (ImportError, ValueError):
    Config = None

try:
    from .core import Dims, Sides, _img_to_pdf, IMG2PDF_VERSION, POPPLER_VERSION
except (ImportError, ValueError):
    Dims = None
    Sides = None
    _img_to_pdf = None
    IMG2PDF_VERSION = "0.0.0"
    POPPLER_VERSION = "0.0.0"

PIKEPDF_VERSION = pikepdf.__version__
LIBQPDF_VERSION = pikepdf.__libqpdf_version__
# GTK_VERSION set above
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
    lang = Config(DOMAIN).language() if Config else None
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

from .session import plan_launch
from .document import Document
from .window import ArrangerWindow
from .win32ipc import Win32Handoff, gtk_unique_is_enough

try:
    from . import undo
    from . import exporter
    from . import metadata
    from . import pageutils
    from . import splitter
    from .search import SearchBarWidget
    from .iconview import CellRendererImage, IconviewCursor, IconviewDragSelect, IconviewPanView
    from .core import img2pdf_supported_img, PageAdder, PDFDocError, PDFRenderer
    if 'image/png' in img2pdf_supported_img and 'image/jpeg' in img2pdf_supported_img:
        from .image_exporter import ImageExporter
    else:
        ImageExporter = None
    if GObject and CellRendererImage:
        GObject.type_register(CellRendererImage)
except (ImportError, ValueError):
    undo = None
    exporter = None
    metadata = None
    pageutils = None
    splitter = None
    SearchBarWidget = None
    CellRendererImage = None
    IconviewCursor = None
    IconviewDragSelect = None
    IconviewPanView = None
    img2pdf_supported_img = []
    PageAdder = None
    PDFDocError = Exception
    PDFRenderer = None
    ImageExporter = None


def _install_workaround_bug29():
    """ Install a workaround for https://gitlab.gnome.org/GNOME/pygobject/issues/29 """
    if not gi or not Gtk:
        return
    try:
        gi.check_version('3.29.2')
    except ValueError:
        def func(self, entries):
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


ApplicationBase = Gtk.Application if Gtk else object

class PdfArranger(ApplicationBase):
    # Drag and drop ID for pages coming from the same pdfarranger instance
    MODEL_ROW_INTERN = 1001
    # Drag and drop ID for pages coming from an other pdfarranger instance
    MODEL_ROW_EXTERN = 1002
    # Drag and drop ID for pages coming from a non-pdfarranger application
    TEXT_URI_LIST = 1003
    TARGETS_IV = [Gtk.TargetEntry.new('MODEL_ROW_INTERN', Gtk.TargetFlags.SAME_WIDGET,
                                      MODEL_ROW_INTERN),
                  Gtk.TargetEntry.new('MODEL_ROW_EXTERN', Gtk.TargetFlags.OTHER_APP,
                                      MODEL_ROW_EXTERN)] if Gtk else []
    TARGETS_SW = [Gtk.TargetEntry.new('text/uri-list', 0, TEXT_URI_LIST),
                  Gtk.TargetEntry.new('MODEL_ROW_EXTERN', Gtk.TargetFlags.OTHER_APP,
                                      MODEL_ROW_EXTERN)] if Gtk else []

    def __init__(self, *args, **kwargs):
        if Gtk:
            flags = Gio.ApplicationFlags.HANDLES_COMMAND_LINE if Gio else 0
            super().__init__(*args, application_id="com.github.jeromerobert.pdfarranger",
                             flags=flags,
                             **kwargs)
        else:
            super().__init__()

        if GLib:
            GLib.set_application_name(APPNAME)
            GLib.set_prgname('com.github.jeromerobert.pdfarranger')

        # Create the temporary directory
        self.tmp_dir = tempfile.mkdtemp(DOMAIN)
        os.chmod(self.tmp_dir, 0o700)

        # Defining instance attributes
        self.config = Config(DOMAIN) if Config else None
        self.windows = []
        self.last_focused_window = None
        self._next_doc_id = 0
        self.handoff = None

        self.export_directory = os.path.expanduser('~')
        self.import_directory = None
        self.nfile = 0
        self.disable_quit = False
        try:
            multiprocessing.set_start_method('spawn')
        except RuntimeError:
            pass
        self.quit_flag = multiprocessing.Event()

        # Clipboard for cut copy paste
        self.clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD) if Gtk else None

        self.add_arguments()

    def allocate_doc_id(self):
        self._next_doc_id += 1
        return self._next_doc_id

    def active_window(self):
        if self.last_focused_window is not None and self.last_focused_window in self.windows:
            return self.last_focused_window
        return self.windows[0] if self.windows else None

    def new_window(self):
        window = ArrangerWindow(self)
        self.windows.append(window)
        window.present()
        return window

    def new_window_for_document(self, document):
        window = ArrangerWindow(self, empty=False)
        self.windows.append(window)
        window.accept_document(document)
        window.present()
        return window

    def document_by_id(self, doc_id: int):
        for window in self.windows:
            if doc_id in window.docs:
                return window.docs[doc_id]
        return None

    def close_window(self, window):
        if window in self.windows:
            self.windows.remove(window)
        if getattr(window, 'window', None) and hasattr(window.window, 'destroy'):
            window.window.destroy()
        if not self.windows:
            self.close_application()

    def get_windows(self):
        if hasattr(super(), 'get_windows'):
            return super().get_windows()
        return self.windows

    def activate(self):
        if hasattr(super(), 'activate'):
            super().activate()
        else:
            self.do_activate()

    def add_arguments(self):
        if not GLib:
            return
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

    def do_activate(self):
        """ https://lazka.github.io/pgi-docs/Gio-2.0/classes/Application.html#Gio.Application.do_activate """
        if self.windows:
            active = self.active_window()
            if active:
                active.present()
            return

        iconsdir = os.path.join(sharedir, 'icons')
        if not os.path.exists(iconsdir):
            iconsdir = os.path.join(sharedir, 'data', 'icons')
        if Gtk:
            Gtk.IconTheme.get_default().append_search_path(iconsdir)

        if hasattr(GLib, "unix_signal_add"):
            GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGINT, self.close_application)

        if GObject:
            GObject.type_register(PDFRenderer)
            GObject.signal_new('update_thumbnail', PDFRenderer, GObject.SignalFlags.RUN_FIRST, None,
                               [GObject.TYPE_PYOBJECT, GObject.TYPE_PYOBJECT, GObject.TYPE_PYOBJECT,
                                GObject.TYPE_PYOBJECT, GObject.TYPE_BOOLEAN])

        if Gtk:
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
            scrolledwindow.focused-pane {
                border-width: 2px;
                border-style: solid;
                border-color: #1c71d8;
            }
            """
            style_provider.load_from_data(bytes(css_data.encode()))
            Gtk.StyleContext.add_provider_for_screen(
                Gdk.Screen.get_default(),
                style_provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        window = self.new_window()
        window.show()

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

        files = []
        remaining = options.lookup_value(GLib.OPTION_REMAINING) if GLib else (options.lookup_value(None) if hasattr(options, 'lookup_value') else None)
        if remaining is not None:
            for item in remaining:
                file_obj = command_line.create_file_for_arg(item)
                path = file_obj.get_path() if hasattr(file_obj, 'get_path') else str(file_obj)
                if path:
                    files.append(path)

        if not gtk_unique_is_enough():
            if Win32Handoff.submit(files):
                return 0
            if self.handoff is None:
                self.handoff = Win32Handoff(lambda fs: self.open_launched_files(True, fs))
                self.handoff.start()

        if not self.get_windows():
            self.activate()

        self.open_launched_files(command_line.get_is_remote(), files)
        return 0

    def open_launched_files(self, remote: bool, files: list) -> None:
        window = self.active_window()
        occupied = window.focused_document().occupied() if (window and window.docs) else False
        plan = plan_launch(remote, files, occupied)
        if plan.action == "raise":
            if window:
                window.present()
            return
        if plan.action == "fill" and not plan.files and not remote:
            if window:
                window.present()
            return
        if window:
            window.open_files(plan.files)
            window.present()

    def add_files(self, files):
        """Add files passed as command line arguments."""
        paths = [f.get_path() if hasattr(f, 'get_path') else str(f) for f in files]
        self.open_launched_files(False, paths)

    def on_quit(self, _action=None, _param=None, _unknown=None):
        if self.disable_quit:
            return Gdk.EVENT_STOP if Gdk else False
        self.close_application()
        return Gdk.EVENT_STOP if Gdk else False

    def close_application(self, _widget=None, _event=None, _data=None):
        """Termination"""
        self.quit_flag.set()
        if self.handoff:
            self.handoff.stop()
            self.handoff = None
        for window in list(self.windows):
            for doc in list(window.docs.values()):
                doc.release_renderer()
                if doc.rendering_thread:
                    doc.rendering_thread.join()
                    doc.rendering_thread.pdfqueue = []
                if doc.export_process:
                    doc.export_process.join(timeout=2)
                    if doc.export_process.is_alive():
                        doc.export_process.terminate()
                        doc.export_process.join()
                if doc.iconview:
                    doc.iconview.unselect_all()
                    if doc.iconview.get_model():
                        doc.iconview.get_model().clear()
                doc.pdfqueue.clear()
        gc.collect()
        active = self.active_window()
        if active and active.window and self.config and self.config.save_window_geometry():
            self.config.set_window_size(active.window.get_size())
            self.config.set_maximized(active.window.is_maximized())
            focused = active.focused_document()
            if focused and focused.zoom_level is not None:
                self.config.set_zoom_level(round(focused.zoom_level))
        if self.config:
            self.config.save()
        if os.path.isdir(self.tmp_dir):
            shutil.rmtree(self.tmp_dir)
        self.quit()






class EncryptionPasswordDialog(Gtk.Dialog if Gtk else object):
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


if __name__ == '__main__':
    main()
