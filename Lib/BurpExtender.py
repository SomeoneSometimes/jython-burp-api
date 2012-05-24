# -*- coding: utf-8 -*-

'''
BurpExtender
~~~~~~~~~~~~

BurpExtender is a proxied class that implements the burp.IBurpExtender
interface. It is what makes Jython <-> Burp possible.
'''
from java.lang import System
from org.python.core import PySystemState
from org.python.util import JLineConsole, PythonInterpreter
from burp import IBurpExtender

from threading import Thread
import getopt
import os
import re
import signal
import sys
import types

from gds.burp import HttpRequest
from gds.burp.decorators import callback
from gds.burp.menu import ConsoleMenuItem


class BurpExtender(IBurpExtender):
    def __repr__(self):
        return '<BurpExtender %#x>' % (id(self),)

    def setCommandLineArgs(self, args):
        '''
        -i, --interactive   Run Burp in interactive mode (Jython Console)
        -f <FILE>           Restore burp state file on startup
        -h
        '''
        from optparse import OptionParser
        parser = OptionParser()

        parser.add_option('-i', '--interactive',
                          action='store_true',
                          help='Run Burp in interactive mode (Jython Console)')

        parser.add_option('-f', '--file', metavar='FILE',
                          help='Restore Burp state from FILE on startup')

        parser.add_option('-P', '--python-path',
                          default='',
                          help='Set PYTHONPATH used by Jython')

        opt, args = parser.parse_args(list(args))

        if opt.interactive:
            from java.util import Properties

            pre_properties = System.getProperties()
            pre_properties['python.console'] = 'org.python.util.ReadlineConsole'

            post_properties = Properties()

            if opt.python_path:
                post_properties['python.path'] = opt.python_path

            PythonInterpreter.initialize(pre_properties, post_properties, sys.argv[1:])

            self.console = JLineConsole()
            self.console.exec('import __builtin__ as __builtins__')
            self.console.exec('from gds.burp import HttpRequest, HttpResponse')
            self.console.set('Burp', self)

            sys.stderr.write('Launching interactive session...\n')
            ConsoleThread(self.console).start()

        self.opt, self.args = opt, args

        return


    def applicationClosing(self):
        return


    def registerExtenderCallbacks(self, callbacks):
        self._callbacks = callbacks

        if self.opt.file:
            if os.path.isfile(self.opt.file):
                from java.io import File
                self.restoreState(File(self.opt.file))
                self.issueAlert('restored state from %s' % (self.opt.file,))
            else:
                self.issueAlert('could not restore state from %s:'
                                'file does not exist' % (self.opt.file,))

        if self.opt.interactive:
            ConsoleMenuItem(_burp=self)

        self.issueAlert('burp extender ready...')

        return


    def _check_cb(self):
        if hasattr(self, '_callbacks'):
            return getattr(self, '_callbacks')


    def _check_and_callback(self, method, *args):
        cb = self._check_cb()

        if not hasattr(cb, method.__name__):
            raise Exception("%s not available in your version of Burp" % (
                            method.__name__,))

        return getattr(cb, method.__name__)(*args)


    cb = property(_check_cb)


    @callback
    def addToSiteMap(self, item):
        return


    @callback
    def doActiveScan(self, host, port, useHttps, request, *args):
        return


    @callback
    def doPassiveScan(self, host, port, useHttps, request, response):
        return


    @callback
    def excludeFromScope(self, url):
        return


    def getProxyHistory(self, *args):
        history = []

        if args:
            matchers = [re.compile(arg) for arg in args]
            for request in self._check_and_callback(self.getProxyHistory):
                for matcher in matchers:
                    if matcher.search(request.getUrl().toString()):
                        history.append(HttpRequest(request))
        else:
            for request in self._check_and_callback(self.getProxyHistory):
                history.append(HttpRequest(request))

        return history


    @callback
    def getScanIssues(self, urlPrefix):
        return


    def getSiteMap(self, *urlPrefixes):
        items = []

        for urlPrefix in urlPrefixes:
            for item in self._check_and_callback(self.getSiteMap, urlPrefix):
                items.append(HttpRequest(item, callbacks=self._check_cb()))

        return items


    @callback
    def includeInScope(self, url):
        return


    @callback
    def isInScope(self, url):
        return


    @callback
    def issueAlert(self, message):
        return


    @callback
    def loadConfig(self, config):
        return


    @callback
    def makeHttpRequest(self, host, port, useHttps, request):
        return


    @callback
    def registerMenuItem(self, menuItemCaption, menuItemHandler):
        return


    @callback
    def restoreState(self, file):
        return


    @callback
    def saveConfig(self):
        return


    @callback
    def saveState(self, file):
        return


    @callback
    def sendToIntruder(self, host, port, useHttps, request, *args):
        return


    @callback
    def sendToRepeater(self, host, port, useHttps, request, tabCaption):
        return


    @callback
    def sendToSpider(self, url):
        return


    @callback
    def setProxyInterceptionEnabled(self, enabled):
        return


class ConsoleThread(Thread):
    def __init__(self, console):
        Thread.__init__(self, name='jython-console')
        self.console = console

    def run(self):
        while True:
            try:
                self.console.interact()
            except Exception:
                pass


def _sigbreak(signum, frame):
    '''
    Don't do anything upon receiving ^C. Require user to actually exit
    via Burp, preventing them from accidentally killing Burp from the
    interactive console.
    '''
    pass

signal.signal(signal.SIGINT, _sigbreak)