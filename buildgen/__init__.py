"""Host-side (CPython) generator turning one `devices/<device>.toml` into the equivalent of a
hand-written `sensortask_<device>.py` + boot entry. Never imports `src/`; everything is derived by
parsing TOML and AST-parsing driver source. See SPECIFICATION.md Parts L and C.14."""
