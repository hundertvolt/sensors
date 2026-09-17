"""build_system() construction/wiring tests for dev specifically - one of six per-device
files generated from the shared tests/_sensortask_scenarios.py scenario library (see that module's
own docstring for the full scenario set, the rationale for the per-device split, and every pointer
to SPECIFICATION.md/CLAUDE.md this used to carry directly)."""

from _sensortask_scenarios import register_for_device

globals().update(register_for_device("dev"))

if __name__ == "__main__":
    import microtest

    microtest.run(globals())
