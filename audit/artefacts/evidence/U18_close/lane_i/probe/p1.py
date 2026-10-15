import socket, asyncio
a = socket.getaddrinfo("127.0.0.1", 25001)[0][-1]
print(type(a), a, a[0])
