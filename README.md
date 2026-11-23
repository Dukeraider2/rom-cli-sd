# rom-cli

A tiny, ani-cli-style command-line tool to **search and download legal ROMs, homebrew, and public-domain games** straight from the [Internet Archive](https://archive.org).

The interactive downloader uses the public Internet Archive API or a self-hosted mirror. The optional library commands install authorized single-file games into a configured EmuDeck or RetroDECK library and record them in SQLite. Consult the [library guide](docs/library.md), [format matrix](docs/phase1.md) and [verification report](docs/verification.md).

```
search → fzf menu → pick item → pick file(s) → aria2 download → done
```

## Features

- 🔎 Fuzzy search via `fzf`, just like ani-cli
- 📦 Multi-file selection within an archive item (`TAB` to mark)
- Parallel transfers via `aria2` into private staging
- 🧩 Configurable collections — point it at any IA collection you like
- Bash search and download workflow, plus Python standard-library catalog commands

## Dependencies

- `curl`
- `jq`
- `fzf`
- `aria2`

Library commands use Python 3.9+ with SQLite and Linux procfs. They work independently of the interactive downloader dependencies.

## Install

### SteamOS Desktop Mode

```bash
git clone --branch feature/emudeck-retrodeck-integration https://github.com/Dukeraider2/rom-cli-sd.git
cd rom-cli-sd
./rom-cli --library platforms
```

To make the checkout available on your user PATH, link the launcher. Keep the checkout in place.

```bash
mkdir -p ~/.local/bin
ln -s "$PWD/rom-cli" ~/.local/bin/rom-cli
```

## Usage

```bash
rom-cli                       # interactive: prompts for a search term
rom-cli homebrew snes         # search directly
rom-cli -c opensource_media doom
rom-cli --help
```

### Options

| Option | Description | Default |
|--------|-------------|---------|
| `-d, --download-dir DIR` | Download target | `~/Downloads/roms` |
| `-c, --collection LIST` | `;`-separated IA collections to search | `open_source_software;softwarelibrary_misc;homebrew` |
| `-n, --results N` | Number of search results | `50` |
| `-x, --connections N` | Parallel connections per download | `8` |
| `-V, --version` | Print version | |
| `-h, --help` | Show help | |

### Environment variables

All options have matching env vars: `ROM_CLI_DOWNLOAD_DIR`, `ROM_CLI_COLLECTIONS`, `ROM_CLI_RESULTS`, `ROM_CLI_CONNECTIONS`.

## Self-hosted mirror

`rom-cli` can also browse **your own HTTP file server** instead of the Internet Archive — handy for pulling your personal dumps of games you own onto a Steam Deck or handheld without USB shuffling:

```bash
rom-cli -m https://example.com/roms zelda
```

See [MIRROR.md](MIRROR.md) for full setup (nginx autoindex, FileBrowser, Tailscale/Cloudflare for remote access).

## Finding collections

Browse [archive.org](https://archive.org) and look at the URL of a collection page — the part after `/details/` is the collection id you pass to `-c`. Good legal starting points: homebrew scenes, public-domain software libraries, and openly-licensed game collections.

## Legal note

rom-cli is intended for **freely distributable** content only — homebrew, public domain, and openly-licensed material. Please respect copyright; don't point it at collections you don't have the right to download.

## License

GPL-3.0
