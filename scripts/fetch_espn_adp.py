"""
Fetches MLB ADP from ESPN using the draft rankings endpoint.

Run:
    python scripts/fetch_espn_adp.py
"""

import os
import json
import requests
import pandas as pd

# ESPN slot ID -> position name
SLOT_MAP = {
    0: "C", 1: "1B", 2: "2B", 3: "3B", 4: "SS",
    5: "OF", 6: "2B/SS", 7: "1B/3B", 8: "OF", 9: "OF",
    10: "DH", 11: "P", 12: "SP", 13: "RP",
    14: "BE", 15: "IL", 16: "IL", 17: "IL"
}

def fetch_espn_adp(out_path: str = "data/espn_adp.csv") -> pd.DataFrame:
    espn_s2 = os.environ.get("ESPN_S2")
    swid = os.environ.get("SWID")

    headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
    cookies = {}
    if espn_s2 and swid:
        cookies = {"espn_s2": espn_s2, "SWID": swid}
        print("Using authenticated ESPN session.")

    rows = []

    # ESPN paginates — fetch in chunks of 50 with offset
    # view=kona_player_info returns draft ranks
    base_url = "https://lm-api-reads.fantasy.espn.com/apis/v3/games/flb/seasons/2025/players"

    limit = 50
    offset = 0
    total_fetched = 0

    # We need the kona filter to get draft rank data
    filter_obj = {
        "players": {
            "filterSlotIds": {"value": [0,1,2,3,4,5,6,7,8,9,10,11,12,13]},
            "sortDraftRanks": {
                "sortPriority": 1,
                "sortAsc": True,
                "value": "STANDARD"
            },
            "limit": limit,
            "offset": offset,
            "filterRanksForScoringPeriodIds": {"value": [1]},
            "filterRanksForRankTypes": {"value": ["STANDARD"]},
            "filterRanksForSlotIds": {"value": [0,1,2,3,4,5,6,7,8,9,10,11,12,13]},
        }
    }

    print("Fetching ESPN player rankings...")

    while True:
        filter_obj["players"]["offset"] = offset
        headers["x-fantasy-filter"] = json.dumps(filter_obj)

        resp = requests.get(
            base_url,
            headers=headers,
            cookies=cookies,
            params={"view": "kona_player_info"},
            timeout=30
        )
        resp.raise_for_status()
        data = resp.json()

        players = data if isinstance(data, list) else data.get("players", [])

        if not players:
            break

        for p in players:
            try:
                name = p.get("fullName", "")
                
                # ADP lives in draftRanksByRankType
                draft_ranks = p.get("draftRanksByRankType", {})
                adp = None
                for rank_type in ["STANDARD", "PPR", "HALF"]:
                    if rank_type in draft_ranks:
                        adp = draft_ranks[rank_type].get("averageDraftPosition")
                        if adp:
                            break
                
                # Fallback: ownership percent rank
                if not adp:
                    ownership = p.get("ownership", {})
                    adp = ownership.get("averageDraftPosition") or ownership.get("auctionValueAverage")

                if name and adp and float(adp) > 0:
                    # Get position from defaultPositionId
                    pos_id = p.get("defaultPositionId", -1)
                    pos = SLOT_MAP.get(pos_id, "")
                    rows.append({"Name": name, "Position": pos, "ADP_ESPN": round(float(adp), 1)})
            except Exception as e:
                continue

        total_fetched += len(players)
        print(f"  Fetched {total_fetched} players so far...")

        if len(players) < limit:
            break

        offset += limit
        if offset > 1000:  # safety cap
            break

    if not rows:
        print("\n⚠ Still no ADP data. Dumping raw response to data/espn_raw.json")
        with open("data/espn_raw.json", "w") as f:
            json.dump(data, f, indent=2)
        print("First item sample:")
        if isinstance(data, list) and data:
            print(json.dumps(data[0], indent=2)[:1200])
        return pd.DataFrame()

    df = pd.DataFrame(rows).drop_duplicates("Name").sort_values("ADP_ESPN").reset_index(drop=True)
    df.to_csv(out_path, index=False)
    print(f"\n✓ Saved {len(df)} players to {out_path}")
    print(df.head(30).to_string(index=False))
    return df

if __name__ == "__main__":
    fetch_espn_adp()
