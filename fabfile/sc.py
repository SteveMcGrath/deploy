from fabric.api import *
from fabric.contrib import *
import re, os
from . import config

env = config.env

@task
@hosts(config.sc_host)
def getfeed():
    '''
    Pulls the plugin feeds from SecurityCenter to the local box.
    '''
    get('/opt/sc/data/nasl/all-2.0.tar.gz', config.nessus_plugins_tarball)
