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
try:
	from urllib.request import url2pathname
except: 
	from urllib import url2pathname
import shutil
import time
import sys
import os
import shlex
import locale
import gettext
import subprocess
import threading
import queue

NUM_THREADS = 4
GObject.threads_init()

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

class Worker(GObject.GObject,threading.Thread):
	__gsignals__ = {
		'task-done':(GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE,(object,)),
		}
	
	def __init__(self,cua,secureDelete,total):
		threading.Thread.__init__(self)
		GObject.GObject.__init__(self)		
		self.setDaemon(True)
		self.cua = cua
		self.sd = secureDelete
		self.total = total

	def run(self):
		while True:
			afile = self.cua.get()
			if afile is None or self.sd.stop:
				break
			if afile!=None and os.path.exists(afile):
				args = ['srm','-lvr', afile]
				print(_('Crushing')+' %s'%afile)
				subprocess.call(args)
				print(_('Crushed')+' %s'%afile)
			count = self.sd.launcher.get_property("count")-1
			self.sd.launcher.set_property("count",count)
			self.sd.launcher.set_property("progress",(self.total-count)/self.total)
			self.emit('task-done',afile)
			self.cua.task_done()

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
		button20.set_image(Gtk.Image.new_from_stock(Gtk.STOCK_ADD,Gtk.IconSize.BUTTON))
		button20.set_size_request(32,32)
		button20.set_tooltip_text(_('Add files'))
		button20.connect('clicked',self.on_button_load_clicked)
		hbox21.pack_start(button20,False,False,0)			
		#
		button5 = Gtk.Button()
		button5.set_image(Gtk.Image.new_from_stock(Gtk.STOCK_REMOVE,Gtk.IconSize.BUTTON))
		button5.set_size_request(32,32)
		button5.set_tooltip_text(_('Remove selected files'))
		button5.connect('clicked',self.on_button_remove_one_file)
		hbox21.pack_start(button5,False,False,0)	
		#
		button4 = Gtk.Button()
		button4.set_image(Gtk.Image.new_from_stock(Gtk.STOCK_CLOSE,Gtk.IconSize.BUTTON))
		button4.set_size_request(32,32)
		button4.set_tooltip_text(_('Remove all files'))
		button4.connect('clicked',self.on_button_remove_seleccion)
		hbox21.pack_start(button4,False,False,0)	
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
		# set icon for drag operation
		self.treeview.connect('drag-begin', self.drag_begin)
		self.treeview.connect('drag-data-get', self.drag_data_get_data)
		self.treeview.connect('drag-data-received',self.drag_data_received)
		#
		dnd_list = [Gtk.TargetEntry.new('text/uri-list', 0, 100),Gtk.TargetEntry.new('text/plain', 0, 80)]
		self.treeview.drag_source_set(Gdk.ModifierType.BUTTON1_MASK, dnd_list, Gdk.DragAction.COPY)
		self.treeview.drag_source_add_uri_targets()
		dnd_list = Gtk.TargetEntry.new("text/uri-list", 0, 0)
		self.treeview.drag_dest_set(Gtk.DestDefaults.MOTION | Gtk.DestDefaults.HIGHLIGHT | Gtk.DestDefaults.DROP,[dnd_list],Gdk.DragAction.MOVE )
		self.treeview.drag_dest_add_uri_targets()
		
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
			
	def on_button_remove_one_file(self,widget):
		(model, pathlist) = self.treeview.get_selection().get_selected_rows()
		for path in pathlist :
			tree_iter = model.get_iter(path)
			model.remove(tree_iter)
					
	def on_button_remove_seleccion(self,widget):
		model = self.treeview.get_model()
		model.clear()
		
	def drag_begin(self, widget, context):
		pass

	def drag_data_get_data(self, treeview, context, selection, target_id, etime):
		pass

	def drag_data_received(self,widget, drag_context, x, y, selection_data, info, timestamp):
		model = self.treeview.get_model()
		for filename in selection_data.get_uris():
			if len(filename)>8:
				filename = url2pathname(filename)
				filename = filename[7:]
				model.append([filename])
				
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
				for filename in filenames:
					if os.path.isfile(filename) and not self.is_file_in_model(filename):
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
	
	def remove_item(self,worker,afile):
		model = self.treeview.get_model()
		aiter = model.get_iter_first()
		while(aiter is not None):
			if model[aiter][0] == afile:
				model.remove(aiter)
				while Gtk.events_pending():
					Gtk.main_iteration()		
			aiter = model.iter_next(aiter)
	def on_button_secure_delete_clicked(self,widget):
		self.set_wait_cursor()
		self.stop = False
		model = self.treeview.get_model()
		total=len(model)
		#			
		self.launcher.set_property("count", total)
		self.launcher.set_property("count_visible", True)
		self.launcher.set_property("progress", 0.0)
		self.launcher.set_property("progress_visible", True)
		cua = queue.Queue(maxsize=total+2)
		workers = []
		print(1)
		total_workers = total if NUM_THREADS > total else NUM_THREADS
		for i in range(total_workers):
			worker = Worker(cua,self,total)
			worker.connect('task-done',self.remove_item)
			worker.start()
			workers.append(worker)
		print(2)
		for row in model:
			afile = row[0]
			cua.put(afile)
		# block until all tasks are done
		print(3)
		cua.join()
		# stop workers
		print(4)
		for i in range(total_workers):
			cua.put(None)
		for worker in workers:
			worker.join()
			while Gtk.events_pending():
				Gtk.main_iteration()
			
		print(5)
		self.label.set_text('')
		self.launcher.set_property("count_visible", False)
		self.launcher.set_property("progress_visible", False)
		self.set_normal_cursor()

	def on_button_stop_deletion_clicked(self,widget):
		self.stop = True

	def is_file_in_model(self,afile):		
		model = self.treeview.get_model()
		for row in model:
			if row[0] == afile:
				return True
		return False

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
