from iminuit._core import (
    FCN,
    MnUserParameterState,
    MnMigrad,
    MnStrategy,
    MnScan,
    FunctionMinimum,
    MnSimplex,
)
from pytest import approx
import pytest


@pytest.fixture
def debug():
    from iminuit._core import MnPrint

    prev = MnPrint.global_level
    MnPrint.global_level = 3
    yield
    MnPrint.global_level = prev


def test_MnStrategy():
    assert MnStrategy() == 1
    assert MnStrategy(0) == 0
    assert MnStrategy(2) == 2
    s = MnStrategy()
    s.strategy = 2
    assert s.strategy == 2
    assert s != 1
    assert s > 1
    assert s < 3
    assert s >= 2
    assert s >= 1
    assert s <= 2
    assert s <= 3


def test_FCN():
    f = FCN(lambda x, y: 10 + x ** 2 + ((y - 1) / 2) ** 2, None, False, 1)
    state = MnUserParameterState()
    state.add("x", 5, 0.1)
    state.add("😁", 3, 0.2, -5, 5)
    assert len(state) == 2
    assert state[0].number == 0
    assert state[0].name == "x"
    assert state[0].value == 5
    assert state[0].error == 0.1
    assert state[1].number == 1
    assert state[1].name == "😁"
    assert state[1].value == 3
    assert state[1].error == 0.2
    migrad = MnMigrad(f, state, 1)
    migrad.set_print_level(3)
    fmin = migrad(0, 0.1)
    state = fmin.state
    assert len(state) == 2
    assert state[0].number == 0
    assert state[0].name == "x"
    assert state[0].value == approx(0, abs=1e-2)
    assert state[0].error == approx(1, abs=1e-2)
    assert state[1].number == 1
    assert state[1].name == "😁"
    assert state[1].value == approx(1, abs=1e-2)
    assert state[1].error == approx(2, abs=6e-2)
    assert f.nfcn > 0
    assert f.ngrad == 0


def test_FCN_with_grad():
    # MnPrint.set_global_level(3)
    f = FCN(lambda x: 10 + x ** 2, lambda x: [2 * x], False, 1)
    state = MnUserParameterState()
    state.add("x", 5, 0.1)
    migrad = MnMigrad(f, state, 1)
    fmin = migrad(0, 0.1)
    state = fmin.state
    assert len(state) == 1
    assert state[0].number == 0
    assert state[0].name == "x"
    assert state[0].value == approx(0, abs=1e-3)
    assert state[0].error == approx(1, abs=1e-3)
    assert f.nfcn > 0
    assert f.ngrad > 0


def test_grad_np():
    fcn = FCN(
        lambda xy: 10 + xy[0] ** 2 + ((xy[1] - 1) / 2) ** 2,
        lambda xy: [2 * xy[0], (xy[1] - 1)],
        True,
        1,
    )
    state = MnUserParameterState()
    state.add("x", 5, 0.1)
    state.add("😁", 3, 0.2, -5, 5)
    assert len(state) == 2
    str = MnStrategy(2)
    migrad = MnMigrad(fcn, state, str)
    fmin = migrad(0, 0.1)
    state = fmin.state
    assert len(state) == 2
    assert state[0].number == 0
    assert state[0].name == "x"
    assert state[0].value == approx(0, abs=1e-2)
    assert state[0].error == approx(1, abs=1e-2)
    assert state[1].number == 1
    assert state[1].name == "😁"
    assert state[1].value == approx(1, abs=1e-2)
    assert state[1].error == approx(2, abs=6e-2)
    assert fcn.nfcn > 0
    assert fcn.ngrad > 0


def test_MnScan():
    fcn = FCN(lambda x: 10 + x ** 2, None, False, 1)
    state = MnUserParameterState()
    state.add("x", 2, 5)
    scan = MnScan(fcn, state, 1)
    fmin = scan(0, 0.1)
    assert fmin.is_valid
    state = fmin.state
    assert len(state) == 1
    assert state[0].value == approx(0, abs=1e-2)


def test_MnSimplex():
    fcn = FCN(lambda x: 10 + x ** 2, None, False, 1)
    state = MnUserParameterState()
    state.add("x", 2, 5)
    simplex = MnSimplex(fcn, state, 1)
    fmin = simplex(0, 0.1)
    assert fmin.is_valid
    state = fmin.state
    assert len(state) == 1
    assert state[0].value == approx(0, abs=5e-2)


def test_FunctionMinimum():
    fcn = FCN(lambda x: 10 + x ** 2, None, False, 1)
    st = MnUserParameterState()
    st.add("x", 2, 5)
    str = MnStrategy(1)
    fm = FunctionMinimum(fcn, st, 0.1, str)
    assert fm.is_valid
    assert len(fm.state) == 1
    assert fm.fval == 0.1
