from setuptools import setup, find_packages

setup(
    name='mozci_scripts',
    version='0.1.0',
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'mozci-trigger = trigger:main'
        ],
    },
    install_requires=[
        'mozci>=0.30.0',
    ],

    # Meta-data for upload to PyPI
    author='Armen Zambrano G.',
    author_email='armenzg@mozilla.com',
    description="This is the commandline client for mozci. \
                 It allows you to interact with Mozilla's Buildbot CI and \
                 TaskCluster. It simplifies and unifies querying and triggering \
                 jobs.",
    license='MPL',
    url='https://github.com/mozilla/mozilla_ci_tools',
)
