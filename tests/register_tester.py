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
import os

test_path = os.getcwd()

def print_results(value):
	r = jsonpickle.decode(value)
	print "ok", str(r)

def print_error(error):
	print 'error', error

class RegisterTester(unittest.TestCase):

	#note: setUp is called right before each test
	def setUp(self):
		self.NODE_PORT = 7080
		self.REG_PORT = 7090
		self.daemon = Proxy('http://127.0.0.1:%d/' % self.REG_PORT)
		self.PORTS = range(5050,5058)

	# REGISTER
	def test_register(self):
		import random
		if random.randint(0,10) <=5: ports = self.PORTS
		else: ports = range(5070,5075)
		cpus,cores,memory = 2, 1,400
		specs = [cpus, cores, memory]
		d = self.daemon.callRemote('register','127.0.1.1',self.NODE_PORT, ports, specs)
		d.addCallback(print_results)
		return d
	
	def test_register2(self):
		cpus,cores,memory = 2, 1,400
		specs = [cpus, cores, memory]
		d = self.daemon.callRemote('register','127.0.0.1',self.NODE_PORT+1, self.PORTS, specs)
		d.addCallback(print_results)
		return d

	def test_unregister(self):
		d = self.daemon.callRemote('unregister','10.1.2.137',self.NODE_PORT)
		d.addCallback(print_results)
		return d

	def test_keepalive(self):
		d = self.daemon.callRemote('keepalive','127.0.0.1',self.NODE_PORT, self.PORTS)
		d.addCallback(print_results)
		return d
	
	def test_keepalive_rand(self):
		import random
		port = random.randint(100,200)
		d = self.daemon.callRemote('keepalive','127.0.0.1',port, self.PORTS)
		d.addCallback(print_results)
		return d

	#test_unregister.skip = "disabled locally"
	test_register.skip = "disabled locally"
	test_register2.skip = "disabled locally"
	test_keepalive.skip = "disabled locally"
	test_keepalive_rand.skip = "disabled locally"


