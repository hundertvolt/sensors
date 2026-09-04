# BENCH_NETWORK_LOCKOUT_2026-09-04.md

Temporary handoff doc for the local (on-Pi4) session to pick up from. Written by a separate cloud
session that helped diagnose/recover this incident from outside while the bench Pi4's SSH access
was down, working purely from git history, the SD card mounted on a second machine, and this
session's own `.claude/projects/.../09128d5d-4e23-4fae-95b7-43c6a0cd352b.jsonl` transcript. The
permanent, durable facts from this incident are already migrated into `CLAUDE.md` (new Hard Rule,
in "Hard rules"), `BACKLOG.md` (the `env --tier bench` item), and `dev_legacy/README.md`'s "Current
bench state" section (commit `f35f021`) — this file exists only to hand over the full raw detail
and the still-open follow-ups so the local session doesn't have to reconstruct any of it. **Delete
this file once its open items below are resolved and anything still worth keeping is folded into
the permanent docs** (same lifecycle as `REAL_HARDWARE_RUN_LOG.md`/`REAL_HARDWARE_HANDOFF.md`/
`DEV_HARDWARE_BASELINE_PLAN.md` before it — see git history around 2026-09-04 for that pattern).

## What happened, precisely (confirmed from the session's own JSONL transcript, not reconstructed)

Session `09128d5d-4e23-4fae-95b7-43c6a0cd352b` was mid-way through finally exercising
`env --tier bench`'s genuinely-from-blank bootstrap path for real (BACKLOG.md's top-priority item)
by deliberately tearing down the existing bridge/`dialout` state to simulate a blank host. Exact
sequence, with real timestamps:

1. **06:46:45Z** — wrote `bench_bridge_recovery.sh` (raw `nmcli` calls, no repo/Python dependency,
   recreating `br0`/`br0-eth0`/`br0-wifi-ap` with SSID `sensors-bench-1984de` /
   password `5AExf6MNfhSvezHQ` from scratch) as a dead-man's-switch safety net.
2. **~06:47:26Z** — armed it as a one-shot dry run:
   `sudo systemd-run --unit=bench-bridge-recovery-drytest --on-active=60 /bin/bash
   /tmp/bench_bridge_recovery.sh`.
3. **06:48:30Z** — dry run fired, ran to completion (`RECOVERY DONE` logged), and — completely
   normally, this part was never the bug — the transient systemd unit was garbage-collected
   immediately after, so `systemctl status` right after reported "could not be found". The session
   read this as "recovery mechanism confirmed working" and moved on.
4. **06:52:33Z** — a pure state-check (`connection show --active`, `ip route`, etc.) — no
   destructive action.
5. **06:53:01Z** — **the real destructive step, all in one command, with the one-shot dead-man's-
   switch from step 2 already consumed and never re-armed**:
   ```
   sudo gpasswd -d nico dialout
   for c in br0-wifi-ap br0-eth0 br0; do sudo nmcli connection delete "$c"; done
   nmcli -t -f NAME,TYPE,DEVICE connection show --active
   ```
6. **06:53:27.996Z** — the command's result came back **in full, uncorrupted**, confirming all
   three deletions genuinely succeeded:
   ```
   Removing user nico from group dialout
   ---
   dialout:x:20:
   ---
   Connection 'br0-wifi-ap' (7315b2b7-3759-45b9-af0f-0920ab5a45e8) successfully deleted.
   Connection 'br0-eth0' (ebf95bb6-6be8-40e2-9ef8-06466d88c3c4) successfully deleted.
   Connection 'br0' (737ac879-232f-4dd2-9983-1ec916666051) successfully deleted.
   ---
   br0:bridge:
   br0-wifi-ap:802-11-wireless:wlan0
   lo:loopback:lo
   ```
   Note `br0-eth0`/`eth0` is already absent from that final active-connections listing — it had
   already gone down by the time this same command's own check ran, milliseconds later. `eth0` was
   enslaved to `br0` (`master br0` per `dev_legacy/README.md`'s own bridge recipe), so the host's
   LAN IP lived on the bridge, not raw `eth0` — deleting `br0-eth0`/`br0` dropped it synchronously,
   with zero grace period. That's what cut the SSH session mid-flight.
7. **07:00:13.803Z** — ~6m45s later, a **synthetic client-side timeout**: `"error":"server_error"`,
   `"text":"Request timed out"`. This is the Claude Code CLI's own next API call (needed to decide
   the next step after the tool result above) hanging on the now-dead network and eventually giving
   up. **The agent process itself never crashed or hung on its own — it was cut off from its own
   model backend by the exact same action that cut off the human's SSH view**, simultaneously. No
   further commands ran after step 5; the transcript ends cleanly right here (a `turn_duration`
   system marker at the same timestamp, nothing after it).

**Root cause of the lockout, in one sentence**: a one-shot recovery timer that was proven working
via a dry run was never re-armed (and no pause/confirmation gate existed) before the real
destructive command that followed it in the same continuous turn.

## Recovery performed (from a second machine, no HDMI/console available)

1. Removed the SD card, mounted its root partition read-write on a second Linux machine.
2. Found `/etc/NetworkManager/system-connections/Wired connection 1.nmconnection` — NetworkManager's
   own auto-generated default profile for `eth0`, predating the bridge (`timestamp=1787912056`,
   dated Aug 28). It had been auto-suppressed by NetworkManager itself
   (`autoconnect=false`, `autoconnect-priority=-999`) once the bridge slave profile (`br0-eth0`)
   claimed the device — this is NM's own normal behavior when a more specific profile takes over an
   interface, not something the incident itself corrupted.
3. Edited it: `autoconnect=false` → `autoconnect=true`, deleted the `autoconnect-priority=-999`
   line entirely (defaults back to `0`).
4. Ruled out, methodically, before finding the above (all found clean, no action needed on any of
   these): `NetworkManager.conf`'s `[ifupdown] managed=false` (harmless — no
   `/etc/network/interfaces` file exists, so nothing is actually unmanaged by it), no `conf.d`
   overrides, no competing `dhcpcd`/`systemd-networkd` config, `NetworkManager.service` genuinely
   enabled and the package genuinely installed, `NetworkManager.state`'s
   `NetworkingEnabled=true` (global toggle was fine), `85-nm-unmanaged.rules` is a stock
   package-shipped file (not a custom rule targeting `eth0`), no persisted iptables rules that could
   be silently eating DHCP traffic, no persistent journal existed to check (`/var/log/journal`
   absent — journald was volatile/RAM-only, so pre-reboot logs from the incident itself are
   unrecoverable; this is why the JSONL transcript ended up being the real source of truth instead).
5. Synced, cleanly unmounted, physically reinserted the card, did a genuine full power-cycle (power
   disconnected before reinsertion, not just an OS-level reboot attempt with no console to trigger
   one).
6. Device came back on the network. **Not yet independently re-verified this session whether the
   SD card write was flushed correctly before the physical pull that first surfaced this recovery
   attempt** — a `fsck -n` + re-mount-and-recheck sequence was handed to the project owner
   immediately before this recovery succeeded; whether that specific verification pass was ever run
   is unconfirmed. Worth a quick `sudo fsck -f /dev/<root-partition>` (read-only host disks so needs
   the card out and re-mounted elsewhere, or accept the risk of running it live via
   `touch /forcefsck && sudo reboot` if you'd rather not pull the card again) if anything about the
   filesystem seems off, but there's no current symptom actually pointing at corruption.

## Current real state of the host, as of this file being written

- **`eth0` is UP via NetworkManager's own default `Wired connection 1` profile, plain DHCP, no
  bridge.** This is genuinely working — the host is reachable.
- **`br0`/`br0-eth0`/`br0-wifi-ap` are still deleted, not recreated.** This is not itself a bug to
  fix reactively — it's exactly the genuinely-blank state the interrupted `env --tier bench` test
  needed. The natural next step is to actually run that test for real now, interactively, with a
  human watching (see "What to do next" below) rather than just recreating the bridge by hand.
- **`nico` is still not in the `dialout` group** (`sudo gpasswd -d nico dialout`, never restored).
- **Two new, downstream symptoms surfaced after recovery, both traced to the same one cause — not
  two separate bugs**:
  1. The Pi picked up a **different DHCP-assigned IP** than before, despite the router having a
     static reservation configured for its MAC address.
  2. The router now shows it under a **synthesized hostname `PC-D8-3A-DD-28-EA-5A`** instead of the
     `raspberrypi` name it showed before.

  Root cause for both: a Linux bridge synthesizes its own MAC address (commonly inherited from one
  of its slave ports, and this can shift over the bridge's lifetime) — it is **not** the same as
  `eth0`'s real, permanent hardware MAC underneath it. The router's static reservation (and its
  saved friendly name) were almost certainly captured against whatever MAC `br0` was presenting
  while it existed. Now that `eth0` connects directly, unbridged, it presents its own true hardware
  MAC — which the router has never seen before, so it treats this as a brand-new device: assigns it
  the next free pool address instead of honoring the old reservation, and auto-generates a
  `PC-<MAC>` placeholder name since it has no saved friendly name against *this* MAC. Not yet fixed
  (needs router-UI access, not something scriptable from here) — see "What to do next".

## Datasheet/hardware-fact caveat

None of this incident touched sensor hardware, I2C/SPI buses, or anything `datasheets/`-relevant —
it's entirely host-side Linux networking (NetworkManager, `nmcli`, systemd, DHCP). No datasheet
claims were made or needed here, noted only because CLAUDE.md's "always check/cite datasheets for
hardware claims" rule is otherwise a standing requirement for this repo.

## What to do next (suggested order, not mandatory — use judgement)

1. **Confirm `/etc/hostname`/`/etc/hosts`/`hostname` on the Pi itself still correctly say
   `raspberrypi`** (rules out an actual on-device regression, as opposed to the router's own stale
   MAC-keyed bookkeeping being the whole story).
2. **Get `eth0`'s real hardware MAC** (`ip link show eth0` or `cat /sys/class/net/eth0/address`)
   and reconcile it with the router: update the existing static-reservation entry to this MAC
   (should also fix the `raspberrypi` display name if the router ties both to the same entry;
   otherwise the friendly name may need a manual rename too). This needs the router's own admin UI
   — not automatable from the Pi/repo side.
3. **Re-grant `dialout`**: `sudo gpasswd -a nico dialout` — trivial, do this whenever convenient,
   no ordering dependency on anything else here.
4. **Actually finish the interrupted test**: run `uv run toolchain/setup_toolchain.py env --tier
   bench` for real, interactively, watching it — this is the literal thing the incident interrupted,
   and the host is now honestly in the right starting state for it (genuinely blank bridge). Per
   CLAUDE.md's new standing rule (see "Hard rules" — the dead-man's-switch one added this session),
   if you use any recovery safety net for this run, keep it **continuously re-armed immediately
   before every individual destructive command**, not just once up front. Given this is now being
   run interactively with a human present (not unattended), a real-time pause/confirmation before
   each `nmcli connection delete` is arguably simpler and just as safe as a timer-based switch.
5. **Consider pinning the bridge's MAC** once it's recreated, so this exact IP/hostname drift
   doesn't recur the next time the bridge is torn down and rebuilt:
   ```
   sudo nmcli connection modify br0 bridge.mac-address <eth0's real MAC from step 2>
   ```
6. Once everything above is settled and confirmed working, fold anything from this file still worth
   keeping into `BACKLOG.md`/`dev_legacy/README.md` (most of the durable facts already are, via
   commit `f35f021` — check it's not already redundant before adding more) and **delete this file**.
