from fabric.api import *
from fabric.contrib import *
import re, os
from . import config

env = config.env

@task
def prep():
    '''
    Prepares a vanilla system for use as a PVS sensor.
    This includes things such as firewall entries, additional packages, etc.
    '''
    from . import base
    env.warn_only = True

    base.update()
    base.sshkeys()

    opsys = base.get_os()
    print "\'%s\'" % opsys
    if opsys == 'es6':
        run('chkconfig iptables off')
        run('chkconfig ip6tables off')
        run('service iptables stop')
        run('service ip6tables stop')
    elif opsys == 'es7':
        run('systemctl disable firewalld')
        run('systemctl stop firewalld')


@task
def install():
    '''
    Installs/Updates PVS.
    A specific version can be optionally specified.  If no version is specified
    then the most current version will be selected.
    '''
    from . import base

    # We need to set warn_only for rpm -q
    env.warn_only = True

    # Now to get the installed version info
    iver = base.get_installed('pvs')

    if not iver:
        # If PVS isn't installed, then we will need to determine the
        # appropriate package by querying the info from the machine
        # directly.
        os = base.get_os()
        arch = base.get_arch()
        package = base.local_rpm('pvs', os, arch, version=version)
    else:
        # If we have an installed version of PVS, when we can leverage
        # the information returned from get_installed.
        package = base.local_rpm('pvs', iver[1], iver[2], version=version)

    # Now to place the package on the remote server.
    put(package, '/tmp/pvs.rpm')
    run('yum -y install /tmp/pvs.rpm')

    if not iver:
        # As PVS has not been installed on this host before, we will
        # need to configure Nessus for use as a SecurityCenter managed
        # scanner.
        run('/opt/pvs/bin/pvs -a SecurityCenter')
        run('/opt/pvs/bin/pvs --users --add %s "%s" 1' % (config.pvs_user, config.pvs_pass))
        run('/opt/pvs/bin/pvs --config "Monitored Network Interfaces" "%s"' % config.pvs_interface)
        run('/opt/pvs/bin/pvs --config "Monitored Network IP Addresses and Ranges" "%s"' % config.pvs_monitored_ranges)
        run('/opt/pvs/bin/pvs --config "Realtime Syslog Server List" "%s:0:0"' % config.lce_address)
        run('/opt/pvs/bin/pvs --config "Vulnerability Syslog Server List" "%s:0:0"' % config.lce_address)
    else:
        # As Nessus is already installed, we only need to stop the currently
        # running version of Nessus.
        run('service pvs stop')
    run('service pvs start')
    run('rm -f /tmp/pvs.rpm')
