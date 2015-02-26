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
from core.utils import RetVal
from core.utils import XmlHandler

class CompositionRun(object):
	def __init__(self,comp_id,comp_xml, nodesrc_id, intvars, extvars, compvars, datafile_dir):
		"""\brief Initialize the class
		\param comp (\c Composition) composition object
		"""
		self.__comp_id = comp_id
		self.__comp_xml = comp_xml
		self.__intvars = intvars
		self.__extvars = extvars
		self.__compvars = compvars
		self.__nodesrc = Node(nodesrc_id)
		self.__nodedst = Node()
		self.__comprun_xml = None
		self.__datafile_dir = datafile_dir
		self.__datafiles = []

	@property
	def comp_id(self): return self.__comp_id

	@property
	def comp_xml(self): return self.__comp_xml

	@property
	def nodesrc(self): return self.__nodesrc

	@property
	def nodedst(self): return self.__nodedst
	
	@property
	def comprun_xml(self): return self.__comprun_xml

	@property
	def datafiles(self): return self.__datafiles

	def connect(self, nodedst_id): self.__nodedst = Node(nodedst_id)

	def assign(self,node_type, ip, port, port_in_use):
		if node_type == 'src':
			self.__nodesrc.assign(ip,port,port_in_use)
		elif node_type == 'dst' and self.__nodedst is not None:
			self.__nodedst.assign(ip,port,port_in_use)
		else:
			print "error while trying to assign node to %s", node_type
			return None

	def __substitute_compvars(self):
		for (name, value) in self.__compvars.iteritems():
			self.__comprun_xml = re.sub('"\s*@' + name + '\s*"', '"' + value + '"', self.__comprun_xml)
	
	def __substitute_vars(self, tmpvars, node):
		if node is None or node.ip is None or node.port is None: return
		tmpcomp = self.__comprun_xml
		n_ip, n_port_in_use = node.ip, node.port_in_use
		for ip in tmpvars['ip']: tmpcomp = tmpcomp.replace(ip, n_ip)
		for port in tmpvars['port']: tmpcomp = tmpcomp.replace( port, str(n_port_in_use) )
		self.__comprun_xml = tmpcomp

	def __get_exporter_blocks(self, cur_comp):
		comp_dom = XmlHandler.get_DOM(cur_comp)
		exp_blocks = ""
		for block in comp_dom.getElementsByTagName("block"):
			if block.getAttribute('export') == "yes":
				exp_blocks += block.toxml()
		return exp_blocks
	
	def __get_datafiles(self):
		import base64
		comp_dom = XmlHandler.get_DOM(self.__comprun_xml)
		for datafile in comp_dom.getElementsByTagName("datafile"):
			fname = datafile.getAttribute('filename')
			f = open(self.__datafile_dir +'/' + fname,'rb')
			fbin = base64.b64encode(f.read())
			f.close()
			self.__datafiles.append( (fname,fbin) )

	def update(self):
		print "TODO"
		#self.__substitute_compvars()
		#self.__substitute_vars(self.__intvars, self.__nodesrc)
		#self.__substitute_vars(self.__extvars, self.__nodedst)
		return RetVal.CODE_SUCCESS

	def rescue(self):
		"""\brief substitute the exporter block and get the new 
		xml running composition
		\return (\c RetVal)
		"""
		if self.__comprun_xml is None: return RetVal.CODE_FAILURE
		
		# delete the exporter blocks from the current running comp
		comprun_dom = XmlHandler.get_DOM(self.__comprun_xml)
		delete_dom = comprun_dom.createElement('delete')
		comprun_dom.childNodes[0].appendChild(delete_dom)
		for block in comprun_dom.getElementsByTagName("block"):
			if block.getAttribute('export') == "yes":
				delete_dom.appendChild(block)
		
		# add the exporter blocks from the new running comp
		add_dom = comprun_dom.createElement('add')
		comprun_dom.childNodes[0].appendChild(add_dom)
		comp_dom = XmlHandler.get_DOM(self.__comp_xml)
		for block in comp_dom.getElementsByTagName("block"):
			if block.getAttribute('export') == "yes":
				add_dom.appendChild(block)
		for label in ['general','install']:
			comprun_dom.childNodes[0].removeChild( comprun_dom.getElementsByTagName(label)[0] )

		self.__comprun_xml = comprun_dom.toxml()
		print "----------------"
		print self.__comprun_xml
		print "----------------"
		self.__substitute_compvars()
		self.__substitute_vars(self.__intvars, self.__nodesrc)
		self.__substitute_vars(self.__extvars, self.__nodedst)
		print "**************"
		print self.__comprun_xml
		print "**************"
		return RetVal.CODE_SUCCESS

	def run(self):
		"""\brief substitute the variables into the composition to get 
		an xml running composition
		\return (\c RetVal)
		"""
		self.__comprun_xml = self.__comp_xml
		self.__substitute_compvars()
		self.__substitute_vars(self.__intvars, self.__nodesrc)
		self.__substitute_vars(self.__extvars, self.__nodedst)
		self.__get_datafiles()
		return RetVal.CODE_SUCCESS

#####################################
class Node(object):
	def __init__(self, node_id = None):
		self.__node_id = node_id
		self.__ip = None
		self.__port = None
		self.__port_in_use = None
	
	def __eq__(self, node): return self.__node_id == node.node_id
	
	def __hash__(self):	return hash(self.__node_id)

	@property
	def node_id(self): return self.__node_id

	@property
	def ip(self): return self.__ip

	@property
	def port(self): return self.__port

	@property
	def port_in_use(self): return self.__port_in_use

	def assign(self, ip, port, port_in_use):
		self.__ip = ip
		self.__port = port
		self.__port_in_use = port_in_use
