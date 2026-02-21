"""
Fetches MLB overall ADP from FantasyPros and saves to data/fantasypros_adp.csv

Install deps:
    pip install requests beautifulsoup4 pandas

Run:
    python scripts/fetch_fantasypros_adp.py
"""

import requests
import pandas as pd
from bs4 import BeautifulSoup

URL = "https://www.fantasypros.com/mlb/adp/overall.php"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


def fetch_fantasypros_adp(url: str = URL, out_path: str = "data/fantasypros_adp.csv") -> pd.DataFrame:
    print(f"Fetching FantasyPros ADP from {url} ...")
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    table = soup.find("table", {"id": "data"})
    if table is None:
        raise ValueError("Could not find ADP table on FantasyPros page. The page structure may have changed.")

    rows = []
    for tr in table.find("tbody").find_all("tr"):
        cols = tr.find_all("td")
        if len(cols) < 4:
            continue

        # Column layout: Rank | Player (team, pos) | Pos | AVG | ...
        player_cell = cols[1]
        name_tag = player_cell.find("a")
        if name_tag is None:
            continue
        name = name_tag.text.strip()

        # ADP is the AVG column (index 3)
        try:
            adp = float(cols[3].text.strip())
        except ValueError:
            continue

        rows.append({"Name": name, "ADP_FP": adp})

    df = pd.DataFrame(rows)
    df = df.sort_values("ADP_FP").reset_index(drop=True)
    df.to_csv(out_path, index=False)
    print(f"✓ Saved {len(df)} players to {out_path}")
    return df


if __name__ == "__main__":
    df = fetch_fantasypros_adp()
    print(df.head(20).to_string(index=False))
