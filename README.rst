============================================
mozci - Mozilla Continuous Integration Tools
============================================

.. image:: https://pypip.in/version/mozci/badge.svg
    :target: https://pypi.python.org/pypi/mozci/
    :alt: pypi version

.. image:: http://img.shields.io/travis/armenzg/mozilla_ci_tools/master.png
    :target: https://travis-ci.org/armenzg/mozilla_ci_tools
    :alt: Travis-CI Build Status

.. image:: https://readthedocs.org/projects/mozilla-ci-tools/badge/?version=latest
    :target: https://readthedocs.org/projects/mozilla-ci-tools/?badge=latest
    :alt: Documentation Status

.. image:: https://coveralls.io/repos/armenzg/mozilla_ci_tools/badge.svg
    :target: https://coveralls.io/r/armenzg/mozilla_ci_tools
    :alt: Test coverage status

.. image:: https://pypip.in/license/mozci/badge.svg
    :target: https://www.mozilla.org/MPL
    :alt: License


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

    git clone https://github.com/armenzg/mozilla_ci_tools.git

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
