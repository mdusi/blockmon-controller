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

import xml.dom.minidom, itertools
from core.template import Template
from core.topology import Topology
from core.composition import Composition

class TemplateDefinition(Template,object):
	"""\brief Manages a template definition"""
	def __init__(self, template):
		Template.__init__(self, template)		
		self.__distcomp = self.dom.getElementsByTagName("distcomposition")[0]
		self.__topo = Topology( self.__distcomp.getElementsByTagName("topology")[0] )
		self.__comps = [Composition(c) for c in self.__distcomp.getElementsByTagName("composition")]

	@property
	def distcomp(self): return self.__distcomp

	@property
	def topology(self): return self.__topo

	@property
	def comps(self): return self.__comps

	def get_comp_from_id(self, comp_id):
		s = itertools.ifilter(lambda comp: comp.comp_id == comp_id, self.__comps)
		try: return s.next()
		except StopIteration: return None
