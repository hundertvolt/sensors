# R_fx2: website lane (final fix round)

Worktree `S/wt-fx2`, branch `final-fx2`, on release head `590cffcf`. Two commits, not pushed:
- `e4923bf5` Website Apply sends only what the user changed (item 1)
- `ede01737` Website errcount: any non-zero count shows red again (item 2)

Total: 6 files, +60/-81.

## Item 1: Apply sends only what the user changed: DONE

The owner decided this on 2026-11-13 at 11:56: "yes, only send what I changed".

### `js/render.js` (+9/-30)

I made the three changes V_FWB names:
1. Deleted the pre-PUT section re-read in the click handler (old `:204-207`). I also removed the three `button.disabled` lines that only guarded that await: the old `:203` and one in each early return. The handler is now synchronous up to `send()`, and `send()` disables the button itself. This matches the pre-audit handler.
2. `paint()` no longer re-baselines an existing card (old `:701`). This also covers sibling cards and the live status section.
3. In `send()`, after `putAndShow()` and `resetSettledControls()`, each submitted key the device answered as stored (Valid or Unchanged, `isStoredWord`) becomes the card's baseline. This is the pre-audit rule from `25caf528:js/render.js:247-254`.
   - It builds a new object, so the GET body that sibling cards share is never mutated.
   - `resetToBaseline()` is removed. It would now be a no-op, because the control already shows the value that was sent.

Other details:
- The `baselines` WeakMap has a 2-line comment stating the invariant and pointing to H.4 "Sparse PUT".
- `send()`'s doc is updated.
- Unchanged: the post-write GET (captions and readonly values), confirmations, Clear, the tracker, banners, and `updateWarnings()`.

### `tests_js/render.test.js` (+34/-33)

Replaced:
- The two tests at `~:2044-2075` that pinned the re-read.
- `~:1758` "shows a toggle and a dropdown as the post-write GET reports them, not as sent", which pinned `resetToBaseline()`.

New tests:
- "never sends a toggle or dropdown another client changed that the visitor left untouched". It applies twice and expects only `PUT {MeasInterval}`, then `PUT {COffset}`, with no GET before either. This covers both the re-read and `:701`.
- "sends nothing for an Apply with no edits, whatever another client changed, and re-enables Apply". It sees no request at all.
- "makes each key the device stored the baseline, keeping the controls as sent". The GET always reports the old values. The controls keep Off/x4, a second Apply has nothing to submit, and flipping back sends `{MeasEnabled: true}`.

I also reworded the `failNextPut()` doc line, because Apply no longer sends a GET first.

Bite check: against the release's `render.js`, all three new tests fail. With only the `:701` line put back, the first and third fail.

### `SPECIFICATION.md` (+5/-5, targeted edits on read lines)
- **H.3:** an editable toggle or select changes only by the user, or by `resetControl()` when an Apply resets a command. The old wording, "takes the baseline the post-write GET reports", is gone.
- **H.4 "PUT/GET error handling":** the re-read clause is dropped.
- **H.4 "Sparse PUT":** this is the rule's home, so the decision record sits here. It defines the baseline (the built-from value, or the one an Apply of it last stored), says no GET moves it, and carries `(owner, 2026-11-13: "yes, only send what I changed")`.
- **H.4 "After Apply":** a stored plain toggle or enum keeps the value sent, which is now its baseline. `resetToBaseline()` is no longer named.
- **"Divergences from the legacy site": does not apply.** Legacy's `putSensorCfg()` sent a toggle only once clicked (it was blank until then), so "only what the user changed" is legacy's behaviour, not a departure from it.

## Item 2: errcount count colour back to the pre-audit look: DONE

### `js/templates.js` (+6/-5)
- `ErrcountRowState` gains `hasErrors`, which is true for a numeric counter > 0 and false for the no-data and unavailable rows.
- `paintErrcountRow()` writes `data-has-errors` on the row wrapper, next to `data-worst`. The pre-audit attribute name is kept (`25caf528:templates.js:283`).

### `html/style.css` (+1/-5)
- The two `data-worst` "E"/"W" count colour rules are replaced by one rule: `[data-has-errors="true"]` shows the count in red, as in `25caf528:style.css:407-409`.
- Kept: `data-worst` (used by the flagged filter), the muted italic no-data rule, and the rollup colours, which match pre-audit.
- The "Resolution:" hint and the `console.error` diagnostic are untouched.

### `tests_js/templates.test.js` (+3/-2)
- The test that pinned the warning colour for a warnings-only module (and the absence of `data-has-errors`) now pins `data-has-errors="true"` for SGP40 (counter 3, warnings only) and `"false"` for SCD30 (counter 0).
- It fails against the release `templates.js`.

### `SPECIFICATION.md` (+2/-1)
- H.3's list of hooks the templates write now names `data-has-errors` (`true` for a non-zero count, which shows red).

## Checks (all after `rebuild.sh`)

| Check | Result |
|---|---|
| `npm run lint` | rc=0 |
| `npm run typecheck` | rc=0 |
| `npm run lint:css` | rc=0 |
| `npm run test:unit` (under `ports.flock`) | 25 files, 1192 passed, 0 failed |
| `checks.sh`: lint_direct and the three mypy passes | all clean (287 / 309 / 59 files) |
| `checks.sh`: 12 `tests_scripts` readers that read `js/`, `html/` or `SPECIFICATION.md` | 881 passed |
| MicroPython `tests/test_website_build_integration.py` (frozen site, `tc-c` standard binary, under the lock) | 7/7 at the default, 7/7 at `GC_THRESHOLD=32768` |

The 12 readers were: website_layering, website_tokens, decision_vocabulary, citations, comment_block_cap, definitions_js_mirrors, build_frozen_html_sh, build_website_sh, stage_website, api_reference, tunables_register and no_variant_literals.

The bite checks ran from a scratch copy of the release files and were then restored. The worktree is clean except the untracked `node_modules` link.

## Noticed, not done
- **The Altitude "Ignored: … is set." warning.** It resolves its sibling (AmbPres) from the same baseline. It still follows this page's own stored AmbPres at once. But a change another client makes to AmbPres now reaches the warning only on a reload or section switch. Before this change, the next Apply's GET in that section also delivered it. Keeping it fresher would need a second, GET-fed value map just for the warning; I left that for a decision.
- **No other test needed changes.** The tracker test (`begin, PUT, GET, end`), the disabled-until-post-write-GET test and the stopped-section test pin behaviour this change keeps.
