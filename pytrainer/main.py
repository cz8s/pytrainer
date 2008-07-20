# -*- coding: iso-8859-1 -*-

#Copyright (C) Fiz Vazquez vud1@sindominio.net
# Modified by dgranda

#This program is free software; you can redistribute it and/or
#modify it under the terms of the GNU General Public License
#as published by the Free Software Foundation; either version 2
#of the License, or (at your option) any later version.

#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.

#You should have received a copy of the GNU General Public License
#along with this program; if not, write to the Free Software
#Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.

import locale
import sys
import os
import pygtk
import gobject
pygtk.require('2.0')
import gtk
import gtk.glade
import logging
import traceback

from record import Record
from waypoint import Waypoint
from extension import Extension
from plugins import Plugins
from profile import Profile
from recordgraph import RecordGraph
from daygraph import DayGraph
from monthgraph import MonthGraph
from yeargraph import YearGraph
from heartrategraph import HeartRateGraph

from extensions.googlemaps import Googlemaps
from extensions.waypointeditor import WaypointEditor

#from gui.windowextensions import WindowExtensions
from gui.windowmain import Main
from gui.warning import Warning
from lib.system import checkConf
from lib.date import Date
from lib.gpx import Gpx
from lib.soapUtils import webService
from lib.ddbb import DDBB
from lib.xmlUtils import XMLParser
from lib.system import checkConf
from lib.heartrate import *

# 21.03.2008 - dgranda
# setting up logging
# Only one parameter from command line is accepted
# ERROR is the default log level
debug_level = logging.ERROR
if len(sys.argv) >1:
	if sys.argv[1]=='-d':
		debug_level = logging.DEBUG
	elif sys.argv[1]=='-i':
		debug_level = logging.INFO
	elif sys.argv[1]=='-w':
		debug_level = logging.WARNING
	else:
		print "CLI - Unknown parameter "+sys.argv[1]

print "*** Log level set to "+ logging.getLevelName(debug_level) +" ***"
logging.basicConfig(level=debug_level,
					 format='%(asctime)s|%(levelname)s|%(module)s|%(funcName)s|%(message)s',
					 filemode='w')

class pyTrainer:
	def __init__(self,filename = None, data_path = None): 
		logging.debug('>>') 
		self.data_path = data_path
		self.record = Record(data_path,self)
		self.version ="1.6.0.2" # 20.07.2008
		logging.debug('checking configuration...')
		self.conf = checkConf()
		self.filename = self.conf.getValue("conffile")
		logging.debug('retrieving data from '+ self.filename)
		self.configuration = XMLParser(self.filename)
		self.ddbb = DDBB(self.configuration)
		logging.debug('connecting to DDBB')
		self.ddbb.connect()
		
		self.migrationCheck()
		
		#preparamos la ventana principal
		self.windowmain = Main(data_path,self,self.version)
		self.date = Date(self.windowmain.calendar)

		#Preparamos el webservice	 
		gtk.gdk.threads_init()
		self.webservice = webService(data_path,self.refreshWaypointView,self.newRecord)
		self.webservice.start()

		#comprobamos que el profile esta configurado
		self.profile = Profile(self.data_path,self)
		self.profile.setVersion(self.version)
		self.profile.isProfileConfigured()

		self.waypoint = Waypoint(data_path,self)
		self.extension = Extension(data_path)
		self.plugins = Plugins(data_path)
		self.loadPlugins()
		self.loadExtensions()
		self.windowmain.createGraphs(RecordGraph,DayGraph,MonthGraph,YearGraph,HeartRateGraph)
		self.windowmain.createMap(Googlemaps,self.waypoint)
		self.windowmain.createWaypointEditor(WaypointEditor,self.waypoint)
		self.windowmain.on_calendar_selected(None)
		self.refreshMainSportList()	 
		self.windowmain.run()
		logging.debug('<<') 

	def quit(self): 
		logging.debug('--') 
		self.webservice.stop()
		self.windowmain.gtk_main_quit()
		sys.exit("Exit!")

	def loadPlugins(self):
		logging.debug('>>')
		activeplugins = self.plugins.getActivePlugins()
		if (len(activeplugins)<1):
			 print _("No Active Plugins")
		else:
			 for plugin in activeplugins:
				txtbutton = self.plugins.loadPlugin(plugin)
				self.windowmain.addImportPlugin(txtbutton)
		logging.debug('<<')
	 
	def loadExtensions(self):
		logging.debug('>>')
		activeextensions = self.extension.getActiveExtensions()
		if (len(activeextensions)<1):
			 print _("No Active Extensions")
		else:
			 for extension in activeextensions:
				txtbutton = self.extension.loadExtension(extension)
				self.windowmain.addExtension(txtbutton)
		logging.debug('<<')
	""" 
	def runPlugin(self,widget,pathPlugin):
		logging.debug('>>')
		gpxfile = self.plugins.runPlugin(pathPlugin)
		list_sport = self.profile.getSportList()
		logging.info('gpxfile: '+ gpxfile +' | sports list: '+str(list_sport))
		if gpxfile == False or gpxfile=="":
			 logging.error('gpxfile not valid')
			 pass
		elif os.path.isfile(gpxfile):
			 logging.info('gpxfile exists')
			 self.record.newGpxRecord(gpxfile,list_sport)
		else:
			 logging.info('editing gpxfile...')
			 self.record.editRecord(gpxfile,list_sport)
		logging.debug('<<')
		
		"""
	def runPlugin(self,widget,pathPlugin):
		logging.debug('>>')
		gtrnctrFile = self.plugins.runPlugin(pathPlugin)
		if os.path.isfile(gtrnctrFile):
			logging.info('File exists. Size: '+ str(os.path.getsize(gtrnctrFile)))
 			self.record.importFromGTRNCTR(gtrnctrFile)
 		else:
 			logging.error('File '+gtrnctrFile+' not valid')
		logging.debug('<<')

	def runExtension(self,extension,id):
		logging.debug('>>')
		txtbutton,pathExtension,type = extension
		if type == "record":
			 #Si es record le tenemos que crear el googlemaps, el gpx y darle el id de la bbdd
			 alert = self.extension.runExtension(pathExtension,id)
		logging.debug('<<')
	 
	def refreshMainSportList(self):
		logging.debug('>>')
		listSport = self.profile.getSportList()
		self.windowmain.updateSportList(listSport)
		logging.debug('<<')
		
	def refreshGraphView(self, view, sport=None):
		logging.debug('>>')
		date_selected = self.date.getDate()
		if view=="record":
			 logging.debug('record view')
			 if self.windowmain.recordview.get_current_page()==0:
				self.refreshRecordGraphView("info")
			 elif self.windowmain.recordview.get_current_page()==1:
				self.refreshRecordGraphView("graphs")
			 elif self.windowmain.recordview.get_current_page()==2:
				self.refreshRecordGraphView("map")
			 elif self.windowmain.recordview.get_current_page()==3:
				self.refreshRecordGraphView("heartrate")
		elif view=="day":
			 logging.debug('day view')
			 record_list = self.record.getrecordList(date_selected)
			 self.windowmain.actualize_dayview(record_list)
			 selected,iter = self.windowmain.recordTreeView.get_selection().get_selected()
		elif view=="month":
			 logging.debug('month view')
			 date_ini, date_end = self.date.getMonthInterval(date_selected)
			 sport = self.windowmain.getSportSelected()
			 record_list = self.record.getrecordPeriodSport(date_ini, date_end,sport)
			 #logging.debug('record list: '+record_list)
			 nameMonth = self.date.getNameMonth(date_selected)
			 self.windowmain.actualize_monthview(record_list, nameMonth)
			 self.windowmain.actualize_monthgraph(record_list)
		elif view=="year":
			 logging.debug('year view')
			 date_ini, date_end = self.date.getYearInterval(date_selected)
			 sport = self.windowmain.getSportSelected()
			 year = self.date.getYear(date_selected)
			 record_list = self.record.getrecordPeriodSport(date_ini, date_end,sport)
			 self.windowmain.actualize_yearview(record_list, year)
			 self.windowmain.actualize_yeargraph(record_list)
		logging.debug('<<')
	 
	def refreshRecordGraphView(self, view):
		logging.debug('>>')
		if view=="info":
			 selected,iter = self.windowmain.recordTreeView.get_selection().get_selected()
			 record_list=[]
			 if iter:
				id_record = selected.get_value(iter,0)
				record_list = self.record.getrecordInfo(id_record)
			 self.windowmain.actualize_recordview(record_list)

		if view=="graphs":
			 selected,iter = self.windowmain.recordTreeView.get_selection().get_selected()
			 gpx_tracklist = []
			 if iter:
				id_record = selected.get_value(iter,0)
				gpxfile = self.conf.getValue("gpxdir")+"/%s.gpx" %id_record
				if os.path.isfile(gpxfile):
					 gpx = Gpx(self.data_path,gpxfile)
					 gpx_tracklist = gpx.getTrackList()
			 self.windowmain.actualize_recordgraph(gpx_tracklist)

		if view=="map":
			 self.refreshMapView()

		if view=="heartrate":
			 selected,iter = self.windowmain.recordTreeView.get_selection().get_selected()
			 gpx_tracklist = []
			 record_list=[]
			 if iter:
				id_record = selected.get_value(iter,0)
				record_list = self.record.getrecordInfo(id_record)
				gpxfile = self.conf.getValue("gpxdir")+"/%s.gpx" %id_record
				if os.path.isfile(gpxfile):
					 gpx = Gpx(self.data_path,gpxfile)
					 gpx_tracklist = gpx.getTrackList()
			 self.windowmain.actualize_heartrategraph(gpx_tracklist)
			 zones = getZones()
			 filename = self.conf.getValue("conffile")
			 configuration = XMLParser(filename)
			 karvonen_method = configuration.getValue("pytraining","prf_hrzones_karvonen")
			 self.windowmain.actualize_hrview(record_list,zones,karvonen_method)
		logging.debug('<<')
			 
	def refreshMapView(self):
		logging.debug('>>')
		selected,iter = self.windowmain.recordTreeView.get_selection().get_selected()
		id_record = selected.get_value(iter,0)
		self.windowmain.actualize_map(id_record)
		logging.debug('<<')

	def refreshListRecords(self):
		logging.debug('>>')
		date = self.date.getDate()
		record_list = self.record.getrecordList(date)
		self.windowmain.actualize_recordTreeView(record_list)
		record_list = self.record.getRecordDayList(date)
		self.windowmain.actualize_calendar(record_list)
		logging.debug('<<')

	def refreshListView(self):
		logging.debug('>>')
		record_list = self.record.getAllRecordList()
		self.windowmain.actualize_listview(record_list)
		logging.debug('<<')
	 
	def refreshWaypointView(self,default_waypoint=False,redrawmap=1):
		logging.debug('>>')
		waypoint_list = self.waypoint.getAllWaypoints()
		self.windowmain.actualize_waypointview(waypoint_list,default_waypoint,redrawmap)
		logging.debug('<<')
	 
	def searchListView(self,condition):
		logging.debug('>>')
		record_list = self.record.getRecordListByCondition(condition)
		self.windowmain.actualize_listview(record_list)
		logging.debug('<<')
		
	def editExtensions(self):
		logging.debug('>>')
		self.extension.manageExtensions()
		logging.debug('<<')
		
	def editGpsPlugins(self):
		logging.debug('>>')
		self.plugins.managePlugins()
		logging.debug('<<')

	def newRecord(self,title=None,distance=None,time=None,upositive=None,unegative=None,bpm=None,calories=None,date=None,comment=None):
		logging.debug('>>')
		list_sport = self.profile.getSportList()
		if date == None:
			 date = self.date.getDate()
			 self.record.newRecord(list_sport, date, title, distance, time, upositive, unegative, bpm, calories, comment)
		logging.debug('<<')

	def editRecord(self, id_record):
		logging.debug('>>')
		list_sport = self.profile.getSportList()
		logging.debug('id_record: '+str(id_record)+' | list_sport: '+str(list_sport))
		self.record.editRecord(id_record,list_sport)
		logging.debug('<<')

	def removeRecord(self, id_record, confirm = False):
		logging.debug('>>')
		if confirm:
			 self.record.removeRecord(id_record)
		else:
			 msg = _("Delete this database entry?")
			 params = [id_record,True]
			 warning = Warning(self.data_path,self.removeRecord,params)
			 warning.set_text(msg)
			 warning.run()
		logging.debug('<<')
	 
	def removeWaypoint(self,id_waypoint, confirm = False):
		logging.debug('>>')
		if confirm:
			 self.waypoint.removeWaypoint(id_waypoint)
			 self.refreshWaypointView()
		else:
			 msg = _("Delete this waypoint?")
			 params = [id_waypoint,True]
			 warning = Warning(self.data_path,self.removeWaypoint,params)
			 warning.set_text(msg)
			 warning.run()
		logging.debug('<<')

	def updateWaypoint(self,id_waypoint,lat,lon,name,desc,sym):
		logging.debug('>>')
		self.waypoint.updateWaypoint(id_waypoint,lat,lon,name,desc,sym)
		self.refreshWaypointView(id_waypoint)
		logging.debug('<<')
	 
	def exportCsv(self):
		logging.debug('>>')
		from save import Save
		save = Save(self.data_path, self.record)
		save.run()
		logging.debug('<<')	 
	 
	def editProfile(self):
		logging.debug('>>')
		self.profile.editProfile()
		logging.debug('<<')
		
	def migrationCheck(self):
		"""22.06.2008 - dgranda
		Checks if it is necessary to run migration scripts for new features
		args: none
		returns: none"""
		logging.debug('>>')
		logging.debug('Checking current configuration...')
		self.conf = checkConf()
		self.filename = self.conf.getValue("conffile")
		logging.debug('Retrieving data from '+ self.filename)
		version_tmp = self.configuration.getOption("version")
		logging.info('Old version: '+version_tmp+' | New version: '+self.version)
		if version_tmp=="1.0":
			logging.debug('updating month data')
			self.ddbb.updatemonth()
		if version_tmp<="0.9.8":
			logging.debug('updating date format')
			self.ddbb.updateDateFormat()
		if version_tmp<="0.9.8.2":
			logging.debug('updating DB title')
			self.ddbb.addTitle2ddbb()
		if version_tmp<="1.3.1":
			self.ddbb.addUnevenness2ddbb()
		if version_tmp<="1.4.1.1":
			self.ddbb.addWaypoints2ddbb()
		if version_tmp<="1.4.2":
			try:
				self.ddbb.addWaypoints2ddbb()
			except:
				pass
		if version_tmp<="1.5.0":
			self.ddbb.addweightandmet2ddbb()
		if version_tmp<="1.5.0.1":
			self.ddbb.checkmettable()
		if version_tmp<="1.5.0.2":
			self.ddbb.addpaceandmax2ddbb()
		if version_tmp < "1.6.0.1":
			logging.info('Adding date_time_utc column and retrieving data from local GPX files')
			self.addDateTimeUTC()
		if version_tmp < "1.6.0.2":
			logging.info('Checking pace and max pace stored in DB')
			self.checkPacesDB()
		if version_tmp < self.version:
			self.configuration.setVersion(self.version)
		logging.debug('<<')
	
	def addDateTimeUTC(self):
		"""12.07.2008 - dgranda
		Adds date_time (UTC format) for each record (new column date_time_utc in table records). New in version 1.6.0.1
		args: none
		returns: none"""
		logging.debug('>>')
		# Retrieves info from all GPX files stored locally
		listTracksGPX = self.record.shortFromLocal()
		logging.debug('Retrieved info from local files: '+ str(listTracksGPX))
		# Creates column date_time_utc in records table
		try:
			self.ddbb.addDateTimeUTC2ddbb()
		except:
			logging.error('Column date_time_utc already exists in DB')		
		# Updates data
		for track in listTracksGPX:
			try:
				# update records set date_time_utc="2008-07-11T10:21:31Z" where id_record='158';
				logging.debug('Updating: '+str(track))
				self.ddbb.update("records","date_time_utc",[track[1]], "id_record = %d" %int(track[2]))
			except:
				logging.error('Error when updating data for track '+ track[2])
				traceback.print_last()
		logging.debug('<<')
		
	def checkPacesDB(self):
		"""19.07.2008 - dgranda
		Updates paces in DB (maxspeed<->maxpace | average<->pace). New in version 1.6.0.2
		args: none
		returns: none"""
		logging.debug('>>')
		# Retrieves info from DB: id_record,maxspeed,maxpace,average,pace
		listPaces = self.ddbb.select("records", "id_record,maxspeed,maxpace,average,pace")
		logging.debug('Retrieved info from db: '+ str(listPaces))
		num=0
		for entry in listPaces:
			if entry[1]>0 and entry[3]>0:
				tmpMax = "%d.%d" %((3600/entry[1])/60,(3600/entry[1])%60)
				tmpAve = "%d.%d" %((3600/entry[3])/60,(3600/entry[3])%60)
				try:
					self.ddbb.update("records","maxpace,pace",[eval(tmpMax),eval(tmpAve)], "id_record = %d" %int(entry[0]))
					num+=1
				except:
					logging.error('Error when updating data for track '+ entry[0])
					traceback.print_last()
			else:
				logging.error('No pace info available for entry '+str(entry[0])+' in DB. Please check')
		logging.info('Updated '+str(num)+' entries')
		logging.debug('<<')
