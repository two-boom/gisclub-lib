#EventName2 Converter
# Copyright (c) 2boom 2012-13
# v.1.2-r0
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

from Components.Converter.Converter import Converter
from Components.Element import cached
from enigma import eEPGCache
from time import localtime

class EventName2(Converter, object):
	NAME = 0
	SHORT_DESCRIPTION = 1
	EXTENDED_DESCRIPTION = 2
	FULL_DESCRIPTION = 3
	ID = 4
	NEXT_NAME = 5
	NEXT_DESCRIPTION = 6
	NEXT_NAMEWT = 7
	NEXT_NAME_NEXT = 8
	NEXT_NAME_NEXTWT = 9
	NEXT_EVENT_LIST = 10
	NEXT_EVENT_LISTWT = 11
	NEXT_EVENT_LIST2 = 12
	NEXT_EVENT_LISTWT2 = 13
	
	def __init__(self, type):
		Converter.__init__(self, type)
		self.epgcache = eEPGCache.getInstance()
		if type == "Description" or type == "Short":
			self.type = self.SHORT_DESCRIPTION
		elif type == "ExtendedDescription":
			self.type = self.EXTENDED_DESCRIPTION
		elif type == "FullDescription" or type == "ShortOrExtendedDescription":
			self.type = self.FULL_DESCRIPTION
		elif type == "ID":
			self.type = self.ID
		elif type == "NextName":
			self.type = self.NEXT_NAME
		elif type == "NextNameNext":
			self.type = self.NEXT_NAME_NEXT
		elif type == "NextNameNextWithOutTime":
			self.type = self.NEXT_NAME_NEXTWT
		elif type == "NextNameWithOutTime":
			self.type = self.NEXT_NAMEWT
		elif type == "NextDescription" or type == "NextEvent":
			self.type = self.NEXT_DESCRIPTION
		elif type == "NextEventList":
			self.type = self.NEXT_EVENT_LIST
		elif type == "NextEventListWithOutTime":
			self.type = self.NEXT_EVENT_LISTWT
		elif type == "NextEventList2":
			self.type = self.NEXT_EVENT_LIST2
		elif type == "NextEventListWithOutTime2":
			self.type = self.NEXT_EVENT_LISTWT2
		else:
			self.type = self.NAME

	@cached
	def getText(self):
		event = self.source.event
		if event is None:
			return ""
		if self.type == self.NAME:
			return event.getEventName()
		elif self.type == self.SHORT_DESCRIPTION:
			return event.getShortDescription()
		elif self.type == self.EXTENDED_DESCRIPTION:
			return event.getExtendedDescription() or event.getShortDescription() or event.getEventName()
		elif self.type == self.FULL_DESCRIPTION:
			description = event.getShortDescription()
			extended = event.getExtendedDescription()
			if description and extended:
				description += '\n'
			return description + extended
		elif self.type == self.ID:
			return str(event.getEventId())
		elif self.type == self.NEXT_NAME or self.type == self.NEXT_EVENT_LISTWT or \
		self.type == self.NEXT_EVENT_LIST or self.type == self.NEXT_NAME_NEXTWT or self.type == self.NEXT_NAME_NEXT or \
		self.type == self.NEXT_DESCRIPTION or self.type == self.NEXT_NAMEWT or self.type == self.NEXT_EVENT_LISTWT2 or self.type == self.NEXT_EVENT_LIST2:
			reference = self.source.service
			info = reference and self.source.info
			if info is not None:
				eventNext = self.epgcache.lookupEvent(['IBDCTSERNX', (reference.toString(), 1, -1)])
				eventNextNext = self.epgcache.lookupEvent(["IBDCT", (reference.toString(), 0, -1, -1)])
				if self.type == self.NEXT_NAME:
					if len(eventNext[0]) > 4 and eventNext[0][4]:
						t = localtime(eventNext[0][1])
						duration = _("%d min") %  (eventNext[0][2] / 60)
						return "%02d:%02d  (%s)  %s" % (t[3], t[4], duration, eventNext[0][4])
					else:
						return ""
				elif self.type == self.NEXT_EVENT_LIST or self.type == self.NEXT_EVENT_LISTWT or self.type == self.NEXT_EVENT_LIST2 or self.type == self.NEXT_EVENT_LISTWT2:
					if eventNextNext:
						listNextEpg = ''
						if self.type == self.NEXT_EVENT_LIST2 or self.type == self.NEXT_EVENT_LISTWT2:
							i = -1
						else:
							i = 0
						for x in eventNextNext:
							if i > 0 and i < 10:
								if x[4]:
									t = localtime(x[1])
									if self.type == self.NEXT_EVENT_LIST or self.type == self.NEXT_EVENT_LIST2:
										duration = _("%d min") %  (eventNextNext[i][2] / 60)
										listNextEpg += "%02d:%02d (%s) %s\n" % (t[3], t[4], duration, x[4])
									else:
										listNextEpg += "%02d:%02d %s\n" % (t[3], t[4], x[4])
							i += 1
					return listNextEpg
				elif self.type == self.NEXT_NAME_NEXT:
					if len(eventNextNext) >= 3:
						if len(eventNextNext[2]) > 4 and eventNextNext[2][4]:
							t = localtime(eventNextNext[2][1])
							duration = _("%d min") %  (eventNextNext[2][2] / 60)
							return "%02d:%02d  (%s)  %s" % (t[3], t[4], duration, eventNextNext[2][4])
						else:
							return ""
					else:
						return ""
				elif self.type == self.NEXT_NAME_NEXTWT:
					if len(eventNextNext) >= 3:
						if len(eventNextNext[2]) > 4 and eventNextNext[2][4]:
							return "%s" %  eventNextNext[2][4]
						else:
							return ""
					else:
						return ""
				elif self.type == self.NEXT_NAMEWT:
					if len(eventNext[0]) > 4 and eventNext[0][4]:
						return "%s" %  eventNext[0][4]
					else:
						return ""
				else:
					if len(eventNext[0]) > 6 and eventNext[0][6]:
						return "%s" %  eventNext[0][6]
					elif len(eventNext[0]) > 5 and eventNext[0][5]:
						return "%s" %  eventNext[0][5]
					else:
						return ""
		return ""
		
	text = property(getText)
