import mqtt_codec as mc


def _publish_bytes(topic: bytes, payload: bytes, qos: int, pid: int, *, retain: bool = False, dup: bool = False) -> bytes:
    buf = bytearray(len(topic) + len(payload) + 16)
    n = mc.encode_publish(buf, topic, payload, qos, pid, retain=retain, dup=dup)
    assert n > 0
    return bytes(buf[:n])


# MQTT 3.1.1 section 2.2.3's table: each boundary value and its exact encoding.
_LENGTH_TABLE = (
    (0, b"\x00"),
    (127, b"\x7f"),
    (128, b"\x80\x01"),
    (16383, b"\xff\x7f"),
    (16384, b"\x80\x80\x01"),
    (2097151, b"\xff\xff\x7f"),
    (2097152, b"\x80\x80\x80\x01"),
    (268435455, b"\xff\xff\xff\x7f"),
)


def test_remaining_length_decodes_every_boundary_of_the_specification_table() -> None:
    for value, encoded in _LENGTH_TABLE:
        buf = b"\x30" + encoded + b"tail"
        assert mc.decode_remaining_length(buf, 1, len(buf)) == value, (value, encoded)
        assert mc.remaining_length_bytes(buf, 1, len(buf)) == len(encoded), (value, encoded)


def test_remaining_length_encodes_every_boundary_of_the_specification_table() -> None:
    for value, encoded in _LENGTH_TABLE[:5]:  # the larger ones need a buffer of their own size
        buf = bytearray(value + 8)
        n = mc._put_fixed(buf, mc.PUBLISH, value)
        assert bytes(buf[1:n]) == encoded, (value, bytes(buf[1:n]))


def test_a_remaining_length_split_across_reads_is_incomplete_not_malformed() -> None:
    assert mc.decode_remaining_length(b"\x30\x80", 1, 2) == mc.LENGTH_INCOMPLETE
    assert mc.decode_remaining_length(b"\x30\xff\xff", 1, 3) == mc.LENGTH_INCOMPLETE
    assert mc.decode_remaining_length(b"\x30", 1, 1) == mc.LENGTH_INCOMPLETE


def test_a_fifth_length_byte_is_malformed() -> None:
    buf = b"\x30\xff\xff\xff\xff\x01"
    assert mc.decode_remaining_length(buf, 1, len(buf)) == mc.LENGTH_MALFORMED


def test_a_non_minimal_length_encoding_is_read_as_written() -> None:
    buf = b"\x30\x80\x00"  # zero in two bytes
    assert mc.decode_remaining_length(buf, 1, 3) == 0
    assert mc.remaining_length_bytes(buf, 1, 3) == 2


def test_a_header_past_the_maximum_or_the_buffer_is_refused() -> None:
    assert mc._put_fixed(bytearray(8), mc.PUBLISH, mc.MAX_REMAINING + 1) == -1
    assert mc._put_fixed(bytearray(8), mc.PUBLISH, 7) == -1  # 2 + 7 > 8
    assert mc._put_fixed(bytearray(9), mc.PUBLISH, 7) == 2


def test_connect_matches_the_specification_layout_byte_for_byte() -> None:
    buf = bytearray(128)
    n = mc.encode_connect(buf, b"abc", 60, b"s/abc/status", b"offline", b"", b"")
    expected = (
        b"\x10" + bytes([10 + 2 + 3 + 2 + 12 + 2 + 7])
        + b"\x00\x04MQTT\x04"
        + bytes([0x02 | 0x04 | 0x08 | 0x20])  # clean, will, will QoS 1, will retain
        + b"\x00\x3c"
        + b"\x00\x03abc" + b"\x00\x0cs/abc/status" + b"\x00\x07offline"
    )
    assert bytes(buf[:n]) == expected


def test_connect_carries_user_and_password_only_together() -> None:
    buf = bytearray(128)
    n = mc.encode_connect(buf, b"d", 30, b"w", b"o", b"user", b"pw")
    assert buf[9] == 0x02 | 0x04 | 0x08 | 0x20 | 0x80 | 0x40
    assert bytes(buf[n - 10 : n]) == b"\x00\x04user\x00\x02pw"
    n = mc.encode_connect(buf, b"d", 30, b"w", b"o", b"user", b"")
    assert buf[9] & 0xC0 == 0x80
    assert bytes(buf[n - 6 : n]) == b"\x00\x04user"
    n = mc.encode_connect(buf, b"d", 30, b"w", b"o", b"", b"pw")  # no user: the password is not sent (3.1.2.9)
    assert buf[9] & 0xC0 == 0
    assert n == 2 + 10 + 3 + 3 + 3
    assert bytes(buf[n - 3 : n]) == b"\x00\x01o"


def test_connect_that_does_not_fit_is_refused() -> None:
    assert mc.encode_connect(bytearray(20), b"abc", 60, b"s/abc/status", b"offline", b"", b"") == -1


def test_publish_at_qos_0_has_no_packet_id_and_no_dup() -> None:
    assert _publish_bytes(b"a/b", b"xy", 0, 7, dup=True) == b"\x30\x07\x00\x03a/bxy"


def test_publish_at_qos_1_carries_the_packet_id_retain_and_dup() -> None:
    assert _publish_bytes(b"a/b", b"xy", 1, 0x1234, retain=True) == b"\x33\x09\x00\x03a/b\x12\x34xy"
    assert _publish_bytes(b"a/b", b"xy", 1, 0x1234, retain=True, dup=True) == b"\x3b\x09\x00\x03a/b\x12\x34xy"


def test_publish_crossing_the_one_byte_length_uses_two_length_bytes() -> None:
    packet = _publish_bytes(b"t", b"p" * 125, 0, 0)  # 2 + 1 + 125 = 128
    assert packet[1:3] == b"\x80\x01"
    assert len(packet) == 3 + 128


def test_publish_that_does_not_fit_is_refused() -> None:
    assert mc.encode_publish(bytearray(10), b"topic", b"payload", 0, 0, retain=False, dup=False) == -1


def test_a_publish_head_is_the_packet_up_to_a_payload_its_caller_writes() -> None:
    # The client writes a slot's payload after the head itself; head plus payload is the whole packet, byte for byte.
    payload = b"p" * 130
    buf = bytearray(160)
    i = mc.encode_publish_head(buf, b"a/b", len(payload), 1, 0x1234, retain=True, dup=True)
    buf[i : i + len(payload)] = payload
    assert bytes(buf[: i + len(payload)]) == _publish_bytes(b"a/b", payload, 1, 0x1234, retain=True, dup=True)
    assert mc.encode_publish_head(bytearray(139), b"a/b", len(payload), 1, 0x1234, retain=False, dup=False) == -1  # 3 + 137 > 139


def test_puback_is_four_bytes() -> None:
    buf = bytearray(4)
    assert mc.encode_puback(buf, 0xBEEF) == 4
    assert bytes(buf) == b"\x40\x02\xbe\xef"


def test_subscribe_requests_qos_1_for_every_filter() -> None:
    buf = bytearray(64)
    n = mc.encode_subscribe(buf, 5, (b"a/#", b"b/+"))
    assert bytes(buf[:n]) == b"\x82\x0e\x00\x05\x00\x03a/#\x01\x00\x03b/+\x01"


def test_subscribe_with_no_filter_or_no_room_is_refused() -> None:
    assert mc.encode_subscribe(bytearray(64), 1, ()) == -1
    assert mc.encode_subscribe(bytearray(6), 1, (b"a/#",)) == -1


# Section 4.7's worked examples, plus the edge cases the matcher has to get right.
_MATCHES = (
    (b"sport/tennis/player1/#", b"sport/tennis/player1", True),
    (b"sport/tennis/player1/#", b"sport/tennis/player1/ranking", True),
    (b"sport/tennis/player1/#", b"sport/tennis/player1/score/wimbledon", True),
    (b"sport/#", b"sport", True),
    (b"#", b"sport/tennis", True),
    (b"sport/tennis/+", b"sport/tennis/player1", True),
    (b"sport/tennis/+", b"sport/tennis/player1/ranking", False),
    (b"sport/+", b"sport", False),
    (b"sport/+", b"sport/", True),
    (b"+/+", b"/finance", True),
    (b"/+", b"/finance", True),
    (b"+", b"/finance", False),
    (b"#", b"$SYS/x", False),
    (b"+/monitor/Clients", b"$SYS/monitor/Clients", False),
    (b"$SYS/#", b"$SYS/x", True),
    (b"$SYS/monitor/+", b"$SYS/monitor/Clients", True),
    (b"a/b", b"a/b", True),
    (b"a/b", b"a/bc", False),
    (b"a/b", b"a/b/c", False),
    (b"a/b/c", b"a/b", False),
    (b"a/#", b"ab", False),
)


def test_topic_filters_match_as_section_4_7_specifies() -> None:
    for flt, topic, expected in _MATCHES:
        assert mc.topic_matches(flt, topic) is expected, (flt, topic)
        assert mc.topic_matches(flt, memoryview(topic)) is expected, (flt, topic)


def test_client_ids_are_host_labels_up_to_23_bytes() -> None:
    for good in ("a", "SensorNodeA", "node-1", "x" * 23):
        assert mc.client_id_ok(good), good
    for bad in ("", "x" * 24, "a b", "a/b", "a+", "ä", "a_b", "a.b", "-node", "node-"):
        assert not mc.client_id_ok(bad), bad


def test_prefixes_have_no_wildcard_nul_or_edge_slash() -> None:
    for good in ("sensors", "home/sensors", "a" * 64):
        assert mc.prefix_ok(good), good
    for bad in ("", "/sensors", "sensors/", "s+", "s#", "s\x00", "a" * 65):
        assert not mc.prefix_ok(bad), bad


def test_user_name_and_password_text_has_no_nul_and_a_byte_bound() -> None:
    assert mc.text_ok(b"", 64)
    assert mc.text_ok(b"x" * 64, 64)
    assert not mc.text_ok(b"x" * 65, 64)
    assert not mc.text_ok(b"a\x00b", 64)


def test_topic_names_have_no_wildcard_and_a_byte_bound() -> None:
    assert mc.topic_name_ok(b"a/b")
    assert mc.topic_name_ok(b"x" * 128)
    for bad in (b"", b"x" * 129, b"a/+", b"a/#", b"a\x00"):
        assert not mc.topic_name_ok(bad), bad


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
