---
name: integrate-module
description: Add a module, service or sensor driver to this repository by walking SPECIFICATION.md Part K in order.
---

# Integrate a module

The procedure is SPECIFICATION.md Part K, and only Part K; this file holds no copy of it.

**Inputs**
- For a sensor driver, the chip's datasheet under `datasheets/<chip>/`.
- The record of K.0's owner discussion: the features, the API and the website.
- The repository at its current head.

**Steps**
1. Read SPECIFICATION.md Part 0 and Part K in full, and the closest existing driver in full (K.1 item 3);
   read each Part a step cites when that step comes up (agent, 2026-11-05).
2. Walk K.0 to K.11 in order. A step marked *a sensor driver* applies only to one.
3. For each step, report what was done, or why it does not apply.
4. End with K.11's list checked off.

A question the inputs leave open goes to the owner (K.0), never into a guess.
