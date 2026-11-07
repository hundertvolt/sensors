from _sensortask_scenarios import register_for_device

tests = register_for_device("wozi")
for name in ("test_webserver_status_get_reflects_the_real_object_graph", "test_webserver_status_publishes_utc_time_only_after_the_first_ntp_sync"):
    try:
        tests[name]()
        print("PASS", name)
    except Exception as e:
        print("FAIL", name, type(e).__name__, e)
