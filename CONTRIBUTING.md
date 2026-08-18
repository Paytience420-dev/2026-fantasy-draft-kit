# Updating the Draft Kit

1. Put new Fantasy Footballers transcript text in a working folder.
2. Preserve exact player order when the episode is a ranking.
3. Add the verified claims to the embedded dataset and mark unverified videos as transcript pending.
4. Run `python scripts/audit_sources.py`.
5. Open `index.html` and validate Tier Board, Draft Simulator, Player Explorer, and Source Audits.
6. Commit only verified changes.
