"""
Standard cost functions to minimize.
"""

from .util import describe, make_func_code
import numpy as np
from collections.abc import Sequence


def _safe_log(x):
    # does not return NaN for x == 0
    log_const = 1e-323  # pragma: no cover
    return np.log(x + log_const)  # pragma: no cover


def _sum_log_x(x):
    return np.sum(_safe_log(x))  # pragma: no cover


def _neg_sum_n_log_mu(n, mu):
    # subtract n log(n) to keep sum small, required to not loose accuracy in Minuit
    return np.sum(n * _safe_log(n / (mu + 1e-323)))  # pragma: no cover


def _sum_log_poisson(n, mu):
    # subtract n - n log(n) to keep sum small, required to not loose accuracy in Minuit
    return np.sum(mu - n + n * _safe_log(n / (mu + 1e-323)))  # pragma: no cover


def _z_squared(y, ye, ym):
    z = y - ym  # pragma: no cover
    z /= ye  # pragma: no cover
    return z * z  # pragma: no cover


def _sum_z_squared(y, ye, ym):
    return np.sum(_z_squared(y, ye, ym))  # pragma: no cover


def _sum_z_squared_soft_l1(y, ye, ym):
    z = _z_squared(y, ye, ym)  # pragma: no cover
    return np.sum(2 * (np.sqrt(1.0 + z) - 1.0))  # pragma: no cover


try:
    import numba as nb

    jit = nb.njit(nogil=True, parallel=True, cache=True)

    _safe_log = jit(_safe_log)
    _sum_log_x = jit(_sum_log_x)
    _neg_sum_n_log_mu = jit(_neg_sum_n_log_mu)
    _sum_log_poisson = jit(_sum_log_poisson)
    _z_squared = jit(_z_squared)
    _sum_z_squared = jit(_sum_z_squared)
    _sum_z_squared_soft_l1 = jit(_sum_z_squared_soft_l1)

    del jit
    del nb
except ImportError:  # pragma: no cover
    pass  # pragma: no cover


class Cost:
    """Base class for all cost functions."""

    __slots__ = "_func_code", "_verbose"

    @property
    def errordef(self):
        """For internal use."""
        return 1.0

    @property
    def func_code(self):
        """For internal use."""
        return self._func_code

    @property
    def verbose(self):
        """Verbosity level.

        Set this to 1 to print all function calls with input and output.
        """
        return self._verbose

    @verbose.setter
    def verbose(self, value: int):
        self._verbose = int(value)

    def __init__(self, args, verbose):
        self._func_code = make_func_code(args)
        self.verbose = verbose

    def __add__(self, rhs):
        return CostSum(self, rhs)

    def __call__(self, *args):
        r = self._call(args)
        if self.verbose >= 1:
            print(args, "->", r)
        return r


class MaskedCost(Cost):
    """Base class for cost functions that support data masking."""

    __slots__ = "_mask", "_masked"

    def __init__(self, args, verbose):
        super().__init__(args, verbose)
        self.mask = None

    @property
    def mask(self):
        """Boolean array, array of indices, or None.

        If not None, only values selected by the mask are considered. The mask acts on
        the first dimension of a value array, i.e. values[mask]. Default is None.
        """
        return self._mask

    @mask.setter
    def mask(self, mask):
        if mask is not None:
            self._mask = np.asarray(mask)
        self._masked = self._make_masked()

    def _make_masked(self):
        return self.data if self._mask is None else self.data[self._mask]


class CostSum(Cost, Sequence):
    """Sum of cost functions.

    Users do not need to create objects of this class themselves. They should just add
    cost functions, for example:

        nll = UnbinnedNLL(...)
        lsq = LeastSquares(...)
        ncs = NormalConstraint(...)
        csum = nll + lsq + ncs

    CostSum is used to combine data from different experiments or to combine normal cost
    functions with soft constraints (see NormalConstraint).

    The parameters of CostSum are the union of all parameters of its constituents.
    Supports the sequence protocol to access the constituents.
    """

    __slots__ = "_items", "_maps"

    def __init__(self, *items):
        args, self._maps = self._join_args(items)
        self._items = []
        for item in items:
            if isinstance(item, CostSum):
                self._items += item._items
            else:
                self._items.append(item)
        super().__init__(args, max(c.verbose for c in self))

    def _call(self, args):
        r = 0.0
        for c, m in zip(self._items, self._maps):
            a = tuple(args[mi] for mi in m)
            r += c._call(a)
        return r

    def _join_args(self, costs):
        out_args = []
        in_args = tuple(c._func_code.co_varnames for c in costs)
        for args in in_args:
            for arg in args:
                if arg not in out_args:
                    out_args.append(arg)
        maps = []
        for args in in_args:
            pos = tuple(out_args.index(arg) for arg in args)
            maps.append(pos)
        return tuple(out_args), tuple(maps)

    def __len__(self):
        return self._items.__len__()

    def __getitem__(self, key):
        return self._items.__getitem__(key)


class UnbinnedCost(MaskedCost):
    """Base class for unbinned cost functions."""

    __slots__ = "_data", "_model"

    @property
    def data(self):
        """Unbinned samples."""
        return self._data

    @data.setter
    def data(self, value):
        self._data[:] = value

    def __init__(self, data, model, verbose):
        self._data = _norm(data)
        self._model = model
        super().__init__(describe(model)[1:], verbose)


class UnbinnedNLL(UnbinnedCost):
    """Unbinned negative log-likelihood.

    Use this if only the shape of the fitted PDF is of interest and the original
    unbinned data is available.
    """

    __slots__ = ()

    @property
    def pdf(self):
        """PDF that describes the data."""
        return self._model

    def __init__(self, data, pdf, verbose=0):
        """
        **Parameters**

        data: array-like
            Sample of observations.

        pdf: callable
            Probability density function of the form f(data, par0, par1, ..., parN),
            where `data` is the data sample and par0, ... parN are model parameters.

        verbose: int, optional
            Verbosity level.

            - 0: is no output (default)
            - 1: print current args and negative log-likelihood value
        """
        super().__init__(data, pdf, verbose)

    def _call(self, args):
        data = self._masked
        return -2.0 * _sum_log_x(self._model(data, *args))


class ExtendedUnbinnedNLL(UnbinnedCost):
    """Unbinned extended negative log-likelihood.

    Use this if shape and normalization of the fitted PDF are of interest and the
    original unbinned data is available.
    """

    __slots__ = ()

    @property
    def scaled_pdf(self):
        """Density function that describes the data."""
        return self._model

    def __init__(self, data, scaled_pdf, verbose=0):
        """
        **Parameters**

        data: array-like
            Sample of observations.

        scaled_pdf: callable
            Density function of the form f(data, par0, par1, ..., parN), where `data` is
            the data sample and par0, ... parN are model parameters. Must return a tuple
            (<integral over f in data range>, <f evaluated at data points>).

        verbose: int, optional
            Verbosity level

            - 0: is no output (default)
            - 1: print current args and negative log-likelihood value
        """
        super().__init__(data, scaled_pdf, verbose)

    def _call(self, args):
        data = self._masked
        ns, s = self._model(data, *args)
        return 2.0 * (ns - _sum_log_x(s))


class BinnedCost(MaskedCost):
    """Base class for binned cost functions."""

    __slots__ = "_n", "_xe", "_model"

    @property
    def n(self):
        """Counts per bin."""
        return self._n

    @n.setter
    def n(self, value):
        self._n[:] = value

    @property
    def xe(self):
        """Bin edges."""
        return self._xe

    @xe.setter
    def xe(self, value):
        self.xe[:] = value

    def __init__(self, n, xe, model, verbose):
        self._n = _norm(n)
        self._xe = _norm(xe)
        self._model = model

        if np.any((np.array(self._n.shape) + 1) != self._xe.shape):
            raise ValueError("n and xe have incompatible shapes")

        super().__init__(describe(model)[1:], verbose)


class BinnedNLL(BinnedCost):
    """Binned negative log-likelihood.

    Use this if only the shape of the fitted PDF is of interest and the data is binned.
    """

    __slots__ = ()

    @property
    def cdf(self):
        """Cumulative density function."""
        return self._model

    def __init__(self, n, xe, cdf, verbose=0):
        """
        **Parameters**

        n: array-like
            Histogram counts.

        xe: array-like
            Bin edge locations, must be len(n) + 1.

        cdf: callable
            Cumulative density function of the form f(xe, par0, par1, ..., parN),
            where `xe` is a bin edge and par0, ... parN are model parameters. Must be
            normalized to unity over the range (xe[0], xe[-1]).

        verbose: int, optional
            Verbosity level

            - 0: is no output (default)
            - 1: print current args and negative log-likelihood value
        """
        super().__init__(n, xe, cdf, verbose)

    def _call(self, args):
        prob = np.diff(self._model(self._xe, *args))
        n = self._masked
        ma = self._mask
        if ma is not None:
            prob = prob[ma]
        mu = np.sum(n) * prob
        # + np.sum(mu) can be skipped, it is effectively constant
        return 2.0 * _neg_sum_n_log_mu(n, mu)

    def _make_masked(self):
        return self._n if self._mask is None else self._n[self._mask]


class ExtendedBinnedNLL(BinnedCost):
    """Binned extended negative log-likelihood.

    Use this if shape and normalization of the fitted PDF are of interest and the data
    is binned.
    """

    __slots__ = ()

    @property
    def scaled_cdf(self):
        return self._model

    def __init__(self, n, xe, scaled_cdf, verbose=0):
        """
        **Parameters**

        n: array-like
            Histogram counts.

        xe: array-like
            Bin edge locations, must be len(n) + 1.

        scaled_cdf: callable
            Scaled Cumulative density function of the form f(xe, par0, par1, ..., parN),
            where `xe` is a bin edge and par0, ... parN are model parameters.

        verbose: int, optional
            Verbosity level

            - 0: is no output (default)
            - 1: print current args and negative log-likelihood value
        """
        super().__init__(n, xe, scaled_cdf, verbose)

    def _call(self, args):
        mu = np.diff(self._model(self._xe, *args))
        ma = self._mask
        n = self._masked
        if ma is not None:
            mu = mu[ma]
        return 2.0 * _sum_log_poisson(n, mu)

    def _make_masked(self):
        return self._n if self._mask is None else self._n[self._mask]


class LeastSquares(MaskedCost):
    """Least-squares cost function (aka chisquare function).

    Use this if you have data of the form (x, y +/- yerror).
    """

    __slots__ = "_loss", "_cost", "_x", "_y", "_yerror", "_model"

    @property
    def x(self):
        """Explanatory variable."""
        return self._x

    @x.setter
    def x(self, value):
        self._x[:] = value

    @property
    def y(self):
        """Sample."""
        return self._y

    @y.setter
    def y(self, value):
        self._y[:] = value

    @property
    def yerror(self):
        """Expected uncertainty of sample."""
        return self._yerror

    @yerror.setter
    def yerror(self, value):
        self._yerror[:] = value

    @property
    def model(self):
        """Model of the form y = f(x, par0, [par1, ...])."""
        return self._model

    @property
    def loss(self):
        """Loss function. See LeastSquares.__init__ for details."""
        return self._loss

    @loss.setter
    def loss(self, loss):
        self._loss = loss
        if hasattr(loss, "__call__"):
            self._cost = lambda y, ye, ym: np.sum(loss(_z_squared(y, ye, ym)))
        elif loss == "linear":
            self._cost = _sum_z_squared
        elif loss == "soft_l1":
            self._cost = _sum_z_squared_soft_l1
        else:
            raise ValueError("unknown loss type: " + loss)

    def __init__(self, x, y, yerror, model, loss="linear", verbose=0):
        """
        **Parameters**

        x: array-like
            Locations where the model is evaluated.

        y: array-like
            Observed values. Must have the same length as `x`.

        yerror: array-like or float
            Estimated uncertainty of observed values. Must have same shape as `y` or
            be a scalar, which is then broadcasted to same shape as `y`.

        model: callable
            Function of the form f(x, par0, par1, ..., parN) whose output is compared
            to observed values, where `x` is the location and par0, ... parN are model
            parameters.

        loss: str or callable, optional
            The loss function can be modified to make the fit robust against outliers,
            see scipy.optimize.least_squares for details. Only "linear" (default) and
            "soft_l1" are currently implemented, but users can pass any loss function
            as this argument. It should be a monotonic, twice differentiable function,
            which accepts the squared residual and returns a modified squared residual.

            .. plot:: plots/loss.py

        verbose: int, optional
            Verbosity level

            - 0: is no output (default)
            - 1: print current args and negative log-likelihood value
        """
        x = _norm(x)
        y = _norm(y)
        yerror = np.asarray(yerror, dtype=float)

        if len(x) != len(y):
            raise ValueError("x and y must have same length")

        if yerror.ndim == 0:
            yerror = yerror * np.ones_like(y)
        elif yerror.shape != y.shape:
            raise ValueError("y and yerror must have same shape")

        self._x = x
        self._y = y
        self._yerror = yerror
        self._model = model
        self.loss = loss
        super().__init__(describe(self._model)[1:], verbose)

    def _call(self, args):
        x, y, yerror = self._masked
        ym = self._model(x, *args)
        return self._cost(y, yerror, ym)

    def _make_masked(self):
        ma = self._mask
        if ma is None:
            return self._x, self._y, self._yerror
        else:
            return self._x[ma], self._y[ma], self._yerror[ma]


class NormalConstraint(Cost):

    __slots__ = "_value", "_cov", "_covinv"

    def __init__(self, args, value, error):
        if isinstance(args, str):
            args = [args]
        self._value = _norm(value)
        self._cov = _norm(error)
        if self._cov.ndim < 2:
            self._cov **= 2
        self._covinv = _covinv(self._cov)
        super().__init__(args, False)

    @property
    def covariance(self):
        return self._cov

    @covariance.setter
    def covariance(self, value):
        self._cov[:] = value
        self._covinv = _covinv(self._cov)

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        self._value[:] = value

    def _call(self, args):
        delta = self._value - args
        if self._covinv.ndim < 2:
            return np.sum(delta ** 2 * self._covinv)
        return np.einsum("i,ij,j", delta, self._covinv, delta)


def _norm(value):
    return np.atleast_1d(np.asarray(value, dtype=float))


def _covinv(array):
    return np.linalg.inv(array) if array.ndim == 2 else 1.0 / array
