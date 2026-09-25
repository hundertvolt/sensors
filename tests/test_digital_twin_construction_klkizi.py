"""Digital-twin construction/wiring/REST checks for klkizi - one of six wrappers over the shared
tests/_digital_twin_construction_scenarios.py library (SPECIFICATION.md Part E.2.1)."""

from _digital_twin_construction_scenarios import register_for_device

globals().update(register_for_device("klkizi"))

if __name__ == "__main__":
    import microtest

    microtest.run(globals())
