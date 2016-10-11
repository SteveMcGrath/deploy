from fabric.api import *
from fabric.contrib import *
import re, os
from . import config
from .pkg import get_package

env = config.env

@task
def prep():
    '''
    Prepares a vanilla system for use as a PVS sensor.
    This includes things such as firewall entries, additional packages, etc.
    '''
    from . import base,prep
    env.warn_only = True
    prep.prep()
    opsys = base.get_dist()
    print "\'%s\'" % opsys
    if opsys['version'] == 'es6':
        run('chkconfig iptables off')
        run('chkconfig ip6tables off')
        run('service iptables stop')
        run('service ip6tables stop')
    elif opsys['version'] == 'es7':
        run('systemctl disable firewalld')
        run('systemctl stop firewalld')


@task
def install(version=None):
    '''
    Installs/Updates PVS.
    A specific version can be optionally specified.  If no version is specified
    then the most current version will be selected.
    '''
    from . import base
    from securitycenter import SecurityCenter5

    # We need to set warn_only for rpm -q
    env.warn_only = True

    # Now to get the installed version info
    installed = base.is_installed('pvs')
    opsys = base.get_dist()
    package = get_package(
        name='pvs', 
        arch=opsys['arch'], 
        dist_ver=opsys['version'],
        version=version
    )
    if not package:
        print '!!! No Valid PVS Package Found !!!'
        return

    # Now to place the package on the remote server.
    put(package.path, '/tmp/pvs.rpm')
    run('yum -y install /tmp/pvs.rpm')

    if not installed:
        # As PVS has not been installed on this host before, we will
        # need to configure Nessus for use as a SecurityCenter managed
        # scanner.
        run('/opt/pvs/bin/pvs -a SecurityCenter')
        run('/opt/pvs/bin/pvs --users --chpasswd "admin" "%s"' % config.pvs_pass)
        run('/opt/pvs/bin/pvs --config "Monitored Network Interfaces" "%s"' % config.pvs_interface)
        run('/opt/pvs/bin/pvs --config "Monitored Network IP Addresses and Ranges" "%s"' % config.pvs_monitored_ranges)
        run('/opt/pvs/bin/pvs --config "Realtime Syslog Server List" "%s:514:0:0"' % config.lce_address)
        run('/opt/pvs/bin/pvs --config "Vulnerability Syslog Server List" "%s:514:0:0"' % config.lce_address)

        # Now we will attach the PVS Sensor into SecurityCenter.
        if config.pvs_attach:
            sc = SecurityCenter5(config.sc_host)
            sc.login(config.sc_user, config.sc_pass)
            sc.post('passivescanner', json={
                'authType': 'password',
                'context': '',
                'createdTime': 0,
                'description': '',
                'enabled': 'true',
                'ip': env.host,
                'lastReportTime': 0,
                'modifiedTime': 0,
                'name': run('hostname'),
                'password': config.pvs_pass,
                'port': '8835',
                'repositories': [],
                'status': -1,
                'useProxy': 'false',
                'username': 'admin',
                'verifyHost': 'false'
            })
    else:
        # As Nessus is already installed, we only need to stop the currently
        # running version of Nessus.
        run('service pvs stop')
    run('service pvs start')
    run('rm -f /tmp/pvs.rpm')
