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

# ============ AUTO DATA FEEDS ============

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

def fetch_weather(match_keyword):
    try:
        url = "https://api.open-meteo.com/v1/forecast"
        # simplistic placeholder location
        params = {"latitude": -27.47, "longitude": 153.02, "current_weather": True}
        r = requests.get(url, params=params, timeout=10)
        j = r.json()
        rain = j.get("current_weather", {}).get("precipitation", 0)
        return rain
    except Exception:
        return 0

# ============ STORAGE ============

def load_log():
    if os.path.exists(DATA_FILE):
        return pd.read_csv(DATA_FILE)
    return pd.DataFrame(columns=[
        "date","round","match","player","odds","book",
        "my_prob","edge","stake","type","result",
        "position","team_total","status","confidence"
    ])

def save_log(df):
    df.to_csv(DATA_FILE, index=False)

# ============ MODEL ============

def implied_prob(odds):
    return round((1/float(odds))*100,2)

def weather_factor(rain):
    if rain > 5:
        return 0.90
    if rain > 1:
        return 0.96
    return 1.00

def team_total_factor(total):
    if not total:
        return 1.00
    if total >= 48: return 1.12
    if total >= 44: return 1.06
    if total >= 40: return 1.00
    if total >= 36: return 0.94
    return 0.88

def base_by_position(pos):
    return {
        "Winger":0.36,"Centre":0.27,"Back Row":0.19,
        "Half":0.12,"Hooker":0.15,"Fullback":0.23,"Bench":0.10
    }.get(pos,0.16)

def confidence_score(edge):
    raw = edge * 6
    return max(0,min(100, round(raw,1)))

def calc_probability(position, total, rain):
    p = base_by_position(position)
    p *= team_total_factor(total)
    p *= weather_factor(rain)
    return round(p*100,2)

# ============ ANALYTICS GRAPH ============

def plot_conf_vs_roi(df):
    df = df.copy()
    df = df[df["result"].isin(["Win","Loss"])]
    if df.empty:
        st.write("Not enough data for graph")
        return

    df["profit"] = df.apply(lambda r: (float(r["odds"])-1)*10 if r["result"]=="Win" else -10, axis=1)

    grouped = df.groupby("confidence").agg({"profit":"mean"}).reset_index()

    plt.figure()
    plt.scatter(grouped["confidence"], grouped["profit"])
    plt.xlabel("Confidence")
    plt.ylabel("Avg Profit per Bet")
    st.pyplot(plt)

# ============ UI ============

st.title("🏉 Try Finder PRO – 2026 v13")

tab1, tab2 = st.tabs(["Live Evaluate","Analytics"])

with tab1:
    match = st.text_input("Match search e.g. Broncos")

    if st.button("Load Live Odds"):
        odds_df, total = fetch_live_odds(match)
        rain = fetch_weather(match)

        if odds_df.empty:
            st.warning("No markets found")
        else:
            st.info(f"Match total: {total} | Rain: {rain}mm")

            for i,row in odds_df.iterrows():
                with st.expander(f"{row['player']} – {row['book']} – {row['odds']}"):
                    position = st.selectbox("Position",
                        ["Winger","Centre","Back Row","Half","Hooker","Fullback","Bench"],
                        key=f"p{i}")

                    prob = calc_probability(position, total, rain)
                    edge = prob - implied_prob(row["odds"])
                    conf = confidence_score(edge)

                    st.write(f"Probability: {prob}%")
                    st.write(f"Edge: {round(edge,2)}%")
                    st.write(f"Confidence: {conf}/100")

with tab2:
    df = load_log()
    st.subheader("Confidence vs ROI")
    plot_conf_vs_roi(df)

st.caption("v13: live odds in screen + confidence graph + weather downgrade")
