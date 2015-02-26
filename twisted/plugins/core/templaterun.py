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

from core.utils import RetVal
from core.compositionrun import *
import itertools

class TemplateRun(object):
	"""\brief Manages a template to be executed"""

	def __init__(self, tdef, tins, datafile_dir):
		"""\brief Initialize the class
		\param (\c TemplateDefinition) template definition
		\param (\c TemplateInstance) template instance
		\param (\c string) path to datafile dir
		"""
		self.__tdef = tdef
		self.__tins = tins
		self.__topo = self.__tdef.topology
		self.__topovars = self.__tins.topovars
		self.__compvars = self.__tins.compvars
		self.__compsrun = []
		self.__datafile_dir = datafile_dir

	@property
	def compsrun(self): return self.__compsrun

	def get_num_nodes(self): return len(self.__topo.nodes)

	def install(self):
		"""\brief install the template by expanding topology and 
		creating connection between nodes. If successful, the template
		definition has the 
		- expanded topology: nodes and edges are created according to 
		topovars. Nodes have composition object, comp_id, node_id set
		- connections: nodes have also comp_id_next set
		No substitution of comp variables or actual bmnodes up to this point
		\return (\c RetVal) success or failure
		"""
		if ( (self.__handle_topology() is RetVal.CODE_SUCCESS) and \
			 (self.__handle_edges() is RetVal.CODE_SUCCESS) ):
			return RetVal.CODE_SUCCESS
		return RetVal.CODE_FAILURE

	def assign_nodes(self, nodes):
		collections = []
		for n,cur_comp in enumerate(self.__compsrun):
			(ip, port, port_in_use) = nodes[n]
			#assign node to the nodesrc of the current comp
			cur_comp.assign('src',ip,port,port_in_use)
			#assign node to the nodedst of the comps connected to the current comp
			s = itertools.ifilter(lambda comp: comp.nodedst == cur_comp.nodesrc, self.__compsrun)
			while True:
				try: s.next().assign('dst',ip,port,port_in_use)
				except StopIteration: break
			#collect info: (node ip,port,port_in_use, xml of the composition it will be running w/o any variable substitutions yet)
			coll_info = (ip,port,port_in_use,cur_comp.comp_xml)
			collections.append(coll_info)
		return (RetVal.CODE_SUCCESS, collections)
	
	def __get_comprun_from_node(self, node):
		s = itertools.ifilter(lambda comp: comp.nodesrc == node, self.__compsrun)
		try: return s.next()
		except StopIteration: return None

	def __handle_edges(self):
		"""\brief handle edges
		\return (\c RetVal)"""
		for edge in self.__topo.edges:
			node = Node(edge.src_id)
			comp = self.__get_comprun_from_node(node)
			if comp is None: return RetVal.CODE_FAILURE
			comp.connect(edge.dst_id)
		return RetVal.CODE_SUCCESS

	def __handle_topology(self):
		"""\brief handle topology
		\return (\c RetVal)"""
		if self.__topo.expand(self.__topovars) is RetVal.CODE_FAILURE:
			return RetVal.CODE_FAILURE
		# create a CompositionRun obj for each node
		for node in self.__topo.nodes:
			comp = self.__tdef.get_comp_from_id(node.comp_id)
			(comp_xml, comp_id) = (comp.get_xmlbuf(), comp.comp_id)
			(intvars, extvars) = (comp.intvars, comp.extvars)
			node_id = node.node_id
			self.__compsrun.append( CompositionRun(comp_id,comp_xml,node_id,intvars, extvars,self.__compvars, self.__datafile_dir) )
		return RetVal.CODE_SUCCESS
