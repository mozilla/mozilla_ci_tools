===========================================
mozci - Mozilla Continuous Integration Tools
===========================================

.. image:: http://img.shields.io/travis/armenzg/mozilla_ci_tools/master.png
    :alt: Travis-CI Build Status
    :target: https://travis-ci.org/armenzg/mozilla_ci_tools

.. image:: https://readthedocs.org/projects/mozilla-ci-tools/badge/?version=latest
    :target: https://readthedocs.org/projects/mozilla-ci-tools/?badge=latest
    :alt: Documentation Status

.. image:: https://coveralls.io/repos/armenzg/mozilla_ci_tools/badge.svg
   :target: https://coveralls.io/r/armenzg/mozilla_ci_tools
   :alt: Test coverage status

* Free software: `Mozilla License`__

__ https://www.mozilla.org/MPL/

Installation
============

::

    pip install git+https://github.com/armenzg/mozilla_ci_tools.git

Documentation
=============

Usage is described in the documentation:
https://mozilla-ci-tools.readthedocs.org

Development
===========

To run the all tests run::

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
.. _Tox: http://testrun.org/tox/
.. _Sphinx: http://sphinx-doc.org/
.. _ReadTheDocs: https://readthedocs.org/
.. _Setuptools: https://pypi.python.org/pypi/setuptools
.. _Cookiecutter: https://github.com/audreyr/cookiecutter
