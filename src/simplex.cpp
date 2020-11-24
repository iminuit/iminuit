#include <Minuit2/FCNBase.h>
#include <Minuit2/MnSimplex.h>
#include <pybind11/pybind11.h>
#include "fcn.hpp"

namespace py = pybind11;
using namespace ROOT::Minuit2;

void bind_simplex(py::module m) {
  py::class_<MnSimplex, MnApplication>(m, "MnSimplex")

      .def(py::init<const FCNBase&, const MnUserParameterState&, const MnStrategy&>())
      .def("set_print_level",
           [](MnSimplex& self, int lvl) {
             return self.Minimizer().Builder().SetPrintLevel(lvl);
           })

      ;
}
