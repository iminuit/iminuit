from warnings import warn
from . import util as mutil
from ._core import (
    FCN,
    MnContours,
    MnHesse,
    MnMigrad,
    MnMinos,
    MnPrint,
    MnStrategy,
    MnUserParameterState,
)
import numpy as np

__all__ = ["Minuit"]


class Minuit:
    LEAST_SQUARES = 1.0
    """Set `:attr:errordef` to this constant for a least-squares cost function."""

    LIKELIHOOD = 0.5
    """Set `:attr:errordef` to this constant for a negative log-likelihood function."""

    @property
    def fcn(self):
        """Cost function (usually a chi^2 or likelihood function)."""
        return self._fcn

    @property
    def grad(self):
        """Gradient function of the cost function."""
        return self._fcn.grad

    @property
    def pos2var(self):
        """Map variable position to name"""
        return self._pos2var

    @property
    def var2pos(self):
        """Map variable name to position"""
        return self._var2pos

    @property
    def parameters(self):
        """Tuple of parameter names, an alias for :attr:`pos2var`."""
        return self._pos2var

    @property
    def errordef(self):
        """FCN increment above the minimum that corresponds to one standard deviation.

        Default value is 1.0. `errordef` should be 1.0 for a least-squares cost
        function and 0.5 for negative log-likelihood function. See page 37 of
        http://hep.fi.infn.it/minuit.pdf. This parameter is sometimes called
        ``UP`` in the MINUIT docs.

        To make user code more readable, we provided two named constants::

            from iminuit import Minuit
            assert Minuit.LEAST_SQUARES == 1
            assert Minuit.LIKELIHOOD == 0.5

            Minuit(a_least_squares_function, errordef=Minuit.LEAST_SQUARES)
            Minuit(a_likelihood_function, errordef=Minuit.LIKELIHOOD)
        """
        return self._fcn.up

    @errordef.setter
    def errordef(self, value):
        if value <= 0:
            raise ValueError(f"errordef={value} must be a positive number")
        self._fcn.up = value
        if self._fmin:
            self._fmin._src.up = value

    tol = 0.1
    """Tolerance for convergence.

    The main convergence criteria of MINUIT is ``edm < edm_max``, where ``edm_max`` is
    calculated as ``edm_max = 0.002 * tol * errordef`` and EDM is the *estimated distance
    to minimum*, as described in the `MINUIT paper`_.
    """

    @property
    def strategy(self):
        """Current minimization strategy.

        **0**: Fast. Does not check a user-provided gradient. Does not improve Hesse matrix
        at minimum. Extra call to :meth:`hesse` after :meth:`migrad` is always needed for
        good error estimates. If you pass a user-provided gradient to MINUIT,
        convergence is **faster**.

        **1**: Default. Checks user-provided gradient against numerical gradient. Checks and
        usually improves Hesse matrix at minimum. Extra call to :meth:`hesse` after
        :meth:`migrad` is usually superfluous. If you pass a user-provided gradient to
        MINUIT, convergence is **slower**.

        **2**: Careful. Like 1, but does extra checks of intermediate Hessian matrix during
        minimization. The effect in benchmarks is a somewhat improved accuracy at the cost
        of more function evaluations. A similar effect can be achieved by reducing the
        tolerance attr:`tol` for convergence at any strategy level.
        """
        return self._strategy

    @strategy.setter
    def strategy(self, value):
        self._strategy.strategy = value

    @property
    def print_level(self):
        """Current print level.

        - 0: quiet
        - 1: print minimal debug messages to terminal
        - 2: print more debug messages to terminal
        - 3: print even more debug messages to terminal
        """
        return self._print_level

    @print_level.setter
    def print_level(self, level):
        self._print_level = level
        if level >= 3 or level < MnPrint.global_level:
            warn(
                "Setting print_level >=3 has the side-effect of setting the level "
                "globally for all Minuit instances",
                mutil.IMinuitWarning,
                stacklevel=2,
            )
            MnPrint.global_level = level

    @property
    def throw_nan(self):
        """Boolean. Whether to raise runtime error if function evaluate to nan."""
        return self._fcn.throw_nan

    @throw_nan.setter
    def throw_nan(self, value):
        self._fcn.throw_nan = value

    @property
    def values(self):
        """Parameter values in a array-like object.

        Use to read or write current parameter values based on the parameter index or the
        parameter name as a string. If you change a parameter value and run :meth:`migrad`,
        the minimization will start from that value, similar for :meth:`hesse` and
        :meth:`minos`.

        .. seealso:: :attr:`errors`, :attr:`fixed`, :attr:`limits`
        """
        return self._values

    @values.setter
    def values(self, args):
        self._values[:] = args

    @property
    def errors(self):
        """Parameter parabolic errors in a array-like object.

        Like :attr:`values`, but instead of reading or writing the values, you read or write
        the errors (which double as step sizes for MINUITs numerical gradient estimation).

        .. seealso:: :attr:`values`, :attr:`fixed`, :attr:`limits`
        """
        return self._errors

    @errors.setter
    def errors(self, args):
        self._errors[:] = args

    @property
    def fixed(self):
        """Access fixation state of a parameter in a array-like object.

        Use to read or write the fixation state of a parameter based on the parameter index
        or the parameter name as a string. If you change the state and run :meth:`migrad`,
        :meth:`hesse`, or :meth:`minos`, the new state is used.

        In case of complex fits, it can help to fix some parameters first and only minimize
        the function with respect to the other parameters, then release the fixed parameters
        and minimize again starting from that state.

        .. seealso:: :attr:`values`, :attr:`errors`, :attr:`limits`
        """
        return self._fixed

    @fixed.setter
    def fixed(self, args):
        self._fixed[:] = args

    @property
    def limits(self):
        """Access parameter limits in a array-like object.

        Use to read or write the limits of a parameter based on the parameter index
        or the parameter name as a string. If you change the limits and run :meth:`migrad`,
        :meth:`hesse`, or :meth:`minos`, the new state is used.

        In case of complex fits, it can help to limit some parameters first and then
        remove the limits. Limits will bias the result only if the best fit value is
        outside the limits, not if it is inside. Limits will affect the estimated
        HESSE uncertainties if the parameter is close to a limit.

        .. seealso:: :attr:`values`, :attr:`errors`, :attr:`fixed`
        """
        return self._limits

    @limits.setter
    def limits(self, args):
        self._limits[:] = args

    @property
    def merrors(self):
        """Minos error objects with full status information."""
        return self._merrors

    @property
    def fitarg(self):
        """Current Minuit state in form of a dict.

        * name -> value
        * error_name -> error
        * fix_name -> fix
        * limit_name -> (lower_limit, upper_limit)

        This is very useful when you want to save the fit parameters and
        re-use them later. For example::

            m = Minuit(f, x=1)
            m.migrad()
            fitarg = m.fitarg

            m2 = Minuit(f, **fitarg)
        """

        kwargs = {}
        for mp in self._last_state:
            kwargs[mp.name] = mp.value
            kwargs[f"error_{mp.name}"] = mp.error
            if mp.is_fixed:
                kwargs[f"fix_{mp.name}"] = mp.is_fixed
            has_lower = mp.has_lower_limit
            has_upper = mp.has_upper_limit
            if has_lower or has_upper:
                kwargs[f"limit_{mp.name}"] = (
                    mp.lower_limit if has_lower else -np.inf,
                    mp.upper_limit if has_upper else np.inf,
                )
        return kwargs

    @property
    def narg(self):
        """Number of parameters."""
        return len(self._pos2var)

    @property
    def nfit(self):
        """Number of fitted parameters (fixed parameters not counted)."""
        return self.narg - sum(self.fixed)

    @property
    def covariance(self):
        """Covariance matrix (dict (name1, name2) -> covariance).

        .. seealso:: :meth:`matrix`
        """
        free = tuple(self._free_parameters())
        cov = self._last_state.covariance
        if self._last_state.has_covariance:
            return {
                (v1, v2): cov[i, j]
                for i, v1 in enumerate(free)
                for j, v2 in enumerate(free)
            }

    @property
    def gcc(self):
        """Global correlation coefficients (dict : name -> gcc)."""
        free = self._free_parameters()
        if self._last_state.has_globalcc:
            gcc = self._last_state.globalcc
            if gcc:
                return {v: gcc[i] for i, v in enumerate(free)}

    @property
    def fmin(self):
        """Current function minimum data object"""
        return self._fmin

    @property
    def fval(self):
        """Function minimum value.

        .. seealso:: :attr:`fmin`
        """
        fm = self._fmin
        return fm.fval if fm else None

    @property
    def params(self):
        """List of current parameter data objects."""
        return mutil._get_params(self._last_state, self.merrors)

    @property
    def init_params(self):
        """List of current parameter data objects set to the initial fit state."""
        return mutil._get_params(self._init_state, None)

    @property
    def valid(self):
        """Check if function minimum is valid."""
        return self._fmin and self._fmin.is_valid

    @property
    def accurate(self):
        """Check if covariance (of the last MIGRAD run) is accurate."""
        return self._fmin and self._fmin.has_accurate_covar

    @property
    def nfcn(self):
        """Total number of function calls."""
        return self._fcn.nfcn

    @property
    def ngrad(self):
        """Total number of gradient calls."""
        return self._fcn.ngrad

    def __init__(
        self,
        fcn,
        *args,
        grad=None,
        name=None,
        **kwds,
    ):
        """
        Construct minuit object from given *fcn*

        **Arguments:**

            **fcn**, the function to be optimized, is the only required argument.

            Two kinds of function signatures are understood.

            a) Parameters passed as positional arguments

            The function has several positional arguments, one for each fit
            parameter. Example::

                def func(a, b, c): ...

            The parameters a, b, c must accept a real number.

            iminuit automagically detects parameters names in this case.
            More information about how the function signature is detected can
            be found in :ref:`function-sig-label`

            b) Parameters passed as Numpy array

            The function has a single argument which is a Numpy array.
            Example::

                def func(x): ...

            Pass a sequence as starting values to use this signature. For
            more information, see "Parameter Keyword Arguments" further down.

        **Keyword Arguments:**
            - **grad**: Optional. Provide a function that calculates the
              gradient analytically and returns an iterable object with one
              element for each dimension. If None is given MINUIT will
              calculate the gradient numerically. (Default None)

            - **name**: sequence of strings. If set, this is used to detect
              parameter names instead of iminuit's function signature detection.

        **Parameter Keyword Arguments:**

            iminuit allows user to set initial values via keywords. This is best
            explained through examples::

                def f(x, y):
                    return (x-2)**2 + (y-3)**2

            * Initial value (varname)::

                #initial value for x and y
                m = Minuit(f, x=1, y=2)
        """
        array_call = False
        if len(args) == 1 and hasattr(args[0], "__getitem__"):
            array_call = True
            args = args[0]

        if name is None:
            if len(args) == 0:
                name = mutil.describe(fcn)
            else:
                try:
                    name = mutil.describe(fcn)
                except TypeError:
                    pass

                if name is None or len(name) != len(args):
                    name = tuple(f"x[{i}]" for i in range(len(args)))

        # Maintain two dictionaries to easily convert between
        # parameter names and position
        self._pos2var = tuple(name)
        self._var2pos = {k: i for i, k in enumerate(name)}

        if hasattr(fcn, "errordef"):
            errordef = fcn.errordef
        else:
            errordef = 0

        self._strategy = MnStrategy(1)
        self._print_level = 0

        self._fcn = FCN(fcn, grad, array_call, errordef)
        self._fmin = None
        self._init_state = self._make_init_state(args, kwds)
        self._last_state = self._init_state

        self._values = ValueView(self)
        self._errors = ErrorView(self)
        self._fixed = FixedView(self)
        self._limits = LimitView(self, 1)
        self._merrors = mutil.MErrors()

    def _make_init_state(self, args, kwds):
        nargs = len(args)
        # check kwds
        if nargs:
            if kwds:
                raise RuntimeError(
                    f"positional arguments cannot be mixed with parameter keyword arguments {kwds}"
                )
            if nargs != self.narg:
                raise RuntimeError(f"{nargs} values given for {self.narg} parameters")
        else:
            for kw in kwds:
                if kw not in self.parameters:
                    raise RuntimeError(
                        f"{kw} is not one of the parameters {' '.join(self._pos2var)}"
                    )

        state = MnUserParameterState()
        for i, x in enumerate(self._pos2var):
            if nargs:
                val = args[i]
            else:
                if x not in kwds:
                    warn(
                        f"Parameter {x} has no initial value, using 0",
                        mutil.InitialParamWarning,
                        stacklevel=3,
                    )

                val = kwds.get(x, 0.0)
            err = mutil._guess_initial_step(val)
            state.add(x, val, err)
        return state

    def reset(self):
        """Reset minimization state to initial state."""
        self._last_state = self._init_state
        self._fmin = None
        self._fcn.nfcn = 0
        self._fcn.ngrad = 0
        self._merrors = mutil.MErrors()

    def migrad(self, ncall=None, precision=None, iterate=5):
        """Run MIGRAD.

        MIGRAD is a robust minimisation algorithm which earned its reputation
        in 40+ years of almost exclusive usage in high-energy physics. How
        MIGRAD works is described in the `MINUIT paper`_.

        **Arguments:**

            * **ncall**: integer or None, optional; (approximate)
              maximum number of call before MIGRAD will stop trying. Default: None
              (indicates to use MIGRAD's internal heuristic). Note: MIGRAD may slightly
              violate this limit, because it checks the condition only after a full
              iteration of the algorithm, which usually performs several function calls.

            * **precision**: override Minuit precision estimate for the cost function.
              Default: None (= use epsilon of a C++ double). If the cost function has a
              lower precision (e.g. of a C++ float), setting this to a lower value will
              accelerate convergence and reduce the rate of unsuccessful convergence.

            * **iterate**: automatically call Migrad up to N times if convergence
              was not reached. Default: 5. This simple heuristic makes Migrad converge
              more often even if the numerical precision of the cost function is low.
              Setting this to 1 disables the feature.

        **Return:**

            :ref:`function-minimum-sruct`, list of :ref:`minuit-param-struct`
        """
        if ncall is None:
            ncall = 0  # tells C++ Minuit to use its internal heuristic

        if iterate < 1:
            raise ValueError("iterate must be at least 1")

        _check_errordef(self._fcn)
        migrad = MnMigrad(self._fcn, self._last_state, self.strategy)
        migrad.set_print_level(self.print_level)
        if precision is not None:
            migrad.precision = precision

        # Automatically call Migrad up to `iterate` times if minimum is not valid.
        # This simple heuristic makes Migrad converge more often.
        for _ in range(iterate):
            fm = migrad(ncall, self.tol)
            if fm.is_valid or fm.has_reached_call_limit:
                break

        self._last_state = fm.state

        self._fmin = mutil.FMin(fm, self._fcn.nfcn, self._fcn.ngrad, self.tol)

        mr = mutil.MigradResult(self._fmin, self.params)
        if self.print_level >= 2:
            print(mr)

        return mr

    def hesse(self, ncall=None):
        """Run HESSE to compute parabolic errors.

        HESSE estimates the covariance matrix by inverting the matrix of
        `second derivatives (Hesse matrix) at the minimum
        <http://en.wikipedia.org/wiki/Hessian_matrix>`_. This covariance
        matrix is valid if your :math:`\\chi^2` or likelihood profile looks
        like a hyperparabola around the the minimum. This is usually the case,
        especially when you fit many observations (in the limit of infinite
        samples this is always the case). If you want to know how your
        parameters are correlated, you also need to use HESSE.

        Also see :meth:`minos`, which computes the uncertainties in a
        different way.

        **Arguments:**
            - **ncall**: integer or None, limit the number of calls made by MINOS.
              Default: None (uses an internal heuristic by C++ MINUIT).

        **Returns:**

            list of :ref:`minuit-param-struct`
        """

        ncall = 0 if ncall is None else int(ncall)

        hesse = MnHesse(self.strategy)

        _check_errordef(self._fcn)
        fm = self._fmin._src if self._fmin else None
        if fm and fm.state == self._last_state:
            # _last_state not modified, can update _fmin which is more efficient
            hesse(self._fcn, fm, ncall)
            self._last_state = fm.state
            self._fmin = mutil.FMin(fm, self._fcn.nfcn, self._fcn.ngrad, self.tol)
        else:
            # _fmin does not exist or _last_state was modified,
            # so we cannot just update last _fmin
            self._last_state = hesse(self._fcn, self._last_state, ncall)

        if self._last_state.has_covariance is False:
            if not self._fmin:
                raise RuntimeError("HESSE Failed")

        return self.params

    def minos(self, var=None, sigma=1.0, ncall=None):
        """Run MINOS to compute asymmetric confidence intervals.

        MINOS uses the profile likelihood method to compute (asymmetric)
        confidence intervals. It scans the negative log-likelihood or
        (equivalently) the least-squares cost function around the minimum
        to construct an asymmetric confidence interval. This interval may
        be more reasonable when a parameter is close to one of its
        parameter limits. As a rule-of-thumb: when the confidence intervals
        computed with HESSE and MINOS differ strongly, the MINOS intervals
        are to be preferred. Otherwise, HESSE intervals are preferred.

        Running MINOS is computationally expensive when there are many
        fit parameters. Effectively, it scans over *var* in small steps
        and runs MIGRAD to minimise the FCN with respect to all other free
        parameters at each point. This is requires many more FCN evaluations
        than running HESSE.

        **Arguments:**

            - **var**: optional variable name to compute the error for.
              If var is not given, MINOS is run for every variable.
            - **sigma**: number of :math:`\\sigma` error. Default 1.0.
            - **ncall**: integer or None, limit the number of calls made by MINOS.
              Default: None (uses an internal heuristic by C++ MINUIT).

        **Returns:**

            Dictionary of varname to :ref:`minos-error-struct`, containing
            all up to now computed errors, including the current request.

        """
        if not self._fmin:
            raise RuntimeError(
                "MINOS require function to be at the minimum." " Run MIGRAD first."
            )

        ncall = 0 if ncall is None else int(ncall)

        if not self._fmin.is_valid:
            raise RuntimeError(
                "Function minimum is not valid. Make sure " "MIGRAD converged first"
            )
        if var is not None and var not in self._pos2var:
            raise RuntimeError(f"Unknown parameter {var}")

        _check_errordef(self._fcn)
        with mutil.TemporaryUp(self._fcn, sigma):
            minos = MnMinos(self._fcn, self._fmin._src, self.strategy)

            vnames = self._pos2var if var is None else [var]
            for vname in vnames:
                if self.fixed[vname]:
                    if var is not None and var == vname:
                        warn(
                            f"Cannot scan parameter {var}, it is fixed",
                            mutil.IMinuitWarning,
                        )
                        return None
                    continue
                me = minos(self._var2pos[vname], ncall, self.tol)
                self._merrors[vname] = mutil.MError(vname, me)

        self._fmin.nfcn = self._fcn.nfcn
        self._fmin.ngrad = self._fcn.ngrad

        return self.merrors

    def matrix(self, correlation=False, skip_fixed=True):
        """Error or correlation matrix in tuple or tuples format."""
        if not self._last_state.has_covariance:
            raise RuntimeError(
                "Covariance is not valid. Maybe the last Hesse call failed?"
            )

        mncov = self._last_state.covariance

        # When some parameters are fixed, mncov is a sub-matrix. If skip-fixed
        # is false, we need to expand the sub-matrix back into the full form.
        # This requires a translation between sub-index und full-index.
        if skip_fixed:
            npar = sum(not mp.is_fixed for mp in self._last_state)
            ind = range(npar)

            def cov(i, j):
                return mncov[i, j]

        else:
            ext2int = {}
            iint = 0
            for mp in self._last_state:
                if not mp.is_fixed:
                    ext2int[mp.number] = iint
                    iint += 1
            ind = range(self.narg)

            def cov(i, j):
                if i not in ext2int or j not in ext2int:
                    return 0.0
                return mncov[ext2int[i], ext2int[j]]

        names = [x for x in self.parameters if not (skip_fixed and self.fixed[x])]
        if correlation:

            def cor(i, j):
                return cov(i, j) / ((cov(i, i) * cov(j, j)) ** 0.5 + 1e-100)

            ret = mutil.Matrix(names, ((cor(i, j) for i in ind) for j in ind))
        else:
            ret = mutil.Matrix(names, ((cov(i, j) for i in ind) for j in ind))
        return ret

    def np_matrix(self, **kwds):
        """Covariance or correlation matrix in numpy array format.

        Keyword arguments are forwarded to :meth:`matrix`.

        The name of this function was chosen to be analogous to :meth:`matrix`,
        it returns the same information in a different format. For
        documentation on the arguments, please see :meth:`matrix`.

        **Returns:**

            2D ``numpy.ndarray`` of shape (N,N) (not a ``numpy.matrix``).
        """
        matrix = self.matrix(**kwds)
        return np.array(matrix, dtype=np.double)

    def np_values(self):
        """Parameter values in numpy array format.

        Fixed parameters are included, the order follows :attr:`parameters`.

        **Returns:**

            ``numpy.ndarray`` of shape (N,).
        """
        return np.array(self.values, dtype=np.double)

    def np_errors(self):
        """Hesse parameter errors in numpy array format.

        Fixed parameters are included, the order follows :attr:`parameters`.

        **Returns:**

            ``numpy.ndarray`` of shape (N,).
        """
        a = np.empty(self.narg, dtype=np.double)
        for i in range(self.narg):
            a[i] = self.errors[i]
        return a

    def np_merrors(self):
        """MINOS parameter errors in numpy array format.

        Fixed parameters are included (zeros are returned), the order follows
        :attr:`parameters`.

        The format of the produced array follows matplotlib conventions, as
        in ``matplotlib.pyplot.errorbar``. The shape is (2, N) for N
        parameters. The first row represents the downward error as a positive
        offset from the center. Likewise, the second row represents the
        upward error as a positive offset from the center.

        **Returns:**

            ``numpy.ndarray`` of shape (2, N).
        """
        # array format follows matplotlib conventions, see pyplot.errorbar
        a = np.zeros((2, self.narg))
        for me in self.merrors.values():
            i = self._var2pos[me.name]
            a[0, i] = -me.lower
            a[1, i] = me.upper
        return a

    def np_covariance(self):
        """Covariance matrix in numpy array format.

        Fixed parameters are included, the order follows :attr:`parameters`.

        **Returns:**

            ``numpy.ndarray`` of shape (N,N) (not a ``numpy.matrix``).
        """
        return self.np_matrix(correlation=False, skip_fixed=False)

    def mnprofile(self, vname, bins=30, bound=2, subtract_min=False):
        """Calculate MINOS profile around the specified range.

        Scans over **vname** and minimises FCN over the other parameters in each point.

        **Arguments:**

            * **vname** name of variable to scan

            * **bins** number of scanning bins. Default 30.

            * **bound**
              If bound is tuple, (left, right) scanning bound.
              If bound is a number, it specifies how many :math:`\\sigma`
              symmetrically from minimum (minimum+- bound* :math:`\\sigma`).
              Default 2

            * **subtract_min** subtract_minimum off from return value. This
              makes it easy to label confidence interval. Default False.

        **Returns:**

            bins(center point), value, MIGRAD results
        """
        if vname not in self._pos2var:
            raise ValueError("Unknown parameter %s" % vname)

        bound = self._normalize_bound(vname, bound)

        values = np.linspace(bound[0], bound[1], bins, dtype=np.double)
        results = np.empty(bins, dtype=np.double)
        status = np.empty(bins, dtype=np.bool)

        state = MnUserParameterState(self._last_state)  # copy
        ipar = self._var2pos[vname]
        state.fix(ipar)
        pr = MnPrint("Minuit.mnprofile", self.print_level)
        _check_errordef(self._fcn)
        for i, v in enumerate(values):
            state.set_value(ipar, v)
            migrad = MnMigrad(self._fcn, state, self.strategy)
            fm = migrad(0, self.tol)
            if not fm.is_valid:
                pr.warn(f"MIGRAD fails to converge for {vname}={v}")
            status[i] = fm.is_valid
            results[i] = fm.fval
        vmin = np.min(results)

        if subtract_min:
            results -= vmin

        return values, results, status

    def draw_mnprofile(
        self, vname, bins=30, bound=2, subtract_min=False, band=True, text=True
    ):
        """Draw MINOS profile in the specified range.

        It is obtained by finding MIGRAD results with **vname** fixed
        at various places within **bound**.

        **Arguments:**

            * **vname** variable name to scan

            * **bins** number of scanning bin. Default 30.

            * **bound**
              If bound is tuple, (left, right) scanning bound.
              If bound is a number, it specifies how many :math:`\\sigma`
              symmetrically from minimum (minimum+- bound* :math:`\\sigma`).
              Default 2.

            * **subtract_min** subtract_minimum off from return value. This
              makes it easy to label confidence interval. Default False.

            * **band** show green band to indicate the increase of fcn by
              *errordef*. Default True.

            * **text** show text for the location where the fcn is increased
              by *errordef*. This is less accurate than :meth:`minos`.
              Default True.

        **Returns:**

            bins(center point), value, migrad results

        .. plot:: plots/mnprofile.py
            :include-source:
        """
        x, y, s = self.mnprofile(vname, bins, bound, subtract_min)
        return self._draw_profile(vname, x, y, band, text)

    def profile(self, vname, bins=100, bound=2, subtract_min=False):
        """Calculate cost function profile around specify range.

        **Arguments:**

            * **vname** variable name to scan

            * **bins** number of scanning bin. Default 100.

            * **bound**
              If bound is tuple, (left, right) scanning bound.
              If bound is a number, it specifies how many :math:`\\sigma`
              symmetrically from minimum (minimum+- bound* :math:`\\sigma`).
              Default: 2.

            * **subtract_min** subtract_minimum off from return value. This
              makes it easy to label confidence interval. Default False.

        **Returns:**

            bins(center point), value

        .. seealso::

            :meth:`mnprofile`
        """
        if subtract_min and not self._fmin:
            raise RuntimeError(
                "Request for minimization "
                "subtraction but no minimization has been done. "
                "Run MIGRAD first."
            )

        bound = self._normalize_bound(vname, bound)

        ipar = self._var2pos[vname]
        scan = np.linspace(bound[0], bound[1], bins, dtype=np.double)
        result = np.empty(bins, dtype=np.double)
        values = self.np_values()
        for i, vi in enumerate(scan):
            values[ipar] = vi
            result[i] = self.fcn(values)
        if subtract_min:
            result -= self.fval
        return scan, result

    def draw_profile(
        self, vname, bins=100, bound=2, subtract_min=False, band=True, text=True
    ):
        """A convenient wrapper for drawing profile using matplotlib.

        A 1D scan of the cost function around the minimum, useful to inspect the
        minimum and the FCN around the minimum for defects.

        For a fit with several free parameters this is not the same as the MINOS
        profile computed by :meth:`draw_mncontour`. Use :meth:`mnprofile` or
        :meth:`draw_mnprofile` to compute confidence intervals.

        If a function minimum was found in a previous MIGRAD call, a vertical line
        indicates the parameter value. An optional band indicates the uncertainty
        interval of the parameter computed by HESSE or MINOS.

        **Arguments:**

            In addition to argument listed on :meth:`profile`. draw_profile
            take these addition argument:

            * **band** show green band to indicate the increase of fcn by
              *errordef*. Note again that this is NOT minos error in general.
              Default True.

            * **text** show text for the location where the fcn is increased
              by *errordef*. This is less accurate than :meth:`minos`
              Note again that this is NOT minos error in general. Default True.

        .. seealso::
            :meth:`mnprofile`
            :meth:`draw_mnprofile`
            :meth:`profile`
        """
        x, y = self.profile(vname, bins, bound, subtract_min)
        return self._draw_profile(vname, x, y, band, text)

    def _draw_profile(self, vname, x, y, band, text):

        from matplotlib import pyplot as plt

        plt.plot(x, y)
        plt.xlabel(vname)
        plt.ylabel("FCN")

        v = self.values[vname]
        plt.axvline(v, color="k", linestyle="--")

        vmin = None
        vmax = None
        if (vname, 1) in self.merrors:
            vmin = v + self.merrors[(vname, -1)]
            vmax = v + self.merrors[(vname, 1)]
        if vname in self.errors:
            vmin = v - self.errors[vname]
            vmax = v + self.errors[vname]

        if vmin is not None and band:
            plt.axvspan(vmin, vmax, facecolor="0.8")

        if text:
            plt.title(
                (f"{vname} = {v:.3g}")
                if vmin is None
                else (
                    "{} = {:.3g} - {:.3g} + {:.3g}".format(vname, v, v - vmin, vmax - v)
                ),
                fontsize="large",
            )

        return x, y

    def contour(self, x, y, bins=50, bound=2, subtract_min=False):
        """2D contour scan.

        Return the contour of a function scan over **x** and **y**, while keeping
        all other parameters fixed.

        The related :meth:`mncontour` works differently: for new pair of **x** and **y**
        in the scan, it minimises the function with the respect to the other parameters.

        This method is useful to inspect the function near the minimum to detect issues
        (the contours should look smooth). Use :meth:`mncontour` to create confidence
        regions for the parameters. If the fit has only two free parameters, you can
        use this instead of :meth:`mncontour`.

        **Arguments:**

            - **x** variable name for X axis of scan

            - **y** variable name for Y axis of scan

            - **bound**
              If bound is 2x2 array, [[v1min,v1max],[v2min,v2max]].
              If bound is a number, it specifies how many :math:`\\sigma`
              symmetrically from minimum (minimum+- bound*:math:`\\sigma`).
              Default: 2.

            - **subtract_min** Subtract minimum off from return values. Default False.

        **Returns:**

            x_bins, y_bins, values

            values[y, x] <-- this choice is so that you can pass it
            to through matplotlib contour()

        .. seealso::

            :meth:`mncontour`
            :meth:`mnprofile`

        """
        if subtract_min and not self._fmin:
            raise RuntimeError(
                "Request for minimization "
                "subtraction but no minimization has been done. "
                "Run MIGRAD first."
            )

        try:
            n = float(bound)
            in_sigma = True
        except TypeError:
            in_sigma = False

        if in_sigma:
            x_bound = self._normalize_bound(x, n)
            y_bound = self._normalize_bound(y, n)
        else:
            x_bound = self._normalize_bound(x, bound[0])
            y_bound = self._normalize_bound(y, bound[1])

        x_val = np.linspace(x_bound[0], x_bound[1], bins)
        y_val = np.linspace(y_bound[0], y_bound[1], bins)

        x_pos = self._var2pos[x]
        y_pos = self._var2pos[y]

        result = np.empty((bins, bins), dtype=np.double)
        varg = self.np_values()
        for i, x in enumerate(x_val):
            varg[x_pos] = x
            for j, y in enumerate(y_val):
                varg[y_pos] = y
                result[i, j] = self._fcn(varg)

        if subtract_min:
            result -= self._fmin.fval

        return x_val, y_val, result

    def mncontour(self, x, y, numpoints=100, sigma=1.0):
        """Two-dimensional MINOS contour scan.

        This scans over **x** and **y** and minimises all other free
        parameters in each scan point. This works as if **x** and **y** are
        fixed, while the other parameters are minimised by MIGRAD.

        This scan produces a statistical confidence region with the `profile
        likelihood method <https://en.wikipedia.org/wiki/Likelihood_function>`_.
        The contour line represents the values of **x** and **y** where the
        function passes the threshold that corresponds to `sigma` standard
        deviations (note that 1 standard deviations in two dimensions has a
        smaller coverage probability than 68 %).

        The calculation is expensive since it has to run MIGRAD at various
        points.

        **Arguments:**

            - **x** string variable name of the first parameter

            - **y** string variable name of the second parameter

            - **numpoints** number of points on the line to find. Default 20.

            - **sigma** number of sigma for the contour line. Default 1.0.

        **Returns:**

            x MINOS error struct, y MINOS error struct, contour line

            contour line is a list of the form
            [[x1,y1]...[xn,yn]]

        .. seealso::

            :meth:`contour`
            :meth:`mnprofile`

        """
        if not self._fmin:
            raise ValueError("Run MIGRAD first")

        ix = self._var2pos[x]
        iy = self._var2pos[y]

        vary = self._free_parameters()
        if x not in vary or y not in vary:
            raise ValueError("mncontour cannot be run on fixed parameters.")

        _check_errordef(self._fcn)
        with mutil.TemporaryUp(self._fcn, sigma):
            mnc = MnContours(self._fcn, self._fmin._src, self.strategy)
            mex, mey, ce = mnc(ix, iy, numpoints)

        return mex, mey, ce

    def draw_mncontour(self, x, y, nsigma=2, numpoints=100):
        """Draw MINOS contour.

        **Arguments:**

            - **x**, **y** parameter name

            - **nsigma** number of sigma contours to draw

            - **numpoints** number of points to calculate for each contour

        **Returns:**

            contour

        .. seealso::

            :meth:`mncontour`

        .. plot:: plots/mncontour.py
            :include-source:
        """
        from matplotlib import pyplot as plt
        from matplotlib.contour import ContourSet

        c_val = []
        c_pts = []
        for sigma in range(1, nsigma + 1):
            pts = self.mncontour(x, y, numpoints, sigma)[2]
            # close curve
            pts.append(pts[0])
            c_val.append(sigma)
            c_pts.append([pts])  # level can have more than one contour in mpl
        cs = ContourSet(plt.gca(), c_val, c_pts)
        plt.clabel(cs)
        plt.xlabel(x)
        plt.ylabel(y)

        return cs

    def draw_contour(self, x, y, bins=50, bound=2):
        """Convenience wrapper for drawing contours.

        The arguments are the same as :meth:`contour`.

        Please read the docs of :meth:`contour` and :meth:`mncontour` to understand the
        difference between the two.

        .. seealso::

            :meth:`contour`
            :meth:`draw_mncontour`

        """
        from matplotlib import pyplot as plt

        vx, vy, vz = self.contour(x, y, bins, bound, subtract_min=True)

        v = [self.errordef * (i + 1) for i in range(4)]

        CS = plt.contour(vx, vy, vz, v)
        plt.clabel(CS, v)
        plt.xlabel(x)
        plt.ylabel(y)
        plt.axhline(self.values[y], color="k", ls="--")
        plt.axvline(self.values[x], color="k", ls="--")
        return vx, vy, vz

    def _free_parameters(self):
        return (mp.name for mp in self._last_state if not mp.is_fixed)

    def _normalize_bound(self, vname, bound):
        try:
            n = float(bound)
            in_sigma = True
        except TypeError:
            in_sigma = False
            pass

        if in_sigma:
            if not self.accurate:
                warn(
                    "Specified nsigma bound, but error matrix is not accurate",
                    mutil.IMinuitWarning,
                )
            start = self.values[vname]
            sigma = self.errors[vname]
            bound = (start - n * sigma, start + n * sigma)

        return bound

    def _copy_state_if_needed(self):
        # If FunctionMinimum exists, _last_state may be a reference to its user state.
        # The state is read-only in C++, but mutable in Python. To not violate
        # invariants, we need to make a copy of the state when the user requests a
        # modification. If a copy was already made (_last_state is already a copy),
        # no further copy has to be made.
        #
        # If FunctionMinimum does not exist, we don't want to copy. We want to
        # implicitly modify _init_state; _last_state is an alias for _init_state, then.
        if self._fmin and self._last_state == self._fmin._src.state:
            self._last_state = MnUserParameterState(self._last_state)


def _check_errordef(fcn):
    if fcn.up == 0:
        warn(
            "errordef not set, defaults to 1",
            mutil.InitialParamWarning,
            stacklevel=3,
        )
        fcn.up = 1


# Helper classes
class BasicView:
    """Array-like view of parameter state.

    Derived classes need to implement methods _set and _get to access
    specific properties of the parameter state."""

    _minuit = None
    _ndim = 0

    def __init__(self, minuit, ndim=0):
        self._minuit = minuit
        self._ndim = ndim

    def __iter__(self):
        for i in range(len(self)):
            yield self._get(i)

    def __len__(self):
        return self._minuit.narg

    def __getitem__(self, key):
        if isinstance(key, slice):
            ind = range(*key.indices(len(self)))
            return [self._get(i) for i in ind]
        i = key if mutil._is_int(key) else self._minuit._var2pos[key]
        if i < 0:
            i += len(self)
        if i < 0 or i >= len(self):
            raise IndexError
        return self._get(i)

    def __setitem__(self, key, value):
        self._minuit._copy_state_if_needed()
        if isinstance(key, slice):
            ind = range(*key.indices(len(self)))
            if np.ndim(value) == self._ndim:  # basic broadcasting
                for i in ind:
                    self._set(i, value)
            else:
                if len(value) != len(ind):
                    raise ValueError("length of argument does not match slice")
                for i, v in zip(ind, value):
                    self._set(i, v)
        else:
            i = key if mutil._is_int(key) else self._minuit._var2pos[key]
            if i < 0:
                i += len(self)
            if i < 0 or i >= len(self):
                raise IndexError
            self._set(i, value)

    def __eq__(self, other):
        return len(self) == len(other) and all(x == y for x, y in zip(self, other))

    def __repr__(self):
        s = "<{} of Minuit at {:x}>".format(self.__class__.__name__, id(self._minuit))
        for (k, v) in zip(self._minuit._pos2var, self):
            s += f"\n  {k}: {v}"
        return s


class ValueView(BasicView):
    """Array-like view of parameter values."""

    def _get(self, i):
        return self._minuit._last_state[i].value

    def _set(self, i, value):
        self._minuit._last_state.set_value(i, value)


class ErrorView(BasicView):
    """Array-like view of parameter errors."""

    def _get(self, i):
        return self._minuit._last_state[i].error

    def _set(self, i, value):
        self._minuit._last_state.set_error(i, value)


class FixedView(BasicView):
    """Array-like view of whether parameters are fixed."""

    def _get(self, i):
        return self._minuit._last_state[i].is_fixed

    def _set(self, i, fix):
        if fix:
            self._minuit._last_state.fix(i)
        else:
            self._minuit._last_state.release(i)


class LimitView(BasicView):
    """Array-like view of parameter limits."""

    def _get(self, i):
        p = self._minuit._last_state[i]
        return (
            p.lower_limit if p.has_lower_limit else -np.inf,
            p.upper_limit if p.has_upper_limit else np.inf,
        )

    def _set(self, i, args):
        state = self._minuit._last_state
        args = mutil._normalize_limit(args)
        val = state[i].value
        err = state[i].error
        # changing limits is a cheap operation, start from clean state
        state.remove_limits(i)
        if args is None or args == (-np.inf, np.inf):
            low, high = (-np.inf, np.inf)
        else:
            low, high = args
            if low != -np.inf and high != np.inf:  # both must be set
                state.set_limits(i, low, high)
                if low == high:
                    state.fix(i)
            elif low != -np.inf:  # lower limit must be set
                state.set_lower_limit(i, low)
            else:  # lower limit must be set
                state.set_upper_limit(i, high)
        # bug in Minuit2: must set parameter value and error again after changing limits
        if val < low:
            val = low
        elif val > high:
            val = high
        state.set_value(i, val)
        state.set_error(i, err)
