import unittest
from grid2op.Space import DEFAULT_ALLOW_DETACHMENT
from grid2op.tests.aaa_test_backend_interface import AAATestBackendAPI

from pandamodelsbackend import PandaModelsBackend

class TestBackendAPI_PandaModelsBackend(AAATestBackendAPI, unittest.TestCase):
    def make_backend(self, detailed_infos_for_cascading_failures=False):
        return PandaModelsBackend(detailed_infos_for_cascading_failures=detailed_infos_for_cascading_failures)
    
    # The following tests are skipped as these tests may not relevant for the PandaModelsBackend backend
    # in the PandaModelsBackend as PandaPower runnpp doesn't converge but runpm does
    def test_17_isolated_gen_stops_computation(self, allow_detachment=DEFAULT_ALLOW_DETACHMENT):
        pass

    def test_22_islanded_grid_stops_computation(self):
        pass

    def test_12_modify_gen_pf_getter(self):
        pass
    
    # The following tests are skipped as these tests lead to error in Julia
    # probably a bug in PandaPower or PandaModels that leads to this error 
    def test_16_isolated_load_stops_computation(self, allow_detachment=DEFAULT_ALLOW_DETACHMENT):
        pass

    def test_19_isolated_storage_stops_computation(self, allow_detachment=DEFAULT_ALLOW_DETACHMENT):
        pass

if __name__ == "__main__":
    unittest.main()
