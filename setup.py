from setuptools import setup, find_packages

setup(
    name='mozci',
    version='0.15.1',
    packages=find_packages(),
    entry_points ={
        'console_scripts': [
            'mozci-trigger = mozci.scripts.trigger:main',
            'mozci-triggerbyfilters = mozci.scripts.triggerbyfilters:main',
        ],
    },
    install_requires=[
        'beautifulsoup4>=4.3.2',
        'bugsy>=0.4.0',
        'ijson>=2.2',
        'keyring>=5.3',
        'progressbar>=2.3',
        # Due to upper limit for the TC client
        # https://github.com/taskcluster/taskcluster-client.py/commit/ae32c81ceeb2fed9018614bd9be53ddbd0f99e29
        'requests<=2.7.0',
        'taskcluster>=0.0.22',
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
