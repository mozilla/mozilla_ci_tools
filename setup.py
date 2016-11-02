from setuptools import setup, find_packages


required = [
    "buildapi_client>=0.6.1",
    "ijson",
    "keyring",
    "progressbar",
    "pushlog_client",
    "requests",
    "taskcluster",
    "treeherder-client>=3.1.0",
    "jsonschema",
    "pyyaml"
]

setup(
    name='mozci',
    version='0.49.1.dev0',
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
