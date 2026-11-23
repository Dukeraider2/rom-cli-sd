# M2 investigation and test gates

Baseline 7af3ecd contains the M2 specification and M1's audited installer. Search will resolve files into opaque IDs. A per-user SQLite queue beside the manifest records confirmed requests and destination identity. A single on-demand worker calls the original installer with a restricted HTTP reader and progress/publication callbacks. Tests will separately exercise provider policy, queue transitions, backend request validation, UI navigation, package structure and M1 regressions.

| Target | Contract checked | Verification gate |
|---|---|---|
| Decky | Python async Plugin lifecycle, API version 1, typed callable, definePlugin and Rollup from the [official template](https://github.com/SteamDeckHomebrew/decky-plugin-template) | Build ZIP, load on actual Decky and record installed version |
| SteamOS | User home and Desktop Mode, [Valve FAQ](https://help.steampowered.com/en/faqs/view/671A-4453-E8D2-323C) | Test under the logged-in unprivileged account |
| EmuDeck | [romsPath](https://github.com/dragoonDorise/EmuDeck/blob/main/settings.sh), installed console definition | Mock settings now; SSD, custom and removable paths on device |
| RetroDECK | [paths.roms_path](https://github.com/RetroDECK/RetroDECK/blob/main/config/retrodeck/retrodeck.json), legacy cfg, per-path Flatpak probe | Mock both schemas; actual effective grants and launches on device |
| Internet Archive | [Advanced search](https://archive.org/advancedsearch.php), [item metadata](https://archive.org/developers/md-read.html) | Bounded responses and filtered file metadata; source rights confirmed by user |
| Mirror | Explicit operator-configured base directory | Test controlled HTTP directory indexes and refused off-origin requests |

Keep the M1 console allowlist, no-replace publication, final digest, recovery ledger and read-only reconciliation. Retain M1's caveats about unjournaled parts after abrupt shutdown and headerless content. No installed SteamOS, Decky or emulator version has been observed. Physical Gaming Mode, keyboard focus, launch, permissions and storage removal tests are **BLOCKED** until hardware is available.

