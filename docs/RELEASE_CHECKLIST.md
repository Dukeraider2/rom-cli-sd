# v0.3.0-rc1 release handoff

Baseline dee098d68eca67024742c7e5de6b5d8c300e7415, branch release/v0.3.0-rc1. M3 branches contain separate voice experiments. GitHub issues are disabled. No open PR was listed at audit start.

The baseline passed Linux CI run 45557317914. Historical Desktop and Gaming Mode evidence, retry digests, reload behavior and compositor samples are in m2-steamdeck-hardware.md. Current SSH verified the same kernel over Tailscale with the previously trusted host key.

The npm audit identified a high-severity Rollup build-time advisory and moderate transitive glob/minimatch findings. Update Rollup and rerun build, packaging and Linux tests. Keep the legacy CLI version independent of the Decky package.

Approval gates include both suites, loader ZIP installation, upgrade preserving settings and catalog, removal preserving user data, restart persistence, recovery, artifact checksums, and independent review. Physical storage interruption requires a disposable medium. Historical runs alone cannot close candidate lifecycle gates.

## Candidate evidence, November 26

TypeScript, all four frontend tests and the Rollup build passed. The packaged entry point and three Python fallbacks passed on the physical Deck. A temporary EmuDeck fixture completed a 24,592-byte loopback install and blocked a duplicate. SHA-256 was 02ad100b04e699cc050733affe8b75030be62d7b23f1116515080ed8aac89f64. The extracted runtime directory measured 226,015 bytes using du -sb. No live plugin was replaced. See the PR checks for Linux suite results.

## Release notes and independent review

0.3.0-rc1 carries the hardware-tested M2 implementation forward from Decky package 0.2.5. It updates the build-time Rollup dependency. The companion ZIP now preserves repository layout so a recipient can build the runtime with the documented commands. CI supplies SHA256SUMS alongside the archives.

One fresh 8 MiB loopback run in temporary Deck storage took 0.059 s (134.76 MiB/s), including the fixture server. CPU time was 0.064 s, sampled RSS rose from 29,827,072 to 33,345,536 bytes, search RPC took 2.56 ms, median progress RPC took 0.393 ms, and idle CPU used 0.11 ms over one second with no idle worker. SteamOS 3.9.5 and an active loader were verified. No gamescope process was present.

Independent review of 3b181a5 scored 76/100 and recommended NO-GO. Its source archive layout finding prompted the packaging correction. Live loader installation, upgrade, restart, removal and preservation checks remain outstanding. See decky/README.md for the compatibility matrix and docs/m2-verification.md for recovery limitations.
