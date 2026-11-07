# Minimal reproduction (lane S, scratch only): closing a listening modlwip socket on the host lwIP
# build trips lwIP's own assertion in tcp_err()/tcp_recv() (state LISTEN), which this build aborts on.
import lwip

lwip.reset()
listener = lwip.socket()
listener.bind(("127.0.0.1", 50000))
listener.listen(1)
print("listening; closing it now")
listener.close()
print("closed without an assertion")
