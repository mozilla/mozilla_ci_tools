End of life
###########
Further development of this project has ended. Thanks for all your contributions!

See https://bugzilla.mozilla.org/show_bug.cgi?id=1379172 for details.

------------

============================================
mozci - Mozilla Continuous Integration Tools
============================================

|  |license| |docs| |ci-status| |codecov|  |contribute|


Installation
============

::

    pip install mozci

Documentation
=============

Usage is described in the documentation:
https://mozilla-ci-tools.readthedocs.org

Development
===========

Pull the latest development version::

    git clone https://github.com/mozilla/mozilla_ci_tools.git

Move inside the project directory, create a virtualenv_ (highly recommended)
and after activating a virtualenv, do::

    python setup.py develop

You are all set! Visit the link in the documentation section for
detailed use and contribution guidelines.

To run all the tests run::

    tox

Requirements
------------

Developing on this project requires your environment to  have these
minimal dependencies:

* Tox_ - for running the tests
* Setuptools_ - for building the package, wheels etc. Now-days
  Setuptools is widely available, it shouldn't pose a problem :)
* Sphinx_ - for updating the documentation

Note: the layout for this project came from the Cookiecutter_
template https://github.com/ionelmc/cookiecutter-pylibrary-minimal.

.. _Travis-CI: http://travis-ci.org/
.. _virtualenv: http://docs.python-guide.org/en/latest/dev/virtualenvs/
.. _Tox: http://testrun.org/tox/
.. _Sphinx: http://sphinx-doc.org/
.. _ReadTheDocs: https://readthedocs.org/
.. _Setuptools: https://pypi.python.org/pypi/setuptools
.. _Cookiecutter: https://github.com/audreyr/cookiecutter

.. |ci-status| image:: http://img.shields.io/travis/mozilla/mozilla_ci_tools/master.png
    :target: https://travis-ci.org/mozilla/mozilla_ci_tools
    :alt: Travis-CI Build status
.. |docs| image:: https://readthedocs.org/projects/mozilla-ci-tools/badge/?version=latest&style=flat
    :target: https://mozilla-ci-tools.readthedocs.org
    :alt: Documentation
.. |license| image:: https://img.shields.io/pypi/l/mozci.svg
    :target: https://pypi.python.org/pypi/mozci
    :alt: License: MPL 2.0
.. |codecov| image:: https://coveralls.io/repos/mozilla/mozilla_ci_tools/badge.svg?branch=master&service=github
    :target: https://coveralls.io/github/mozilla/mozilla_ci_tools?branch=master
    :alt: Coverage
.. |contribute| image:: https://badge.waffle.io/mozilla/mozilla_ci_tools.png?label=ready&title=Ready
    :target: https://waffle.io/mozilla/mozilla_ci_tools
    :alt: 'Issues ready to be worked on'
