# Marketplace conformance

This repo ships vendored Claude and Codex plugin bundles. This harness verifies the packaged bundles still
preserve the shared protocol contract without depending on the development repo.

Run:

```sh
python3 conformance/conformance.py
```

The script feeds identical canned persona outputs through the Claude-style collect path and the Codex
`wait_agent` + `collect.py` demux path, then asserts the produced round records are identical and pass the
vendored validator.
