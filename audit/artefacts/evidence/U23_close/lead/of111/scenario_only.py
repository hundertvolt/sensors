# The one shutdown scenario of tests/_sensortask_scenarios.py, for the devices named on the command line (scratch driver).
import sys

import microtest
from _sensortask_scenarios import register_for_device

_NAME = "test_every_api_write_is_refused_from_a_system_commands_acceptance_to_its_reset"
tests = {}
for device in sys.argv[1:]:
    tests[_NAME + "_" + device] = register_for_device(device)[_NAME]
microtest.run(tests)
