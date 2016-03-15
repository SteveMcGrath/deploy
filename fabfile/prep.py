from fabric.api import *
from fabric.contrib import *
import re, os
from . import config

env = config.env


@task
def sshkeys(keyfile=None):
    '''
    Pushes the management keys to remote server.
    '''
    from base import get_dist
    # This is needed for restorecon

    # First thing, lets go ahead and read the public key into memory.
    if not keyfile:
        keyfile = config.public_key_filename
    pubkey = open(keyfile).read()

    # Now lets check to see if the .ssh folder exists for the root user.  if it
    # doesn't, then we will need to create it.
    if not files.exists('/root/.ssh', use_sudo=True):
        sudo('mkdir /root/.ssh')

    # Next up we need to see if the authorized_keys file exists.  If it doesn't
    # then we will touch the file.
    auth_keys = '/root/.ssh/authorized_keys'
    if not files.exists(auth_keys, use_sudo=True):
        sudo('touch %s' % auth_keys)

    # Now we check to see if the authorized_keys file already has the public key
    # that we are trying to push.  If it does, then we wont need to do anything.
    # if it doesn't, then lets append the ssh key into the file.
    if not files.contains(auth_keys, pubkey, use_sudo=True):
        files.append(auth_keys, pubkey, use_sudo=True)

    # Now, we need to perform some cleanup.  Mainly make sure the permissions on
    # the .ssh directory and the authorized_keys files are setup properly and
    # run restorecon to make RHEL play nice with our changes.
    sudo('chmod 0700 /root/.ssh')
    sudo('chmod 0600 /root/.ssh/authorized_keys')
    if get_dist()['dist'] == 'redhat':
        with settings(warn_only=True):
            sudo('restorecon -R -v /root/.ssh')


@task
def update():
    '''
    Updates the OS to current
    '''
    from base import get_dist
    opsys = get_dist()
    if opsys['dist'] == 'redhat':
        sudo('yum -y update')
    elif opsys['dist'] in ['debian', 'ubuntu']:
        sudo('apt-get update')
        sudo('apt-get -y upgrade')


@task
def epel():
    '''
    Installs the EPEL repository
    '''
    from base import get_dist
    os = get_dist()
    sudo('yum -y install https://dl.fedoraproject.org/pub/epel/epel-release-latest-%s.noarch.rpm' % os['version'][-1])


@task
def mosh():
    '''
    Installs Mosh binary.
    '''
    from base import get_dist
    opsys = get_dist()
    if opsys['dist'] == 'redhat':
        sudo('yum -y install mosh')
    elif opsys['dist'] in ['debian', 'ubuntu']:
        sudo('apt-get -y install mosh')


@task
def rmate():
    '''
    Installs the rmate shell script into /usr/local/bin
    '''
    from base import get_dist
    opsys = get_dist()
    url = 'https://raw.githubusercontent.com/aurora/rmate/master/rmate'
    if opsys['dist'] == 'redhat':
        sudo('curl -o /usr/local/bin/rmate %s' % url)
    elif opsys['dist'] in ['debian', 'ubuntu']:
        sudo('wget -O /usr/local/bin/rmate %s' % url)
    sudo('chmod 755 /usr/local/bin/rmate')


@task
def prep():
    '''
    Generic preperation script for CentOS/RHEL boxen.
    '''
    sshkeys()
    rmate()
    update()


@task
def template(script='sysprep.sh'):
    '''
    Performs the needed actions to make the host templatable.
    '''
    put(os.path.join(config.packages,script), '/usr/local/bin/sysprep')
    run('chmod 755 /usr/local/bin/sysprep')
    run('sysprep buildme')
    run('shutdown -h now')
