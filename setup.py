import os
import sys
try:
    from setuptools import setup, find_packages
except ImportError:
    from distutils.core import setup, find_packages

try:
    import pyvim  # https://github.com/prompt-toolkit/pyvim - pip install pyvim
except ImportError:
    pyvim = None


is_py3 = sys.version_info >= (3,)

if len(sys.argv) <= 1:
    print("""
Suggested setup.py parameters:

    * build
    * install
    * sdist  --formats=zip
    * sdist  # NOTE requires tar/gzip commands

    python -m pip install -e .
""")

readme_filename = 'README.md'
if os.path.exists(readme_filename):
    f = open(readme_filename)
    long_description = f.read()
    f.close()
else:
    long_description = None

# Lookup __version__
exec(open(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'puren_tonbo', '_version.py')).read())


# TODO/FIXME dupe of requirements.txt - also chi_io missing here (as not on pypi)
install_requires = ['colorama', 'pycryptodome', 'python-gnupg']
if is_py3:
    install_requires += ['pyzipper']  # pyzipperis python 3.x+
# TODO consider extras_require, for things like; pyvim, python-gnupg, chi_io
# TODO chi_io on pypi
# https://setuptools.pypa.io/en/latest/userguide/dependency_management.html#optional-dependencies
# https://stackoverflow.com/questions/10572603/specifying-optional-dependencies-in-pypi-python-setup-py

setup(
    name='puren_tonbo',
    version=__version__,
    author='clach04',
    url='https://github.com/clach04/puren_tonbo',
    description='Plain text notes Tombo (chi) alternative, also supports AES-256 ZIP AE-1/AE-2 and VimCrypt encrypted files. Work-In-Progress (WIP)!',  # FIXME
    long_description=long_description,
    #packages=['puren_tonbo'],
    packages=find_packages(where=os.path.dirname(__file__), include=['*']),
    package_data={
        'puren_tonbo': [os.path.join(os.path.dirname(__file__), 'puren_tonbo', 'tests', 'data', '*')],
    },
    #scripts=['ptcipher.py'],
    #py_modules=[''], # TODO scripts
    entry_points={
        'console_scripts': [
            'ptcat = puren_tonbo.tools.ptcat:main',
            'ptcipher = puren_tonbo.tools.ptcipher:main',
            'ptconfig = puren_tonbo.tools.ptconfig:main',
            'ptgrep = puren_tonbo.tools.ptgrep:main',
            'ptig = puren_tonbo.tools.ptig:main',
        ] + (['ptpyvim = puren_tonbo.tools.ptpyvim:main'] if pyvim else []),
    },
    #data_files=[('.', [readme_filename])],  # does not work :-( ALso tried setup.cfg [metadata]\ndescription-file = README.md # Maybe try include_package_data = True and a MANIFEST.in?
    classifiers=[  # See http://pypi.python.org/pypi?%3Aaction=list_classifiers
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: GNU Lesser General Public License v2 (LGPLv2)',
        'Operating System :: OS Independent',
        'Topic :: Security :: Cryptography',
        'Topic :: Text Processing :: General',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',  # Python 3.6.9
        'Programming Language :: Python :: 3.10',
        # FIXME TODO more
        ],
    platforms='any',  # or distutils.util.get_platform()
    install_requires=install_requires,
)
