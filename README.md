Mozilla's continous integration tools
=====================================

This repository contains a collection of tools that allows to interact with Mozilla's continuos integration.

Status
======

[![Build Status](https://travis-ci.org/armenzg/mozilla_ci_tools.svg?branch=master)](https://travis-ci.org/armenzg/mozilla_ci_tools)
[![Coverage Status](https://coveralls.io/repos/armenzg/mozilla_ci_tools/badge.svg)](https://coveralls.io/r/armenzg/mozilla_ci_tools)

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

Install or develop with it:
<pre>
python setup.py {install|develop}
</pre>

Scripts
=======
You will have under the scripts/ directory various scripts that you can run.

trigger.py
* Allows you to trigger arbitrary jobs through buildapi
