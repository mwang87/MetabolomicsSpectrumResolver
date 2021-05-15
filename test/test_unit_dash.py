import functools
import json
import sys
import unittest.mock
sys.path.insert(0, '..')

from usi_test_data import usis_to_test
import dashinterface

def test_url_parse():
    # ValueError will be thrown if invalid USI.
    for usi in usis_to_test:
        dashinterface.set_drawing_controls("", "?usi={}".format(usi))