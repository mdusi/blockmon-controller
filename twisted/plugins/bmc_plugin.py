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

from zope.interface import implements
from twisted.python import usage, log
from twisted.plugin import IPlugin
from twisted.application.service import IServiceMaker
from twisted.application import internet, service
from twisted.web import server

import Queue
import os, sqlite3, sys
sys.path.append(os.getcwd() + "/twisted/plugins") 
from core.utils import Parser
from core.register import Register
from core.controller import Controller

class Options(usage.Options):
    optParameters = [["config", "f", "config", "config file"]]

class BCDaemon(object):
	implements(IServiceMaker, IPlugin)
	tapname = "bmc"
	description = "Blockmon Controller plugin"
	options = Options

	def opendb(self, db_name, schema_name):
		db_is_new = not os.path.exists(db_name)
		with sqlite3.connect(db_name) as conn:
			if db_is_new:
				print "creating database", db_name
				with open(schema_name,'r') as fid:
					schema = fid.read()
				conn.executescript(schema)

	def makeService(self, options):
		config = Parser(options['config'])
		top_service = service.MultiService()

		db_bmnodes = config.dbnodes
		nodeschema_name = 'nodes.sql'
		self.opendb(db_bmnodes, nodeschema_name)
		
		db_templates = config.dbtemplates
		templateschema_name = 'templates.sql'
		self.opendb(db_templates, templateschema_name)

		# shared queue for dead nodes
		dead_nodes_queue = Queue.Queue()

		### server for node registration ###
		reg_port = config.node_registration_port
		reg = Register(port = reg_port, dbnodes = db_bmnodes, queue = dead_nodes_queue)
		node = server.Site(reg, logPath="/dev/null")
		node.noisy = False
		node_iface = internet.TCPServer(reg_port, node)
		node_iface.setServiceParent(top_service)

		### server for external ###
		listening_port = config.ext_listening_port
		contr = Controller(port = listening_port, dbnodes = db_bmnodes, dbtemplates = db_templates, datafile_dir = config.datafile_dir, queue = dead_nodes_queue)
		ext = server.Site(contr, logPath="/dev/null")
		ext.noisy = False
		ext_iface = internet.TCPServer(listening_port, ext)
		ext_iface.setServiceParent(top_service)
		
		### return top service
		return top_service

bcd = BCDaemon()
