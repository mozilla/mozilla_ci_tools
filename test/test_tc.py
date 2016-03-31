"""This file contains the tests for mozci/sources/tc.py"""
import unittest
import json
import os
from jsonschema.exceptions import ValidationError
from mozci.sources import tc

json_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "tc_test_graph.json")
json_file2 = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "tc_test_graph2.json")
json_file3 = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "tc_test_graph3.json")


class TestTaskCluster(unittest.TestCase):
    """Testing mozci integration with TaskCluster"""
    def setUp(self):
        with open(json_file) as data_file:
            self.data = json.load(data_file)
        with open(json_file2) as data_file:
            self.data2 = json.load(data_file)
        with open(json_file3) as data_file:
            self.data3 = json.load(data_file)

    def test_check_invalid_graph(self):
        # This file lacks the "task" property under "tasks"
        self.assertRaises(ValidationError, tc.validate_graph, self.data)

    def test_check_invalid_graph2(self):
        # This should fail as the owner's email ID is not valid
        self.assertRaises(ValidationError, tc.validate_graph, self.data2)

    def test_check_valid_graph(self):
        # Similar to the previous test, but with the correct owner field
        tc.validate_graph(self.data3)
        self.assert_(True)
