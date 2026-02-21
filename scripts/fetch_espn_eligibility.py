"""
Fetches player position eligibility from ESPN.
Uses the same authenticated session as fetch_espn_adp.py.

Run:
    python scripts/fetch_espn_eligibility.py
"""

import os
import json
import requests
import pandas as pd

URL = "https://lm-api-reads.fantasy.espn.com/apis/v3/games/flb/seasons/2025/players"

# ESPN slot ID -> position abbreviation
SLOT_MAP = {
    0:  "C",
    1:  "1B",
    2:  "2B",
    3:  "3B",
    4:  "SS",
    5:  "OF",
    6:  "MI",   # 2B/SS
    7:  "CI",   # 1B/3B
    8:  "OF",
    9:  "OF",
    10: "DH",
    11: "P",
    12: "SP",
    13: "RP",
    14: "BE",
    15: "IL",
    16: "IL",
    17: "IL",
}

# Slots we care about (ignore bench/IL/P)
VALID_SLOTS = {0, 1, 2, 3, 4, 5, 10, 12, 13}

# Primary position from defaultPositionId
DEFAULT_POS_MAP = {
    1:  "SP",
    2:  "C",
    3:  "1B",
    4:  "2B",
    5:  "3B",
    6:  "SS",
    7:  "OF",
    8:  "OF",
    9:  "OF",
    10: "DH",
    11: "SP",
    12: "RP",
}


def fetch_espn_eligibility(out_path: str = "data/espn_eligibility.csv") -> pd.DataFrame:
    espn_s2 = os.environ.get("ESPN_S2")
    swid    = os.environ.get("SWID")

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
    }
    cookies = {}
    if espn_s2 and swid:
        cookies = {"espn_s2": espn_s2, "SWID": swid}
        print("Using authenticated ESPN session.")
    else:
        print("⚠ No ESPN credentials — set ESPN_S2 and SWID env vars.")
        return pd.DataFrame()

    # Fetch all players in batches
    limit  = 50
    offset = 0
    rows   = []

    filter_obj = {
        "players": {
            "filterSlotIds": {"value": list(VALID_SLOTS)},
            "limit": limit,
            "offset": offset,
        }
    }

    print("Fetching player eligibility from ESPN...")
    while True:
        filter_obj["players"]["offset"] = offset
        headers["x-fantasy-filter"] = json.dumps(filter_obj)

        resp = requests.get(
            URL,
            headers=headers,
            cookies=cookies,
            params={"view": "players_wl"},
            timeout=30,
        )
        resp.raise_for_status()
        players = resp.json()

        if not players or not isinstance(players, list):
            break

        for p in players:
            name = p.get("fullName", "")
            if not name:
                continue

            # Primary position
            default_pos_id = p.get("defaultPositionId", -1)
            primary = DEFAULT_POS_MAP.get(default_pos_id, "")

            # All eligible slots
            eligible_slot_ids = p.get("eligibleSlots", [])
            eligible = []
            seen = set()
            for slot_id in eligible_slot_ids:
                if slot_id in VALID_SLOTS:
                    pos = SLOT_MAP.get(slot_id, "")
                    if pos and pos not in seen and pos != primary:
                        eligible.append(pos)
                        seen.add(pos)

            rows.append({
                "Name":               name,
                "Primary_Position":   primary,
                "Eligible_Positions": ",".join(eligible) if eligible else "",
            })

        print(f"  Fetched {len(rows)} players...", end="\r")

        if len(players) < limit:
            break
        offset += limit
        if offset > 2000:
            break

    print()

    if not rows:
        print("⚠ No eligibility data returned.")
        return pd.DataFrame()

    df = pd.DataFrame(rows).drop_duplicates("Name")
    df.to_csv(out_path, index=False)
    print(f"✓ Saved {len(df)} players to {out_path}")

    # Show sample of multi-position players
    multi = df[df["Eligible_Positions"] != ""].head(20)
    print("\nSample multi-position players:")
    print(multi.to_string(index=False))

    return df


if __name__ == "__main__":
    fetch_espn_eligibility()
