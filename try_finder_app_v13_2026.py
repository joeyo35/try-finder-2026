# Try Finder PRO v14 (based on v13 stable build)
# This version maintains existing functionality while new bet365/Sportsbet collectors are finalised.

import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import os
import matplotlib.pyplot as plt

st.set_page_config(page_title="Try Finder PRO 2026", layout="centered")

DATA_FILE = "bets_log.csv"
ODDS_API_KEY = os.getenv("ODDS_API_KEY","PUT_YOUR_KEY_HERE")

SPORTS = "rugbyleague_nrl"
BOOKS = "sportsbet,bet365"

def fetch_live_odds(match_keyword):
    try:
        url = f"https://api.the-odds-api.com/v4/sports/{SPORTS}/odds"
        params = {
            "apiKey": ODDS_API_KEY,
            "regions": "au",
            "markets": "player_anytime_try,totals",
            "bookmakers": BOOKS
        }
        r = requests.get(url, params=params, timeout=12)
        data = r.json()

        rows = []
        total = None

        for game in data:
            match = f"{game['home_team']} v {game['away_team']}"
            if match_keyword.lower() not in match.lower():
                continue

            for book in game.get("bookmakers", []):
                for market in book.get("markets", []):
                    if market["key"] == "totals":
                        for o in market["outcomes"]:
                            if o["name"] == "Over":
                                total = o["point"]

                    if market["key"] == "player_anytime_try":
                        for o in market["outcomes"]:
                            rows.append({
                                "match": match,
                                "player": o["name"],
                                "odds": o["price"],
                                "book": book["title"]
                            })
        return pd.DataFrame(rows), total
    except Exception:
        return pd.DataFrame(), None

st.title("Try Finder PRO – v14")
st.write("This build keeps the stable engine while enhanced bet365 collectors are being added.")

match = st.text_input("Match search")

if st.button("Load Live Odds"):
    df, total = fetch_live_odds(match)
    if df.empty:
        st.warning("No markets found")
    else:
        st.dataframe(df)
