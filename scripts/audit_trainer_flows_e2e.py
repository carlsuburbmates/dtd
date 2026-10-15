"""Retired legacy trainer-flow audit entrypoint.

The former script mixed persistent trainer submissions, claim-email dispatch,
owner enquiries and Ops checks without deterministic fixture cleanup or a
test-only mail sink. Use the isolated integration suite and bounded sandbox
acceptance runners instead. Do not restore live-write behavior until the
sandbox has synthetic fixtures, recipient containment and verified cleanup.
"""

if __name__ == "__main__":
    raise SystemExit(
        "Retired: this legacy audit performed persistent writes and could send email. "
        "Use the isolated integration suite and bounded sandbox acceptance runners."
    )
