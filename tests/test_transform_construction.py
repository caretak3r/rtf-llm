"""construct_transform: signature filtering + body-TypeError propagation."""

import pytest

from modules.engine.registry import construct_transform


class Zero:
    def __init__(self):
        self.seen = {}


class Needs:
    def __init__(self, client=None, config=None):
        self.seen = {"client": client, "config": config}


class Buggy:
    def __init__(self):
        raise TypeError("bug inside body")


def test_zero_arg_ignores_available():
    t = construct_transform(Zero, client="c", config={})
    assert t.seen == {}


def test_kwargs_filtered_by_signature():
    t = construct_transform(Needs, client="c", config={"a": 1}, pair_turns=4)
    assert t.seen == {"client": "c", "config": {"a": 1}}


def test_body_typeerror_propagates():
    with pytest.raises(TypeError, match="bug inside body"):
        construct_transform(Buggy, client="c")
