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

import xml.dom.minidom, re
from core.utils import XmlHandler

class Composition(object):
	def __init__(self, compdom):
		"""\brief Initialize the class
		\param (\c dom) composition as DOM object
		"""
		self.__compdom = compdom
		self.__id = XmlHandler.get_label("id", self.__compdom)
		self.__intvars = {}
		self.__extvars = {}
		for v in [self.__intvars, self.__extvars]:
			for p in ['ip','port']: v[p] = []
		self.__get_intvars()
		self.__get_extvars()

	@property
	def intvars(self): return self.__intvars

	@property
	def extvars(self): return self.__extvars

	@property
	def comp_id(self): return self.__id

	@comp_id.setter
	def comp_id(self, value): self.__id = value

	def get_xmlbuf(self):
		return self.__compdom.toxml()

	def __get_intvars(self):
		iprule = re.compile(r'"(\*ip\[\'[a-zA-Z]*\'\])"')
		portrule = re.compile(r'"(\*port\[\'[a-zA-Z]*\'\])"')
		self.__intvars['ip'] = self.__get_vars(iprule)
		self.__intvars['port'] = self.__get_vars(portrule)

	def __get_extvars(self):
		iprule = re.compile(r'"(\@ip\[\'[a-zA-Z]*\'\])"')
		portrule = re.compile(r'"(\@port\[\'[a-zA-Z]*\'\])"')
		self.__extvars['ip'] = self.__get_vars(iprule)
		self.__extvars['port'] = self.__get_vars(portrule)
	
	def __get_vars(self, rule):
		r = rule.search(self.__compdom.toxml())
		return ( r.groups() if r else [])
