from setuptools import setup, find_packages


required = [
    "buildapi_client",
    "ijson",
    "keyring",
    "progressbar",
    "pushlog_client",
    "requests",
    "taskcluster",
    "treeherder-client",
    "jsonschema"
]

setup(
    name='mozci',
    version='0.39.1',
    packages=find_packages(),
    install_requires=required + ['pytest-runner'],
    tests_require=required + ['mock', 'pytest'],
    # Meta-data for upload to PyPI
    author='Armen Zambrano G.',
    author_email='armenzg@mozilla.com',
    description="It is a python library to interact with \
                 Mozilla's Buildbot CI and TaskCluster. \
                 It simplifies and unifies querying and triggering jobs.",
    license='MPL',
    url='https://github.com/mozilla/mozilla_ci_tools',
)
