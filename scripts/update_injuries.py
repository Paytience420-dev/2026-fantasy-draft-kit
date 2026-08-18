#!/usr/bin/env python3
"""Refresh structured fantasy injury data without silently overwriting source ranks.

Sources:
- Sleeper public NFL players endpoint (daily metadata)
- nflverse current-season weekly injury/practice reports
- Optional short-lived verified overrides in data/injury-overrides.json

The output keeps source rankings untouched. `rank_penalty` is only consumed by the
site's optional health-adjusted overlay, and `adjust_rank=false` prevents an
uncertain or resolved row from moving anyone automatically.
"""
from __future__ import annotations

import csv
import io
import json
import re
import urllib.error
import urllib.request
from datetime import datetime, timezone, date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
OUT = DATA_DIR / "injuries.json"
OVERRIDES = DATA_DIR / "injury-overrides.json"
SEASON = 2026
SLEEPER_URL = "https://api.sleeper.app/v1/players/nfl?active=true"
NFLVERSE_URL = f"https://github.com/nflverse/nflverse-data/releases/download/injuries/injuries_{SEASON}.csv"
FANTASY_POSITIONS = {"QB", "RB", "WR", "TE", "K"}


def norm_name(value: str) -> str:
    value = re.sub(r"[^a-z0-9]", "", (value or "").lower())
    return re.sub(r"(jr|sr|ii|iii|iv)$", "", value)


def request(url: str, timeout: int = 45) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "2026-fantasy-draft-kit/1.1"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read()


def load_json(path: Path, fallback: Any) -> Any:
    try:
        return json.loads(path.read_text())
    except Exception:
        return fallback


def severity(status: str, injury: str, practice: str, notes: str = "") -> int:
    """Return current severity, prioritizing current status over historical notes.

    0 resolved, 1 improving, 2 monitor, 3 medium, 4 multi-week/high,
    5 out/surgical, 6 reserve/season-ending.
    """
    status_l = (status or "").strip().lower()
    practice_l = (practice or "").strip().lower()
    injury_l = (injury or "").strip().lower()
    notes_l = (notes or "").strip().lower()

    # Current official designations beat older descriptive text.
    if re.search(r"injured reserve|\bir\b|\bpup\b|\bnfi\b|season.?ending|out for season", status_l):
        return 6
    if re.search(r"^out$|will not play|ruled out", status_l):
        return 5
    if re.search(r"doubtful", status_l):
        return 4
    if re.search(r"questionable", status_l):
        return 3

    # Clear/full practice is resolved even when notes explain the prior injury.
    if re.search(r"cleared|good to go|healthy|no injury designation|will play", status_l) or re.search(r"full participation|full practice", practice_l):
        return 0
    if re.search(r"improving|returning|ramping up", status_l):
        return 1

    current_text = f"{injury_l} {notes_l} {practice_l}"
    if re.search(r"season.?ending|out for season|surgery scheduled|underwent surgery", current_text):
        return 6
    if re.search(r"surgery (?:is |remains )?(?:possible|recommended)|expected to miss (?:the )?season", current_text):
        return 5
    if re.search(r"high.?ankle|week.?to.?week|no timetable|miss (?:the )?(?:start|beginning)|multi.?week", current_text):
        return 4
    if re.search(r"did not participate|hamstring|groin|ankle|toe|knee|calf|foot|limited", current_text):
        return 3
    if re.search(r"snap count|tightness|managed workload|monitor", current_text):
        return 2
    return 2


def impact_and_penalty(status: str, injury: str, practice: str, notes: str = "") -> tuple[str, int]:
    level = severity(status, injury, practice, notes)
    impact = {6: "High", 5: "High", 4: "High", 3: "Medium", 2: "Low", 1: "Low", 0: "Low"}[level]
    penalty = {6: 45, 5: 24, 4: 14, 3: 5, 2: 2, 1: 0, 0: 0}[level]
    return impact, penalty


def infer_adjust_rank(status: str, injury: str, practice: str, notes: str, source: str) -> bool:
    level = severity(status, injury, practice, notes)
    if level <= 1:
        return False
    status_l = (status or "").lower()
    source_l = (source or "").lower()
    if "nflverse" in source_l:
        return level >= 3
    if re.search(r"injured reserve|\bir\b|\bpup\b|\bnfi\b|out|doubtful|questionable", status_l):
        return True
    # Sleeper's offseason feed can lag known camp injuries. Generic monitor rows
    # stay review-only unless a verified override explicitly enables movement.
    if "sleeper" in source_l:
        return False
    return level >= 4


def sleeper_rows() -> tuple[list[dict[str, Any]], str]:
    try:
        payload = json.loads(request(SLEEPER_URL))
    except Exception as exc:
        return [], f"error: {exc}"
    rows = []
    for sleeper_id, player in payload.items():
        pos = player.get("position") or ""
        if pos not in FANTASY_POSITIONS:
            continue
        status = player.get("injury_status") or player.get("status") or ""
        injury = player.get("injury_notes") or ""
        practice = player.get("practice_participation") or ""
        start = player.get("injury_start_date") or ""
        if not any((player.get("injury_status"), injury, practice, start)) and not re.search(r"injur|reserve|pup|nfi", status, re.I):
            continue
        name = player.get("full_name") or f"{player.get('first_name','')} {player.get('last_name','')}".strip()
        notes = injury or "Sleeper lists an active injury or availability designation."
        impact, penalty = impact_and_penalty(status, injury, practice, notes)
        rows.append({
            "name": name,
            "team": player.get("team") or "",
            "pos": pos,
            "status": status or "Monitor",
            "injury": injury or "Availability concern",
            "notes": notes,
            "practice": practice or "Not reported",
            "impact": impact,
            "rank_penalty": penalty,
            "adjust_rank": infer_adjust_rank(status, injury, practice, notes, "Sleeper"),
            "injury_start_date": start,
            "source": "Sleeper",
            "source_url": "https://docs.sleeper.com/",
            "source_kind": "structured metadata",
            "sleeper_id": sleeper_id,
            "_priority": 1,
        })
    return rows, "ok"


def nflverse_rows() -> tuple[list[dict[str, Any]], str]:
    try:
        raw = request(NFLVERSE_URL)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return [], "not published for current season yet"
        return [], f"error: HTTP {exc.code}"
    except Exception as exc:
        return [], f"error: {exc}"
    text = raw.decode("utf-8", errors="replace")
    records = list(csv.DictReader(io.StringIO(text)))
    latest: dict[str, dict[str, str]] = {}
    for row in records:
        pos = row.get("position") or ""
        if pos not in FANTASY_POSITIONS:
            continue
        key = norm_name(row.get("full_name") or "")
        if not key:
            continue
        sort_key = (int(row.get("week") or 0), row.get("date_modified") or "")
        prior = latest.get(key)
        if prior is None or sort_key > (int(prior.get("week") or 0), prior.get("date_modified") or ""):
            latest[key] = row
    out = []
    for row in latest.values():
        status = row.get("report_status") or ""
        injury = row.get("report_primary_injury") or row.get("practice_primary_injury") or ""
        practice = row.get("practice_status") or ""
        if not any((status, injury, practice)):
            continue
        notes = "; ".join(x for x in [injury, row.get("report_secondary_injury") or "", row.get("practice_secondary_injury") or ""] if x)
        impact, penalty = impact_and_penalty(status, injury, practice, notes)
        out.append({
            "name": row.get("full_name") or "",
            "team": row.get("team") or "",
            "pos": row.get("position") or "",
            "status": status or "Monitor",
            "injury": injury or "Availability concern",
            "notes": notes or "Official weekly injury report entry.",
            "practice": practice or "Not reported",
            "impact": impact,
            "rank_penalty": penalty,
            "adjust_rank": infer_adjust_rank(status, injury, practice, notes, "nflverse weekly report"),
            "week": row.get("week"),
            "updated_at": row.get("date_modified") or "",
            "source": "nflverse weekly report",
            "source_url": "https://nflreadr.nflverse.com/reference/load_injuries.html",
            "source_kind": "weekly official report dataset",
            "_priority": 2,
        })
    return out, "ok" if out else "current file has no fantasy-position rows"


def active_overrides() -> list[dict[str, Any]]:
    data = load_json(OVERRIDES, {"players": {}})
    today = date.today()
    rows = []
    for _, row in (data.get("players") or {}).items():
        expiry = row.get("expires_at")
        if expiry:
            try:
                if date.fromisoformat(expiry) < today:
                    continue
            except ValueError:
                pass
        rows.append({
            **row,
            "source": row.get("source") or "Manual verified override",
            "source_kind": row.get("source_kind") or "verified editorial override",
            "manual": True,
            "_priority": 3,
        })
    return rows


def merge_rows(*groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for rows in groups:
        for row in rows:
            key = norm_name(row.get("name") or "")
            if not key:
                continue
            row = dict(row)
            if key not in merged:
                merged[key] = row
                continue
            current = merged[key]
            current_priority = int(current.get("_priority") or 0)
            row_priority = int(row.get("_priority") or 0)
            # Higher-priority current status wins. Sources and context are retained.
            if row_priority >= current_priority:
                for field in (
                    "name", "team", "pos", "status", "injury", "practice",
                    "updated_at", "source_url", "source_kind", "adjust_rank",
                    "rank_penalty", "impact", "expires_at", "manual"
                ):
                    if field in row and row.get(field) not in (None, ""):
                        current[field] = row[field]
                current["_priority"] = row_priority
            notes = [current.get("notes") or "", row.get("notes") or ""]
            current["notes"] = " ".join(dict.fromkeys(x.strip() for x in notes if x.strip()))
            current["source"] = " + ".join(dict.fromkeys(x for x in [current.get("source"), row.get("source")] if x))
    return list(merged.values())


def change_label(new: dict[str, Any], old: dict[str, Any] | None) -> str:
    if old is None:
        return "new"
    new_sev = severity(new.get("status", ""), new.get("injury", ""), new.get("practice", ""), new.get("notes", ""))
    old_sev = severity(old.get("status", ""), old.get("injury", ""), old.get("practice", ""), old.get("notes", ""))
    if new_sev > old_sev:
        return "worse"
    if new_sev < old_sev:
        return "improved"
    fields = ("status", "injury", "practice", "notes", "adjust_rank", "rank_penalty")
    return "updated" if any((new.get(f) or "") != (old.get(f) or "") for f in fields) else "unchanged"


def main() -> None:
    old_payload = load_json(OUT, {"players": []})
    old = {norm_name(x.get("name") or ""): x for x in old_payload.get("players", [])}
    sleeper, sleeper_health = sleeper_rows()
    nflverse, nflverse_health = nflverse_rows()
    overrides = active_overrides()
    rows = merge_rows(sleeper, nflverse, overrides)
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    live_source_ok = sleeper_health == "ok" or nflverse_health == "ok"
    preserved_stale_snapshot = False
    if not rows and not live_source_ok and old_payload.get("players"):
        rows = [dict(x) for x in old_payload.get("players", [])]
        preserved_stale_snapshot = True
    for row in rows:
        computed_impact, computed_penalty = impact_and_penalty(
            row.get("status", ""), row.get("injury", ""), row.get("practice", ""), row.get("notes", "")
        )
        is_manual = bool(row.get("manual"))
        row["impact"] = row.get("impact") if is_manual and row.get("impact") else computed_impact
        row["rank_penalty"] = int(row.get("rank_penalty")) if is_manual and row.get("rank_penalty") is not None else computed_penalty
        if row.get("adjust_rank") is None:
            row["adjust_rank"] = infer_adjust_rank(
                row.get("status", ""), row.get("injury", ""), row.get("practice", ""), row.get("notes", ""), row.get("source", "")
            )
        row["updated_at"] = row.get("updated_at") or now
        row["change"] = change_label(row, old.get(norm_name(row.get("name") or "")))
        row["review_required"] = bool(row.get("rank_penalty", 0) and not row.get("adjust_rank"))
        row.pop("_priority", None)
    rows.sort(key=lambda x: (not bool(x.get("adjust_rank")), -int(x.get("rank_penalty") or 0), x.get("name") or ""))
    payload = {
        "generated_at": old_payload.get("generated_at") if preserved_stale_snapshot else now,
        "last_attempt_at": now,
        "preserved_stale_snapshot": preserved_stale_snapshot,
        "season": SEASON,
        "refresh_cadence": "daily",
        "method": "Source ranks remain visible. Only confirmed or explicitly verified rows move the optional health-adjusted layer; resolved and ambiguous offseason rows remain review-only.",
        "sources": ["Sleeper public NFL players endpoint", "nflverse weekly injury reports", "Short-lived verified overrides"],
        "source_health": {"sleeper": sleeper_health, "nflverse": nflverse_health, "verified_overrides": len(overrides)},
        "players": rows,
    }
    OUT.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"Wrote {len(rows)} injury rows to {OUT}")


if __name__ == "__main__":
    main()
