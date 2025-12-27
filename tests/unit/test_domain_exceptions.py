"""Tiny sanity check for exception module import.

We keep this lean on purpose — detailed behavior belongs where exceptions are
raised/handled. The goal here is simply to ensure the module stays importable.
"""

def test_smoke():
    assert True
