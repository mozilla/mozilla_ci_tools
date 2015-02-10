.. Mozilla CI Tools documentation master file, created by
   sphinx-quickstart on Wed Jan 21 14:26:02 2015.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Introduction
============

Mozilla CI Tools (mozci) is designed to allow you interact and connect the different
pieces of Mozilla's Continous Integration.

It has several modules and command line scripts to help you use them.

Understanding
=============
.. toctree::
   :maxdepth: 2

   project_definition
   data_sources
   scripts

Modules
=======
You can either interact through low-level modules or use the mozci module as an interface
to the other modules.

.. toctree::
   :maxdepth: 2

   mozci
   platforms

Modules to deal with data sources:

.. toctree::
   :maxdepth: 2

   allthethings
   buildapi
   buildjson
   pushlog

Resources
=========
* Source_
* Docs_
* Tasks_
* Pypi_

Contribute
==========
If you would like to contribute to this project, feel free to pick up one of the tasks
in the Trello board (Tasks_).

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

.. _Source: https://github.com/armenzg/mozilla_ci_tools
.. _Docs: https://mozilla-ci-tools.readthedocs.org
.. _Tasks: https://trello.com/b/BplNxd94/mozilla-ci-tools-public
.. _Pypi: https://pypi.python.org/pypi/mozci
