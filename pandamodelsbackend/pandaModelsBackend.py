# SPDX-License-Identifier: MIT
# This file is a plugin to Grid2Op, a testbed platform to model sequential decision making in power systems.

import sys
import warnings

import numpy as np
from typing import Union, Tuple

import pandapower as pp
from pandapower.optimal_powerflow import OPFNotConverged
import scipy

from packaging import version

import grid2op
from grid2op.Exceptions import BackendError
from grid2op.Backend import PandaPowerBackend

MIN_LS_VERSION_VM_PU = version.parse("0.6.0")

try:
    import numba
    NUMBA_ = True
except (ImportError, ModuleNotFoundError):
    NUMBA_ = False
    warnings.warn(
        "Numba cannot be loaded. You will gain possibly massive speed if installing it by "
        "\n\t{} -m pip install numba\n".format(sys.executable)
    )


class PandaModelsBackend(PandaPowerBackend):
    # For maintainability, this class is lightly edited from grid2op's PandaPowerBackend at
    # https://github.com/Grid2op/grid2op/blob/master/grid2op/Backend/pandaPowerBackend.py
    # Please consult that file for documentation and usage, and keep this file up-to-date
    # with the target Grid2op version (dev_1.11.0 as of March 2025).
    
    def _aux_run_pf_init(self):
        """run a powerflow when the file is being loaded. This is called three times for each call to "load_grid" """
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore")
            try:
                self._aux_runpf_pp(False)
                if getattr(self._grid, 'converged', False) and getattr(self._grid, 'OPF_converged', False):
                    raise pp.powerflow.LoadflowNotConverged
            except pp.powerflow.LoadflowNotConverged:
                self._aux_runpf_pp(True)

    def _aux_runpf_pp(self, is_dc: bool):
        with warnings.catch_warnings():
            # remove the warning if _grid non connex. And it that case load flow as not converged
            warnings.filterwarnings(
                "ignore", category=scipy.sparse.linalg.MatrixRankWarning
            )
            warnings.filterwarnings("ignore", category=RuntimeWarning)
            warnings.filterwarnings("ignore", category=DeprecationWarning)
            self._pf_init = "dc"
            try:
                if is_dc:
                    # TODO: Could call PwMd function here too, but Ben says DC will be same
                    pp.rundcpp(self._grid, check_connectivity=True, init="flat")

                    # if I put check_connectivity=False then the test AAATestBackendAPI.test_22_islanded_grid_make_divergence
                    # does not pass

                    # if dc i start normally next time i call an ac powerflow
                    self._nb_bus_before = None
                else:
                    pp.runpm(
                        self._grid,
                        check_connectivity=False,
                        #silence=False,
                        pm_log_level=2
                    )
            except IndexError as exc_:
                raise pp.powerflow.LoadflowNotConverged(f"Surprising behaviour of pandapower when a bus is not connected to "
                                                        f"anything but present on the bus (with check_connectivity=False). "
                                                        f"Error was {exc_}"
                                                        )
            except OPFNotConverged as exc_:
                raise pp.powerflow.LoadflowNotConverged(f" runpm / runpm_dc_opf in _aux_runpf_pp"
                                                        f"Error was {exc_}"
                                                        )
            # print("-"*50)
            # print(self._grid.res_gen)
            # print(f"converged: {self._grid.converged} OPF_converged: {self._grid.OPF_converged}")
            # print("-"*50)
            # stores the computation time
            if "_ppc" in self._grid:
                if "et" in self._grid["_ppc"]:
                    self.comp_time += self._grid["_ppc"]["et"]
            if self._grid.res_gen.isnull().values.any():
                # TODO see if there is a better way here -> do not handle this here, but rather in Backend._next_grid_state
                # sometimes pandapower does not detect divergence and put Nan.
                raise pp.powerflow.LoadflowNotConverged("Divergence due to Nan values in res_gen table (most likely due to "
                                                        "a non connected grid).")

    def runpf(self, is_dc : bool=False) -> Tuple[bool, Union[Exception, None]]:
        """
        INTERNAL

        .. warning:: /!\\\\ Internal, do not use unless you know what you are doing /!\\\\

        Run a power flow on the underlying _grid. This implements an optimization of the powerflow
        computation: if the number of
        buses has not changed between two calls, the previous results are re used. This speeds up the computation
        in case of "do nothing" action applied.
        """
        try:
            # as pandapower does not modify the topology or the status of
            # powerline, then we can compute the topology (and the line status)
            # at the beginning
            # This is also interesting in case of divergence :-)
            self._get_line_status()
            self._get_topo_vect()
            self._aux_runpf_pp(is_dc)
            cls = type(self)
            # if a connected bus has a no voltage, it's a divergence (grid was not connected)
            if self._grid.res_bus.loc[self._grid.bus["in_service"]]["va_degree"].isnull().any():
                buses_ko = self._grid.res_bus.loc[self._grid.bus["in_service"]]["va_degree"].isnull()
                buses_ko = buses_ko.values.nonzero()[0]
                raise pp.powerflow.LoadflowNotConverged(f"Isolated bus, check buses {buses_ko} with `env.backend._grid.res_bus.iloc[{buses_ko}, :]`")

            (
                self.prod_p[:],
                self.prod_q[:],
                self.prod_v[:],
                self.gen_theta[:],
            ) = self._gens_info()
            (
                self.load_p[:],
                self.load_q[:],
                self.load_v[:],
                self.load_theta[:],
            ) = self._loads_info()

            if is_dc:
                # fix voltages magnitude that are always "nan" for dc case
                # self._grid.res_bus["vm_pu"] is always nan when computed in DC
                self.load_v[:] = self.load_pu_to_kv  # TODO
                # need to assign the correct value when a generator is present at the same bus
                # TODO optimize this ugly loop
                # see https://github.com/e2nIEE/pandapower/issues/1996 for a fix
                for l_id in range(cls.n_load):
                    if cls.load_to_subid[l_id] in cls.gen_to_subid:
                        ind_gens = (
                            cls.gen_to_subid == cls.load_to_subid[l_id]
                        ).nonzero()[0]
                        for g_id in ind_gens:
                            if (
                                self._topo_vect[cls.load_pos_topo_vect[l_id]]
                                == self._topo_vect[cls.gen_pos_topo_vect[g_id]]
                            ):
                                self.load_v[l_id] = self.prod_v[g_id]
                                break
                self.load_v[~self._grid.load["in_service"]] = 0.

            # I retrieve the data once for the flows, so has to not re read multiple dataFrame
            self.p_or[:] = self._aux_get_line_info("p_from_mw", "p_hv_mw")
            self.q_or[:] = self._aux_get_line_info("q_from_mvar", "q_hv_mvar")
            self.v_or[:] = self._aux_get_line_info("vm_from_pu", "vm_hv_pu")
            self.a_or[:] = self._aux_get_line_info("i_from_ka", "i_hv_ka") * 1000.
            self.theta_or[:] = self._aux_get_line_info(
                "va_from_degree", "va_hv_degree"
            )
            self.a_or[~np.isfinite(self.a_or)] = 0.0
            self.v_or[~np.isfinite(self.v_or)] = 0.0

            self.p_ex[:] = self._aux_get_line_info("p_to_mw", "p_lv_mw")
            self.q_ex[:] = self._aux_get_line_info("q_to_mvar", "q_lv_mvar")
            self.v_ex[:] = self._aux_get_line_info("vm_to_pu", "vm_lv_pu")
            self.a_ex[:] = self._aux_get_line_info("i_to_ka", "i_lv_ka") * 1000.
            self.theta_ex[:] = self._aux_get_line_info(
                "va_to_degree", "va_lv_degree"
            )
            self.a_ex[~np.isfinite(self.a_ex)] = 0.0
            self.v_ex[~np.isfinite(self.v_ex)] = 0.0

            # it seems that pandapower does not take into account disconencted powerline for their voltage
            self.v_or[~self.line_status] = 0.0
            self.v_ex[~self.line_status] = 0.0
            self.v_or[:] *= self.lines_or_pu_to_kv
            self.v_ex[:] *= self.lines_ex_pu_to_kv

            # see issue https://github.com/Grid2Op/grid2op/issues/389
            self.theta_or[~np.isfinite(self.theta_or)] = 0.0
            self.theta_ex[~np.isfinite(self.theta_ex)] = 0.0

            self._nb_bus_before = None
            if self._iref_slack is not None:
                # a gen has been added to represent the slack, modeled as an "ext_grid"
                self._grid._ppc["gen"][self._iref_slack, 1] = 0.0

            # handle storage units
            # note that we have to look ourselves for disconnected storage
            (
                self.storage_p[:],
                self.storage_q[:],
                self.storage_v[:],
                self.storage_theta[:],
            ) = self._storages_info()
            deact_storage = ~np.isfinite(self.storage_v)
            self.storage_p[deact_storage] = 0.0
            self.storage_q[deact_storage] = 0.0
            self.storage_v[deact_storage] = 0.0
            self._grid.storage["in_service"].values[deact_storage] = False

            if getattr(self._grid, 'converged', False) and getattr(self._grid, 'OPF_converged', False):
                raise pp.powerflow.LoadflowNotConverged("Divergence without specific reason (self._grid.converged and self._grid.OPF_converged both are False)")
            self.div_exception = None
            if is_dc:
                # pandapower apparently does not set 0 for q in DC...
                self.prod_q[:] = 0.
                self.load_q[:] = 0.
                self.storage_q[:] = 0.
                self.q_or[:] = 0.
                self.q_ex[:] = 0.
            return True, None

        except pp.powerflow.LoadflowNotConverged as exc_:
            # of the powerflow has not converged, results are Nan
            self.div_exception = exc_
            self._reset_all_nan()
            msg = exc_.__str__()
            return False, BackendError(f'powerflow diverged with error :"{msg}", you can check `env.backend.div_exception` for more information')
        except OPFNotConverged as exc_:
            return False
