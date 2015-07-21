from setuptools import setup, find_packages

setup(
    name='mozci',
    version='0.11.1.dev0',
    packages=find_packages(),
    entry_points ={
        'console_scripts': [
            'mozci-trigger = mozci.scripts.trigger:main',
            'mozci-triggerbyfilters = mozci.scripts.triggerbyfilters:main',
            'mozci-alltalos = mozci.scripts.alltalos:main',
        ],
    },
    install_requires=[
        'beautifulsoup4>=4.3.2',
        'bugsy>=0.4.0',
        'ijson>=2.2',
        'progressbar>=2.3',
        'requests>=2.5.1',
        'keyring>=5.3',
        'treeherder-client>=1.4'
    ],

    # Meta-data for upload to PyPI
    author='Armen Zambrano G.',
    author_email='armenzg@mozilla.com',
    description="It is a commandline client and python library to interact with \
                 Mozilla's Buildbot CI (and TaskCluster in the future). \
                 It simplifies and unifies querying and triggering jobs.",
    license='MPL',
    url='http://github.com/armenzg/mozilla_ci_tools',
)
