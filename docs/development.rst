Development
===========
This page is simply to indicate how the development workflow for this project is like.

Release process
---------------
There are two branches:
* master
* stable

On master we have the latest code. We iterate fast on it to fix any bugs and where we add new features.
We merge to stable before we make a new release which we put on pypi. We use tags to define releases.
We use semantic versioning for versions of mozci.

Contributing
------------
In order to contribute to the project:
* Fork the project
* Create a new branch (based on master)
* Fix the issue
* Run tox successfully
* Request pull request
