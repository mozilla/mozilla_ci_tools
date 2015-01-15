import os
from setuptools import setup, find_packages

here = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(here, "requirements.txt")) as f:
    dependencies = f.read().splitlines()

setup(name='mozci',
      version='0.1',
      description='It helps us dealing with the CI.',
      url='http://github.com/armenzg/mozilla_ci_tools',
      author='Armen Zambrano G.',
      author_email='armenzg@mozilla.com',
      license='MPL',
      install_requires=dependencies,
      packages=["mozci"],
      entry_points={
          "console_scripts": [
              # XXX: I'm not sure about this
              "trigger = scripts.trigger:main"
          ],
      },
     )
