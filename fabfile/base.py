from fabric.api import *
from fabric.contrib import *
from distutils.version import LooseVersion
import re, os
from . import config

env = config.env


def get_installed(appname):
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


def get_os():
    '''
    Return the remote host's OS
    '''
    reos = re.compile(r'\.e[ls](\d)\.')
    return 'es%s' % reos.findall(run('uname -r'))[0]


def get_arch():
    '''
    Return the remote host's architecture
    '''
    hostarch = run('uname -i')
    if hostarch in ['i386', 'i486', 'i586', 'i686']:
        hostarch = 'i386'
    if hostarch in ['amd64', 'x86_64']:
        hostarch = 'x86_64'
    return hostarch


def local_rpm(appname, opsys, arch, version=None):
    '''
    Get the appropriate current RPM file.
    '''
    # Some defaults that will be overridden
    latest = LooseVersion('0.0')
    latestpkg = None

    # This here is the regex for pulling out the relevent information from the
    # RPM filename itself.
    rst = r'%s-(\d{1,2}\.\d{1,2}(?:\.\d{1,2}))-(es\d)\.(.*?)\.rpm' % appname
    reinfo = re.compile(rst)

    # Now that we have everything set, lets go ahead and iterate through all of
    # the files in the packages folder, select the ones that are relevent (i.e.
    # they have the appname variable in the filename) and then try to determine
    # if its either (a) the version we are looking for for this host, or (b) the
    # latest version of the application as it pertains to the host.
    print os.listdir(config.packages)
    for filename in os.listdir(config.packages):
        if appname in filename:
            try:
                ver, pkgos, pkgarch = reinfo.findall(filename)[0]
            except IndexError:
                pass
            else:
                if version != None:
                    # If we are looking for a specific version then lets go
                    # ahead and do a comparison here.
                    if (LooseVersion(version) == LooseVersion(ver) and
                        opsys == pkgos and arch == pkgarch):
                        latest = LooseVersion(ver)
                        latestpkg = filename
                else:
                    # If we are simply looking for the latest version that
                    # matches the OS version and the arch,
                    if (LooseVersion(ver) > latest and
                        opsys == pkgos and arch == pkgarch):
                        latest = LooseVersion(ver)
                        latestpkg = filename
    print latestpkg
    return os.path.join(config.packages, latestpkg)
