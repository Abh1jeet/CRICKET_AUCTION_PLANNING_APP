"""
Founder's Cup - Player Database & Tier Classification
44 total players: 4 Captains + 4 Vice-Captains (pre-assigned) + 36 Auction Pool
"""

# ── 36 Auction-pool players (sequential IDs 1-36) ────────────────────
AUCTION_PLAYERS = [
    {"id": 1,  "name": "Abhishek R",     "batting": 7, "bowling": 4, "fielding": 7},
    {"id": 2,  "name": "Nitin",          "batting": 4, "bowling": 0, "fielding": 4},
    {"id": 3,  "name": "Kohli",          "batting": 9, "bowling": 0, "fielding": 10},
    {"id": 4,  "name": "Bramesh",        "batting": 4, "bowling": 10, "fielding": 7},
    {"id": 5,  "name": "Vivek Sharma",   "batting": 7, "bowling": 0, "fielding": 5},
    {"id": 6,  "name": "Alok",           "batting": 5, "bowling": 5, "fielding": 5},
    {"id": 7,  "name": "Yadu",           "batting": 9, "bowling": 0, "fielding": 7},
    {"id": 8,  "name": "Aravinth",       "batting": 0, "bowling": 9, "fielding": 0},
    {"id": 9,  "name": "Mehul",          "batting": 5, "bowling": 7, "fielding": 2},
    {"id": 10, "name": "Ashish P",       "batting": 2, "bowling": 0, "fielding": 6},
    {"id": 11, "name": "Vikash",         "batting": 5, "bowling": 5, "fielding": 5},
    {"id": 12, "name": "Sailendra",      "batting": 7, "bowling": 4, "fielding": 8},
    {"id": 13, "name": "Vishwash",       "batting": 8, "bowling": 4, "fielding": 6},
    {"id": 14, "name": "Rajeev Kumar",   "batting": 4, "bowling": 4, "fielding": 4},
    {"id": 15, "name": "Amit",           "batting": 4, "bowling": 4, "fielding": 4},
    {"id": 16, "name": "Abhinav",        "batting": 4, "bowling": 4, "fielding": 4},
    {"id": 17, "name": "Atul",           "batting": 7, "bowling": 9, "fielding": 9},
    {"id": 18, "name": "Dillip",         "batting": 7, "bowling": 0, "fielding": 4},
    {"id": 19, "name": "Lamby",          "batting": 2, "bowling": 8, "fielding": 5},
    {"id": 20, "name": "Ashish Anand",   "batting": 5, "bowling": 0, "fielding": 7},
    {"id": 21, "name": "Aniket Bhat",    "batting": 7, "bowling": 7, "fielding": 7},
    {"id": 22, "name": "Harish",         "batting": 5, "bowling": 10, "fielding": 5},
    {"id": 23, "name": "Ankit",          "batting": 7, "bowling": 0, "fielding": 5},
    {"id": 24, "name": "Sanjeev",        "batting": 2, "bowling": 6, "fielding": 5},
    {"id": 25, "name": "Runit",          "batting": 4, "bowling": 4, "fielding": 4},
    {"id": 26, "name": "Prashant",       "batting": 5, "bowling": 5, "fielding": 5},
    {"id": 27, "name": "Dharmendra",     "batting": 5, "bowling": 0, "fielding": 5},
    {"id": 28, "name": "Abhay",          "batting": 9, "bowling": 9, "fielding": 9},
    {"id": 29, "name": "Aman",           "batting": 5, "bowling": 5, "fielding": 5},
    {"id": 30, "name": "Prakhar",        "batting": 5, "bowling": 7, "fielding": 5},
    {"id": 31, "name": "Abhi Agarwal",   "batting": 4, "bowling": 0, "fielding": 0},
    {"id": 32, "name": "Rahul",          "batting": 4, "bowling": 7, "fielding": 4},
    {"id": 33, "name": "Samit",          "batting": 5, "bowling": 0, "fielding": 5},
    {"id": 34, "name": "Kawal",          "batting": 7, "bowling": 2, "fielding": 2},
    {"id": 35, "name": "Saumil",         "batting": 0, "bowling": 7, "fielding": 0},
    {"id": 36, "name": "Yug",            "batting": 2, "bowling": 5, "fielding": 2},
]

# ── 4 Captains (IDs 37-40) — pre-assigned, always Tier 1 ────────────
CAPTAINS = [
    {"id": 37, "name": "Abhijeet",  "batting": 7, "bowling": 6, "fielding": 9, "tag": "Captain",      "team": "Abhijeet",  "forced_role": "All-rounder"},
    {"id": 38, "name": "Saurav",    "batting": 4, "bowling": 8, "fielding": 5, "tag": "Captain",      "team": "Saurav",    "forced_role": "Bowler"},
    {"id": 39, "name": "Vishal",    "batting": 8, "bowling": 0, "fielding": 7, "tag": "Captain",      "team": "Vishal",    "forced_role": "Batsman"},
    {"id": 40, "name": "Pravakar",  "batting": 6, "bowling": 10, "fielding": 8, "tag": "Captain",      "team": "Pravakar",  "forced_role": "Bowler"},
]

# ── 4 Vice-Captains / Marquee (IDs 41-44) — pre-assigned, always Tier 1
VICE_CAPTAINS = [
    {"id": 41, "name": "Vivek C",       "batting": 7, "bowling": 10, "fielding": 8, "tag": "Vice-Captain", "team": "Abhijeet",  "forced_role": "All-rounder"},
    {"id": 42, "name": "Shubham",       "batting": 10, "bowling": 5, "fielding": 10, "tag": "Vice-Captain", "team": "Saurav",    "forced_role": "Batsman"},
    {"id": 43, "name": "Aniket (VC)",   "batting": 8, "bowling": 9, "fielding": 8, "tag": "Vice-Captain", "team": "Vishal",    "forced_role": "All-rounder"},
    {"id": 44, "name": "Padam",         "batting": 7, "bowling": 10, "fielding": 6, "tag": "Vice-Captain", "team": "Pravakar",  "forced_role": "All-rounder"},
]

# ── Combined list of all 44 players ──────────────────────────────────
PLAYERS = AUCTION_PLAYERS + CAPTAINS + VICE_CAPTAINS

# ── Pre-assigned mapping (captain + vice-captain auto-belong to team) ─
PRE_ASSIGNED = {}
for _p in CAPTAINS + VICE_CAPTAINS:
    PRE_ASSIGNED[_p["id"]] = {"team": _p["team"], "tag": _p["tag"]}

# ── Teams ────────────────────────────────────────────────────────────
TEAMS = {
    "Abhijeet": {"color": "#1E90FF", "emoji": "🔵"},
    "Saurav":   {"color": "#FF4500", "emoji": "🔴"},
    "Vishal":   {"color": "#32CD32", "emoji": "🟢"},
    "Pravakar": {"color": "#FFD700", "emoji": "🟡"},
}

# ── Constants ────────────────────────────────────────────────────────
BUDGET_PER_TEAM = 100
BASE_PRICE = 5
BID_INCREMENT = 1
SQUAD_SIZE = 11                                # 2 pre-assigned + 9 auction
AUCTION_SLOTS = 9                              # slots to fill via auction
TOTAL_PLAYERS = len(PLAYERS)                   # 44
TOTAL_AUCTION_PLAYERS = len(AUCTION_PLAYERS)   # 36


# ── Classification helpers ───────────────────────────────────────────
def classify_role(player):
    """Classify player as Batsman, Bowler, or All-rounder.
    Captains/VCs use forced_role."""
    if player.get("forced_role"):
        return player["forced_role"]
    bat = player["batting"]
    bowl = player["bowling"]
    if bat >= 4 and bowl >= 4:
        return "All-rounder"
    elif bowl >= 4:
        return "Bowler"
    else:
        return "Batsman"


def compute_overall(player):
    """Weighted overall rating: Bat 40%, Bowl 35%, Field 25%."""
    return round(player["batting"] * 0.40 + player["bowling"] * 0.40 + player["fielding"] * 0.20, 1)


def classify_tier(player):
    """
    Tier classification:
      Captains & Vice-Captains → always Tier 1
      Tier 1: overall >= 7.5
      Tier 2: overall >= 5.5
      Tier 3: overall >= 3.5
      Tier 4: overall < 3.5
    """
    if player.get("tag") in ("Captain", "Vice-Captain"):
        return 1
    overall = compute_overall(player)
    if overall >= 7.5:
        return 1
    elif overall >= 5.5:
        return 2
    elif overall >= 3.5:
        return 3
    else:
        return 4


# ── Enrich all players ───────────────────────────────────────────────
for p in PLAYERS:
    p["role"] = classify_role(p)
    p["overall"] = compute_overall(p)
    p["tier"] = classify_tier(p)
