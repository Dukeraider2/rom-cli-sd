# v0.3.0-rc1 release handoff

Baseline dee098d68eca67024742c7e5de6b5d8c300e7415, branch release/v0.3.0-rc1. M3 branches contain separate voice experiments. GitHub issues are disabled. No open PR was listed at audit start.

The baseline passed Linux CI run 45557317914. Historical Desktop and Gaming Mode evidence, retry digests, reload behavior and compositor samples are in m2-steamdeck-hardware.md. Current SSH verified the same kernel over Tailscale with the previously trusted host key.

The npm audit identified a high-severity Rollup build-time advisory and moderate transitive glob/minimatch findings. Update Rollup and rerun build, packaging and Linux tests. Keep the legacy CLI version independent of the Decky package.

Approval gates include both suites, loader ZIP installation, upgrade preserving settings and catalog, removal preserving user data, restart persistence, recovery, artifact checksums, and independent review. Physical storage interruption requires a disposable medium. Historical runs alone cannot close candidate lifecycle gates.

## Candidate evidence, November 26

TypeScript, all four frontend tests and the Rollup build passed. The packaged entry point and three Python fallbacks passed on the physical Deck. A temporary EmuDeck fixture completed a 24,592-byte loopback install and blocked a duplicate. SHA-256 was 02ad100b04e699cc050733affe8b75030be62d7b23f1116515080ed8aac89f64. The extracted runtime directory measured 226,015 bytes using du -sb. No live plugin was replaced. See the PR checks for Linux suite results.
