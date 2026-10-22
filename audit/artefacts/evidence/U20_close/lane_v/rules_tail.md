| `instance.no-bus-kind-row` | base doc, with `buildspec.BUS_KIND_BY_DRIVER` lacking its `"scd30"` row (a table patch; no TOML reaches it) | scd30 | - |
| `names.label-collision` | a model holding the keys `("foo_bar", "")` and `("foo", "bar")`, which both render as `foo_bar` (synthetic model; no driver name today has an underscore) | - | - |
| `names.settings-key-collision` | `SETTINGS_GROUPS` plus the row `("networking", "ntp", ("Hostname",), None)` (a table patch) | - | Hostname |
| `toolchain.lwip-table` | `lwip_macros()` returning the pinned table with `TCP_MSS = "12000"` (a toolchain patch) | - | max_connections |
| `toolchain.overrides-unloadable` | `importlib.util.spec_from_file_location` returning `None` (a toolchain patch) | - | max_connections |
