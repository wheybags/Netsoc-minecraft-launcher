#!/usr/bin/env python

import os
import subprocess
import sys
import platform
import urllib
import zipfile
from threading import Thread
from tempfile import gettempdir

from time import sleep

def iswindows():
	return platform.system() == "Windows"

def islinux():
	return platform.system() == "Linux"

def isosx():
	return platform.system() == "Darwin"


temp = gettempdir()
#csep is a java thing, the seperator used between jar files in the -cp arg
if iswindows():
	sep = "\\"
	csep = ";"
	OS = "windows"
else:
	sep = "/"
	csep = ":"
	if islinux():
		OS = "linux"
	elif isosx():
		OS = "osx"

temp += sep

def getarch():
	if platform.architecture()[0] == "32bit":
		return "i386"
	elif platform.architecture()[0] == "64bit":
		return "amd64"

def getinstallpath():
	if islinux():
		return os.getenv("HOME") + sep + ".mcnetsoc"
	
	elif iswindows():
		return os.path.expanduser("~") + sep + "AppData" + sep + "Roaming" + sep + ".mcnetsoc"
	
	elif isosx():
		return os.getenv("HOME") + sep + "Library" + sep + "Application Support" + sep + "mcnetsoc"

def getcommand(username):
	cmd = ""

	# If on linux, set LD_LIBRARY_PATH
	# This is not always necessary, but sometimes is
	if islinux():
		p = subprocess.Popen(['which', 'java'], stdout=subprocess.PIPE)
		output = p.stdout.read()[:-1]
		p = subprocess.Popen(['readlink', '-f', output], stdout=subprocess.PIPE)
		output = p.stdout.read()[:-1]
		
		if output is not None:
			path = "%s%sjre%slib%s%s" % (output[:-9], sep, sep, sep, getarch())
			if os.path.exists(path):
				cmd += "LD_LIBRARY_PATH=\"%s\" " % path
		java = "java"

	elif iswindows():
		p = subprocess.Popen(['cmd', '/C', 'ftype', 'jarfile'], stdout=subprocess.PIPE)
		output = p.stdout.read()
		java = "\"" + output.split("\"")[1] + "\""
	
	elif isosx():
		java = "java"                
		
	cmd += "%s -Xms1G -Xmx1G -cp \"%s%sbin%s*%s.\" " % (java, getinstallpath(), sep, sep, csep) # set classpath
	
	if iswindows():
		# Windows java doesn't like quotes in this parameter :S
		# This only matters if you have a username with a space in it, which is batshit insane anyway
		cmd += "-Djava.library.path=%s%sbin%snatives%s " % (getinstallpath(), sep, sep, sep) # set library path
	else:
		# Osx needs quuotes because of Application Data
		cmd += "-Djava.library.path=\"%s%sbin%snatives%s\" " % (getinstallpath(), sep, sep, sep)

	cmd += "net.minecraft.client.Minecraft \"%s\"" % username
	return cmd

#-1 means not installed, or invalid version file
def getinstalledver():
	path = getinstallpath() + sep + "mcnetsocversion.txt"
	if not os.path.exists(path):
		return -1
	else:
		try:
			return int(open(path).read())
		except:
			return -1

def setinstalledver(ver):
	f = open(getinstallpath() + sep + "mcnetsocversion.txt", "w")
	f.write(str(ver))
	f.close()

def getlatestver():
	return int(urllib.urlopen("http://wheybags.netsoc.ie/mcnetsoc/datafiles/version").read())

def updategame(gui):
	latestversion = getlatestver()
	if latestversion > getinstalledver():
		#print "updating..."

		filename = temp + "mcnetsocupdate" + str(os.getpid()) + ".zip"
		print filename

		# Download zip file
		u = urllib.urlopen("http://wheybags.netsoc.ie/mcnetsoc/datafiles/datafiles_" + OS + ".zip")
		size = float(u.info()['Content-Length'])
		print size
		#print "http://wheybags.netsoc.ie/mcnetsoc/datafiles/datafiles_" + OS + ".zip"
		try:
			done = 0.0
			f = open(filename, "wb")
			while True:
				buffer = u.read(8192)
				if not buffer:
					break
				
				f.write(buffer)
				done += len(buffer)
				#print str(int((done / size) * 100)) + "%"
				gui.labelVariable.set("Updating: " + str(int((done / size) * 100)) + "%")
				#sleep(0.01)

			f.close()

			gui.labelVariable.set("Extracting...")
			# Extract
			path = getinstallpath()
			z = zipfile.ZipFile(filename)
			for f in z.namelist():
				print f,
				if f.endswith("/"):
					print " dir"
					try:
						os.makedirs(path + sep + f)
					except:
						pass
				else:		
					print " file"					
					z.extract(f, path=path)

			z.close()
			setinstalledver(latestversion)
			os.remove(filename)
			gui.labelVariable.set("Successfully Updated.")

		except Exception,e:
			print e
			try:
				os.remove(filename)
			except:
				pass
			gui.labelVariable.set("Update Failed!")
	else:
		gui.labelVariable.set("Up to date.")


# Gui code here
# mostly shtolen from http://sebsauvage.net/python/gui/
import Tkinter

class simpleapp_tk(Tkinter.Tk):
	def __init__(self,parent):
		Tkinter.Tk.__init__(self,parent)
		self.parent = parent
		self.initialize()

	def initialize(self):
		self.grid()

		self.entryVariable = Tkinter.StringVar()
		self.entry = Tkinter.Entry(self,textvariable=self.entryVariable)
		self.entry.grid(column=0,row=0,sticky='EW')
		self.entry.bind("<Return>", self.OnPressEnter)
		
		try:
			self.entryVariable.set(str(open(getinstallpath() + sep + "username.txt", "r").read()))
		except:
			self.entryVariable.set(u"Username:")

		button = Tkinter.Button(self,text=u"Launch", command=self.Launch)
		button.grid(column=2,row=0)
		
		self.labelVariable = Tkinter.StringVar()
		label = Tkinter.Label(self,textvariable=self.labelVariable, anchor="w",fg="white",bg="blue")
		label.grid(column=0,row=1,columnspan=2,sticky='EW')
		self.labelVariable.set(u"Hello !")

		self.grid_columnconfigure(0,weight=1)
		self.resizable(True,False)
		self.update()
		self.geometry(self.geometry())	   
		self.entry.focus_set()
		self.entry.selection_range(0, Tkinter.END)
		
		self.updatethread = Thread(target=updategame, args=(self,))
		self.updatethread.start()

	def Launch(self):
		if not self.updatethread.is_alive():
			open(getinstallpath() + sep + "username.txt", "w").write(self.entryVariable.get())
			cmd = getcommand(self.entryVariable.get())
			print cmd
			subprocess.Popen(cmd, shell=True)
	
		#self.labelVariable.set( self.entryVariable.get()+" (You clicked the button)" )
		self.entry.focus_set()
		self.entry.selection_range(0, Tkinter.END)
	
	def OnPressEnter(self,event):
		self.Launch()
		#self.labelVariable.set( self.entryVariable.get()+" (You pressed ENTER)" )
		self.entry.focus_set()
		self.entry.selection_range(0, Tkinter.END)

if __name__ == "__main__":

#	print getinstallpath()
		
	gui = simpleapp_tk(None)
	gui.title('Netsoc Minecraft Launcher')
	gui.geometry("300x50")
	gui.resizable(0,0)
	gui.mainloop()
