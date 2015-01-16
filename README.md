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
Suggested use with a virtualenv:
<pre>
virtualenv --no-site-packages venv
source venv/bin/activate
</pre>

Install or develop mozci:
<pre>
python setup.py {install|develop}
</pre>

Scripts
=======
You will have under the scripts/ directory various scripts that you can run.

trigger.py
* Allows you to trigger arbitrary jobs through buildapi
