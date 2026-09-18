"""build_system() construction/wiring tests for arzi - one of six wrappers over the shared
tests/_sensortask_scenarios.py library (SPECIFICATION.md Part E.2.1)."""

from _sensortask_scenarios import register_for_device

globals().update(register_for_device("arzi"))

if __name__ == "__main__":
    import microtest

    microtest.run(globals())
