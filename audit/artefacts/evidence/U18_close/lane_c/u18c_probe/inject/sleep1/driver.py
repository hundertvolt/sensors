import sys
ns = {"__name__": "probe"}
exec(open("tests/test_asy_captive_dns.py").read(), ns)
try:
    ns["test_run_answers_queued_queries_back_to_back"]()
    print("PASS")
except AssertionError as e:
    print("FAIL", e)
