from setuptools import setup, find_packages

with open('requirements.txt') as f:
    required = f.read().splitlines()

setup(
    name='mozci',
    version='0.32.0',
    packages=find_packages(),
    install_requires=required,

    # Meta-data for upload to PyPI
    author='Armen Zambrano G.',
    author_email='armenzg@mozilla.com',
    description="It is a python library to interact with \
                 Mozilla's Buildbot CI and TaskCluster. \
                 It simplifies and unifies querying and triggering jobs.",
    license='MPL',
    url='https://github.com/mozilla/mozilla_ci_tools',
)
