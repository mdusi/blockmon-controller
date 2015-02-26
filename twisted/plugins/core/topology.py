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
from core.utils import XmlHandler, RetVal

class Topology(object):

	TOPO_TYPES = ["manual","tree"]

	def __init__(self, topodom):
		self.__topodom = topodom
		self.__type = XmlHandler.get_label("type", self.__topodom)
		self.__nodes = []
		self.__edges = []

	@property
	def nodes(self): return self.__nodes
	
	@property
	def edges(self): return self.__edges

	def __get_nodes(self):
		params = self.__topodom.getElementsByTagName("params")[0]
		return params.getElementsByTagName("node")

	def __get_edges(self):
		params = self.__topodom.getElementsByTagName("params")[0]
		return params.getElementsByTagName("edge")

	def __get_tree(self):
		params = self.__topodom.getElementsByTagName("params")[0]
		return params.getElementsByTagName("node")

	def __get_manual(self):
		params = self.__topodom.getElementsByTagName("params")[0]
		return params.getElementsByTagName("node")
		
	def __create_node(self, comp, node_id):
		node = "<node id=\"%d\" composition=\"%s\"/>" % (node_id, comp)
		dom = xml.dom.minidom.parseString( node )
		return dom.getElementsByTagName("node")[0]

	def __create_edge(self, src_id, dst_id):
		edge = "<edge src_id=\"%d\" dst_id=\"%s\"/>" % (src_id, dst_id)
		dom = xml.dom.minidom.parseString( edge )
		return dom.getElementsByTagName("edge")[0]

	def __tree_plugin(self):
		tree = self.__get_tree()
		nodes,edges = [],[]
		root_node_id = 1
		for elem in tree:
			comp = XmlHandler.get_label("composition", elem)
			if XmlHandler.get_label("type", elem) == "root": 
				node = self.__create_node(comp, root_node_id)
				nodes.append( TopoNode(node) )
			elif XmlHandler.get_label("type", elem) == "leaf":
				num_nodes = int(XmlHandler.get_label("value", elem))
				for node_id in xrange(root_node_id+1, root_node_id+1+num_nodes):
					node = self.__create_node(comp, node_id)
					edge = self.__create_edge(node_id, root_node_id)
					nodes.append( TopoNode(node) )
					edges.append( Edge(edge) )
		return (nodes,edges)

	def __manual_plugin(self):
		tree = self.__get_manual()
		nodes = []
		root_node_id = 1
		for elem in tree:
			comp = XmlHandler.get_label("composition", elem)
			num_nodes = int(XmlHandler.get_label("value", elem))
			for node_id in xrange(0, num_nodes):
				node = self.__create_node(comp, node_id)
				#node = TopoNode(node_id)
				nodes.append( TopoNode(node) )
		return (nodes)
		
	def expand(self, topovars):
		"""\brief expand the topology according to its type (see TOPO_TYPES for supported types)
		\param topovars (\c dict) {'name':value,...}
		\return (\c RetVal) success or failure
		"""
		#expand, and create objects TopoNode and Edge as needed
		if self.__type not in self.TOPO_TYPES:
			print "topology not implemented"
			return RetVal.CODE_FAILURE
		self.__substitute_topovars(topovars)
		if self.__type == "manual":
			#self.__nodes = [TopoNode(n) for n in self.__get_nodes()]
			self.__nodes = self.__manual_plugin()
		elif self.__type == "tree":
			(self.__nodes, self.__edges) = self.__tree_plugin()
		return RetVal.CODE_SUCCESS

	def __substitute_topovars(self, topovars):
		import re
		topo = self.__topodom.toxml()
		for (name, value) in topovars.iteritems():
			topo = re.sub('"\s*@' + name + '\s*"', '"' + value + '"', topo)
		self.__topodom = XmlHandler.get_DOM(topo)

	def run_comp(self, compvars, node):
		node_next = self.__get_next_node(node)
		comp = node.get_running_comp(compvars, node_next)
		return comp

	def run_comps(self, compvars):
		comps = []
		for node in self.__nodes:
			comp = self.run_comp(compvars, node)
			comps.append( (node.ip, node.port, comp) )
		return comps

	def __get_next_node(self, n):
		s = itertools.ifilter(lambda node: node.comp_id == n.comp_id_next, self.__nodes)
		try: return s.next()
		except StopIteration: return None

#####################################
class Edge(object):
	def __init__(self, edge):
		self.__edge = edge
		self.__src = XmlHandler.get_label("src_id", self.__edge)
		self.__dst = XmlHandler.get_label("dst_id", self.__edge)

	@property
	def src_id(self): return self.__src
		
	@property
	def dst_id(self): return self.__dst

#####################################
class TopoNode(object):
	def __init__(self, node):
		self.__node = node
		self.__id = XmlHandler.get_label("id", self.__node)
		self.__comp_id = XmlHandler.get_label("composition", self.__node)
	
	@property
	def node_id(self): return self.__id

	@property
	def comp_id(self): return self.__comp_id
