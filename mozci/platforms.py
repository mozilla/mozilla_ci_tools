#! /usr/bin/env python
"""
This module helps us connect builds to tests since we don't have an API
to help us with this task.
"""
PREFIX = {
    "Windows 8 64-bit": "WINNT 6.1 x86-64",
}

JOB_TYPE = {
    "opt": "build",
    "talos": "build",
    "debug": "leak test build",
}
