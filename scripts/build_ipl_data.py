import json
from datetime import datetime, timezone
from pathlib import Path
import zipfile


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw" / "ipl_json"
RAW_ZIP_FILE = PROJECT_ROOT / "data" / "raw" / "ipl_json.zip"
OUTPUT_FILE = PROJECT_ROOT / "data" / "matches.json"

TEAM_SHORT_NAMES = {
    "Chennai Super Kings": "CSK",
    "Chennai super kings": "CSK",
    "Deccan Chargers": "DCG",
    "Delhi Capitals": "DC",
    "Delhi Daredevils": "DD",
    "Gujarat Lions": "GL",
    "Gujarat Titans": "GT",
    "Kings XI Punjab": "KXIP",
    "Kochi Tuskers Kerala": "KTK",
    "Kolkata Knight Riders": "KKR",
    "Lucknow Super Giants": "LSG",
    "Mumbai Indians": "MI",
    "Pune Warriors": "PWI",
    "Punjab Kings": "PBKS",
    "Rajasthan Royals": "RR",
    "Rising Pune Supergiant": "RPS",
    "Rising Pune Supergiants": "RPS",
    "Royal Challengers Bangalore": "RCB",
    "Royal Challengers Bengaluru": "RCB",
    "Sunrisers Hyderabad": "SRH",
}


def team_short_name(team_name: str) -> str:
    return TEAM_SHORT_NAMES.get(team_name, team_name[:3].upper())


def ensure_raw_data_ready() -> None:
    if RAW_DATA_DIR.exists() and any(RAW_DATA_DIR.glob("*.json")):
        return

    if not RAW_ZIP_FILE.exists():
        raise FileNotFoundError(
            f"Could not find extracted IPL JSON files in {RAW_DATA_DIR} "
            f"or archive file at {RAW_ZIP_FILE}"
        )

    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(RAW_ZIP_FILE, "r") as archive:
        archive.extractall(RAW_DATA_DIR)


def calculate_innings_totals(innings: dict) -> dict:
    total_runs = 0
    wickets = 0
    legal_deliveries = 0

    for over in innings.get("overs", []):
        for delivery in over.get("deliveries", []):
            runs = delivery.get("runs", {})
            total_runs += runs.get("total", 0)

            extras = delivery.get("extras", {})
            legal_delivery = "wides" not in extras and "noballs" not in extras
            if legal_delivery:
                legal_deliveries += 1

            wickets += len(delivery.get("wickets", []))

    completed_overs = legal_deliveries // 6
    balls = legal_deliveries % 6
    overs = f"{completed_overs}.{balls}"

    return {
        "team": innings.get("team"),
        "shortName": team_short_name(innings.get("team", "")),
        "runs": total_runs,
        "wickets": wickets,
        "overs": overs,
    }


def build_result_text(outcome: dict) -> str:
    winner = outcome.get("winner")
    by = outcome.get("by", {})

    if "runs" in by and winner:
        return f"{winner} won by {by['runs']} runs"
    if "wickets" in by and winner:
        return f"{winner} won by {by['wickets']} wickets"
    if outcome.get("result") == "tie":
        return "Match tied"
    if outcome.get("result") == "no result":
        return "No result"
    if outcome.get("result"):
        return outcome["result"].title()
    if winner:
        return f"{winner} won"
    return "Result unavailable"


def build_match_summary(file_path: Path) -> dict:
    with file_path.open(encoding="utf-8") as handle:
        match = json.load(handle)

    info = match.get("info", {})
    outcome = info.get("outcome", {})
    event = info.get("event", {})
    teams = info.get("teams", [])
    innings = [calculate_innings_totals(item) for item in match.get("innings", [])]
    dates = info.get("dates", [])
    date_value = dates[0] if dates else None

    return {
        "id": file_path.stem,
        "date": date_value,
        "season": str(info.get("season", "")),
        "matchNumber": event.get("match_number"),
        "eventName": event.get("name", "Indian Premier League"),
        "venue": info.get("venue"),
        "city": info.get("city"),
        "teams": [
            {
                "name": team,
                "shortName": team_short_name(team),
            }
            for team in teams
        ],
        "toss": info.get("toss", {}),
        "winner": outcome.get("winner"),
        "resultText": build_result_text(outcome),
        "playerOfMatch": info.get("player_of_match", []),
        "innings": innings,
    }


def main() -> None:
    ensure_raw_data_ready()
    match_files = sorted(RAW_DATA_DIR.glob("*.json"))
    matches = [build_match_summary(path) for path in match_files]
    matches.sort(key=lambda match: match["date"] or "", reverse=True)

    seasons = sorted({match["season"] for match in matches if match["season"]})
    teams = sorted(
        {
            team["name"]
            for match in matches
            for team in match.get("teams", [])
            if team.get("name")
        }
    )

    payload = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "source": {
            "name": "Cricsheet IPL JSON archive",
            "url": "https://cricsheet.org/downloads/",
        },
        "matchCount": len(matches),
        "latestMatchDate": matches[0]["date"] if matches else None,
        "seasons": seasons,
        "teams": teams,
        "matches": matches,
    }

    OUTPUT_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {len(matches)} matches to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
