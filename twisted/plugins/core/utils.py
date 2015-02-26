# Copyright (c) 2015, NEC Europe Ltd. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without 
# modification, are permitted provided that the following conditions are met:
#    * Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#    * Redistributions in binary form must reproduce the above copyright
#      notice, this list of conditions and the following disclaimer in the
#      documentation and/or other materials provided with the distribution.
#    * Neither the name of NEC Europe Ltd, nor the names of its contributors
#      may be used to endorse or promote products derived from this software 
#      without specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS 
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT 
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR 
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT 
# HOLDERBE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, 
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, 
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR 
# PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER 
# IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR 
# OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF 
# ADVISED OF THE POSSIBILITY OF SUCH DAMAGE
#

class RetVal(object):
	CODE_SUCCESS = 0
	CODE_FAILURE = -1

##################################################
import ConfigParser, os
class Parser(object):
	def __init__(self, config):
		self.__config = config
		self.__dbnodes = None
		self.__dbtemplates = None
		self.__datafile_dir = None
		self.__ext_listening_port = None
		self.__node_registration_port = None
		self.__parse_config()

	def __parse_config(self):
		cp = ConfigParser.ConfigParser() 
		cp.read(self.__config)
		self.__dbnodes = cp.get('MAIN', 'bmnodes')
		self.__dbtemplates = cp.get('MAIN', 'templates')
		self.__datafile_dir = cp.get('MAIN', 'datafile')
		self.__ext_listening_port = int(cp.get('EXT_IFACE', 'listening_port'))
		self.__node_registration_port = int(cp.get('NODE_IFACE', 'registration_port'))

		# check on port numbers
		if (self.__ext_listening_port == self.__node_registration_port):
			print "EXT_IFACE and NODE_IFACE listening ports must differ"
			os._exit(1)

	@property
	def node_registration_port(self): return self.__node_registration_port

	@property
	def ext_listening_port(self): return self.__ext_listening_port

	@property
	def dbnodes(self): return self.__dbnodes

	@property
	def dbtemplates(self): return self.__dbtemplates

	@property
	def datafile_dir(self): return self.__datafile_dir

##################################################
import xml.dom.minidom
class XmlHandler(object):
	
	@classmethod
  	def get_DOM(self, xmlfile):
		"""\brief Turns an xml file into a DOM object.
		\return      (\c xml.dom.minidom.Document) The DOM object
		"""
		dom = None
		try: dom = xml.dom.minidom.parseString(xmlfile)
		except Exception, e:
	  		print "Error getting dom:", str(e)
	  		return None
		return dom
	 
	@classmethod
  	def get_label(self, key, xml_object):
		"""\brief Given an xml object and a key, returns the value matching that key
		(a string) or None if nothing matches the key.
		\param key (\c string) The key to search for
		\param xml_object (\c minidom.Node)  The xml object to search for the key in
		\return (\c string) The value found or None if no value was found for the given key
		"""
		if xml_object.attributes.has_key(key):
	  		return xml_object.attributes[key].value
		else: return None
