import os
import platform
import sys
try:
    from setuptools import setup, find_packages
except ImportError:
    from distutils.core import setup
    find_packages = None

try:
    import pyvim  # https://github.com/prompt-toolkit/pyvim - pip install pyvim
except ImportError:
    pyvim = None


is_cpython = platform.python_implementation() == 'CPython'
is_py3 = sys.version_info >= (3,)
is_win = sys.platform.startswith('win')
is_pypy = '__pypy__' in sys.builtin_module_names  # platform.python_implementation() == 'PyPy'

if len(sys.argv) <= 1:
    print("""
Suggested setup.py parameters:

    * build
    * install
    * sdist  --formats=zip
    * sdist  # NOTE requires tar/gzip commands


    python -m pip install -e .

PyPi:

    python -m pip install setuptools twine

    python setup.py sdist
    # python setup.py sdist --formats=zip
    python -m twine upload dist/* --verbose

    ./setup.py  sdist ; twine upload dist/* --verbose

""")

readme_filename = 'README.md'
if os.path.exists(readme_filename):
    f = open(readme_filename)
    long_description = f.read()
    f.close()
else:
    long_description = None

# Metadata
project_name = 'puren_tonbo'
project_name_lower = project_name.lower()
license = "GNU Lesser General Public License v2 (LGPLv2)"  # ensure this matches tail of http://pypi.python.org/pypi?%3Aaction=list_classifiers
person_name = 'clach04'
person_email = None

__version__ = None  # Overwritten by executing _version.py.
exec(open(os.path.join(os.path.abspath(os.path.dirname(__file__)), project_name_lower, '_version.py')).read())  # get __version__


# TODO/FIXME dupe of requirements.txt - also chi_io missing here (as not on pypi)
install_requires = ['colorama', 'pycryptodome', 'openssl_enc_compat', 'percolator']  # TODO reorder/indent
if is_py3:
    install_requires += ['pyzipper']  # pyzipperis python 3.x+
if is_win and is_cpython:
    install_requires += ['pywin32']
# https://setuptools.pypa.io/en/latest/userguide/dependency_management.html#optional-dependencies
# https://stackoverflow.com/questions/10572603/specifying-optional-dependencies-in-pypi-python-setup-py

extras_require = {
    'chi_io': ['chi_io', ],
    'jenc': ['jenc>=0.0.5', ],
    'pyvim': ['pyvim', ],  # TODO version?
    'python-gnupg': ['python-gnupg', ],  # TODO version?
    # Web
    'cherrypy': ['cherrypy', ],  # TODO version?
    'Markdown': ['Markdown', ],  # TODO version?
    # TODO python-gnupg (consider replacements before implementing https://github.com/clach04/puren_tonbo/issues/118)
}
if is_cpython and is_py3:
    extras_require['age'] = ['age', ],  # 0.5.1 is known to work
    #'ssage': ['ssage', ],  # ssage-1.4.0

extras_require_all = []
for extra_name in extras_require:
    extras_require_all.append(extras_require[extra_name])
extras_require['all'] = extras_require_all  # convenience, all of the above. NOTE duplicate of above
extras_require['web'] = extras_require['cherrypy'] + extras_require['Markdown']  # convenience. NOTE duplicate of above

# disable package finding, explictly list package
find_packages = False
if find_packages:
    packages =     find_packages(where=os.path.dirname(__file__), include=['*'])
else:
    packages = [project_name_lower]

setup(
    name=project_name,
    version=__version__,
    url='https://github.com/clach04/' + project_name,
    description='Plain text notes Tombo (chi) alternative, also supports; age, ccrypt, GnuPG (OpenPGP, gpg), jenc (Markor), OpenSSL AES-256-CBC, AES-256 ZIP AE-1/AE-2 and VimCrypt1-3 encrypted files. Integrates with VIM. WIP',
    long_description=long_description,
    long_description_content_type='text/markdown',

    author=person_name,
    author_email=person_email,
    maintainer=person_name,
    maintainer_email=person_email,

    packages=packages,
    package_data={
        'puren_tonbo': [os.path.join(os.path.dirname(__file__), 'puren_tonbo', 'tests', 'data', '*'),  # TODO demo_notes?
                        os.path.join(os.path.dirname(__file__), 'puren_tonbo', 'resources', '*'),
                        ],
    },
    #scripts=['ptcipher.py'],
    #py_modules=[''], # TODO scripts
    entry_points={
        'console_scripts': [
            'ptcat = puren_tonbo.tools.ptcat:main',
            'ptcipher = puren_tonbo.tools.ptcipher:main',
            'ptconfig = puren_tonbo.tools.ptconfig:main',
            'ptdiff3merge = puren_tonbo.tools.ptdiff3merge:main',
            'ptgrep = puren_tonbo.tools.ptgrep:main',
            'ptnewline_check = puren_tonbo.tools.ptnewline_check:main',
            'ptrecrypt = puren_tonbo.tools.ptrecrypt:main',
            'ptig = puren_tonbo.tools.ptig:main',
            'pttkview = puren_tonbo.tools.pttkview:main',  # Assume tk available
            #'ptwebcp = puren_tonbo.tools.ptwebcp:main',  # Assume CherryPy (or dietcherrypy) and Markdown
        ] + (['ptpyvim = puren_tonbo.tools.ptpyvim:main'] if pyvim else []),
    },
    #data_files=[('.', [readme_filename])],  # does not work :-( ALso tried setup.cfg [metadata]\ndescription-file = README.md # Maybe try include_package_data = True and a MANIFEST.in?
    classifiers=[  # See http://pypi.python.org/pypi?%3Aaction=list_classifiers
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: ' + license,
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
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        # FIXME TODO more
        ],
    platforms='any',  # or distutils.util.get_platform()
    install_requires=install_requires,
    extras_require=extras_require,
    zip_safe=True,
)
