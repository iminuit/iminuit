from __future__ import (absolute_import, division, print_function,
                        unicode_literals)
from iminuit.util import describe
from iminuit.tests.utils import requires_dependency
from math import ldexp


# simple function
def f(x, y):
    pass


def test_simple():
    assert describe(f, True) == ['x', 'y']


# test bound method
class A:
    def f(self, x, y):
        pass


def test_bound():
    a = A()
    assert describe(a.f, True) == ['x', 'y']


# unbound method
def test_unbound():
    assert describe(A.f, True) == ['self', 'x', 'y']


# faking func code
class Func_Code:
    def __init__(self, varname):
        self.co_varnames = varname
        self.co_argcount = len(varname)


# test __call__
class Func1:
    def __init__(self):
        pass

    def __call__(self, x, y):
        return (x - 2.) ** 2 + (y - 5.) ** 2 + 10


def test_call():
    f1 = Func1()
    assert describe(f1, True) == ['x', 'y']


# fake func
class Func2:
    def __init__(self):
        self.func_code = Func_Code(['x', 'y'])

    def __call__(self, *arg):
        return (arg[0] - 2.) ** 2 + (arg[1] - 5.) ** 2 + 10


def test_fakefunc():
    f2 = Func2()
    assert describe(f2, True) == ['x', 'y']


# builtin (parsing doc)
def test_builtin():
    assert describe(ldexp, True) == ['x', 'i']


@requires_dependency('Cython')
def test_cython_embedsig():
    import pyximport
    pyximport.install()
    from . import cyfunc
    assert describe(cyfunc.f, True) == ['a', 'b']


@requires_dependency('Cython')
def test_cython_class_method():
    import pyximport
    pyximport.install()
    from . import cyfunc
    cc = cyfunc.CyCallable()
    assert describe(cc.test, True) == ['c', 'd']
