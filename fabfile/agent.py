from fabric.api import *
from fabric.contrib import *
import re, os
from .pkg import get_package
from . import config

env = config.env


@task(default=True)
def install(version=None):
    '''
    Installs/Updates Nessus.
    A specific version can be optionally specified.  If no version is specified
    then the most current version will be selected.
    '''
    from . import base
    opsys = base.get_dist()

    # We need to set warn_only for rpm -q
    env.warn_only = True

    # Now to get the installed version info
    installed = base.is_installed('NessusAgent')
    package = get_package(
        name='NessusAgent', 
        dist_ver=opsys['version'],
        arch=opsys['arch'], 
        version=version
    )

    if not package:
        print '!!!! No valid package found! Aborting! !!!'
        return

    if not installed:
        # Now to place the package on the remote server.
        put(str(package), '/tmp/NessusAgent.rpm')
        run('yum -y -q install /tmp/NessusAgent.rpm')
        run('/opt/nessus_agent/sbin/nessuscli agent link --host=cloud.tenable.com --port=443 --key=%s --groups="%s"' % (
            config.linking_key,
            ','.join(config.agent_groups)
        ))
        run('systemctl start nessusagent')
        run('rm -f /tmp/NessusAgent.rpm')