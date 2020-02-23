.. include:: references.txt

iminuit
=======

Jupyter-friendly Python interface to the C++ Minuit2 library.

`iminuit` can be used for general function minimization, but is most commonly used for least-squares and maximum-likelihood fits of models to data, and to get model parameter error estimates from likelihood profile analysis.

* Code: https://github.com/scikit-hep/iminuit
* Documentation: http://iminuit.readthedocs.org/
* Gitter: https://gitter.im/Scikit-HEP/community
* Mailing list: https://groups.google.com/forum/#!forum/scikit-hep-forum
* PyPI: https://pypi.org/project/iminuit/
* License: MINUIT is LGPL and iminuit is MIT
* Citation: https://github.com/scikit-hep/iminuit/blob/master/CITATION

In a nutshell
-------------

.. code-block:: python

    from iminuit import Minuit

    def f(x, y, z):
        return (x - 2) ** 2 + (y - 3) ** 2 + (z - 4) ** 2

    m = Minuit(f)

    m.migrad()  # run optimiser
    print(m.values)  # {'x': 2,'y': 3,'z': 4}

    m.hesse()   # run uncertainty estimator
    print(m.errors)  # {'x': 1,'y': 1,'z': 1}


.. toctree::
    :maxdepth: 4
    :hidden:

    about
    install
    tutorials
    reference
    benchmark
    faq
    changelog
    contribute
