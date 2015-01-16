import os
from setuptools import setup, find_packages

here = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(here, "requirements.txt")) as f:
    dependencies = f.read().splitlines()

setup(
    name='mozci',
    version='0.1.1',
    packages=find_packages(),

    install_requires=dependencies,

    # Meta-data for upload to PyPI
    author='Armen Zambrano G.',
    author_email='armenzg@mozilla.com',
    description='It helps us dealing with the CI.',
    license='MPL',
    url='http://github.com/armenzg/mozilla_ci_tools',
)
