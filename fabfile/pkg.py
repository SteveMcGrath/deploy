from sqlalchemy import Column, Integer, Text, create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.hybrid import hybrid_property
from distutils.version import LooseVersion
from fabric.api import task
import re, os
from . import config


env = config.env
Base = declarative_base()
engine = create_engine(config.pkg_db)
Session = sessionmaker(engine)


class Package(Base):
    __tablename__ = 'packages'
    id = Column(Integer, primary_key=True)
    name = Column(Text)
    _version = Column(Text)
    dist = Column(Text)
    dist_ver = Column(Text)
    ext = Column(Text)
    arch = Column(Text)
    filename = Column(Text, unique=True)

    def __repr__(self):
        return os.path.join(config.packages, self.filename)

    @hybrid_property
    def version(self):
        return LooseVersion(self._version)

    @hybrid_property
    def path(self):
        return os.path.join(config.packages, self.filename)

    @version.setter
    def version(self, value):
        self._version = str(value)

    def populate(self, filename):
        '''
        Attempts to populate the values based on the filename.
        '''
        f = filename
        self.filename = f

        # Attempt to determing the architecture.
        if 'i386' in f or 'i486' in f or 'i586' in f or 'i686' in f:
            self.arch = 'i386'
        elif 'amd64' in f or 'x86_64' in f:
            self.arch = 'x86_64'

        # Attempt to determine the package product name
        name = re.findall(r'^([0-9a-zA-Z_]+)[\.\-]\d{1,3}\.\d{1,3}',f)
        if len(name) > 0:
            self.name = name[0]

        # Get the Extention
        self.ext = f.split('.')[-1]

        # Attempt to get the package version
        v = re.findall(r'^[0-9a-zA-Z_]+[\.\-](\d{1,2}\.\d{1,2}(?:\.\d{1,2}))',f)
        if len(v) > 0:
            self.version = v[0]

        # Lastly, we will crudely set something for the distribution.
        if self.ext == 'rpm':
            self.dist = 'redhat'

            # Look for markers for RHEL and CentOS.
            rhel = re.findall(r'[\-\.](e[sl]\d)',f)
            if len(rhel) > 0:
                self.dist_ver = rhel[0]

            # Fedora markers
            fedora = re.findall(r'[\.\-](fc\d{1,2})',f)
            if len(fedora) > 0:
                self.dist_ver = fedora[0]

        elif self.ext == 'deb':
            self.dist = 'debian'

            # Debian markers
            debian = re.findall(r'[\.\-](debian\d)',f)
            if len(debian) > 0:
                self.dist_ver = debian[0]

            # Ubuntu markers
            ubuntu = re.findall(r'[\-\.](ubuntu\d{3,4})',f)
            if len(ubuntu) > 0:
                self.dist_ver = ubuntu[0]
                self.dist = 'ubuntu'


@task(default=True, alias='update')
def initialize(update=True):
    Package.metadata.create_all(engine)
    if update:
        update_pkg_db()


def get_package(**args):
    s = Session()
    qa = s.query(Package)
    results = []
    for arg in args:
        if arg == 'name' and args[arg] is not None:
            qa = qa.filter(Package.name == args[arg])
        if arg == 'dist' and args[arg] is not None:
            qa = qa.filter(Package.dist == args[arg])
        if arg == 'dist_ver' and args[arg] is not None:
            qa = qa.filter(Package.dist_ver == args[arg])
        if arg == 'version' and args[arg] is not None:
            qa = qa.filter(Package._version == str(args[arg]))
        if arg == 'arch' and args[arg] is not None:
            qa = qa.filter(Package.arch == args[arg])
        if arg == 'ext' and args[arg] is not None:
            qa = qa.filter(Package.ext == args[arg])
        if arg == 'filename' and args[arg] is not None:
            qa = qa.filter(Package.filename.like('%' + args[arg] + '%'))
    latest = None
    for pkg in qa.all():
        if not latest or pkg.version > latest.version:
            latest = pkg
    s.expunge(latest)
    s.close()
    return latest


def pkg_update(pkg):
    '''
    Simple Manual Package Info Updater
    '''
    def get_info(name, var):
        value = raw_input('- %s (%s) : ' % (name, var))
        if value != '':
            return value
        else:
            return var

    print 'Updating %s' % pkg.filename
    pkg.name = get_info('Name', pkg.name)
    pkg.version = get_info('Version', pkg.version)
    pkg.dist = get_info('Distro', pkg.dist)
    pkg.dist_ver = get_info('Distro Version', pkg.dist_ver)
    pkg.arch = get_info('Architecture', pkg.arch)
    return pkg


def update_pkg_db():
    '''
    Scans the packages folder and looks for new files and orphaned entries
    in the database and attempts to reconcile those differences.
    '''
    s = Session()
    allowed_exts = ['rpm', 'deb']
    files = []

    # Looking for new files that are not in the database...
    for filename in os.listdir(config.packages):
        valid = False
        for ext in allowed_exts:
            if filename[-3:] == ext:
                valid = True
        if valid:
            files.append(filename)
            r = s.query(Package).filter(Package.filename == filename).first()
            if not r:
                pkg = Package()
                pkg.populate(filename)
                pkg = pkg_update(pkg)
                if pkg:
                    s.add(pkg)
    s.commit()

    # Looking for files that have been orphaned from the DB and clean them
    # out.
    qd = s.query(Package)
    for filename in files:
        qd = qd.filter(Package.filename != filename)
    print 'Checking for orphaned packages to remove...'
    for pkg in qd.all():
        print '\t- %s' % pkg.filename
        s.delete(pkg)
    s.commit()
    s.close()
