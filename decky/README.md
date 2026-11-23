# Decky backend milestone

The current backend runs one requested operation and exits. The library CLI is available without a plugin. Build the prototype against named methods and version its response schema before exposing it to Gaming Mode. Use the [official template](https://github.com/SteamDeckHomebrew/decky-plugin-template) for frontend calls and backend events.

| Method | Inputs and returned information | Implementation |
|---|---|---|
| list_platforms / list_consoles | Suite enum, configured root, status, writable flag, allowed suffixes | Adapt platforms and consoles |
| list_games / inspect_game | Game ID, release fields and recorded installations | Adapt games and inspect, add pagination |
| reconcile | Suite, optional console, optional expected root | Read-only report available |
| search | Source ID, bounded text and page | Planned IA and configured mirror providers |
| enqueue / cancel / get_progress | Confirmed result ID, suite, console and metadata; job ID, state and byte counts | Planned worker and bounded queue. Current install is synchronous |
| duplicate decision | Existing path and checksum, cancel or select another allowed destination | Translate current duplicate errors to typed responses |

The frontend supplies enums and opaque search-result IDs. The backend resolves URLs, derives paths, enforces allowed operations and returns typed errors. Do not expose shell commands, raw SQL, filesystem browsing, user-supplied URLs or an arbitrary CLI argument array as a plugin RPC. Resolve the unprivileged SteamOS user explicitly before writing any data. Implement progress throttling, cancellation cleanup and serialized downloads. Exercise permission, library and controller navigation on hardware before distributing a plugin.

A later optional voice method accepts push-to-talk audio for local transcription, then feeds text into the same search method. Release the microphone and unload idle models. Require controller confirmation of the result and destination before enqueue. Keep whisper.cpp and Piper behind optional local providers, disabled by default. Use ES-DE's existing manual scraper for artwork.

