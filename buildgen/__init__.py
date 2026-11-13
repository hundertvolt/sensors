"""Host-side (CPython) generator turning one `devices/<device>.toml` into the device module
`sensortask_<device>.py` + boot entry. Never imports `src/`; everything is derived by
parsing TOML and AST-parsing driver source. See SPECIFICATION.md Parts L and C.14."""
