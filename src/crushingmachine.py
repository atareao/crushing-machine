#!/usr/bin/python3
# -*- coding: iso-8859-15 -*-
#
__author__='atareao'
__date__ ='$06-jun-2010 12:34:44$'
#
# <one line to give the program's name and a brief idea of what it does.>
#
# Copyright (C) 2010 Lorenzo Carbonell
# lorenzo.carbonell.cerezo@gmail.com
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
#
#
#
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GObject
from gi.repository import Nautilus
from gi.repository import Unity
import shutil
import time
import sys
import os
import shlex
import locale
import gettext
import subprocess
import functools
import concurrent
import concurrent.futures

NUM_THREADS = 4


try:
	current_locale, encoding = locale.getdefaultlocale()
	language = gettext.translation('crushing-machine', '/usr/share/locale-langpack', [current_locale])
	language.install()
	if sys.version_info[0] == 3:
		_ = language.gettext
	else:
		_ = language.ugettext
except Exception as e:
	print(e)
	_ = str	
LOCAL_LAUNCHER = os.path.join(os.path.expanduser('~'),'.local/share/applications/crushing-machine.desktop')
if not os.path.exists(LOCAL_LAUNCHER):
	shutil.copyfile('/usr/share/applications/crushing-machine.desktop', LOCAL_LAUNCHER)

def wait(time_lapse):
	time_start = time.time()
	time_end = (time_start + time_lapse)
	while time_end > time.time():
		while Gtk.events_pending():
			Gtk.main_iteration()

class SecureDelete(Gtk.Dialog): # needs GTK, Python, Webkit-GTK
	def __init__(self,files = None):
		#***************************************************************
		Gtk.Dialog.__init__(self)
		self.set_position(Gtk.WindowPosition.CENTER_ALWAYS)
		self.set_size_request(600, 400)
		self.set_position(Gtk.WindowPosition.CENTER)
		self.connect('destroy', self.on_close_dialog)
		self.set_icon_from_file('/usr/share/icons/gnome/256x256/actions/crushing-machine.png')
		#
		vbox0 = Gtk.VBox(spacing = 5)
		vbox0.set_border_width(5)
		self.get_content_area().add(vbox0)
		#
		frame2 = Gtk.Frame()
		vbox0.pack_start(frame2,True,True,0)
		#
		hbox21 = Gtk.HBox(spacing = 5)
		hbox21.set_border_width(5)
		frame2.add(hbox21)
		#
		button20 = Gtk.Button()
		button20.set_image(Gtk.Image.new_from_stock(Gtk.STOCK_DIRECTORY,Gtk.IconSize.BUTTON))
		button20.set_size_request(32,32)
		button20.set_tooltip_text(_('Load files'))
		button20.connect('clicked',self.on_button_load_clicked)
		hbox21.pack_start(button20,False,False,0)			
		#
		self.label = Gtk.Label()
		hbox21.pack_start(self.label,False,False,0)
		#
		button2 = Gtk.Button()
		button2.set_image(Gtk.Image.new_from_stock(Gtk.STOCK_EXECUTE,Gtk.IconSize.BUTTON))
		button2.set_size_request(32,32)
		button2.set_tooltip_text(_('Secure Delete'))
		button2.connect('clicked',self.on_button_secure_delete_clicked)
		hbox21.pack_end(button2,False,False,0)	
		#
		button3 = Gtk.Button()
		button3.set_image(Gtk.Image.new_from_stock(Gtk.STOCK_STOP,Gtk.IconSize.BUTTON))
		button3.set_size_request(32,32)
		button3.set_tooltip_text(_('Stop deletion'))
		button3.connect('clicked',self.on_button_stop_deletion_clicked)
		hbox21.pack_end(button3,False,False,0)	
		#
		frame3 = Gtk.Frame()
		vbox0.pack_start(frame3,True,True,0)
		#
		scrolledwindow = Gtk.ScrolledWindow()
		scrolledwindow.set_size_request(600,300)
		scrolledwindow.set_border_width(2)
		frame3.add(scrolledwindow)
		self.treeview = Gtk.TreeView()
		scrolledwindow.add(self.treeview)
		#
		model = Gtk.ListStore(str)
		self.treeview.set_model(model)
		#
		column = Gtk.TreeViewColumn(_('To Secure Delete'),Gtk.CellRendererText(),text=0)
		self.treeview.append_column(column)		
		#
		self.file_dir = os.getenv('HOME')
		self.show_all()
		#
		self.launcher = Unity.LauncherEntry.get_for_desktop_id("crushing-machine.desktop")
		#
		for afile in files:
			model.append([afile])

	def on_button_load_clicked(self,widget):
		dialog = Gtk.FileChooserDialog(_('Select one or more files to secure delete'),
										self,
									   Gtk.FileChooserAction.OPEN,
									   (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
										Gtk.STOCK_OPEN, Gtk.ResponseType.OK))
		dialog.set_default_response(Gtk.ResponseType.OK)
		dialog.set_select_multiple(True)
		dialog.set_current_folder(self.file_dir)
		filter = Gtk.FileFilter()
		filter.set_name(_('All files'))
		filter.add_pattern('*.*')
		dialog.add_filter(filter)
		response = dialog.run()
		if response == Gtk.ResponseType.OK:
			filenames = dialog.get_filenames()
			if len(filenames)>0:
				model = self.treeview.get_model()
				#model.clear()
				for filename in filenames:
					if os.path.isfile(filename) and not self.is_file_in_model(filename):
						#head,tail = os.path.split(filename)
						model.append([filename])	
				self.file_dir = os.path.dirname(filenames[0])
				if len(self.file_dir)<=0 or os.path.exists(self.file_dir)==False:
					self.file_dir = os.getenv('HOME')									
		dialog.destroy()
		
	def on_close_dialog(self,widget):
		self.hide()
		self.destroy()

	def set_wait_cursor(self):
		self.get_root_window().set_cursor(Gdk.Cursor(Gdk.CursorType.WATCH))					
		while Gtk.events_pending():
			Gtk.main_iteration()		
	def set_normal_cursor(self):
		self.get_root_window().set_cursor(Gdk.Cursor(Gdk.CursorType.ARROW))			
		while Gtk.events_pending():
			Gtk.main_iteration()		
		
	def on_button_secure_delete_clicked(self,widget):
		self.set_wait_cursor()
		model = self.treeview.get_model()
		total=len(model)
		#			
		self.launcher.set_property("count", total)
		self.launcher.set_property("count_visible", True)
		self.launcher.set_property("progress", 0.0)
		self.launcher.set_property("progress_visible", True)		
		with concurrent.futures.ProcessPoolExecutor(max_workers=NUM_THREADS) as executor:
			self.stop = False
			for row in model:
				afile = row[0]
				cmd = 'srm -r'
				print(_('Crushing')+' %s'%afile)
				if len(afile)>50:
					num = len(afile)-47
					text = '...'+afile[num:]
				else:
					text = afile				
				future = executor.submit(ejecuta,cmd,[afile])
				future.add_done_callback(functools.partial(self.callback,total,text,row.iter))
				if self.stop:
					break
		self.label.set_text('')
		self.launcher.set_property("count_visible", False)
		self.launcher.set_property("progress_visible", False)
		self.set_normal_cursor()

	def callback(self,total,text,aiter,job):
		model = self.treeview.get_model()
		max_value=len(model)
		model.remove(aiter)
		self.label.set_text(_('Crushing')+' %s'%text)
		self.launcher.set_property("count", total-(max_value-1))
		self.launcher.set_property("progress", float(total-(max_value-1))/float(total))
		while Gtk.events_pending():
			Gtk.main_iteration()
		print(job.result())
		
	def on_button_stop_deletion_clicked(self,widget):
		self.stop = True

	def is_file_in_model(self,afile):		
		model = self.treeview.get_model()
		for row in model:
			if row[0] == afile:
				return True
		return False

def ejecuta(comando,afile=None):
	args = shlex.split(comando)
	if afile!=None:
		args.extend(afile)
	p = subprocess.Popen(args, bufsize=10000, stdout=subprocess.PIPE)
	valor = p.communicate()[0]
	return valor
	
def get_files_to_secure_delete(files):
	files_to_secure_delete = []
	for afile in files:
		if not os.path.isdir(afile):
			if afile not in files_to_secure_delete:
				files_to_secure_delete.append(afile)
	return files_to_secure_delete

class SecureDeleteMenuProvider(GObject.GObject, Nautilus.MenuProvider):
	"""Implements the 'rename-me' extension to the nautilus right-click menu"""
	def __init__(self):
		"""Nautilus crashes if a plugin doesn't implement the __init__ method"""
		pass

	def securedelete_files(self, menu, selected):		
		"""Runs the Replace in Filenames on the given Directory"""
		files = []
		for afile in selected:
			afile = afile.get_uri()[7:]
			if os.path.isfile(afile) and afile not in files:
				files.append(afile)
		dialog = SecureDelete(files)
		dialog.run()
		dialog.hide()
		dialog.destroy()
	
	def get_file_items(self, window, sel_items):
		"""Adds the 'Replace in Filenames' menu item to the Nautilus right-click menu,
		   connects its 'activate' signal to the 'run' method passing the selected Directory/File"""
		#if len(sel_items) != 1 or sel_items[0].get_uri_scheme() not in ['file', 'smb']: return
		item = Nautilus.MenuItem(name='SecureDeleteMenuProvider::Gtk-secure-delete-files',
								 label=_('Secure delete files'),
								 tip=_('Secure delete files'),
								 icon='Gtk-find-and-replace')
		item.connect('activate', self.securedelete_files, sel_items)
		return item,
		
	
if __name__ == '__main__':
	if len(sys.argv) < 2:
		print(_('At least one file to trash'))
		files = []
	else:
		files=sys.argv[1:]	
	sd = SecureDelete(files)
	sd.run()	
	exit(0)
