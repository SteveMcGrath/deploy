from fabric.api import *
from fabric.contrib import *
from distutils.version import LooseVersion
import re, os
from . import config

env = config.env


def is_installed(appname):
    '''
    Returns the currently installed RPM of the application.
    '''
    # The regex that we will be using to pull the information that we
    # need for comparison.
    rst = r'%s-([0-9\.]+)-e[ls](\d)\.(.*)' % appname
    reinfo = re.compile(rst)

    # Next to get the information
    output = reinfo.findall(run('rpm -qa %s' % appname))

    # If we have info, then return it, else return None
    if len(output) > 0:
        return LooseVersion(output[0][0]), 'es%s' % output[0][1], output[0][2]
    else:
        return None


def get_dist():
    '''
    Returns the distribution and version number of the remote host.
    '''
    uname = run('uname -a')
    if '.el' in uname:
        # RedHat Derivatives.
        rhel = reos = re.compile(r'\.e[ls](\d)\.')
        return {
            'dist': 'redhat',
            'version': 'es%s' % rhel.findall(run('uname -r'))[0],
            'arch': run('uname -m'),
        }
    elif files.exists('/etc/os-release'):
        # Debian Derivatives.
        os_file = run('cat /etc/os-release')
        return {
            'dist': re.findall(r'\nID=(.*)',os_file)[0].strip('\r').strip('"'),
            'version': re.findall(r'\nVERSION_ID=(.*)',os_file)[0].strip('\r').strip('"'),
            'arch': run('uname -m'),
        }
    else:
        return {
            'dist': 'unknown',
            'version': 'unknown',
            'arch': 'unknown',
        }


def get_arch():
    '''
    Return the remote host's architecture
    '''
    hostarch = run('uname -m')
    if hostarch in ['i386', 'i486', 'i586', 'i686']:
        hostarch = 'i386'
    if hostarch in ['amd64', 'x86_64']:
        hostarch = 'x86_64'
    return hostarch
