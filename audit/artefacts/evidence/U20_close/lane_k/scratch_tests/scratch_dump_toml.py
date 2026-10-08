"""Scratch proof (not committed): dump_toml() writes a non-table wiring as the plain value it is."""
import tomllib

from _toml_fixtures import base_doc, dump_toml


def test_instance_wiring_written_as_a_string_stays_a_string() -> None:
    doc = base_doc()
    doc["instance"][0]["wiring"] = "fram"
    assert tomllib.loads(dump_toml(doc))["instance"][0]["wiring"] == "fram"


def test_device_wiring_written_as_an_int_stays_an_int() -> None:
    doc = base_doc()
    doc["device"]["wiring"] = 1
    assert tomllib.loads(dump_toml(doc))["device"]["wiring"] == 1


def test_inline_tables_and_arrays_round_trip() -> None:
    doc = base_doc()
    doc["instance"][0]["wiring"]["fram_target"] = {"default": True, "a": [1, "x"]}
    doc["device"]["extra"] = [1, 2]
    parsed = tomllib.loads(dump_toml(doc))
    assert parsed["device"]["extra"] == [1, 2]
    assert parsed["instance"][0]["wiring"]["fram_target"] == {"default": True, "a": [1, "x"]}


def test_base_doc_round_trips_unchanged() -> None:
    assert tomllib.loads(dump_toml(base_doc())) == base_doc()
