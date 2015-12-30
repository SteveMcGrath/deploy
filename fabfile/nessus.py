from fabric.api import *
from fabric.contrib import *
import re, os
from . import config

env = config.env

@task
def prep():
    '''
    Prepares a vanilla system for use as a Nessus scanner.
    This includes things such as firewall entries, additional packages, etc.
    '''
    from . import base
    from . import prep
    env.warn_only = True

    prep.prep()

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
def install(version=None, attach=None, pushplugs=None):
    '''
    Installs/Updates Nessus.
    A specific version can be optionally specified.  If no version is specified
    then the most current version will be selected.
    '''
    from . import base
    from securitycenter import SecurityCenter5

    # We need to set warn_only for rpm -q
    env.warn_only = True

    # Now to get the installed version info
    iver = base.get_installed('Nessus')

    if not iver:
        # If Nessus isn't installed, then we will need to determine the
        # appropriate package by querying the info from the machine
        # directly.
        os = base.get_os()
        arch = base.get_arch()
        package = base.local_rpm('Nessus', os, arch, version=version)
    else:
        # If we have an installed version of Nessus, when we can leverage
        # the information returned from get_installed.
        package = base.local_rpm('Nessus', iver[1], iver[2], version=version)
    if not package:
        print '!!!! No valid package found! Aborting! !!!'

    # Now to place the package on the remote server.
    put(package, '/tmp/Nessus.rpm')
    run('yum -y -q install /tmp/Nessus.rpm')

    if not iver:
        # As Nessus has not been installed on this host before, we will
        # need to configure Nessus for use as a SecurityCenter managed
        # scanner.
        run('/opt/nessus/sbin/nessuscli fetch --security-center')
        with settings(prompts={
            'Login password: ': config.nessus_pass,
            'Login password (again): ': config.nessus_pass,
            'Do you want this user to be a Nessus \'system administrator\' user (can upload plugins, etc.)? (y/n) [n]: ': 'y',
            '(the user can have an empty rules set)': '\n',
            'Is that ok? (y/n) [n]: ': 'y',
        }):
            run('/opt/nessus/sbin/nessuscli adduser %s' % config.nessus_user)
    else:
        # As Nessus is already installed, we only need to stop the currently
        # running version of Nessus.
        run('service nessusd stop')
    run('rm -f /tmp/Nessus.rpm')

    # The scanner should be ready to fire at this point, however if the scanner
    # is on the remote end of a slow or high-latency link, we may want to
    # pre-load the plugins into the scanner to prevent a lengthy wait for
    # SecurityCenter to push and verify the pluginset is correct.
    if config.nessus_auto_upload or pushplugs:
        plugin_push()

    # Lets start up the Nessus daemon
    run('service nessusd start')

    # Now to attach the scanner to SecurityCenter.  SWe will use the hostname
    # as the default name for the server when inputting into SC.  No zone will
    # be attached however as we just want to get the scanner up and running
    # with the latest plugins as quickly as possible.  We will only attach
    # the sacanner to SecurityCenter if there is no Nessus binary installed on
    # the host.  This prevents things from getting troublesome.  There is however
    # an override as the "attach" flag.  Setting that to really anything will
    # override the safety checks and attach the scanner to SecurityCenter as
    # well.
    if (config.nessus_attach and not iver) or attach:
        sc = SecurityCenter5(config.sc_host)
        sc.login(config.sc_user, config.sc_pass)
        sc.post('scanner', json={
            'agentCapable': 'false',
            'authType': 'password',
            'context': '',
            'createdTime': 0,
            'description': '',
            'enabled': 'true',
            'ip': env.host,
            'modifiedTime': 0,
            'name': run('hostname'),
            'nessusManagerOrgs': [],
            'password': config.nessus_pass,
            'port': '8834',
            'status': -1,
            'useProxy': 'false',
            'username': config.nessus_user,
            'verifyHost': 'false',
            'zones': []
        })
        sc.logout()


@task
def plugin_push():
    '''
    Pushes plugin tarball to the remote scanner.
    '''
    if os.path.exists(config.nessus_plugins_tarball):
        put(config.nessus_plugins_tarball, '/tmp/plugins.tar.gz')
        run('/opt/nessus/sbin/nessuscli update /tmp/plugins.tar.gz')
    else:
        print '!! Could not find plugin tarball.'
    run('rm -f /tmp/plugins.tar.gz')

