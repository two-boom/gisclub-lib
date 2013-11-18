# -*- coding: utf-8 -*-
#
# Extended ServiceName Converter for Enigma2 Dreamboxes (ServiceName2.py)
# Coded by vlamo (c) 2011
#
# Version: 0.4 (03.06.2011 18:40)
# Version: 0.5 (08.09.2012) add Alternative numbering mode support - Dmitry73 & 2boom
# Version: 0.6 (19.10.2012) add stream mapping
# Version: 0.7 (19.09.2013) add iptv info - nikolasi & 2boom
# Version: 0.8 (29.10.2013) add correct output channelnumner - Dmitry73
# Version: 0.9 (15.11.2013) code fix and optimization - Taapat
# Support: http://dream.altmaster.net/ & http://gisclub.tv
#

from Components.Converter.Converter import Converter
from enigma import iServiceInformation, iPlayableService, iPlayableServicePtr, eServiceReference, eServiceCenter, eTimer
from Components.Element import cached
from Components.config import config
try:
	from Components.Renderer.ChannelNumber import ChannelNumberClasses
	correctChannelNumber = True
except:
	correctChannelNumber = False

class ServiceName2(Converter, object):
	NAME = 0
	NUMBER = 1
	BOUQUET = 2
	PROVIDER = 3
	REFERENCE = 4
	ORBPOS = 5
	TPRDATA = 6
	SATELLITE = 7
	FORMAT = 8

	def __init__(self, type):
		Converter.__init__(self, type)
		if type == "Name" or not len(str(type)):
			self.type = self.NAME
		elif type == "Number":
			self.type = self.NUMBER
		elif type == "Bouquet":
			self.type = self.BOUQUET
		elif type == "Provider":
			self.type = self.PROVIDER
		elif type == "Reference":
			self.type = self.REFERENCE
		elif type == "OrbitalPos":
			self.type = self.ORBPOS
		elif type == "TpansponderInfo":
			self.type = self.TPRDATA
		elif type == "Satellite":
			self.type = self.SATELLITE
		else:
			self.type = self.FORMAT
			self.sfmt = type[:]
		try:
			if (self.type == 1 or (self.type == 8 and '%n' in self.sfmt)) and correctChannelNumber:
				ChannelNumberClasses.append(self.forceChanged)
		except:
			pass
		self.what = self.tpdata = None
		self.Timer = eTimer()
		self.Timer.callback.append(self.neededChange)

	def getServiceNumber(self, ref):
		def searchHelper(serviceHandler, num, bouquet):
			servicelist = serviceHandler.list(bouquet)
			if not servicelist is None:
				while True:
					s = servicelist.getNext()
					if not s.valid(): break
					if not (s.flags & (eServiceReference.isMarker|eServiceReference.isDirectory)):
						num += 1
						if s == ref: return s, num
			return None, num

		if isinstance(ref, eServiceReference):
			isRadioService = ref.getData(0) in (2,10)
			lastpath = isRadioService and config.radio.lastroot.value or config.tv.lastroot.value
			if 'FROM BOUQUET' not in lastpath:
				if 'FROM PROVIDERS' in lastpath:
					return 'P', 'Provider'
				if 'FROM SATELLITES' in lastpath:
					return 'S', 'Satellites'
				if ') ORDER BY name' in lastpath:
					return 'A', 'All Services'
				return 0, 'N/A'
			try:
				acount = config.plugins.NumberZapExt.enable.value and config.plugins.NumberZapExt.acount.value or config.usage.alternative_number_mode.value
			except:
				acount = False
			rootstr = ''
			for x in lastpath.split(';'):
				if x != '': rootstr = x
			serviceHandler = eServiceCenter.getInstance()
			if acount is True or not config.usage.multibouquet.value:
				bouquet = eServiceReference(rootstr)
				service, number = searchHelper(serviceHandler, 0, bouquet)
			else:
				if isRadioService:
					bqrootstr = '1:7:2:0:0:0:0:0:0:0:FROM BOUQUET "bouquets.radio" ORDER BY bouquet'
				else:
					bqrootstr = '1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "bouquets.tv" ORDER BY bouquet'
				number = 0
				cur = eServiceReference(rootstr)
				bouquet = eServiceReference(bqrootstr)
				bouquetlist = serviceHandler.list(bouquet)
				if not bouquetlist is None:
					while True:
						bouquet = bouquetlist.getNext()
						if not bouquet.valid(): break
						if bouquet.flags & eServiceReference.isDirectory:
							service, number = searchHelper(serviceHandler, number, bouquet)
							if not service is None and cur == bouquet: break
			if not service is None:
				info = serviceHandler.info(bouquet)
				name = info and info.getName(bouquet) or ''
				return number, name
		return 0, ''

	def getProviderName(self, ref, sname):
		if isinstance(ref, eServiceReference):
			from Screens.ChannelSelection import service_types_radio, service_types_tv
			typestr = ref.getData(0) in (2,10) and service_types_radio or service_types_tv
			pos = typestr.rfind(':')
			rootstr = '%s (channelID == %08x%04x%04x) && %s FROM PROVIDERS ORDER BY name' %(typestr[:pos+1],ref.getUnsignedData(4),ref.getUnsignedData(2),ref.getUnsignedData(3),typestr[pos+1:])
			provider_root = eServiceReference(rootstr)
			serviceHandler = eServiceCenter.getInstance()
			providerlist = serviceHandler.list(provider_root)
			if not providerlist is None:
				while True:
					provider = providerlist.getNext()
					if not provider.valid(): break
					if provider.flags & eServiceReference.isDirectory:
						servicelist = serviceHandler.list(provider)
						if not servicelist is None:
							while True:
								service = servicelist.getNext()
								if not service.valid(): break
								if service == ref:
									info = serviceHandler.info(provider)
									return info and info.getName(provider) or "Unknown"
			return self.getIPTVProvider(sname)
		return " "

	def getTransponderInfo(self, info, ref, fmt):
		result = ""
		if self.tpdata is None:
			self.tpdata = ref and (info.getInfoObject(ref, iServiceInformation.sTransponderData) or -1) or info.getInfoObject(iServiceInformation.sTransponderData)
			if not isinstance(self.tpdata, dict):
				self.tpdata = None
				return result
		type = self.tpdata.get('tuner_type', '')
		if fmt == '' or fmt == '%T':
			if type == 'DVB-C':
				fmt = '%t %F %Y %i %f %M'	#(type frequency symbol_rate inversion fec modulation)
			elif type == 'DVB-T':
				fmt = '%t %F %h %m %g %c'	#(type frequency code_rate_hp transmission_mode guard_interval constellation)
			else:
				 fmt = '%O %F%p %Y %f'		#(orbital_position frequency polarization symbol_rate fec)
		for line in fmt:
			f = line[:1]
			if f == 't':	# %t - tuner_type (dvb-s/s2/c/t)
				if type == 'DVB-S':
					result += _("Satellite")
				elif type == 'DVB-C':
					result += _("Cable")
				elif type == 'DVB-T':
					result += _("Terrestrial")
				else:
					result += 'N/A'
			elif f == 's':	# %s - system (dvb-s/s2/c/t)
				if type == 'DVB-S':
					x = self.tpdata.get('system', 0)
					result += x in range(2) and {0:'DVB-S',1:'DVB-S2'}[x] or ''
				else:
					result += type
			elif f == 'F':	# %F - frequency (dvb-s/s2/c/t) in KHz
				result += '%d'%(self.tpdata.get('frequency', 0) / 1000)
			elif f == 'f':	# %f - fec_inner (dvb-s/s2/c/t)
				if type in ('DVB-S','DVB-C'):
					x = self.tpdata.get('fec_inner', 15)
					result += x in range(10)+[15] and {0:'Auto',1:'1/2',2:'2/3',3:'3/4',4:'5/6',5:'7/8',6:'8/9',7:'3/5',8:'4/5',9:'9/10',15:'None'}[x] or ''
				elif type == 'DVB-T':
					x = self.tpdata.get('code_rate_lp', 5)
					result += x in range(6) and {0:'1/2',1:'2/3',2:'3/4',3:'5/6',4:'7/8',5:'Auto'}[x] or ''
			elif f == 'i':	# %i - inversion (dvb-s/s2/c/t)
				x = self.tpdata.get('inversion', 2)
				result += x in range(3) and {0:'On',1:'Off',2:'Auto'}[x] or ''
			elif f == 'O':	# %O - orbital_position (dvb-s/s2)
				if type == 'DVB-S':
					x = self.tpdata.get('orbital_position', 0)
					result += x > 1800 and "%d.%d°W"%((3600-x)/10, (3600-x)%10) or "%d.%d°E"%(x/10, x%10)
			elif f == 'M':	# %M - modulation (dvb-s/s2/c)
				x = self.tpdata.get('modulation', 1)
				if type == 'DVB-S':
					result += x in range(4) and {0:'Auto',1:'QPSK',2:'8PSK',3:'QAM16'}[x] or ''
				elif type == 'DVB-C':
					result += x in range(6) and {0:'Auto',1:'QAM16',2:'QAM32',3:'QAM64',4:'QAM128',5:'QAM256'}[x] or ''
			elif f == 'p':	# %p - polarization (dvb-s/s2)
				if type == 'DVB-S':
					x = self.tpdata.get('polarization', 0)
					result += x in range(4) and {0:'H',1:'V',2:'L',3:'R'}[x] or '?'
			elif f == 'Y':	# %Y - symbol_rate (dvb-s/s2/c)
				if type in ('DVB-S','DVB-C'):
					result += '%d'%(self.tpdata.get('symbol_rate', 0) / 1000)
			elif f == 'r':	# %r - rolloff (dvb-s2)
				x = self.tpdata.get('rolloff')
				if not x is None:
					result += x in range(3) and {0:'0.35',1:'0.25',2:'0.20'}[x] or ''
			elif f == 'o':	# %o - pilot (dvb-s2)
				x = self.tpdata.get('pilot')
				if not x is None:
					result += x in range(3) and {0:'Off',1:'On',2:'Auto'}[x] or ''
			elif f == 'c':	# %c - constellation (dvb-t)
				if type == 'DVB-T':
					x = self.tpdata.get('constellation', 3)
					result += x in range(4) and {0:'QPSK',1:'QAM16',2:'QAM64',3:'Auto'}[x] or ''
			elif f == 'l':	# %l - code_rate_lp (dvb-t)
				if type == 'DVB-T':
					x = self.tpdata.get('code_rate_lp', 5)
					result += x in range(6) and {0:'1/2',1:'2/3',2:'3/4',3:'5/6',4:'7/8',5:'Auto'}[x] or ''
			elif f == 'h':	# %h - code_rate_hp (dvb-t)
				if type == 'DVB-T':
					x = self.tpdata.get('code_rate_hp', 5)
					result += x in range(6) and {0:'1/2',1:'2/3',2:'3/4',3:'5/6',4:'7/8',5:'Auto'}[x] or ''
			elif f == 'm':	# %m - transmission_mode (dvb-t)
				if type == 'DVB-T':
					x = self.tpdata.get('transmission_mode', 2)
					result += x in range(3) and {0:'2k',1:'8k',2:'Auto'}[x] or ''
			elif f == 'g':	# %g - guard_interval (dvb-t)
				if type == 'DVB-T':
					x = self.tpdata.get('guard_interval', 4)
					result += x in range(5) and {0:'1/32',1:'1/16',2:'1/8',3:'1/4',4:'Auto'}[x] or ''
			elif f == 'b':	# %b - bandwidth (dvb-t)
				if type == 'DVB-T':
					x = self.tpdata.get('bandwidth', 1)
					result += x in range(4) and {0:'8 MHz',1:'7 MHz',2:'6 MHz',3:'Auto'}[x] or ''
			elif f == 'e':	# %e - hierarchy_information (dvb-t)
				if type == 'DVB-T':
					x = self.tpdata.get('hierarchy_information', 4)
					result += x in range(5) and {0:'None',1:'1',2:'2',3:'4',4:'Auto'}[x] or ''
			result += line[1:]
		return result

	def getSatelliteName(self, ref, sname):
		if isinstance(ref, eServiceReference):
			orbpos = ref.getUnsignedData(4) >> 16
			if orbpos == 0xFFFF: #Cable
				return _("Cable")
			elif orbpos == 0xEEEE: #Terrestrial
				return _("Terrestrial")
			elif orbpos == 0: #IPTV
				if 'http' in sname:
					return _("IPTV")
			else: #Satellite
				orbpos = ref.getData(4) >> 16
				if orbpos < 0: orbpos += 3600
				try:
					from Components.NimManager import nimmanager
					return str(nimmanager.getSatDescription(orbpos))
				except:
					refString = ref.toString().lower()
					if "%3a//" in refString:
						return _("Stream")
					elif refString.startswith("1:134:"):
						return _("Altern")
					else:
						name = orbpos > 1800 and "%d.%d°W"%((3600-orbpos)/10, (3600-orbpos)%10) or "%d.%d°E"%(orbpos/10, orbpos%10)
		return ""

	def getIPTVProvider(self, sname):
		if 'http' not in sname:
			return " "
		if 'tvshka' in sname:
			return "SCHURA"
		elif 'vsadmin' in sname:
			return "IPTV" 
		elif '3a4050' in sname:
			return "Ukrtelecom"
		elif '3a7777' in sname:
			return "IPTVNTV"
		elif '3a1234' in sname:
			return "IPTV1"
		elif 'KartinaTV' in sname:
			return "KartinaTV"
		elif 'Megaimpuls' in sname:
			return "MEGAIMPULSTV"
		elif 'Newrus' in sname:
			return "NEWRUSTV"
		elif 'Sovok' in sname:
			return "SOVOKTV"
		elif 'Rodnoe' in sname:
			return "RODNOETV"
		elif '238.1.1.89%3a1234' in sname:
			return "TRK UKRAINE"
		elif '238.1.1.181%3a1234' in sname:
			return "VIASAT"
		elif 'cdnet' in sname:
			return "NonameTV"
		elif 'unicast' in sname:
			return "StarLink"
		return "IPTV"

	@cached
	def getText(self):
		service = self.source.service
		if isinstance(service, iPlayableServicePtr):
			info = service and service.info()
			ref = None
		else: # reference
			info = service and self.source.info
			ref = service
		if info is None: return ""
		sname = ref and ref.toString() or info.getInfoString(iServiceInformation.sServiceref)
		if self.type == self.NAME:
			name = ref and (info.getName(ref) or 'N/A') or (info.getName() or 'N/A')
			return name.replace('\xc2\x86', '').replace('\xc2\x87', '')
		elif self.type == self.NUMBER:
			try:
				service = self.source.serviceref
				num = service and service.getChannelNum() or None
			except:
				num = None
			if num:
				return str(num)
			else:
				num, bouq = self.getServiceNumber(ref or eServiceReference(info.getInfoString(iServiceInformation.sServiceref)))
				return num and str(num) or ''
		elif self.type == self.BOUQUET:
			num, bouq = self.getServiceNumber(ref or eServiceReference(info.getInfoString(iServiceInformation.sServiceref)))
			return bouq
		elif self.type == self.PROVIDER:
			return ref and self.getProviderName(ref, sname) or info.getInfoString(iServiceInformation.sProvider)
		elif self.type == self.REFERENCE:
			return ref and ref.toString() or info.getInfoString(iServiceInformation.sServiceref)
		elif self.type == self.ORBPOS or self.type == self.TPRDATA:
			if 'http' in sname:
				snameIptv = True
			else:
				snameIptv = False
			if self.type == self.ORBPOS:
				if snameIptv:
					return "0.0°E"
				else:
					return self.getTransponderInfo(info, ref, '%O')
			elif snameIptv:
				return "0.0°E - Internet TV - %s"%(self.getIPTVProvider(sname))
			else:
				return self.getTransponderInfo(info, ref, '%T')
		elif self.type == self.SATELLITE:
			return self.getSatelliteName((ref or eServiceReference(info.getInfoString(iServiceInformation.sServiceref))), sname)
		elif self.type == self.FORMAT:
			num = bouq = ''
			#if '%n' in self.sfmt or '%B' in self.sfmt:
				#num, bouq = self.getServiceNumber(ref or eServiceReference(info.getInfoString(iServiceInformation.sServiceref)))
			tmp = self.sfmt[:].split("%")
			if tmp and tmp[0]:
				ret = tmp[0]
				tmp.remove(ret)
			else:
				ret = ""
			for line in tmp:
				f = line[:1]
				if f == 'N':	# %N - Name
					name = ref and (info.getName(ref) or '') or (info.getName() or '')
					ret += name.replace('\xc2\x86', '').replace('\xc2\x87', '')
				elif f == 'n':	# %n - Number
					try:
						service = self.source.serviceref
						num = service and service.getChannelNum() or None
					except:
						num = None
					if num:
						ret += str(num)
					else:
						num, bouq = self.getServiceNumber(ref or eServiceReference(info.getInfoString(iServiceInformation.sServiceref)))
						ret += num and str(num) or ''
				elif f == 'B':	# %B - Bouquet
					num, bouq = self.getServiceNumber(ref or eServiceReference(info.getInfoString(iServiceInformation.sServiceref)))
					ret += bouq
				elif f == 'P':	# %P - Provider
					ret += ref and self.getProviderName(ref, sname) or info.getInfoString(iServiceInformation.sProvider)
				elif f == 'R':	# %R - Reference
					ret += ref and ref.toString() or info.getInfoString(iServiceInformation.sServiceref)
				elif f == 'S':	# %S - Satellite
					ret += self.getSatelliteName((ref or eServiceReference(info.getInfoString(iServiceInformation.sServiceref))), sname)
				elif f in 'TtsFfiOMpYroclhmgbe':
					ret += self.getTransponderInfo(info, ref, '%'+f)
				ret += line[1:]
			return '%s'%(ret.replace('N/A', ''))

	text = property(getText)

	def neededChange(self):
		if self.what:
			Converter.changed(self, self.what)
			self.what = None

	def forceChanged(self, what):
		if what == True:
			Converter.changed(self, (self.CHANGED_ALL,))
			self.what = None

	def changed(self, what):
		if what[0] != self.CHANGED_SPECIFIC or what[1] in (iPlayableService.evStart,):
			self.tpdata = None
			if self.type in (self.NUMBER,self.BOUQUET) or \
				(self.type == self.FORMAT and ('%n' in self.sfmt or '%B' in self.sfmt)):
				self.what = what
				self.Timer.start(200, True)
			else:
				Converter.changed(self, what)
