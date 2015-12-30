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
    # This is needed for restorecon
    env.warn_only = True

    # First thing, lets go ahead and read the public key into memory.
    if not keyfile:
        keyfile = config.public_key_filename
    pubkey = open(keyfile).read()

    # Now lets check to see if the .ssh folder exists for the root user.  if it
    # doesn't, then we will need to create it.
    if not files.exists('/root/.ssh'):
        run('mkdir /root/.ssh')

    # Next up we need to see if the authorized_keys file exists.  If it doesn't
    # then we will touch the file.
    auth_keys = '/root/.ssh/authorized_keys'
    if not files.exists(auth_keys):
        run('touch %s' % auth_keys)

    # Now we check to see if the authorized_keys file already has the public key
    # that we are trying to push.  If it does, then we wont need to do anything.
    # if it doesn't, then lets append the ssh key into the file.
    if not files.contains(auth_keys, pubkey):
        files.append(auth_keys, pubkey)

    # Now, we need to perform some cleanup.  Mainly make sure the permissions on
    # the .ssh directory and the authorized_keys files are setup properly and
    # run restorecon to make RHEL play nice with our changes.
    run('chmod 0700 /root/.ssh')
    run('chmod 0600 /root/.ssh/authorized_keys')
    run('restorecon -R -v /root/.ssh')


@task
def update():
    '''
    Updates the OS to current
    '''
    run('yum -y -q update')


@task
def rmate():
    '''
    Installs the rmate shell script into /usr/local/bin
    '''
    url = 'https://raw.githubusercontent.com/aurora/rmate/master/rmate'
    run('curl -o /usr/local/bin/rmate %s' % url)
    run('chmod 755 /usr/local/bin/rmate')


@task
def prep():
    '''
    Generic preperation script for CentOS/RHEL boxen.
    '''
    sshkeys()
    rmate()
    update()
