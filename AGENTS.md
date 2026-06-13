# Agent Operating Contract — swarm-discussion (aggregator)

This repository is the **thin aggregator marketplace** for the swarm-discussion
plugin family. As of v0.2 it contains no protocol, runtime, or plugin code —
only `.claude-plugin/marketplace.json` pointing at certified adapter releases,
plus README / LICENSE / CHANGELOG / CI.

## Principles

1. Keep it thin. The only substantive file is `.claude-plugin/marketplace.json`.
   Do NOT add plugin bundles, runtime code, protocol docs, or vendored runtimes
   here — those live in `swarm-discussion-runtime` and the per-host adapter
   repos.
2. List only **certified** adapter releases. An adapter entry's `source` points
   at the adapter repo and pins `ref` (a release tag) or `sha`; only add or bump
   it after that release passes `conformance/certify_adapter.py` in the runtime
   repo.
3. The v0.1 dual-host line is preserved at the `v0.1.16` tag and `v0.1.x`
   branch; do not resurrect it onto `main`.

## Push Cadence

The maintainer has opted into auto-push: after any work turn that commits to
this repo, push the new commits to `origin/main` without asking first.

## Release checklist

- `python3 -c` marketplace validation passes (the CI job), and
  `claude plugin validate .` passes locally.
- Each listed adapter `ref`/`sha` corresponds to a certified release.
- README install instructions and CHANGELOG are updated for the version bump.
