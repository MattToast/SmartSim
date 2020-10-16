import time
import pytest
from shutil import which
from os import getcwd, path, environ

from smartsim import Experiment
from smartsim.control import Controller
from smartsim.utils.test.decorators import controller_test


# --- Setup ---------------------------------------------------

# Path to test outputs
test_path = path.join(getcwd(),  "./controller_test/")
ctrl = Controller()

# --- Tests  -----------------------------------------------

# experiment with non-clustered orchestrator
exp = Experiment("Stop-Tests")

run_settings = {
    "ppn": 1,
    "nodes": 1,
    "executable": "python",
    "exe_args": "sleep.py"
}

@controller_test
def test_stop_entity():
    # setup allocation and models
    alloc = get_alloc_id()
    run_settings["alloc"] = alloc
    M1 = exp.create_model("m1", path=test_path, run_settings=run_settings)

    ctrl.start(M1)
    time.sleep(3)
    ctrl.stop_entity(M1)
    assert(M1.name in ctrl._jobs.completed)
    assert(ctrl.get_entity_status(M1).startswith("CANCELLED"))

@controller_test
def test_stop_entity_list():
    # setup allocation and orchestrator
    alloc = get_alloc_id()
    O1 = exp.create_orchestrator(path=test_path, alloc=alloc)

    ctrl.start(O1)
    time.sleep(5)
    ctrl.stop_entity_list(O1)
    assert(all([orc.name in ctrl._jobs.completed for orc in O1.entities]))


# ------ Helper Functions ------------------------------------------

def get_alloc_id():
    alloc_id = environ["TEST_ALLOCATION_ID"]
    return alloc_id