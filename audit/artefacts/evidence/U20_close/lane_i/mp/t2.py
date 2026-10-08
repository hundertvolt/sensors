entry = ('writeto', 97, b'\x03\x00', True)
word = 0x0300
print(entry[0] == "writeto" and entry[1] == 97 and len(entry[2]) >= 2 and (entry[2][0] << 8 | entry[2][1]) == word)
print((entry[2][0] << 8 | entry[2][1]), word)
log = [entry, ('writeto', 97, b'\xd3\x04', True)]
print(sum(1 for e in log if e[0] == "writeto" and e[1] == 97 and len(e[2]) >= 2 and (e[2][0] << 8 | e[2][1]) == word))
