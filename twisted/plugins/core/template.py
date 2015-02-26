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

import xml.dom.minidom
from core.utils import XmlHandler

class Template(object):
	"""\brief Manages a template"""
	def __init__(self, template):
		"""\brief Initialize the class
		\param (\c string) xml template as string buffer
		"""
		self.__template = template
		self.__docname = self.__get_docname()
		self.__temp_id = self.__get_id()

		if ( (self.__template == None) \
			or (self.__temp_id == None) \
			or (self.__docname == None) ):
			print "Template::__init__:error"
			return None

	@property
	def temp_id(self): return self.__temp_id

	@property
	def template(self): return self.__template

	@template.setter
	def template(self, value): self.__template = value

	@property
	def dom(self): return XmlHandler.get_DOM(self.__template)

	def __get_docname(self):
		node = self.dom.documentElement
		return (node.nodeName if node.nodeType == xml.dom.Node.ELEMENT_NODE else None)

	def __get_id(self):
		try: template_xml = self.dom.getElementsByTagName(self.__docname)[0]
		except: 
			print "Template::get_id: error while getting template_docname", self.__docname
			return None
		return XmlHandler.get_label("id", template_xml)
