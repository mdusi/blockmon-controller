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

from core.template import Template
from core.utils import XmlHandler

class TemplateInstance(Template,object):
	"""\brief Manages a template to be executed"""

	def __init__(self, template):
		"""\brief Initialize the class
		\param (\c string) xml template instance as string buffer
		"""
		Template.__init__(self, template)
		self.__compvars = {}
		self.__topovars = {}
		self.__get_vars()

	def __get_vars(self):
		"""\brief get vars from xml template and save them into 
		a dict {'name': value}, one for topology vars and one for 
		compositions vars
		"""
		self.__tvars = {}
		var = self.dom.getElementsByTagName("vars")[0]
		for var_xml in var.getElementsByTagName("var"):
			v_name = XmlHandler.get_label("name", var_xml)
			v_value = XmlHandler.get_label("value", var_xml)
			v_topo = XmlHandler.get_label("topology", var_xml)
			if (v_topo is not None) and (v_topo.lower() == "yes"):
				self.__topovars[v_name] = v_value
			else: self.__compvars[v_name] = v_value

	@property
	def compvars(self): return self.__compvars

	@property
	def topovars(self): return self.__topovars
