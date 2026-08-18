# 2026 Fantasy Football Draft Kit

A static, shareable 12-team full-PPR redraft application built around Fantasy Footballers analysis, a multi-source community consensus, tier drop-offs, draft-slot timing, strength of schedule, official bye-week conflict planning, movement signals, favorites, heat maps, sleepers, busts, and late-round targets.

## Data lenses

- **Ballers** — exact positional ranks and player analysis from supplied Fantasy Footballers videos/transcripts.
- **Community** — supplied PPR tier board, RotoWire PPR consensus, supplied Top 72, Pitcher List, FantasyPros/Boris public signals, and Sharp public schedule context.
- **Blend 1.5×** — Ballers signal receives 1.5 times the weight of community consensus. Players without Ballers coverage remain community-only.

## Local use

Open `index.html` directly in a browser. Most data is embedded and works offline. GitHub Pages serves the same file from the repository root.

## Updating

- Add verified Ballers transcripts before populating new video claims.
- Replace manual screenshot JSON files in `data/` when those boards change.
- GitHub Actions runs the public-source audit and safe public-feed updater on a schedule.
- Blocked or paywalled data is never inferred.

## Source operations

See `data/sources.json`, `data/source-audit.json`, and the in-app **Source Audits** view.


## V4 draft-day features

- **Bye Week Radar** — official 2026 NFL bye weeks, favorite/drafted-player collision heat maps, and position-specific warnings.
- **Movement signals** — rank movement persists between data refreshes; current Ballers injury and breakout direction appears immediately.
- **Favorites** — heart any player and use the same queue across tiers, the simulator, player profiles, and the bye radar.
- **Heat maps** — value/risk heat on tier lanes plus estimated availability across the user's next four snake picks.
- **Visual tier lanes** — larger lane headers, explicit tier widths, tier-cliff callouts, official bye labels, and movement chips.

The official bye map lives in `data/bye-weeks-2026.json` and is audited through the public NFL schedule-release page.


## V5 community transcript expansion

- Seven formerly pending YouTube transcripts are fully processed.
- Exact community WR1–WR50 ranking with S/A/B/C/D/E tier lanes.
- Community conviction layer: all-in RBs, every-league targets, shock picks, and price-based avoids.
- Preseason starter-snap and opportunity movement with conflict badges.
- Kicker tiers, DST rankings, and early streaming plans.
- Community rankings use the exact WR list as a 1.0x positional source and cap promotional player-take adjustments.
- Blend remains Fantasy Footballers 1.5x versus Community 1.0x.

## Pending spreadsheet

The supplied multi-tab Google Sheet link is logged but not imported because this build environment had no connected Google Drive mount or downloadable spreadsheet bytes. Upload an XLSX/CSV export to import every tab without guessing.


## V6 hero and injury operations

- Editorial, image-like hero with the exact headline **2026 FANTASY FOOTBALL DRAFT KIT** and in-hero Ballers / Community / Blend filtering.
- Dedicated Injury Center with source status, practice participation, change tracking, and transparent health-adjusted rankings.
- `scripts/update_injuries.py` refreshes Sleeper once daily and merges nflverse weekly injury/practice reports when available.
- Source ranks are retained. Injury movement is a separate provisional layer that can be turned off in the app.
- Resolved/full-practice items never receive an automatic penalty. Ambiguous offseason metadata stays review-only unless a verified override enables movement.
- Manual overrides are supported through `data/injury-overrides.json`, use explicit `adjust_rank` controls, and expire automatically to prevent stale context from persisting.

## V7 draft-slot playbooks

The My Draft Slot view now includes source-grounded playbooks for picks 1.01 through 1.10 from the user-provided `2026 Fantasy Football Research` document. Each playbook adds:

- opening strategy and ideal first-pick framework
- round-by-round construction guidance
- target chips with current market timing and injury flags
- roster checkpoints, position-run radar, bye/stack warnings, and fall values
- a clear pending state for 1.11 and 1.12 because those sections were not yet present in the source

The source strategy remains separate from live ADP, injury, movement, Community, and Fantasy Footballers layers.

### V7 source boundary

The uploaded draft-position document is treated as a strategy overlay, not a ranking source. Slots 1.01–1.10 are implemented directly; 1.11 and 1.12 remain explicitly pending because the source does not yet contain those sections.
