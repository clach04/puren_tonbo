import os
import sys
try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

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

#exec(open(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'puren_tonbo', '_version.py')).read())
__version__ = '0.0.1'


# TODO/FIXME dupe of requirements.txt - also chi_io missing here (as not on pypi)
install_requires = ['pycryptodome']
if is_py3:
    install_requires += ['pyzipper']  # pyzipperis python 3.x+

setup(
    name='puren_tonbo',
    version=__version__,
    author='clach04',
    url='https://github.com/clach04/puren_tonbo',
    description='Tombo alternative, also supports AES-256 ZIP files. Work-In-Progress (WIP)!',  # FIXME
    long_description=long_description,
    packages=['puren_tonbo'],
    #scripts=['ptcipher.py'],
    #py_modules=[''], # TODO scripts
    entry_points={
        'console_scripts': [
            'ptcipher = puren_tonbo.tools.ptcipher:main',
        ],
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
