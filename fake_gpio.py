#pylint: disable=missing-docstring, invalid-name, multiple-statements

def _a(_a): pass
def _a_b(_a, _b): pass

input = _a #pylint: disable=redefined-builtin
setup = output = _a_b

IN = 0
OUT = 1
LOW = 0
HIGH = 1
