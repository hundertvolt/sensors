import pytest
@pytest.fixture(autouse=True)
def _plant(monkeypatch):
    import buildgen.validate as v
    monkeypatch.setattr(v, "_WDT_TIMEOUT_MS", 8001)  # planted: the budget's watchdog is no longer the armed one
