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

from twisted.python import log
import sqlite3, cPickle, jsonpickle
import threading, time, Queue

from core.utils import RetVal
from core.returnvalue import *

class CompOrphan(threading.Thread):
	def __init__(self, dbnodes, rescue_queue, dead_nodes_queue):
		threading.Thread.__init__(self)
		self.__name = "CompOrphan"
		self.__dbnodes = dbnodes
		self.__running = False
		self.__cond = threading.Condition()
		self.__rescue_queue = rescue_queue
		self.__dead_nodes_queue = dead_nodes_queue
		self.setDaemon(True)

	def run(self):
		with self.__cond: self.__running = True
		while True:
			with self.__cond:
				if not self.__running: break
			(ip,port) = self.__dead_nodes_queue.get()
			comps = self.__orphan_comps(ip,port)
			log.msg("%d running composition(s) died" % len(comps), system = self.__name)
			for temp_id,compobj in comps: 
				comp = cPickle.loads(str(compobj))
				CompUtils.delete_comp(self.__dbnodes, temp_id, comp)
				self.__rescue_queue.put( (temp_id,comp) )
			self.__dead_nodes_queue.task_done()
	
	def stop(self):
		with self.__cond: self.__running = False
		log.msg("stopping", system = self.__name)

	def __orphan_comps(self, ip, port):
		with sqlite3.connect(self.__dbnodes) as conn:
			retcode = conn.execute("select temp_id,compobj from comps where ipsrc = ? and sport = ?", (ip,port))
		return [comp for comp in retcode]

##################################################
class CompHandler(threading.Thread):
	def __init__(self, dbnodes, run_queue, rescue_queue):
		threading.Thread.__init__(self)
		self.__name = "CompHandler"
		self.__dbnodes = dbnodes
		self.__run_queue = run_queue
		self.__rescue_queue = rescue_queue
		self.__running = False
		self.__cond = threading.Condition()
		self.setDaemon(True)

	def __start_comp(self, comp):
		return (comp.comprun_xml if comp.run() is RetVal.CODE_SUCCESS else None)

	def __update_comp(self, comp):
		return (comp.comprun_xml if comp.update() is RetVal.CODE_SUCCESS else None)

	def __rescue_comp(self, comp):
		return (comp.comprun_xml if comp.rescue() is RetVal.CODE_SUCCESS else None)

	def __parse_retval(self, value, temp_id, comp, action):
		"""the action was successful
		if start_composition: save the comp into the db
		if stop_composition: delete the comp from the db
		"""
		r = jsonpickle.decode(value)
		code, msg = r.get_code(), r.get_msg()
		log.msg("retval %d while %s:%s" % (code,action,msg), system = self.__name)
		success = code is ReturnValue.CODE_SUCCESS
		if action == 'start_composition' and success:
			CompUtils.save_comp(self.__dbnodes, temp_id, comp)
		elif action == 'start_composition' and not success:
			self.__rescue_queue.put( (temp_id, comp) ) 
		elif action == 'stop_composition' and success: 
			CompUtils.delete_comp(self.__dbnodes, temp_id, comp)
		elif action == 'stop_composition' and not success: 
			CompUtils.delete_comp(self.__dbnodes, temp_id, comp)

	def __parse_error(self, error, temp_id, comp, action):
		comp_id = comp.comp_id
		log.msg("error on comp id=%s [temp id=%s] while %s: %s" % (comp_id,temp_id, action, str(error)), system = self.__name)
		if action == 'start_composition':
			self.__rescue_queue.put( (temp_id, comp) ) 
		elif action == 'stop_composition': 
			CompUtils.delete_comp(self.__dbnodes, temp_id, comp)

	def run(self):
		with self.__cond: self.__running = True
		while True:
			with self.__cond:
				if not self.__running: break
			(temp_id,comp,action) = self.__run_queue.get()
			ip,port = comp.nodesrc.ip, comp.nodesrc.port
			comp_id = comp.comp_id
			if action == 'start_composition': 
				tmp = self.__start_comp(comp)
				if len(comp.datafiles): args = (tmp,comp.datafiles)
				else: args = (tmp,)
			elif action == 'update_composition': args = self.__update_comp(comp)
			elif action == 'rescue_composition': 
				args = (self.__rescue_comp(comp),)
				action = 'update_composition'
			elif action == 'stop_composition': args = (comp_id,)
			log.msg("%s id=%s on node %s:%d" % (action,comp_id,ip,port), system = self.__name)
			retcode = CompUtils.query(ip, port, action, *args)
			retcode.addCallback(self.__parse_retval,temp_id,comp,action).addErrback(self.__parse_error, temp_id,comp,action)
			self.__run_queue.task_done()
	
##################################################
class CompRescue(threading.Thread):
	def __init__(self, dbnodes, run_queue, rescue_queue):
		threading.Thread.__init__(self)
		self.__name = "CompRescue"
		self.__dbnodes = dbnodes
		self.__run_queue = run_queue
		self.__rescue_queue = rescue_queue
		self.__running = False
		self.__cond = threading.Condition()
		self.setDaemon(True)

	def run(self):
		with self.__cond: self.__running = True
		while True:
			with self.__cond:
				if not self.__running: break
			(temp_id, comp) = self.__rescue_queue.get()
			rescued_comps = self.__rescue_comp(temp_id,comp)
			if len(rescued_comps):
				self.__run_queue.put((temp_id,rescued_comps[0],'start_composition'))
			if len(rescued_comps) > 1:
				[self.__run_queue.put((temp_id,res_comp,'update_composition')) for res_comp in rescued_comps[1:]]
			self.__rescue_queue.task_done()
	
	def stop(self):
		with self.__cond: self.__running = False
		log.msg("stopping", system = self.__name)

	def __rescue_comp(self, temp_id, comp):
		"""return an array or rescued comps"""
		(ip_dead,port_dead,port_in_use_dead) = (comp.nodesrc.ip,comp.nodesrc.port, comp.nodesrc.port_in_use)
		comp_id = comp.comp_id
		node = self.__select_nodes(temp_id,comp_id)
		if not len(node): 
			log.msg("no nodes, impossible to rescue", system = self.__name)
			return []
		(ip,port,port_in_use) = node[0]
		log.msg("rescuing composition on node %s:%d" % (ip,port), system = self.__name)
		comp.assign('src',ip,port,port_in_use)
		neighbor_comps = self.__get_neighbors_comps(ip_dead,port_dead)
		[n_comp.assign('dst',ip, port, port_in_use) for n_comp in neighbor_comps]
		rescued_comps = [comp] + neighbor_comps
		return rescued_comps
	
	def __get_neighbors_comps(self, ipdst, dport):
		with sqlite3.connect(self.__dbnodes) as conn:
			conn.text_factory = str
			retcode = conn.execute("select compobj from comps where ipdst = ? and dport = ?", (ipdst,dport))
			#retcode = conn.execute("select * from comps where ipdst = ? and dport = ?", (ipdst,dport))
			comps_db = [row[0] for row in retcode]
		return [cPickle.loads(str(comp)) for comp in comps_db]

	# FIX THIS: function more or less taken from Controller
	def __select_nodes(self, temp_id, comp_id,num_nodes = 1):
		with sqlite3.connect(self.__dbnodes) as conn:
			conn.text_factory = str
			#retcode = conn.execute("select ip,port from bmnodes where not exists (select ipsrc,sport from comps where temp_id = ? and comp_id = ? and bmnodes.ip = comps.ipsrc and bmnodes.port = comps.sport) limit ?", (temp_id, comp_id, num_nodes) )
			retcode = conn.execute("select ip,port from bmnodes where not exists (select ipsrc,sport from comps where temp_id = ? and bmnodes.ip = comps.ipsrc and bmnodes.port = comps.sport) limit ?", (temp_id, num_nodes) )
		import random
		#FIX THIS: pick a random port?
		return [ (ip,port,random.randint(10000,10100)) for (ip,port) in retcode ]

##################################################
from txjsonrpc.web.jsonrpc import Proxy

class CompUtils(object):
	
	@classmethod
	def query(cls, ip, port, action, *args):
		daemon = Proxy('http://%s:%d/' % (ip,port))
		return daemon.callRemote(action, *args)

	@classmethod
	def delete_comp(cls, dbnodes, temp_id, comp):
		comp_id = comp.comp_id
		log.msg("deleting comp id=%s [temp id=%s] from db" % (comp_id,temp_id), system = cls.__name__)
		(ipsrc,sport) = (comp.nodesrc.ip, comp.nodesrc.port)
		with sqlite3.connect(dbnodes) as conn:
	 		retcode = conn.execute("delete from comps where temp_id = ? and comp_id = ? and ipsrc = ? and sport = ?", (temp_id,comp_id,ipsrc,sport))
		return (RetVal.CODE_SUCCESS if retcode.rowcount>0 else RetVal.CODE_FAILURE)

	@classmethod
	def	save_comp(cls, dbnodes, temp_id, comp):
		comp_id = comp.comp_id
		log.msg("saving comp id=%s [temp id=%s] on db" % (comp_id,temp_id), system = cls.__name__)
		(ipsrc,sport) = (comp.nodesrc.ip, comp.nodesrc.port)
		(ipdst,dport) = (comp.nodedst.ip, comp.nodedst.port)
		compobj = cPickle.dumps(comp, cPickle.HIGHEST_PROTOCOL)
		with sqlite3.connect(dbnodes) as conn:
	 		try:
	 			conn.execute("insert or replace into comps (temp_id,comp_id,ipsrc,sport,ipdst,dport,compobj) values (?,?,?,?,?,?,?)", (temp_id,comp_id,ipsrc,sport,ipdst,dport,sqlite3.Binary(compobj)))
	 		except sqlite3.IntegrityError: 
				log.msg("error while saving comp id=%s [temp id=%s] on db (is it already in there?)" % (comp_id,temp_id), system = self.__name)
				return RetVal.CODE_FAILURE
		return RetVal.CODE_SUCCESS

