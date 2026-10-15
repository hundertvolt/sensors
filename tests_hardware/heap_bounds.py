"""The heap bound the hardware tier's floors are multiples of, defined once: host tests import it, device scripts
receive it as a render extra (harness.render_device_script())."""

# The largest contiguous allocation the firmware could be asked to make when the floors were set: 16,384 B through
# microdot's own max_body_length default, kept as the tripwire's margin though both caps now bind it to 2,048 B
# (SPECIFICATION.md Part I.6) (agent, 2026-09-19; owner-reviewed, 2026-10-02; the retired 80,000 B floor was the owner's, 2026-09-19).
WORST_CASE_ALLOCATION = 16_384
