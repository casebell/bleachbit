# vim: ts=4:sw=4:expandtab
# -*- coding: UTF-8 -*-


# BleachBit
# Copyright (C) 2008-2019 Andrew Ziem
# https://www.bleachbit.org
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


"""
GUI for making chaff
"""

from __future__ import absolute_import

from bleachbit import _
from bleachbit.Chaff import download_models, generate_emails, DEFAULT_CONTENT_MODEL_PATH, DEFAULT_SUBJECT_MODEL_PATH

from gi.repository import Gtk, GLib
import logging
import os


logger = logging.getLogger(__name__)


def make_files_thread(email_count, content_model_path, subject_model_path, email_output_folder, delete_when_finished, on_progress):
    generated_file_names = generate_emails(email_count, content_model_path,
                                           subject_model_path, email_output_folder, on_progress=on_progress)
    if delete_when_finished:
        on_progress(0, msg=_('Deleting files'))
        for i in range(0, email_count):
            os.unlink(generated_file_names[i])
            on_progress(1.0 * (i+1)/email_count)
    on_progress(1.0, is_done=True)


class ChaffDialog(Gtk.Dialog):

    """Present the dialog to make chaff"""

    def __init__(self, parent):
        self.content_model_path = DEFAULT_CONTENT_MODEL_PATH
        self.subject_model_path = DEFAULT_SUBJECT_MODEL_PATH

        self._make_dialog(parent)

    def _make_dialog(self, parent):
        """Make the main dialog"""
        Gtk.Dialog.__init__(self, _("Make chaff"), parent)
        self.set_border_width(5)
        box = self.get_content_area()

        label = Gtk.Label(
            _("Make randomly-generated messages derived from Hillary Clinton's emails."))
        box.add(label)

        spin_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        spin_box.add(Gtk.Label(_("Number of files")))
        adjustment = Gtk.Adjustment(100, 1, 99999, 1, 1000, 0)
        self.file_count = Gtk.SpinButton(adjustment=adjustment)
        spin_box.add(self.file_count)
        box.add(spin_box)

        folder_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        folder_box.add(Gtk.Label(_("Select destination folder")))
        self.choose_folder_button = Gtk.FileChooserButton()
        self.choose_folder_button.set_action(
            Gtk.FileChooserAction.SELECT_FOLDER)
        import tempfile
        self.choose_folder_button.set_filename(tempfile.gettempdir())
        folder_box.add(self.choose_folder_button)
        box.add(folder_box)

        delete_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        delete_box.add(Gtk.Label(_("When finished")))
        self.when_finished_combo = Gtk.ComboBoxText()
        self.combo_options = (
            _('Delete without shredding'), _('Do not delete'))
        for combo_option in self.combo_options:
            self.when_finished_combo.append_text(combo_option)
        self.when_finished_combo.set_active(0)  # Set default
        delete_box.add(self.when_finished_combo)
        box.add(delete_box)

        self.progressbar = Gtk.ProgressBar()
        box.add(self.progressbar)
        self.progressbar.hide()

        self.make_button = Gtk.Button(_("Make files"))
        self.make_button.connect('clicked', self.on_make_files)
        box.add(self.make_button)

    def download_models_gui(self):
        """Download models and return whether successful as boolean"""
        def on_download_error(msg, msg2):
            dialog = Gtk.MessageDialog(self, 0, Gtk.MessageType.ERROR,
                                       Gtk.ButtonsType.CANCEL, msg)
            dialog.format_secondary_text(msg2)
            dialog.run()
            dialog.destroy()
        return download_models(on_error=on_download_error)

    def download_models_dialog(self):
        """Download models"""
        dialog = Gtk.MessageDialog(self, 0, Gtk.MessageType.QUESTION,
                                   Gtk.ButtonsType.OK_CANCEL, _("Download data needed for email generator?"))
        response = dialog.run()
        ret = None
        if response == Gtk.ResponseType.OK:
            # User wants to download
            ret = self.download_models_gui()  # True if successful
        elif response == Gtk.ResponseType.CANCEL:
            ret = False
        dialog.destroy()
        return ret

    def on_make_files(self, widget):
        """Callback for make files button"""
        email_count = self.file_count.get_value_as_int()
        email_output_folder = self.choose_folder_button.get_filename()
        delete_when_finished = self.when_finished_combo.get_active() == 0
        if not email_output_folder:
            dialog = Gtk.MessageDialog(self, 0, Gtk.MessageType.ERROR,
                                       Gtk.ButtonsType.CANCEL, _("Select destination folder"))
            dialog.run()
            dialog.destroy()
            return
        from bleachbit import options_dir
        if not os.path.exists(self.content_model_path) or not os.path.exists(self.subject_model_path):
            if not self.download_models_dialog():
                return

        def _on_progress(fraction, msg, is_done):
            """Update progress bar from GLib main loop"""
            if msg:
                self.progressbar.set_text(msg)
            self.progressbar.set_fraction(fraction)
            if is_done:
                self.progressbar.hide()
                self.make_button.set_sensitive(True)

        def on_progress(fraction, msg=None, is_done=False):
            """Callback for progress bar"""
            # Use idle_add() because threads cannot make GDK calls.
            GLib.idle_add(_on_progress, fraction, msg, is_done)

        msg = _('Generating emails')
        logger.info(msg)
        self.progressbar.show()
        self.progressbar.set_text(msg)
        self.progressbar.set_show_text(True)
        self.progressbar.set_fraction(0.0)
        self.make_button.set_sensitive(False)
        import threading
        t = threading.Thread(target=make_files_thread, args=(email_count, self.content_model_path,
                                                             self.subject_model_path, email_output_folder, delete_when_finished, on_progress))
        t.start()

    def run(self):
        """Run the dialog"""
        self.show_all()