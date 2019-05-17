# Copyright (c) 2016-2019 Renata Hodovan, Akos Kiss.
#
# Licensed under the BSD 3-Clause License
# <LICENSE.rst or https://opensource.org/licenses/BSD-3-Clause>.
# This file may not be copied, modified, or distributed except
# according to those terms.

from setuptools import setup, find_packages


def fuzzinator_version():
    def _version_scheme(version):
        return version.format_with('{tag}')

    def _local_scheme(version):
        if version.exact and not version.dirty:
            return ''
        parts = ['{distance}'.format(distance=version.distance)]
        if version.node:
            parts.append('{node}'.format(node=version.node))
        if version.dirty:
            parts.append('d{time:%Y%m%d}'.format(time=version.time))
        return '+{parts}'.format(parts='.'.join(parts))

    return { 'version_scheme': _version_scheme, 'local_scheme': _local_scheme }


setup(
    name='fuzzinator',
    packages=find_packages(),
    url='https://github.com/renatahodovan/fuzzinator',
    license='BSD',
    author='Renata Hodovan, Akos Kiss',
    author_email='hodovan@inf.u-szeged.hu, akiss@inf.u-szeged.hu',
    description='Fuzzinator Random Testing Framework',
    long_description=open('README.rst').read(),
    zip_safe=False,
    include_package_data=True,
    setup_requires=['setuptools_scm'],
    use_scm_version=fuzzinator_version,
    install_requires=[
        'chardet',
        'chevron',
        'google-api-python-client',
        'jinja2',
        'keyring',
        'keyrings.alt',
        'markdown',
        'oauth2client',
        'pexpect',
        'picire==19.3',
        'picireny==19.3',
        'psutil',
        'PyGithub',
        'pymongo',
        'pyperclip',
        'python-bugzilla',
        'python-gitlab',
        'rainbow_logging_handler',
        'setuptools',
        'tornado<6.0',  # no Tornado 6 for Python < 3.5
        'urwid',
    ],
    extras_require={
        'docs': [
            'sphinx',
            'sphinx_rtd_theme',
        ]
    },
    entry_points={
        'console_scripts': ['fuzzinator = fuzzinator.executor:execute']
    }
)
