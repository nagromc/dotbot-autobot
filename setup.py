#!/usr/bin/env python

from setuptools import find_packages
from setuptools import setup

setup(
    name='autobot',
    description="Automatically update your Dotbot config file when you"
                "add files in Git",
    url='https://github.com/gwerbin/dotbot-autobot',
    classifiers=[
        'Programming Language :: Python :: 3',
    ],
    packages=find_packages(),
    install_requires=[
        'cffi',
        'pyyaml',
        # 'pygit2==0.21.1',
        'pygit2',
        'unidiff'
    ]
)
