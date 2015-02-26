# Blockmon Controller

This codes implements the Blockmon controller, that is the controller
for deploying and checking the execution of distributed applications 
that run over a set of Blockmon nodes.

Before proceeding, make sure you have at least a working instance of a 
[Blockmon node](https://github.com/blockmon/blockmon.git), so that you 
have something to control.

Additional documentation on the capabilities of the node and of the 
controller at the following links:

* [Blockmon: Toward High-Speed Composable Network Traffic Measurement](http://www.ing.unibs.it/~maurizio.dusi/pub/blockmon-infocom2013.pdf), IEEE INFOCOM Mini-Conference, 2013

* [Stream-monitoring with BlockMon: convergence of network measurements and data analytics platforms](http://www.ing.unibs.it/~maurizio.dusi/pub/dblockmon-ccr2013.pdf), ACM SIGCOMM Computer Communication Review, 2013


## Install

In order to run, the Blockmon controller requires:

* sqlite library (http://www.sqlite.org), tested with sqlite3 v.3.7.9
* twisted library (easy_install twisted), tested with twisted v.15.0
* txjsonrpc (easy_install txJSON-RPC), tested with txjsonrpc v.0.3.1
* jsonpickle (easy_install jsonpickle), tested with jsonpickle v.0.9.0


## Run the Blockmon controller

* In debug mode

    `twistd -n bmc -f myconfig`

* Otherwise

    `twistd -l bmcontroller.log bmc -f myconfig`

    To rotate the logfile bmcontroller.log:

    ```
    kill -SIGUSR1 `cat twistd.pid`
    ```

myconfig file is a copy of the config file, where you have set the parameters. At startup, the controller creates the variables as specified in the [MAIN] section of the config file is they do not exist already.


## Run distribute compositions

* **Start the system**
  1. start the Blockmon controller, please see instruction under the section *Run the Blockmon controller*
  2. on each blockmon node, 

    `cd daemon`

    `chown u+x core/bmprocess.py`

    `sudo python bmdaemon.py myconfig`

* **Template definition**
  1. Write a template definition, e.g., see tests/templatedef.xml
  2. Send it to the blockmon controller, e.g., see the function test\_put\_template in tests/contr\_tester.py

* **Template instance**
  1. Write a template instance, e.g., see tests/templateins.xml
  2. Invoke a template instance, e.g., see the function test\_invoke\_template in tests/contr\_tester.py
  3. Get values from a running template,e.g., see the function test\_read\_variable in tests/contr\_tester.py
  4. Stop a template instance, e.g., see the function test\_stop\_template in tests/contr\_tester.py)


## Tests

The directory tests contains the tester.py files to run some tests, together with some example templates (definition and instance) xml files.

To run the tests:

`cd tests`

`trial --random=10 *_tester.py`


## Bugs & Questions

Please write to <blockmon@neclab.eu>
