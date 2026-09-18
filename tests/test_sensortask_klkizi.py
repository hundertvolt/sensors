"""build_system() construction/wiring tests for klkizi - one of six wrappers over the shared
tests/_sensortask_scenarios.py library (SPECIFICATION.md Part E.2.1)."""

from _sensortask_scenarios import register_for_device

globals().update(register_for_device("klkizi"))

if __name__ == "__main__":
    import microtest

    microtest.run(globals())
