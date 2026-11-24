import logging

import pytest

from app.robot.service import RobotControlState


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def make_state(timeout_seconds: float = 60.0):
    clock = FakeClock()
    state = RobotControlState(timeout_seconds=timeout_seconds, clock=clock)
    return state, clock


def test_starts_empty_then_acquire_succeeds():
    state, _ = make_state()

    assert state.holder() is None

    assert state.acquire("jisoo") is True
    assert state.holder() == "jisoo"


def test_acquire_rejected_when_held_by_other():
    state, _ = make_state()
    state.acquire("jisoo")

    assert state.acquire("sumin") is False
    assert state.holder() == "jisoo"


def test_acquire_extends_expiry():
    state, clock = make_state(timeout_seconds=60.0)
    state.acquire("jisoo")

    clock.advance(50.0)
    assert state.acquire("jisoo") is True

    clock.advance(50.0)
    assert state.holder() == "jisoo"


def test_is_holder_reflects_holder_and_expiry():
    state, clock = make_state(timeout_seconds=60.0)
    state.acquire("jisoo")

    assert state.is_holder("jisoo") is True
    assert state.is_holder("sumin") is False

    clock.advance(61.0)
    assert state.is_holder("jisoo") is False


def test_release_frees_control():
    state, _ = make_state()
    state.acquire("jisoo")

    state.release("jisoo")

    assert state.holder() is None
    assert state.acquire("sumin") is True


def test_release_by_other_is_ignored():
    state, _ = make_state()
    state.acquire("jisoo")

    state.release("sumin")

    assert state.holder() == "jisoo"


def test_release_clears_expired_holder():
    state, clock = make_state(timeout_seconds=60.0)
    state.acquire("jisoo")

    clock.advance(61.0)
    state.release("jisoo")

    assert state._holder is None


def test_expires_at_timeout():
    state, clock = make_state(timeout_seconds=60.0)
    state.acquire("jisoo")

    clock.advance(59.0)
    assert state.holder() == "jisoo"

    clock.advance(1.0)
    assert state.holder() is None


def test_holder_can_acquire_again_after_expiry():
    state, clock = make_state(timeout_seconds=60.0)
    state.acquire("jisoo")

    clock.advance(61.0)
    assert state.holder() is None

    assert state.acquire("jisoo") is True
    assert state.holder() == "jisoo"


def test_other_takes_over_after_expiry():
    state, clock = make_state(timeout_seconds=60.0)
    state.acquire("jisoo")

    clock.advance(61.0)

    assert state.acquire("sumin") is True
    assert state.acquire("jisoo") is False
    assert state.holder() == "sumin"


def test_repeated_acquire_logs_once(caplog):
    state, _ = make_state()

    with caplog.at_level(logging.INFO, logger="uvicorn.error"):
        for _ in range(10):
            state.acquire("jisoo")

    acquired = [r for r in caplog.records if "control_acquired" in r.getMessage()]
    assert len(acquired) == 1


@pytest.mark.parametrize("bad_timeout", [0.0, -1.0, float("inf"), float("nan")])
def test_invalid_timeout_is_rejected(bad_timeout):
    with pytest.raises(ValueError):
        RobotControlState(timeout_seconds=bad_timeout)
