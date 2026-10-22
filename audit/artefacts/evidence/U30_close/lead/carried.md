# U30 carried items (from the U23 owner report; fold at U30 start; U31 instead if U30 edits no src/asy_webserver_service.py)

1. OF-145 (owner, 2026-10-13): question "Clear nothing when ResetErrors answers Failed in mempause?" with options
   "(b, recommended) Clear nothing while storage is paused: on every device the answer matches the effect and the history
   survives the pause; a reset wanted during a pause is sent again after it." / "(a) As is: on every device the reset
   answers "Failed" but the history is gone once the pause ends." Answer: "1 b". Site: src/asy_print_log.py reset()
   (:219-233 at 9bf2274). Seen failing first: a mempause ResetErrors then a post-pause store keeps the history.
   Docs: DEVICE_REFERENCE.md's backup-pause sentence (today: "still clears the in-memory logs") flips to the new effect,
   with the quote and the question (decision-records rule 2).
2. OF-146 (owner, 2026-10-13): question "Refuse ResetErrors from the supervisor's own reboot decision too?" with options
   "(b, recommended) Refuse it from the supervisor's decision on: on every device the logs explaining a supervisor reboot
   survive it; the web service reads the system's shutdown state through one new generated route (a build-generator
   change), which also replaces today's OF-111 flag, so one state covers both paths." / "(a) As is: on every device a
   reset in that window still clears the logs the reboot left." Answer: "2 b". Sites: src/asy_system_service.py _reboot()
   (:311-322 at 9bf2274), the generator's route, src/asy_webserver_service.py (the OF-111 flag retires into the one
   state). Seen failing first: a supervisor-budget reboot window + ResetErrors leaves the logs intact; OF-111's four
   commands still refused through the shared state. Twin: both paths on every device.
