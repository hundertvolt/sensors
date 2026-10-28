# U29 review list

1. **Sign off the threat model**: decided, signed off as it stands (owner, 2026-10-20: "Option 1, sign off A.11 as is", to "sign off A.11 as it stands, or change rows 4, 5 or 7");
   recorded in A.11 (`442a564`). The item: SPECIFICATION.md A.11 (the plan leaves the sign-off to you) applies your
   trusted-home-LAN model (owner, 2026-09-26) to the 16 ways a unit is reachable, each with the modes it is reachable in.
   Three rows had no earlier decision of yours and follow the same model: the hotspot's DHCP server, mDNS, and ICMP/IPv6
   (each answers only on the local network).

Settled without you, recorded in REGISTER (sources or your own decisions decide each):
- The coverage job's time limit, 35 to 95 minutes: your timeout rule applied through the CI budget rule.
- The second generated bench password: the same kind as the first, under your 2026-09-25 words.
- GitHub's secret scanning and push protection are on; the history scan covered every path outside `arduino/`, which
  stays out of the audit (owner, 2026-09-30).
- A retried live JS test cannot overlap its predecessor: every live check ends one twin stop before its test's timeout.
- Three attempt counts the retry check could not see are now tagged and classified like every other.

Owner-decided this unit (recorded in REGISTER with the questions):
- "Two retries everywhere" (owner, 2026-10-20);
- "pytest tier", "JS tier", "This rule / consistency is for testing only. Firmware stays unaffected." (owner, 2026-10-20);
- "The retry logic is for tests running into timeout. ... The Hotspot remains untouched." (owner, 2026-10-20).
