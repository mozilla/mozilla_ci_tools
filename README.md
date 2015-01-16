mozilla_ci_tools
================

This repository contains a collection of tools that allows to interact with Mozilla's continuos integration.

Requirements
============
* python 2.7
* pip
* virtualenv

Installation
============
<pre>
virtualenv --no-site-packages venv
source venv/bin/activate
python setup.py {install|develop}
</pre>

Scripts
=======
* scripts/trigger.py
** Allows you to trigger arbitrary jobs through buildapi
