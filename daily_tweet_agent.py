#!/usr/bin/env python3

import os
import json
import requests
from datetime import datetime
from pathlib import Path
from html.parser import HTMLParser

# AI
from groq import Groq

# Google Sheets
import gspread
from google.oauth2.service_account import Credentials

# ENV
from dotenv import load_dotenv
load_dotenv()

# ─── CONFIG ─────────────────────────────────────────────

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
MODEL = "llama-3.3-70b-versatile"

TODAY = datetime.now().strftime("%Y-%m-%d")

# Google Sheets
SHEET_NAME = "tweet agent"
CREDS_FILE = "google_creds.json"
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# ─── GROQ ─────────────────────────────────────────────

def ask_groq(prompt, expect_json=False):
    client = Groq(api_key=GROQ_API_KEY)

    res = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "You are a viral Twitter expert."},
            {"role": "user", "content": prompt}
        ]
    )

    text = res.choices[0].message.content.strip()

    if expect_json:
        text = text.replace("```json", "").replace("```", "")
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1:
            text = text[start:end+1]

    return text

# ─── GOOGLE SHEETS ─────────────────────────────────────

def init_sheet():
    creds = Credentials.from_service_account_file(CREDS_FILE, scopes=SCOPES)
    client = gspread.authorize(creds)
    sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/1bO_6zZ-Ftf6Hc0KAmTZfGLuCxfkuVAFJkFVlYGUw_xQ/edit?gid=0#gid=0").sheet1

    headers = [
        "date", "tweet", "status", "approved",
        "likes", "retweets", "replies", "impressions", "score"
    ]

    if sheet.row_values(1) != headers:
        sheet.clear()
        sheet.append_row(headers)

    return sheet


def save_tweets(sheet, tweets):
    rows = []

    for t in tweets:
        rows.append([
            TODAY,
            t["text"],
            "draft",
            "no",
            "", "", "", "", ""
        ])

    sheet.append_rows(rows)
    print(f"✅ Saved {len(rows)} tweets to Google Sheets")


def get_top_tweets(sheet):
    data = sheet.get_all_records()
    scored = [r for r in data if r.get("score") not in ("", None)]

    scored.sort(key=lambda x: float(x.get("score", 0)), reverse=True)
    return scored[:5]


def learning_context(sheet):
    top = get_top_tweets(sheet)

    if not top:
        return ""

    lines = [f"- {t['tweet']} (score: {t['score']})" for t in top]
    return "Top performing tweets:\n" + "\n".join(lines)

# ─── TRENDS ────────────────────────────────────────────

def fetch_trends():
    print("📡 Fetching trends...")

    try:
        r = requests.get("https://trends24.in/united-states/")
        return ["AI", "Startups", "Finance","IPO","Stock Market","Nifty","Sensex", "Crypto", "Productivity"]
    except:
        return ["AI", "Tech", "Startups"]

# ─── ANALYSIS ──────────────────────────────────────────

def analyze(trends):
    prompt = f"""
Trends: {trends}

What content works today?

Return JSON:
{{
 "tone": "...",
 "angle": "..."
}}
"""

    raw = ask_groq(prompt, expect_json=True)
    return json.loads(raw)

# ─── GENERATE ──────────────────────────────────────────

def generate(analysis, trends, memory):
    prompt = f"""
{memory}

Trends: {trends}
Tone: {analysis.get("tone")}

Write 3 viral tweets.

Return JSON:
{{
 "tweets": [
   {{"text": "..."}},
   {{"text": "..."}},
   {{"text": "..."}}
 ]
}}
"""

    raw = ask_groq(prompt, expect_json=True)
    return json.loads(raw)

# ─── MAIN ──────────────────────────────────────────────

def main():
    print("🤖 Tweet Agent Running...\n")

    if not GROQ_API_KEY:
        print("❌ Missing GROQ_API_KEY")
        return

    sheet = init_sheet()
    memory = learning_context(sheet)

    trends = fetch_trends()
    analysis = analyze(trends)
    content = generate(analysis, trends, memory)

    if "tweets" in content:
        save_tweets(sheet, content["tweets"])

    print("\n✅ Done. Check Google Sheets.")

# ─── RUN ───────────────────────────────────────────────

if __name__ == "__main__":
    main()
