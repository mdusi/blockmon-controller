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

from twisted.internet import defer, threads
from twisted.web import server
from txjsonrpc.web import jsonrpc
from txjsonrpc.web.jsonrpc import Proxy
from twisted.python import log

import jsonpickle, sqlite3, cPickle
import Queue

from core.utils import RetVal
from core.topology import Topology
from core.templatedef import TemplateDefinition
from core.templateins import TemplateInstance
from core.templaterun import TemplateRun
from core.returnvalue import *
from core.block import VariableInfo, BlockInfo
from core.comphandler import *

class Controller(jsonrpc.JSONRPC,object):
	def __init__(self, dbnodes, dbtemplates, datafile_dir, queue, port = None):
		self.__name = "Controller"
		self.__port = port
		self.__dbnodes = dbnodes
		self.__dbtemplates = dbtemplates
		self.__datafile_dir = datafile_dir
		self.__run_queue = Queue.Queue()
		self.__rescue_queue = Queue.Queue()
		self.__dead_nodes_queue = queue
		# look for orphan comps
		self.__corph = CompOrphan(self.__dbnodes, self.__rescue_queue, self.__dead_nodes_queue)
		self.__corph.start()
		# rescue comps
		self.__cres = CompRescue(self.__dbnodes, self.__run_queue, self.__rescue_queue)
		self.__cres.start()
		# start/stop compositions
		self.__chand = CompHandler(self.__dbnodes, self.__run_queue, self.__rescue_queue)
		self.__chand.start()

	def __get_tempdef_from_id(self, temp_id):
		with sqlite3.connect(self.__dbtemplates) as conn:
			retcode = conn.execute("select template from templatedefs where temp_id = ?", (temp_id,))
		temp = retcode.fetchone()
		return ( TemplateDefinition(temp[0]) if temp else None)

	def __select_nodes(self, num_nodes = 1):
		with sqlite3.connect(self.__dbnodes) as conn:
			conn.text_factory = str
			retcode = conn.execute("select ip,port from bmnodes limit ?", (num_nodes,))
		import random
		#FIX THIS: pick a random port?
		return [ (ip,port,random.randint(10000,10100)) for (ip,port) in retcode ]

	#################################
	# JSONRPC: TEMPLATE DEFINITIONS #
	#################################
	def __put_template(self, temp_id, temp):
		with sqlite3.connect(self.__dbtemplates) as conn:
			try:
				conn.execute("insert into templatedefs (temp_id,template) values (?,?)", (temp_id,temp))
			except sqlite3.IntegrityError: 
				return RetVal.CODE_FAILURE
		return RetVal.CODE_SUCCESS

	def __remove_template(self, temp_id):
		with sqlite3.connect(self.__dbtemplates) as conn:
			retcode = conn.execute("delete from templatedefs where temp_id = ? ", (temp_id,))
		return retcode.rowcount

	def __get_templates(self):
		with sqlite3.connect(self.__dbtemplates) as conn:
			retcode = conn.execute("select temp_id from templatedefs")
		return [ row[0] for row in retcode ]

	@defer.inlineCallbacks
	def jsonrpc_put_template(self, temp):
		"""\brief receive template definitions
		\param temp (\c string) xml template definition
		\return (\c ReturnValue) Value member is empty
		"""
		log.msg("received put_template definition request", system = self.__name)
		tempdef = TemplateDefinition(temp)
		if tempdef.dom is None:
			r = ReturnValue(ReturnValue.CODE_FAILURE, "not well-formed template", None)
			defer.returnValue(jsonpickle.encode(r))
		temp_id = tempdef.temp_id
		retcode = yield threads.deferToThread(self.__put_template, temp_id, temp)
		msg = ("added template definition" if retcode is RetVal.CODE_SUCCESS else "template already exists")
		r = ReturnValue(ReturnValue.CODE_SUCCESS, msg, None)
		defer.returnValue(jsonpickle.encode(r))

	@defer.inlineCallbacks
	def jsonrpc_remove_template(self, temp_id):
		"""\brief remove a given template definition based on the template definition id
		\param temp_id (\c string) template definition ID
		\return (\c ReturnValue) Value member is empty
		"""
		log.msg("received remove_template definition request", system = self.__name)
		deleted = yield threads.deferToThread(self.__remove_template, temp_id)
		msg = ("deleted template definition" if deleted else "template does not exist")
		r = ReturnValue(ReturnValue.CODE_SUCCESS, msg, None)
		defer.returnValue(jsonpickle.encode(r))

	@defer.inlineCallbacks
	def jsonrpc_get_templates(self):
		"""\brief return the list of existing templates definitions 
		\return (\c ReturnValue) The template definitions' XML (list[string])
		"""
		log.msg("received get_templates request", system = self.__name)
		templates = yield threads.deferToThread(self.__get_templates)
		r = ReturnValue(ReturnValue.CODE_SUCCESS, "list of template definitions", templates)
		defer.returnValue(jsonpickle.encode(r))
	
	###############################
	# JSONRPC: TEMPLATE INSTANCES #
	###############################

	def __is_temp_running(self,temp_id):
		with sqlite3.connect(self.__dbnodes) as conn:
			retcode = conn.execute("select comp_id from comps where temp_id = ?", (temp_id,))
		comps = [row[0] for row in retcode]
		return (True if len(comps) else False)

	def __invoke_template(self, temp, ext_nodes):
		"""\brief invoke a template instance
		\param temp (\c string) xml template instance
		\param ext_nodes (\c list) list of nodes
		\return (\c RetVal) 
		"""
		tins = TemplateInstance(temp)
		temp_id = tins.temp_id
		if self.__is_temp_running(temp_id):
			log.msg("template already running", system = self.__name)
			return RetVal.CODE_SUCCESS
		tdef = self.__get_tempdef_from_id(temp_id)
		if not tdef:
			log.msg("no template definition for the given id", system = self.__name)
			return RetVal.CODE_FAILURE
		t = TemplateRun(tdef, tins, self.__datafile_dir)
		if t.install() is RetVal.CODE_FAILURE:
			log.msg("error while installing template", system = self.__name)
			return RetVal.CODE_FAILURE
		num_nodes = t.get_num_nodes()
		if len(ext_nodes) > 0: nodes = ext_nodes
		else: nodes = self.__select_nodes(num_nodes = num_nodes)

		if len(nodes) < num_nodes :
			log.msg("%d node(s) available (%d needed)" % (len(nodes),num_nodes), system = self.__name)
			return RetVal.CODE_FAILURE
		#if t.assign_nodes(nodes) is RetVal.CODE_FAILURE:
		if t.assign_nodes(nodes)[0] is RetVal.CODE_FAILURE:
			log.msg("error while assigning nodes to template", system = self.__name)
			return RetVal.CODE_FAILURE
		log.msg("send comps to the run queue", system = self.__name)
		for comp in t.compsrun: 
			self.__run_queue.put( (temp_id,comp,'start_composition') )
		return RetVal.CODE_SUCCESS

	def __stop_template(self, temp_id):
		log.msg("stopping template instance %s" % temp_id, system = self.__name)
		with sqlite3.connect(self.__dbnodes) as conn:
			retcode = conn.execute("select compobj from comps where temp_id = ?", (temp_id,))
		comps_db = [comp[0] for comp in retcode]
		for comp_db in comps_db:
			comp = cPickle.loads(str(comp_db))
			self.__run_queue.put( (temp_id,comp,'stop_composition') )
		return RetVal.CODE_SUCCESS

	def __expand_template(self, temp):
		"""\brief expand a template instance
		\param temp (\c string) xml template instance
		\return (\c RetVal,list) list is None or the list of nodes 
		"""
		tins = TemplateInstance(temp)
		temp_id = tins.temp_id
		if self.__is_temp_running(temp_id):
			log.msg("template already running", system = self.__name)
			return (RetVal.CODE_SUCCESS, None)
		tdef = self.__get_tempdef_from_id(temp_id)
		if not tdef:
			log.msg("no template definition for the given id", system = self.__name)
			return (RetVal.CODE_FAILURE, None)
		t = TemplateRun(tdef, tins, self.__datafile_dir)
		if t.install() is RetVal.CODE_FAILURE:
			log.msg("error while installing template", system = self.__name)
			return (RetVal.CODE_FAILURE, None)
		num_nodes = t.get_num_nodes()
		nodes = self.__select_nodes(num_nodes = num_nodes)
		if len(nodes) < num_nodes :
			log.msg("%d node(s) available (%d needed)" % (len(nodes),num_nodes), system = self.__name)
			return (RetVal.CODE_FAILURE, None)
		(retval,all_info) = t.assign_nodes(nodes)
		if retval is RetVal.CODE_FAILURE:
			log.msg("error while assigning nodes to template", system = self.__name)
			return (RetVal.CODE_FAILURE, None)
		return (RetVal.CODE_SUCCESS,all_info)
		#return (RetVal.CODE_SUCCESS,nodes)

	@defer.inlineCallbacks
	def jsonrpc_invoke_template(self, temp, nodes = []):
		"""\brief listen for template invocation request
		\param temp (\c string) xml template instance
		\param auth (\c boolean) authorization from WPOC needed
		\return (\c ReturnValue) Value member is empty
		"""
		log.msg("received invoke_template request", system = self.__name)
		tempins = TemplateInstance(temp)
		if tempins.dom is None:
			r = ReturnValue(ReturnValue.CODE_FAILURE, "not well-formed template", None)
			defer.returnValue(jsonpickle.encode(r))
		retcode_dict = None
		retcode = yield threads.deferToThread(self.__invoke_template,temp, nodes)
		if retcode is RetVal.CODE_SUCCESS:
			code,msg = ReturnValue.CODE_SUCCESS,"invocation sent to nodes"
		else:
			code,msg = ReturnValue.CODE_FAILURE,"error during invocation"
		r = ReturnValue(code, msg, None)
		defer.returnValue(jsonpickle.encode(r))

	@defer.inlineCallbacks
	def jsonrpc_stop_template(self, temp_id):
		"""\brief stop a running template instance 
		\param temp_id (\c string) template instance ID
		\return (\c ReturnValue) Value member is empty
		"""
		log.msg("received stop_template request", system = self.__name)
		retcode = yield threads.deferToThread(self.__stop_template,temp_id)
		r = ReturnValue(ReturnValue.CODE_SUCCESS, "stop request sent to nodes", None)
		defer.returnValue(jsonpickle.encode(r))

	@defer.inlineCallbacks
	def jsonrpc_expand_template(self, temp):
		"""\brief listen for requests to expand template
		\param temp (\c string) xml template instance
		\return (\c ReturnValue) Value member contains a list of (ip,port,port_in_use,comp_xml)
		"""
		log.msg("received expand_template request", system = self.__name)
		tempins = TemplateInstance(temp)
		if tempins.dom is None:
			r = ReturnValue(ReturnValue.CODE_FAILURE, "not well-formed template", None)
			defer.returnValue(jsonpickle.encode(r))
		retcode_dict = None
		(retcode,nodes) = yield threads.deferToThread(self.__expand_template,temp)
		if retcode is RetVal.CODE_SUCCESS:
			code,msg = ReturnValue.CODE_SUCCESS,"template expanded"
			value = nodes
		else:
			code,msg = ReturnValue.CODE_FAILURE,"error during expansion"
			value = None
		r = ReturnValue(code, msg, value)
		defer.returnValue(jsonpickle.encode(r))

	#######################
	# JSONRPC: BLOCK INFO #
	#######################

	def __parse_get_variable(self, ret_values):
		outmsg = []
		for (success,retval) in ret_values:
			if success: outmsg.append(jsonpickle.decode(retval))
		return outmsg

	def __get_variable(self, temp_id, comp_id, variable):
		with sqlite3.connect(self.__dbnodes) as conn:
			conn.text_factory = str
			retcode = conn.execute("select ipsrc,sport from comps where temp_id = ? and comp_id = ?", (temp_id, comp_id))
		nodes = [node for node in retcode]
		deflist = [CompUtils.query(ip, port, 'read_variables', comp_id,variable) for ip,port in nodes]
		d = defer.DeferredList(deflist,consumeErrors=1)
		d.addCallback(self.__parse_get_variable)
		return defer.DeferredList(deflist,consumeErrors=1)

	def __write_variable(self, temp_id, comp_id, variable):
		with sqlite3.connect(self.__dbnodes) as conn:
			conn.text_factory = str
			retcode = conn.execute("select ipsrc,sport from comps where temp_id = ? and comp_id = ?", (temp_id, comp_id))
		nodes = [node for node in retcode]
		deflist = [CompUtils.query(ip, port, 'write_variables', comp_id,variable) for ip,port in nodes]
		d = defer.DeferredList(deflist,consumeErrors=1)
		d.addCallback(self.__parse_get_variable)
		return defer.DeferredList(deflist,consumeErrors=1)

	@defer.inlineCallbacks
	def jsonrpc_get_variable(self, temp_id, comp_id, block_id, var_id):
		"""\brief get the value of a variable
		\param temp_id (\c string) template instance ID
		\param comp_id (\c string) composition ID
		\param block_id (\c string) block ID
		\param var_id (\c string) variable ID
		\return (\c ReturnValue) The values (list[ReturnValue])
		"""
		log.msg("received get_variable request", system = self.__name)
		variable = [ [ block_id, var_id, "", "read" ] ]
		retvals = yield self.__get_variable(temp_id, comp_id, variable)
		r = ReturnValue(ReturnValue.CODE_SUCCESS,None,retvals)
		defer.returnValue(jsonpickle.encode(r))
	
	@defer.inlineCallbacks
	def jsonrpc_write_variable(self, temp_id, comp_id, block_id, var_id, var_val):
		"""\brief get the value of a variable
		\param temp_id (\c string) template instance ID
		\param comp_id (\c string) composition ID
		\param block_id (\c string) block ID
		\param var_id (\c string) variable ID
		\param var_val (\c string) value to assign to the variable ID
		\return (\c ReturnValue) The values (list[ReturnValue])
		"""
		log.msg("received write_variable request", system = self.__name)
		variable = jsonpickle.encode([VariableInfo(block_id, var_id, "", "write", var_val)])
		retvals = yield self.__write_variable(temp_id, comp_id, variable)
		r = ReturnValue(ReturnValue.CODE_SUCCESS,None,retvals)
		defer.returnValue(jsonpickle.encode(r))

	#########################
	# JSONRPC: GENERAL INFO #
	#########################

	def __get_blocks_list(self):
		with sqlite3.connect(self.__dbnodes) as conn:
			retcode = conn.execute("select distinct name from blocks")
		return [row[0] for row in retcode]

	def __get_blocks_info(self, block_types):
		block_infos = []
		with sqlite3.connect(self.__dbnodes) as conn:
			for name in block_types:
				retcode = conn.execute("select distinct info from blocks where name = ?", (name,))
				try: info = retcode.fetchone()[0]
				except TypeError: info = "no info available"
				block_infos.append(info)
		return [cPickle.loads(str(b)) for b in block_infos]

	def __save_datafile(self, fname, databin):
		import base64
		data = base64.b64decode(databin)
		f = open(self.__datafile_dir +'/'+fname,'w')
		try: f.write(data)
		except: return RetVal.CODE_FAILURE
		f.close()
		return RetVal.CODE_SUCCESS

	@defer.inlineCallbacks
	def jsonrpc_get_supported_blocks(self):
		"""\brief return the list of supported blocks,
		\return (\c ReturnValue) The list of blocks (list[string])
		"""
		log.msg("received get_supported_blocks request", system = self.__name)
		blocks = yield threads.deferToThread(self.__get_blocks_list)
		r = ReturnValue(ReturnValue.CODE_SUCCESS, "supported blocks", blocks)
		defer.returnValue(jsonpickle.encode(r))

	@defer.inlineCallbacks
	def jsonrpc_get_block_infos(self, block_types):
		"""\brief return the info about the given set of blocks,
		\param (\c list[string]) block_types the block types (e.g., ["PFQSource"]
		\return (\c ReturnValue) The information (list[BlockInfo])
		"""
		log.msg("received get_blocks_info request", system = self.__name)
		block_infos = yield threads.deferToThread(self.__get_blocks_info, block_types)
		msg = "block infos"
		r = ReturnValue(ReturnValue.CODE_SUCCESS, msg, block_infos)
		defer.returnValue(jsonpickle.encode(r))

	def jsonrpc_get_supported_topologies(self):
		"""\brief return the list of supported topology
		\return (\c ReturnValue) The list of supported topologies
		"""
		log.msg("received get_supported_topology request", system = self.__name)
		r = ReturnValue(ReturnValue.CODE_SUCCESS, "supported topologies", Topology.TOPO_TYPES)
		return jsonpickle.encode(r)
	
	@defer.inlineCallbacks
	def jsonrpc_save_datafile(self, fname, databin):
		"""\brief receive the datafile to send to nodes
		\param fname (\c string) file name
		\param databin (\c base64) b64 encoded file
		\return (\c ReturnValue) Value is empty
		"""
		log.msg("received save_datafile request", system = self.__name)
		retcode = yield threads.deferToThread(self.__save_datafile,fname,databin)
		r = ReturnValue(ReturnValue.CODE_FAILURE, "cannot save datafile", None)
		if retcode == RetVal.CODE_SUCCESS:
			r = ReturnValue(ReturnValue.CODE_SUCCESS, "datafile saved successfully", None)
		defer.returnValue(jsonpickle.encode(r))
