# vim: set syntax=python:

import os, platform, shutil, sys

from waflib import Configure
from waflib import Errors
from waflib import Logs
from waflib import Options
from waflib import Scripting
from waflib import Task
from waflib import Utils
from waflib import TaskGen
from waflib import Tools

APPNAME = 'hstcal'
VERSION = '0.1.1'

top = '.'
out = 'build.' + platform.platform()

# A list of subdirectories to recurse into
SUBDIRS = [
    'cfitsio', # cfitsio needs to go first
    'applib',
    'cvos',
    'hstio',
    'hstio/test',
    'include',
    'pkg',
    'tables',
    ]

# Have 'waf dist' create tar.gz files, rather than tar.bz2 files
Scripting.g_gz = 'gz'

option_parser = None
def options(opt):
    # We want to store
    # the option parser object so we can use it later (during the
    # configuration phase) to parse options stored in a file.
    global option_parser
    option_parser = opt.parser

    opt.load('compiler_c')
    opt.load('compiler_fc')

    opt.add_option(
        '--disable-openmp', action='store_true',
        help="Disable OpenMP")

    opt.add_option(
        '--debug', action='store_true',
        help="Create a debug build")

    opt.recurse('cfitsio')

def _setup_openmp(conf):
    conf.start_msg('Checking for OpenMP')

    if conf.options.disable_openmp:
        conf.end_msg('OpenMP disabled.', 'YELLOW')
        return

    try:
        conf.check_cc(
            header_name="omp.h", lib="gomp", cflags="-fopenmp",
            uselib_store="OPENMP")
    except Errors.ConfigurationError:
        conf.end_msg("OpenMP not found.", 'YELLOW')
    else:
        conf.end_msg("OpenMP found.", 'GREEN')

def _check_mac_osx_version(version):
    '''
     Native     Encoded
    -------    --------
     10.5.0 == 0x0A0500
      ^ ^ ^       ^ ^ ^
      | | |       | | |
      major       major
        | |         | |
        minor       minor
          |           |
          patch       patch

    version -> 24-bit encoded version
    '''

    assert isinstance(version, int)
    floor_version = version
    osx_version = 0

    floor_version_major = (floor_version >> 8 & 0xff)
    floor_version_minor = (floor_version >> 8 & 0xff)
    floor_version_patch = (floor_version & 0xff)

    s = platform.popen("/usr/bin/sw_vers -productVersion").read()
    osx_version_major, osx_version_minor, osx_version_patch = \
        tuple(int(x) for x in s.strip().split('.'))

    osx_version = (osx_version << 8 | osx_version_major & 0xff)
    osx_version = (osx_version << 8 | osx_version_minor & 0xff)
    osx_version = (osx_version << 8 | osx_version_patch & 0xff)

    if osx_version < floor_version:
        return False

    return True

def _determine_mac_osx_fortran_flags(conf):
    # On Mac OS-X, we need to know the specific version in order to
    # send some compile flags to the Fortran compiler.
    import platform
    conf.env.MAC_OS_NAME = None
    if platform.system() == 'Darwin' :
        conf.start_msg('Checking Mac OS-X version')

        if _check_mac_osx_version(0x0A0500):
            conf.end_msg('done', 'GREEN')
        else:
            conf.end_msg(
                "Unsupported OS X version detected (<10.5.0)",
                'RED')
            exit(1)

        conf.env.append_value('FCFLAGS', '-m64')

def _determine_sizeof_int(conf):
    conf.check(
        fragment='#include <stdio.h>\nint main() { printf("%d", sizeof(int)); return 0; }\n',
        define_name="SIZEOF_INT",
        define_ret=True,
        quote=False,
        execute=True,
        msg='Checking for sizeof(int)')

def _determine_architecture(conf):
    # set architecture specific flags if not set in the environment
    arch_modes = ['-m32', '-m64']
    cflags_forced = False
    ldflags_forced = False

    def get_forced_arch(flag):
        try:
            flags = os.environ[flag].split()
        except KeyError:
            return None

        for arg in flags:
            for arch in arch_modes:
                if arg == arch:
                    return arch


    conf.start_msg('Checking architecture')
    if platform.architecture()[0] == '64bit':
        arch_mode = '-m64'
        conf.end_msg('x86_64')
    else:
        arch_mode = '-m32'
        conf.end_msg('x86')

    conf.start_msg('User-defined CFLAGS')
    conf.end_msg(get_forced_arch('CFLAGS'))

    conf.start_msg('User-defined LDFLAGS')
    conf.end_msg(get_forced_arch('LDFLAGS'))

    if get_forced_arch('CFLAGS') is None:
        if ('CFLAGS' not in conf.env) or \
            ('CFLAGS' in conf.env and arch_modes not in conf.env['CFLAGS']):
            conf.env.append_value('CFLAGS', arch_mode)

    if get_forced_arch('LDFLAGS') is None:
        if ('LDFLAGS' not in conf.env) or \
            ('LDFLAGS' in conf.env and arch_modes not in conf.env['LDFLAGS']):
            conf.env.append_value('LDFLAGS', arch_mode)

def configure(conf):
    # NOTE: All of the variables in conf.env are defined for use by
    # wscript files in subdirectories.

    # Read in options from a file.  The file is just a set of
    # commandline arguments in the same syntax.  May be spread across
    # multiple lines.
    if os.path.exists('build.cfg'):
        fd = open('build.cfg', 'r')
        for line in fd.readlines():
            tokens = line.split()
            options, args = option_parser.parse_args(tokens)
            for key, val in options.__dict__.items():
                if Options.options.__dict__.get(key) is None:
                    Options.options.__dict__[key] = val
        fd.close()

    # Load C compiler support
    conf.load('compiler_c')

    # Check for the existence of a Fortran compiler
    conf.load('compiler_fc')
    conf.check_fortran()

    # Set the location of the hstcal include directory
    conf.env.INCLUDES = [os.path.abspath('include')] # the hstcal include directory

    # A list of the local (hstcal) libraries that are typically linked
    # with the executables
    conf.env.LOCAL_LIBS = [
        'applib', 'xtables', 'hstio', 'cvos', 'CFITSIO']

    # A list of external libraries that are typically linked with the
    # executables
    conf.env.EXTERNAL_LIBS = ['m']
    if sys.platform.startswith('sunos'):
        conf.env.EXTERNAL_LIBS += ['socket', 'nsl']

    # A list of paths in which to search for external libraries
    conf.env.LIBPATH = []

    _determine_architecture(conf)

    _determine_mac_osx_fortran_flags(conf)

    _setup_openmp(conf)

    _determine_sizeof_int(conf)

    # The configuration related to cfitsio is stored in
    # cfitsio/wscript
    conf.recurse('cfitsio')


    # check whether the compiler supports -02 and add it to CFLAGS if it does
    if conf.options.debug:
        if conf.check_cc(cflags='-g'):
            conf.env.append_value('CFLAGS', '-g')
        if conf.check_cc(cflags='-O0'):
            conf.env.append_value('CFLAGS', '-O0')
        if conf.check_cc(cflags='-Wall'):
            conf.env.append_value('CFLAGS','-Wall')
    else:
        if conf.check_cc(cflags='-O2'):
            conf.env.append_value('CFLAGS','-O2')
        if conf.check_cc(cflags='-Wall'):
            conf.env.append_value('CFLAGS','-Wall')
        if conf.check_cc(cflags='-fstack-protector-all'):
            conf.env.append_value('CFLAGS','-fstack-protector-all')


def build(bld):
    bld(name='lib', always=True)
    bld(name='test', always=True)

    targets = [x.strip() for x in bld.targets.split(',')]

    if not len(targets):
        targets = ['lib', 'test']

    if 'lib' in targets:
        bld.env.INSTALL_LIB = True
        targets.remove('lib')
    else:
        bld.env.INSTALL_LIB = None

    if 'test' in targets:
        bld.env.INSTALL_TEST = True
        targets.remove('test')
    else:
        bld.env.INSTALL_TEST = None

    bld.targets = ','.join(targets)

    # Recurse into all of the libraries
    for library in SUBDIRS:
        bld.recurse(library)

    if bld.cmd == 'clean':
        return clean(bld)

    # Add a post-build callback function
    bld.add_post_fun(post_build)

def post_build(bld):
    # WAF has its own way of dealing with build products.  We want to
    # emulate the old stsdas way of creating a flat directory full of
    # .a and .e files.  This simply runs through the build tree and
    # copies such files to the bin.* directory.
    src_root = os.path.join(
        bld.srcnode.abspath(),
        'build.' + platform.platform())
    dst_root = os.path.join(
        bld.srcnode.abspath(),
        'bin.' + platform.platform())

    if not os.path.exists(dst_root):
        os.mkdir(dst_root)

    for root, dirs, files in os.walk(src_root):
        for file in files:
            base, ext = os.path.splitext(file)
            if ext in ('.e', '.a'):
                src_path = os.path.join(root, file)
                dst_path = os.path.join(dst_root, file)
                shutil.copy(src_path, dst_path)

def clean(ctx):
    # Clean the bin.* directory
    bin_root = 'bin.' + platform.platform()
    if os.path.exists(bin_root):
        shutil.rmtree(bin_root)

def test(ctx):
    # Recurse into all of the libraries
    # Just to check that nose is installed
    try:
        import nose
    except ImportError:
        raise ImportError("nose must be installed to run hstcal tests.")

    for library in SUBDIRS:
        if library.endswith('test'):
            if os.system('nosetests %s' % library):
                raise Exception("Tests failed")

# This is a little recipe from the waf docs to produce abstract
# targets that define what to build and install.
from waflib.TaskGen import feature, before_method
@feature("*")
@before_method('process_rule')
def post_the_other(self):
    deps = getattr(self, 'depends_on', [])
    for name in self.to_list(deps):
        other = self.bld.get_tgen_by_name(name)
        other.post()
