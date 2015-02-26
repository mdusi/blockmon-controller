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

from txjsonrpc.web.jsonrpc import Proxy
import jsonpickle
from twisted.trial import unittest

import os,sys
sys.path.append(os.getcwd() + '/../twisted/plugins')
from core.returnvalue import *

def print_results(value):
	r = jsonpickle.decode(value)
	print str(r)

def print_error(error):
	print 'error', error

class ControllerTester(unittest.TestCase):

	#note: setUp is called right before each test
	def setUp(self):
		self.PORT = 7070
		self.daemon = Proxy('http://127.0.0.1:%d/' % self.PORT)
		
		self.tdef = "../templatedef.xml"
		self.tins = "../templateins.xml"
		self.tdef_id = "pkt_counter_aggregator"
		self.tins_id = "pkt_counter_aggregator"

	def test_put_template(self):
		f = open(self.tdef, "r")
		fxml = f.read()
		f.close()
		d = self.daemon.callRemote('put_template',fxml)
		d.addCallback(print_results).addErrback(print_error)
		return d

	def test_remove_template(self):
		d = self.daemon.callRemote('remove_template',self.tdef_id)
		d.addCallback(print_results).addErrback(print_error)
		return d
	
	def test_get_templates(self):
		d = self.daemon.callRemote('get_templates')
		d.addCallback(print_results).addErrback(print_error)
		return d
	
	def test_expand_template(self):
		f = open(self.tins, "r")
		fxml = f.read()
		f.close()
		d = self.daemon.callRemote('expand_template', fxml)
		d.addCallback(print_results).addErrback(print_error)
		return d
	
	def test_invoke_template(self):
		f = open(self.tins, "r")
		fxml = f.read()
		f.close()
		d = self.daemon.callRemote('invoke_template', fxml)
		d.addCallback(print_results).addErrback(print_error)
		return d
	
	def test_invoke_template_nodes(self):
		f = open(self.tins, "r")
		fxml = f.read()
		f.close()
		nodes = [('127.0.0.1',7081,10005),('127.0.0.1',7082,10006)]
		d = self.daemon.callRemote('invoke_template', fxml, nodes)
		d.addCallback(print_results).addErrback(print_error)
		return d
	
	def test_stop_template(self):
		d = self.daemon.callRemote('stop_template',self.tins_id)
		d.addCallback(print_results).addErrback(print_error)
		return d

	def test_read_variable(self):
		temp_id, comp_id = self.tins_id, "step2"
		block_id, var_id = "counter", "pktcnt"
		print temp_id,comp_id,block_id,var_id
		d = self.daemon.callRemote('get_variable',temp_id, comp_id, block_id, var_id)
		d.addCallback(print_results).addErrback(print_error)
		return d

	def test_write_variable(self):
		temp_id, comp_id = self.tins_id, "step2"
		block_id, var_id = "counter", "reset"
		d = self.daemon.callRemote('write_variable',temp_id, comp_id, block_id, var_id, "1")
		d.addCallback(print_results).addErrback(print_error)
		return d

	def test_get_supported_topologies(self):
		d = self.daemon.callRemote('get_supported_topologies')
		d.addCallback(print_results).addErrback(print_error)
		return d
	
	def test_get_supported_blocks(self):
		d = self.daemon.callRemote('get_supported_blocks')
		d.addCallback(print_results).addErrback(print_error)
		return d
	
	def test_get_block_infos(self):
		block_types = ["PFQSource","PacketPrinter"]
		d = self.daemon.callRemote('get_block_infos', block_types)
		d.addCallback(print_results).addErrback(print_error)
		return d
	
	def test_save_datafile(self):
		import base64
		f = open("../datafile.zip", "rb")
		fbin = base64.b64encode(f.read())
		f.close()
		d = self.daemon.callRemote('save_datafile', 'test.zip',fbin)
		d.addCallback(print_results).addErrback(print_error)
		return d
	

	test_put_template.skip = "disabled locally"
	#test_remove_template.skip = "disabled locally"
	test_expand_template.skip = "disabled locally"
	test_invoke_template.skip = "disabled locally"
	test_invoke_template_nodes.skip = "disabled locally"
	test_stop_template.skip = "disabled locally"
	#test_read_variable.skip = "disabled locally"
	test_write_variable.skip = "disabled locally"
	test_get_supported_blocks.skip = "disabled locally"
	test_get_block_infos.skip = "disabled locally"
	test_get_supported_topologies.skip = "disabled locally"
	test_get_templates.skip = "disabled locally"
	test_save_datafile.skip = "disabled locally"
