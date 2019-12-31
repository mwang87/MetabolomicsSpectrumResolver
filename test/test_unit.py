import sys
sys.path.insert(0, "..")
import parsing  # noqa: E402
from usi_test_cases import test_usi_list


def test_uri_parse():
    for usi in test_usi_list:
        parsing.parse_usi(usi)  
