# 🏏 CricBazaar — Cricket Auction Planning App

**CricBazaar** is a feature-rich **Streamlit** web app for planning and tracking cricket auctions in real-time. Built for tournament organizers and team owners who want to strategize, bid smartly, and build the best squad within budget.

> 🏆 *Currently configured for the **Founder's Cup** tournament — easily adaptable to any cricket auction format.*

---

## 📸 Features at a Glance

| Feature | Description |
|---------|-------------|
| ⚡ **Live Auction Tracker** | Record player sales in real-time with **live bid advisor** — see recommended max bid, predicted auction price, and which teams will compete |
| 📊 **Team Dashboard** | Budget remaining, squad composition, role & tier breakdown per team |
| 📋 **Player Pool** | Filterable view of all 44 players with ratings, tiers, and sale status |
| 🏆 **Strategy Console** | Personal war-room for Abhijeet — MILP optimizer, per-player bid recommendations, need analysis |
| 🎯 **Best Team Builder** | Real-time best possible team at every point — dream 11, realistic team (competition-adjusted), priority targets, budget allocation strategy |
| 🤖 **AI Insights (Ollama)** | Local AI-powered analysis via **Gemma3:4b** — bid advice, player comparisons, power rankings, full strategy briefs |
| 📈 **Tier Analysis** | Tier distribution across teams, spending patterns, classification guide |
| ✏️ **Edit Ratings** | Update batting/bowling/fielding ratings live — tiers auto-recalculate |
| 📥 **Download Squads** | Export any team's full squad as a CSV file |
| ↩️ **Undo & Reset** | Undo last sale or reset entire auction |

---

## 🧠 How It Works — Logic & Theory

### Player Structure (44 Total)

```
44 Players = 4 Captains + 4 Vice-Captains + 36 Auction Pool
```

| Category | Count | IDs | How Assigned |
|----------|-------|-----|-------------|
| Auction Players | 36 | 1–36 | Sold via live auction bidding |
| Captains | 4 | 37–40 | Pre-assigned to teams (1 per team) |
| Vice-Captains | 4 | 41–44 | Pre-assigned to teams (1 per team) |

### Team Composition

Each of the **4 teams** ends up with **11 players**:
- **2 Fixed** — Captain + Vice-Captain (pre-assigned, no cost)
- **9 Auction** — Bought during the live auction within budget

### Auction Rules

| Rule | Value |
|------|-------|
| Budget per team | ₹100 Lakhs |
| Base price per player | ₹5L |
| Bid increment | ₹1L |
| Auction slots per team | 9 |
| Max affordable bid | `Remaining Budget - (Slots Left - 1) × Base Price` |

> The **max affordable** formula ensures a team always has enough budget left to fill remaining slots at base price.

### Player Rating System

Each player has three ratings (0–10 scale):

| Rating | Weight | Description |
|--------|--------|-------------|
| 🏏 Batting | 40% | Batting ability |
| 🎳 Bowling | 40% | Bowling ability |
| 🧤 Fielding | 20% | Fielding ability |

**Overall Rating** = `Batting × 0.40 + Bowling × 0.40 + Fielding × 0.2`

### Role Classification

| Role | Condition |
|------|-----------|
| All-rounder | Batting ≥ 4 **AND** Bowling ≥ 4 |
| Bowler | Bowling ≥ 4 (but Batting < 4) |
| Batsman | Everything else |

> Captains & Vice-Captains have a **forced role** that overrides this logic.

### Tier Classification

| Tier | Condition | Strategy |
|------|-----------|----------|
| 🥇 Tier 1 | Overall ≥ 7.5 **or** Captain/VC | Elite — bid aggressively |
| 🥈 Tier 2 | Overall ≥ 5.5 | Strong — solid value picks |
| 🥉 Tier 3 | Overall ≥ 3.5 | Decent — fill squad gaps |
| 🏷️ Tier 4 | Overall < 3.5 | Budget — pick at base price |

> **Captains & Vice-Captains are always Tier 1** regardless of their computed overall rating.

### 🧠 MILP Optimizer — Mathematically Optimal Squad

The app uses **Mixed Integer Linear Programming** (via `scipy.optimize.linprog` with integrality constraints) to find the mathematically best set of players Abhijeet should target.

**How it works:**
- **Decision variables:** Binary (0 or 1) for each unsold player — pick or skip
- **Objective:** Maximize total squad Overall Rating
- **Constraints:**
  - Exactly `slots_left` players selected
  - Total cost ≤ remaining budget (each pick costs at least ₹5L base)
  - At least 6 players in the final 11 who can bowl (bowling ≥ 4)

The solver runs in milliseconds and guarantees the **globally optimal solution**.

### 💰 Bid Recommendation System

For each player, the system calculates a **recommended maximum bid** using:

```
Max Bid = Base Price + (Marginal Value × 1.5) + Need Premium + Tier Bonus
```

| Component | What It Measures |
|-----------|------------------|
| **Marginal Value** | MILP solves your best team *with* and *without* this player. The OVR difference = marginal value |
| **Need Premium** | Extra value if the player fills a squad gap (e.g., you need bowlers and this player bowls) |
| **Tier Bonus** | Premium for elite players: Tier 1 = +8, Tier 2 = +4, Tier 3 = +1, Tier 4 = 0 |
| **Hard Cap** | Absolute max you *could* bid while still filling remaining slots at base price |

**Verdicts:**

| Verdict | Meaning |
|---------|---------|
| 🟢 **MUST BUY** | Marginal value ≥ 3.0 — this player significantly boosts your team |
| 🟡 **GOOD BUY** | Marginal value ≥ 1.0 — solid addition, worth paying above base price |
| 🟡 **NEED-BASED BUY** | Low marginal value but fills a role gap your squad needs |
| 🟡 **BOWLING NEED** | You need bowling options and this player can bowl |
| 🔴 **SKIP / BASE ONLY** | Limited value — only buy at base price if slots need filling |

**Example card explained:**

```
🟡 GOOD BUY
💰 Recommended Max Bid: ₹14L (Hard cap: ₹54L)
📊 Marginal Value: +1.3 OVR | Need Premium: 3.5 | Tier Bonus: 4
📈 Without: 48.4 OVR → With: 49.7 OVR
```

- **₹14L** = The smart maximum. Going above means overpaying.
- **₹54L** = You *could* bid this much (budget math allows it), but you shouldn't.
- **+1.3 OVR** = Adding this player improves your best possible team by 1.3 overall rating points.
- **48.4 → 49.7** = Your best team without them vs. with them.

### 🏟️ Competitive Bidding Engine

Other teams also bid! The system predicts competition by analyzing each rival team's:

| Factor | How It's Used |
|--------|---------------|
| **Role needs** | If a team needs bowlers and this player bowls → high desire |
| **Bowling scarcity** | If few bowling options remain in the pool → premium |
| **Player tier** | All teams want Tier 1 stars → more competition |
| **Budget capacity** | Teams with more budget can bid higher |
| **Slot scarcity** | If similar players are running out → urgency |

The system outputs:
- **Predicted auction price** (what the player will likely sell for)
- **Price range** (low–high estimate)
- **Competition level** (🟢 Low / 🟡 Moderate / 🔴 Fierce)
- **Which teams** will compete and why

### 🎯 Best Team Builder (Real-Time)

At every point during the auction, the app computes:

1. **Dream 11** — Best possible squad if you get all optimal picks at base price
2. **Realistic 11** — Competition-adjusted: accounts for players other teams will likely snipe
3. **Priority Targets** — Top 10 players ranked by `expected_value = quality × acquisition_probability`
4. **Budget Allocation** — How to split remaining budget: spend big on priority picks, save base price for fillers

### 🤖 AI Insights (Ollama + Gemma3:4b)

The app integrates with **Ollama** running Google's **Gemma3:4b** model locally for natural language analysis:

| AI Feature | What It Does |
|------------|--------------|
| **Bid Advisor** | Deep analysis of any player: should you bid? how much? who'll compete? alternatives? |
| **Player Comparison** | Head-to-head comparison of two players for your team's needs |
| **Power Rankings** | AI rates all 4 teams with strengths, weaknesses, and predictions |
| **Full Strategy Brief** | Comprehensive auction strategy: targets, budget plan, threats, backup plans |
| **Live Quick Insight** | Fast 3-line advice during live auction (bid/skip, why, watch out for) |

The AI receives **full context** — your squad, needs, budget, all teams' squads, unsold pool — so its advice is data-driven, not generic.

---

## 🏗️ Project Structure

```
CRICKET_AUCTION_PLANNING_APP/
├── app.py              # Main Streamlit application (8 tabs, full UI)
├── players.py          # Player database, ratings, tier/role classification
├── optimizer.py        # MILP solver, competitive bidding engine, best team builder
├── ai_insights.py      # Ollama/Gemma3:4b AI integration for natural language insights
├── requirements.txt    # Python dependencies
└── README.md           # This file
```

---

## 🚀 Installation & Setup

### Prerequisites

- **Python 3.9+** installed
- **pip** or **uv** package manager

### Step 1: Clone the Repository

```bash
git clone https://github.com/Abh1jeet/CRICKET_AUCTION_PLANNING_APP.git
cd CRICKET_AUCTION_PLANNING_APP
```

### Step 2: Create a Virtual Environment (Recommended)

```bash
python -m venv .venv
source .venv/bin/activate        # macOS/Linux
# .venv\Scripts\activate          # Windows
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

Or using **uv** (faster):

```bash
uv pip install -r requirements.txt
```

### Step 4: Set Up Ollama for AI Insights (Optional but Recommended)

```bash
# Install Ollama (macOS)
brew install ollama

# Pull the Gemma3:4b model (~3GB)
ollama pull gemma3:4b

# Start Ollama (keep this running in a separate terminal)
ollama serve
```

> The app works fully without Ollama — the MILP optimizer and competitive bidding engine run independently. Ollama adds natural language AI insights on top.

### Step 5: Run the App

```bash
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`.

---

## 📦 Dependencies

| Package | Purpose |
|---------|--------|
| `streamlit` | Web app framework & UI |
| `pandas` | Data handling & table display |
| `scipy` | MILP solver for optimal squad selection |
| `requests` | Communication with Ollama API |
| `numpy` | Numerical operations for optimizer |

---

## 🎮 Usage Guide

### During the Auction

1. Open the **⚡ Live Auction** tab
2. Select the player being auctioned from the dropdown
3. **Check the Live Bid Advisor** panel that appears:
   - 🎯 Optimizer verdict & recommended max bid
   - 📊 Predicted auction price range
   - 🏟️ Which teams will compete and why
   - 🤖 Click "Get AI Quick Insight" for instant Gemma3 advice
4. Choose the buying team & enter the sold price
5. Click **✅ Confirm Sale**
6. The dashboard, best team builder, and recommendations all update automatically

### Building the Best Team

- Open **🎯 Best Team Builder** to see your optimal squad at any point
- **Dream 11** — mathematically best team if you get all targets
- **Realistic 11** — adjusted for competition from other teams
- **Priority Targets** — top 10 players ranked by expected value
- **Budget Allocation** — how to spread money across remaining slots

### AI-Powered Analysis

- Open **🤖 AI Insights** for natural language analysis powered by Gemma3:4b
- **Bid Advisor** — select any player for deep AI bid analysis
- **Player Comparison** — compare two players head-to-head for your needs
- **Power Rankings** — AI rates all 4 teams with predictions
- **Full Strategy Brief** — comprehensive auction game plan

### Monitoring Teams

- Switch to **📊 Team Dashboard** to see all 4 teams at a glance
- Each team card shows: budget left, player count, role split, tier split
- Expand to see the full squad list
- **📥 Download** any team's squad as CSV

### Strategic Planning

- Use **🏆 My Strategy** tab for Abhijeet's personal war-room
- MILP solver shows the mathematically optimal 9 picks
- Per-player recommendation table with verdict, max bid, and score
- Detailed analysis card for any selected player

### Adjusting Ratings

- Go to **✏️ Edit Ratings** to update any player's batting/bowling/fielding
- Tier and role auto-recalculate on save
- Use bulk edit (table) or quick edit (sliders) mode

---

## 🔧 Customization

To adapt CricBazaar for a different tournament:

1. **Edit `players.py`**:
   - Update `AUCTION_PLAYERS` list with your player names & ratings
   - Update `CAPTAINS` and `VICE_CAPTAINS` with team leaders
   - Adjust `BUDGET_PER_TEAM`, `BASE_PRICE`, `SQUAD_SIZE` as needed

2. **Edit `app.py`**:
   - Update the tournament name in the subtitle
   - Modify the strategy tab owner name if different

---

## 👨‍💻 Developer

**Developed with ❤️ by Abhijeet**

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Abhijeet-0A66C2?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/abh1jeet/)
[![GitHub](https://img.shields.io/badge/GitHub-Repo-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/Abh1jeet/CRICKET_AUCTION_PLANNING_APP)

---

## 📄 License

This project is open-source. Feel free to fork, modify, and use it for your own cricket auctions!

---

*CricBazaar v2.0 · March 2026*
