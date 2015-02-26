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
from twisted.python import log
from twisted.web import server
from txjsonrpc.web import jsonrpc

import time, sqlite3, jsonpickle, cPickle
from core.returnvalue import *
from core.host import HostSpecsInfo
from core.block import BlockInfo

class Register(jsonrpc.JSONRPC,object):

	def __init__(self, dbnodes, queue, port = None):
		self.__name = "Register"
		self.__port = port
		self.__dbnodes = dbnodes
		# garbage collector for bmnodes
		self.__dead_nodes_queue = queue
		self.__gc = GC(self.__dbnodes, self.__dead_nodes_queue)
		self.__gc.start()
	
	def __registration(self, ipaddr, port, priority, vcores):
		with sqlite3.connect(self.__dbnodes) as conn:
			conn.execute("insert or replace into bmnodes (ip,port,last_seen, priority, cores) values (?,?,?,?,?)", (ipaddr,port,int(time.time()), priority, vcores))
		msg = "registration successful from node %s:%d" % (ipaddr,port)
		log.msg(msg, system = self.__name)
		return ReturnValue(ReturnValue.CODE_SUCCESS, msg, None)

	def __supported_blocks(self, blocks, blocks_descr):
		descr = [cPickle.dumps(b, cPickle.HIGHEST_PROTOCOL) for b in blocks_descr]
		with sqlite3.connect(self.__dbnodes) as conn:
			for pos,bname in enumerate(blocks):
				try:
					conn.execute("insert into blocks (name,info) values (?,?)", (bname,sqlite3.Binary(descr[pos])))
				except sqlite3.IntegrityError: continue

	def __keepalive(self, ipaddr, port):
		with sqlite3.connect(self.__dbnodes) as conn:
			retcode = conn.execute("update bmnodes set last_seen = ? where ip = ? and port = ?", (int(time.time()),ipaddr,port))
		if not retcode.rowcount:
			msg = "keepalive from non-existing node %s:%d" % (ipaddr, port)
			retval = ReturnValue.CODE_FAILURE
		else:
			msg, retval = "keepalive successful", ReturnValue.CODE_SUCCESS
		#log.msg(msg, system = self.__name)
		#log.msg("keepalive from %s:%d" % (ipaddr,port), system = self.__name)
		return ReturnValue(retval, msg, None)

	def __unregistration(self, ipaddr, port):
		with sqlite3.connect(self.__dbnodes) as conn:
			retcode = conn.execute("delete from bmnodes where ip = ? and port = ?", (ipaddr,port))
		if not retcode.rowcount:
			msg = "node %s:%d is not registered" % (ipaddr, port)
			retval = ReturnValue.CODE_FAILURE
		else: 
			msg = "unregistration successful" 
			retval = ReturnValue.CODE_SUCCESS
		log.msg(msg, system = self.__name)
		return ReturnValue(retval, msg, None)

	@defer.inlineCallbacks
	def jsonrpc_register(self, ipaddr, port, specs, blocks, blocks_descr):
		"""\brief listen for registration sent by nodes
		\param ipaddr (\c string) node IP address
		\param port (\c int) listening port of the node
		\param specs (\c HostSpecsInfo) the host's specs as jsonpickle-encoded object
		\param blocks (\c list[string]) list of supported blocks 
		\param blocks_descr (\c list[BlockInfo]) list of blocks info as jsonpickle-encoded object
		\return (\c ReturnValue) Value member is empty
		"""
		host_specs = jsonpickle.decode(specs)
		# FIX THIS: map host specs into a priority value for node selection
		try: 
			host_priority = host_specs.get_memory()
			host_vcores = host_specs.get_n_cpus() * host_specs.get_cores_per_cpu()
		except: 
			host_priority = 0
			host_vcores = 1
		r = yield threads.deferToThread(self.__registration,ipaddr,port, host_priority, host_vcores)
		if len(blocks):
			descr = jsonpickle.decode(blocks_descr)
			b = yield threads.deferToThread(self.__supported_blocks, blocks, descr)
		defer.returnValue(jsonpickle.encode(r))

	@defer.inlineCallbacks
	def jsonrpc_keepalive(self, ipaddr, port):
		"""\brief listen for keepalive sent by nodes
		\param ipaddr (\c string) node IP address
		\param port (\c int) listening port of the node
		\return (\c ReturnValue) Value member is empty
		"""
		r = yield threads.deferToThread(self.__keepalive,ipaddr,port)
		defer.returnValue(jsonpickle.encode(r))

	@defer.inlineCallbacks
	def jsonrpc_unregister(self, ipaddr, port):
		"""\brief listen for unregistration sent by nodes
		\param ipaddr (\c string) node IP address
		\param port (\c int) listening port of the node
		\return (\c ReturnValue) Value member is empty
		"""
		r = yield threads.deferToThread(self.__unregistration,ipaddr,port)
		defer.returnValue(jsonpickle.encode(r))

##################################################
import time, threading, Queue
class GC(threading.Thread):
	def __init__(self, dbnodes, queue, TIMEOUT = 10):
		threading.Thread.__init__(self)
		self.__name = "GC-register"
		self.__dbnodes = dbnodes
		self.__TIMEOUT = TIMEOUT
		self.__running = False
		self.__dead_nodes_queue = queue
		self.__cond = threading.Condition()
		self.setDaemon(True)

	def run(self):
		with self.__cond: self.__running = True
		while True:
			with self.__cond:
				if not self.__running: break
			self.__gc_nodes()
			time.sleep(self.__TIMEOUT)

	def stop(self):
		with self.__cond: self.__running = False
		log.msg("stopping", system = self.__name)
	
	def __gc_nodes(self):
		with sqlite3.connect(self.__dbnodes) as conn:
			conn.text_factory = str
			retcode = conn.execute("select ip,port from bmnodes where ( ? - last_seen > ?)", (int(time.time()), self.__TIMEOUT))
			nodes = [(ip,port) for ip,port in retcode]
			if len(nodes): log.msg("%d node(s) died" % len(nodes), system = self.__name)
			[conn.execute("delete from bmnodes where ip = ? and port = ?", (ip,port)) for ip,port in nodes]
		[self.__dead_nodes_queue.put((ip,port)) for ip,port in nodes]
