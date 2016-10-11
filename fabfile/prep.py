from fabric.api import *
from fabric.contrib import *
import re, os
from . import config

env = config.env


@task
def clear_sshkeys():
    if files.exists('/root/.ssh/authorized_keys'):
        run('rm -f /root/.ssh/authorized_keys')

@task
def sshkeys(keyfile=None):
    '''
    Pushes the management keys to remote server.
    '''
    from base import get_dist
    # This is needed for restorecon

    # The first thing we need to do is build the public keys array.  This array
    # will be the basis for the authorized_keys file down the road.
    pubkeys = list()
    for root, d, f in os.walk(config.public_keys_path):
        for key in f:
            with open(os.path.join(root, key)) as keyfile:
                pubkeys.append(keyfile.read())

    # Now lets check to see if the .ssh folder exists for the root user.  if it
    # doesn't, then we will need to create it.
    if not files.exists('/root/.ssh', use_sudo=True):
        sudo('mkdir /root/.ssh')

    # Next up we need to see if the authorized_keys file exists.  If it doesn't
    # then we will touch the file.
    auth_keys = '/root/.ssh/authorized_keys'
    if files.exists(auth_keys, use_sudo=True):
        sudo('rm -f %s' % auth_keys)
    sudo('touch %s' % auth_keys)

    # Now we check to see if the authorized_keys file already has the public key
    # that we are trying to push.  If it does, then we wont need to do anything.
    # if it doesn't, then lets append the ssh key into the file.
    files.append(auth_keys, '\n'.join(pubkeys), use_sudo=True)

    # Now, we need to perform some cleanup.  Mainly make sure the permissions on
    # the .ssh directory and the authorized_keys files are setup properly and
    # run restorecon to make RHEL play nice with our changes.
    sudo('chmod 0700 /root/.ssh')
    sudo('chmod 0600 /root/.ssh/authorized_keys')
    if get_dist()['dist'] == 'redhat':
        with settings(warn_only=True):
            sudo('restorecon -R -v /root/.ssh')


@task
def ssh_remove_weak_ciphers():
    from base import get_dist
    opsys = get_dist()
    ssh_config = '\n'.join(['',
        '# default is aes128-ctr,aes192-ctr,aes256-ctr,arcfour256,arcfour128,',
        '# aes128-cbc,3des-cbc,blowfish-cbc,cast128-cbc,aes192-cbc,',
        '# aes256-cbc,arcfour',
        '# you can remove the cbc ciphers by adding the line\n',
        'Ciphers aes128-ctr,aes192-ctr,aes256-ctr,arcfour256,arcfour128,arcfour\n',
        '# default is hmac-md5,hmac-sha1,hmac-ripemd160,hmac-sha1-96,hmac-md5-96',
        '# you can remove the hmac-md5 MACs with\n',
        'MACs hmac-sha1,hmac-ripemd160',
    ]), 
    if not files.contains('/etc/ssh/sshd_config', 'you can remove the hmac-md5', use_sudo=True):   
        files.append('/etc/ssh/sshd_config', ssh_config, use_sudo=True)
    if opsys['dist'] == 'redhat':
        run('service sshd restart')


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
        with settings(warn_only=True):
            sudo('apt-get update')
        sudo('apt-get -y upgrade')


@task
def epel():
    '''
    Installs the EPEL repository
    '''
    from base import get_dist
    opsys = get_dist()
    if opsys['dist'] == 'redhat':
        if run('rpm -qa epel-release') == '':
            sudo('yum -y install epel-release')


@task
def yumcron():
    '''
    Installs and activates yum-cron
    '''
    from base import get_dist
    opsys = get_dist()
    if opsys['dist'] == 'redhat':
        if run('rpm -qa yum-cron') == '':
            sudo('yum -y install yum-cron')
            if files.exists('/etc/yum/yum-cron.conf'):
                files.sed('/etc/yum/yum-cron.conf', 
                            'apply_updates = no', 
                            'apply_updates = yes', 
                            use_sudo=True)
            sudo('chkconfig yum-cron on')

@task
def mosh():
    '''
    Installs Mosh binary.
    '''
    from base import get_dist
    opsys = get_dist()
    if opsys['dist'] == 'redhat':
        if run('rpm -qa mosh') == '':
            epel()
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
    print opsys
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
    epel()
    mosh()
    yumcron()
    ssh_remove_weak_ciphers()
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
