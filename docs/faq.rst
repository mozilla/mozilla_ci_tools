F.A.Q.
======

How do you release software?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

We use zest.releaser. You simply install it: ::

    pip install zest.releaser

TBD - https://github.com/armenzg/mozilla_ci_tools/issues/29

How do I generate the docs?
^^^^^^^^^^^^^^^^^^^^^^^^^^^

To generate the docs, follow these steps:

* Move inside docs/ directory
* Run:
::

    pip install -r requirements.txt
    make html

* To view the docs on a webserver http://127.0.0.1:8000 and auto-rebuild
  the documentation when any files are changed:
::

    make livehtml

How can I contribute?
^^^^^^^^^^^^^^^^^^^^^

If you would like to contribute to this project, feel free to pick up one of the issues or tasks
in the Trello board (Tasks_) or the issues page (Issues_).

In order to contribute the code:

* Fork the project
* Create a new branch
* Fix the issue - add the feature
* Run tox successfully
* Commit your code
* Request a pull request

.. _Tasks: https://trello.com/b/BplNxd94/mozilla-ci-tools-public
.. _Pypi: https://pypi.python.org/pypi/mozci
.. _Issues: https://github.com/armenzg/mozilla_ci_tools/issues
