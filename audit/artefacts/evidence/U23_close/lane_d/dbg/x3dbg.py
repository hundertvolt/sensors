import test_asy_webserver_service as t
import json
slow, bad, fast = t._SlowResetModule("A"), t._RaisingResetModule("B"), t._FakeModule("C")
service, app = t._make_service(error_sources=[slow, bad, fast])
res = t.run(app.dispatch_request(t._make_request(app, "PUT", "/status", {"ResetErrors": True})))
print(res.status_code, res.body)
print(t.run(service.get_error_counter()))
print(t.code("E", "CALLBACK"))
