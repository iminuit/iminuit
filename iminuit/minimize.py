from iminuit import Minuit
import warnings


class OptimizeResult(dict):
    """Imitation of scipy.optimize.OptimizeResult"""
    def __init__(self, **kwargs):
        dict.__init__(self, **kwargs)
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)


def minimize(fun, x0, args=(), method=None,
             jac=None, hess=None, hessp=None,
             bounds=None, constraints=(),
             tol=None,
             callback=None, options=None):
    """Imitates the interface of the SciPy method of the same name in scipy.optimize.

    For argument description, see scipy.optimize.minimize.

    The only supported method is 'Migrad'.
    """
    from numpy import array as np_array

    if method:
        m = method.lower()
        if m != "migrad":
            raise ValueError("Unknown solver " + m)

    nfev = 0
    njev = 0

    class Wrapped:
        fun = None
        jac = None
        args = ()
        callback = None
        nfev = 0
        njev = 0
        def __init__(self, fun, jac, args, callback):
            self.fun = fun
            self.jac = jac
            self.args = args
            self.callback = callback
        def func(self, *args):
            self.nfev += 1
            x = np_array(args)
            if self.callback:
                self.callback(x)
            return self.fun(x, *self.args)
        def grad(self, *args):
            self.njev += 1
            x = np_array(args)
            return self.jac(x, *self.args)

    wrapped = Wrapped(fun, jac, args, callback)

    if hess or hessp:
        warnings.warn("hess and hessp arguments cannot be handled and are ignored")

    if constraints:
        raise ValueError("Minuit only supports bounds, not constraints")

    if tol:
        warnings.warn("tol argument has no effect on Minuit")

    kwargs = dict(errordef=1, print_level=0)
    if jac:
        kwargs['grad_fcn'] = wrapped.grad

    maxiter = 10000
    if options:
        if "disp" in options:
            kwargs['print_level'] = 1
        if "maxiter" in options:
            maxiter = options["maxiter"]

    names = ['%i'%i for i in range(len(x0))]
    for i, x in enumerate(names):
        kwargs[x] = x0[i]
        kwargs['error_'+x] = 0.1 if x0[i] == 0 else abs(0.1 * x0[i])
        if bounds:
            kwargs['limit_'+x] = bounds[i]
    kwargs['forced_parameters'] = names

    m = Minuit(wrapped.func, **kwargs)
    m.migrad(ncall=maxiter)

    message = "Optimization terminated successfully."
    success = m.migrad_ok()
    if not success:
        message = "Optimization failed."
        fmin = m.get_fmin()
        if fmin.has_reached_call_limit:
            message +=" Call limit was reached."
        if fmin.is_above_max_edm:
            message += " Estimated distance to minimum too large."

    return OptimizeResult(x=m.np_values(),
                          success=success,
                          fun=m.fval,
                          hess_inv=m.np_covariance(),
                          message=message,
                          nfev=wrapped.nfev,
                          njev=wrapped.njev)
