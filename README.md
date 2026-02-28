# 🏏 CricBazaar — Cricket Auction Planning App

**CricBazaar** is a feature-rich **Streamlit** web app for planning and tracking cricket auctions in real-time. Built for tournament organizers and team owners who want to strategize, bid smartly, and build the best squad within budget.

> 🏆 *Currently configured for the **Founder's Cup** tournament — easily adaptable to any cricket auction format.*

---

## 📸 Features at a Glance

| Feature | Description |
|---------|-------------|
| ⚡ **Live Auction Tracker** | Record player sales in real-time — select player, team, and price |
| 📊 **Team Dashboard** | Budget remaining, squad composition, role & tier breakdown per team |
| 📋 **Player Pool** | Filterable view of all 44 players with ratings, tiers, and sale status |
| 🏆 **Strategy Console** | Personal war-room for Abhijeet — recommended targets, need analysis |
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
| 🎳 Bowling | 35% | Bowling ability |
| 🧤 Fielding | 25% | Fielding ability |

**Overall Rating** = `Batting × 0.40 + Bowling × 0.35 + Fielding × 0.25`

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

---

## 🏗️ Project Structure

```
CRICKET_AUCTION_PLANNING_APP/
├── app.py              # Main Streamlit application (UI + logic)
├── players.py          # Player database, ratings, tier/role classification
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

### Step 4: Run the App

```bash
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`.

---

## 📦 Dependencies

| Package | Purpose |
|---------|---------|
| `streamlit` | Web app framework & UI |
| `pandas` | Data handling & table display |

---

## 🎮 Usage Guide

### During the Auction

1. Open the **⚡ Live Auction** tab
2. Select the player being auctioned from the dropdown
3. Choose the buying team
4. Enter the sold price
5. Click **✅ Confirm Sale**
6. The dashboard updates automatically — budget, squad, tiers

### Monitoring Teams

- Switch to **📊 Team Dashboard** to see all 4 teams at a glance
- Each team card shows: budget left, player count, role split, tier split
- Expand to see the full squad list
- **📥 Download** any team's squad as CSV

### Strategic Planning

- Use **🏆 My Strategy** tab for Abhijeet's personal war-room
- See recommended targets based on squad gaps
- Available players are sorted by tier with need indicators (🎯)

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

*CricBazaar v1.0 · March 2026*
