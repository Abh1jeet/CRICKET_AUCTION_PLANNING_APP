"""
🏏 CricBazaar — Cricket Auction Planner
Streamlit app: 44 players (4 captains + 4 VCs pre-assigned, 36 in auction).
Each team ends with 11 players (2 fixed + 9 from auction).
"""

import streamlit as st
import pandas as pd
import copy
import io
from players import (
    PLAYERS, AUCTION_PLAYERS, CAPTAINS, VICE_CAPTAINS,
    TEAMS, PRE_ASSIGNED, BUDGET_PER_TEAM, BASE_PRICE,
    BID_INCREMENT, SQUAD_SIZE, AUCTION_SLOTS,
    TOTAL_PLAYERS, TOTAL_AUCTION_PLAYERS,
    classify_role, compute_overall, classify_tier,
)
from optimizer import (
    analyze_squad_needs, solve_optimal_squad,
    recommend_max_bid, get_ranked_recommendations,
    estimate_competition, predict_auction_price,
    build_best_team_snapshot,
)
from ai_insights import (
    check_ollama_status, get_bid_advice,
    get_best_team_analysis, get_live_auction_insight,
    get_post_auction_review, get_player_comparison,
)

# ── Page config ──────────────────────────────────────────────────────
st.set_page_config(
    page_title="🏏 CricBazaar — Auction Planner",
    page_icon="🏏",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ───────────────────────────────────────────────────────
st.markdown("""
<style>
    .team-card {
        border-radius: 12px; padding: 18px; margin: 8px 0;
        color: white; text-align: center;
    }
    .metric-big { font-size: 2rem; font-weight: 800; margin: 0; }
    .metric-label { font-size: 0.85rem; opacity: 0.85; }
    .tier-1 { background: linear-gradient(135deg, #FFD700, #FFA500); color: #333; }
    .tier-2 { background: linear-gradient(135deg, #C0C0C0, #A0A0A0); color: #333; }
    .tier-3 { background: linear-gradient(135deg, #CD7F32, #A0522D); color: white; }
    .tier-4 { background: linear-gradient(135deg, #708090, #556677); color: white; }
    div[data-testid="stExpander"] { border: 1px solid #ddd; border-radius: 8px; margin-bottom: 8px; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0; padding: 8px 20px; font-weight: 600;
    }
    .captain-badge { background: #FFD700; color: #333; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 700; }
    .vc-badge { background: #C0C0C0; color: #333; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 700; }
</style>
""", unsafe_allow_html=True)

# ── Session state init ───────────────────────────────────────────────
if "auction_log" not in st.session_state:
    st.session_state.auction_log = {}   # player_id -> {"team": str, "price": int}

if "player_data" not in st.session_state:
    st.session_state.player_data = copy.deepcopy(PLAYERS)


# ── Helper functions ─────────────────────────────────────────────────
def get_pre_assigned_players(team_name):
    """Return the captain + VC pre-assigned to this team."""
    result = []
    for p in st.session_state.player_data:
        if p.get("tag") in ("Captain", "Vice-Captain") and p.get("team") == team_name:
            result.append({**p, "sold_price": 0})
    return result


def get_auction_players(team_name):
    """Return auction players bought by this team."""
    result = []
    for pid, info in st.session_state.auction_log.items():
        if info["team"] == team_name:
            player = next(p for p in st.session_state.player_data if p["id"] == pid)
            result.append({**player, "sold_price": info["price"]})
    return result


def get_full_squad(team_name):
    """All players: pre-assigned + auction bought."""
    return get_pre_assigned_players(team_name) + get_auction_players(team_name)


def get_team_budget_spent(team_name):
    return sum(info["price"] for info in st.session_state.auction_log.values() if info["team"] == team_name)


def get_team_remaining(team_name):
    return BUDGET_PER_TEAM - get_team_budget_spent(team_name)


def get_auction_count(team_name):
    """How many auction players this team bought."""
    return sum(1 for info in st.session_state.auction_log.values() if info["team"] == team_name)


def get_unsold_players():
    sold_ids = set(st.session_state.auction_log.keys())
    return [p for p in st.session_state.player_data
            if p["id"] not in sold_ids and p.get("tag") is None]


def role_count_full(team_name, role):
    return sum(1 for p in get_full_squad(team_name) if p["role"] == role)


def tier_count_full(team_name, tier):
    return sum(1 for p in get_full_squad(team_name) if p["tier"] == tier)


def max_affordable(team_name):
    """Max a team can bid = remaining - (auction_slots_left - 1) * BASE_PRICE"""
    remaining = get_team_remaining(team_name)
    slots_left = AUCTION_SLOTS - get_auction_count(team_name)
    if slots_left <= 1:
        return remaining
    return remaining - (slots_left - 1) * BASE_PRICE


def recalc_player(player):
    """Recalculate derived fields after a rating update."""
    player["role"] = classify_role(player)
    player["overall"] = compute_overall(player)
    player["tier"] = classify_tier(player)


def build_all_teams_data():
    """Build a dict of all teams' current state for optimizer & AI."""
    data = {}
    for tname in TEAMS:
        squad = get_full_squad(tname)
        data[tname] = {
            "squad": squad,
            "budget_left": get_team_remaining(tname),
            "slots_left": AUCTION_SLOTS - get_auction_count(tname),
            "budget_spent": get_team_budget_spent(tname),
        }
    return data


def build_auction_log_data():
    """Build a list of auction log entries for AI context."""
    log_data = []
    for pid, info in st.session_state.auction_log.items():
        p = next(pl for pl in st.session_state.player_data if pl["id"] == pid)
        log_data.append({
            "name": p["name"], "role": p["role"], "tier": p["tier"],
            "overall": p["overall"], "team": info["team"], "price": info["price"],
        })
    return log_data


def build_team_csv(team_name):
    """Build a CSV string for a team's full squad."""
    squad = get_full_squad(team_name)
    rows = []
    for i, p in enumerate(squad, 1):
        tag = p.get("tag", "Auction")
        rows.append({
            "#": i,
            "Name": p["name"],
            "Role": p["role"],
            "Type": tag,
            "Tier": p["tier"],
            "Batting": p["batting"],
            "Bowling": p["bowling"],
            "Fielding": p["fielding"],
            "Overall": p["overall"],
            "Price (₹L)": p.get("sold_price", 0),
        })
    df = pd.DataFrame(rows)
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    return buf.getvalue()


# ── Sidebar ──────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🏏 CricBazaar")
    st.markdown("### Cricket Auction Planner")
    st.caption("44 players · 4 teams · 11 per squad")
    st.divider()

    sold = len(st.session_state.auction_log)
    st.markdown(f"**Auction Progress:** {sold} / {TOTAL_AUCTION_PLAYERS} sold")
    st.progress(sold / TOTAL_AUCTION_PLAYERS if TOTAL_AUCTION_PLAYERS else 0)

    st.divider()
    st.markdown("### 💰 Budget Snapshot")
    for tname, tinfo in TEAMS.items():
        remaining = get_team_remaining(tname)
        auc_count = get_auction_count(tname)
        total_count = auc_count + 2  # +captain +VC
        pct = remaining / BUDGET_PER_TEAM
        st.markdown(
            f"{tinfo['emoji']} **{tname}** — ₹{remaining}L left | "
            f"{total_count}/{SQUAD_SIZE} players ({auc_count} bought)"
        )
        st.progress(pct)

    st.divider()

    # Pre-assigned reference
    with st.expander("👑 Captains & Vice-Captains"):
        for tname in TEAMS:
            pre = get_pre_assigned_players(tname)
            cap = next((p for p in pre if p.get("tag") == "Captain"), None)
            vc = next((p for p in pre if p.get("tag") == "Vice-Captain"), None)
            st.markdown(f"**{tname}:**")
            if cap:
                st.markdown(f"  🏅 C: {cap['name']} ({cap['role']})")
            if vc:
                st.markdown(f"  🥈 VC: {vc['name']} ({vc['role']})")

    st.divider()
    if st.button("🔄 Reset Entire Auction", type="secondary", use_container_width=True):
        st.session_state.auction_log = {}
        st.rerun()

    st.divider()
    with st.expander("👨‍💻 Developer Details"):
        st.markdown(
            """
            **Developed with ❤️ by Abhijeet**

            [![LinkedIn](https://img.shields.io/badge/LinkedIn-0A66C2?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/abh1jeet/)

            [![GitHub Repo](https://img.shields.io/badge/GitHub-Repo-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/abh1jeet/founders-bid)

            *CricBazaar v1.0 · March 2026*
            """
        )

# ── Main title ───────────────────────────────────────────────────────
st.markdown("# 🏏 CricBazaar — Live Auction Planner")
st.markdown("*Founder's Cup · 44 players · 4 teams · 11 per squad (2 fixed + 9 auction)*")

# ── Tabs ─────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
    "⚡ Live Auction",
    "📊 Team Dashboard",
    "📋 Player Pool",
    "🏆 My Strategy (Abhijeet)",
    "🎯 Best Team Builder",
    "🤖 AI Insights",
    "📈 Tier Analysis",
    "✏️ Edit Ratings",
])

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TAB 1 — LIVE AUCTION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
with tab1:
    st.markdown("## ⚡ Record a Player Sale")
    unsold = get_unsold_players()

    if not unsold:
        st.success("🎉 All 36 auction players have been sold!")
    else:
        col_form, col_preview = st.columns([3, 2])

        with col_form:
            player_options = {
                f"{p['name']} (Tier {p['tier']} | {p['role']} | OVR {p['overall']})": p["id"]
                for p in unsold
            }
            selected_label = st.selectbox("🎯 Select Player", list(player_options.keys()))
            selected_id = player_options[selected_label]
            selected_player = next(p for p in unsold if p["id"] == selected_id)

            eligible_teams = [t for t in TEAMS if get_auction_count(t) < AUCTION_SLOTS]
            if not eligible_teams:
                st.warning("All teams have filled their 9 auction slots!")
            else:
                sold_to = st.selectbox("🏷️ Sold to Team", eligible_teams)
                max_bid = max_affordable(sold_to)
                sold_price = st.number_input(
                    f"💰 Sold Price (₹L) — Base: {BASE_PRICE}, Max: {max_bid}",
                    min_value=BASE_PRICE,
                    max_value=max(BASE_PRICE, max_bid),
                    value=BASE_PRICE,
                    step=BID_INCREMENT,
                )

                if st.button("✅ Confirm Sale", type="primary", use_container_width=True):
                    st.session_state.auction_log[selected_id] = {"team": sold_to, "price": sold_price}
                    st.success(f"🎉 {selected_player['name']} sold to **{sold_to}** for ₹{sold_price}L!")
                    st.rerun()

        with col_preview:
            st.markdown("### 🔍 Player Preview")
            tier_class = f"tier-{selected_player['tier']}"
            st.markdown(f"""
            <div class="team-card {tier_class}">
                <p class="metric-big">{selected_player['name']}</p>
                <p class="metric-label">Tier {selected_player['tier']} | {selected_player['role']}</p>
                <hr style="opacity:0.3">
                <p>🏏 Bat: <b>{selected_player['batting']}</b> | 🎳 Bowl: <b>{selected_player['bowling']}</b> | 🧤 Field: <b>{selected_player['fielding']}</b></p>
                <p class="metric-label">Overall: <b>{selected_player['overall']}</b></p>
            </div>
            """, unsafe_allow_html=True)

        # ── Live Bid Advisor (always visible when player selected) ────
        st.divider()
        st.markdown("### 🎯 Live Bid Advisor")

        my_team_live = "Abhijeet"
        my_squad_live = get_full_squad(my_team_live)
        my_remaining_live = get_team_remaining(my_team_live)
        my_slots_live = AUCTION_SLOTS - get_auction_count(my_team_live)
        all_teams_live = build_all_teams_data()

        if my_slots_live > 0:
            # Quick optimizer recommendation
            bid_rec = recommend_max_bid(
                selected_player, my_squad_live, unsold,
                my_remaining_live, my_slots_live
            )
            # Competition analysis
            competitors = estimate_competition(selected_player, all_teams_live, unsold)
            price_pred = predict_auction_price(selected_player, all_teams_live, unsold)

            adv1, adv2, adv3 = st.columns(3)
            with adv1:
                v_color = {"🟢 MUST BUY": "#28a745", "🟡 GOOD BUY": "#ffc107",
                           "🟡 NEED-BASED BUY": "#ffc107", "🟡 BOWLING NEED": "#ffc107",
                           "🔴 SKIP / BASE ONLY": "#dc3545"}.get(bid_rec['verdict'], "#6c757d")
                st.markdown(f"""
                <div class="team-card" style="background: {v_color}; text-align: left; padding: 12px;">
                    <p style="font-size:1.2rem; font-weight:800; margin:0;">{bid_rec['verdict']}</p>
                    <p style="margin:4px 0;">{bid_rec['verdict_detail']}</p>
                    <hr style="opacity:0.3">
                    <p style="font-size:1.3rem; font-weight:700;">💰 Max Bid: ₹{bid_rec['recommended_max']}L</p>
                    <p style="font-size:0.85rem;">Marginal: +{bid_rec['marginal_value']} OVR | Hard cap: ₹{bid_rec['hard_max']}L</p>
                </div>
                """, unsafe_allow_html=True)

            with adv2:
                st.markdown(f"""
                <div class="team-card" style="background: #2c3e50; text-align: left; padding: 12px;">
                    <p style="font-size:1.2rem; font-weight:800; margin:0;">📊 Price Prediction</p>
                    <p style="font-size:1.3rem; font-weight:700; margin:8px 0;">₹{price_pred['predicted_price']}L expected</p>
                    <p>Range: ₹{price_pred['price_range'][0]}L — ₹{price_pred['price_range'][1]}L</p>
                    <p>Competition: {price_pred['competition_level']}</p>
                </div>
                """, unsafe_allow_html=True)

            with adv3:
                st.markdown(f"""
                <div class="team-card" style="background: #34495e; text-align: left; padding: 12px;">
                    <p style="font-size:1.2rem; font-weight:800; margin:0;">🏟️ Who'll Compete?</p>
                """, unsafe_allow_html=True)
                if competitors:
                    for comp in competitors[:3]:
                        emoji = TEAMS.get(comp['team'], {}).get('emoji', '🏏')
                        st.markdown(
                            f"  {emoji} **{comp['team']}** — desire: {comp['desire_score']} | "
                            f"may bid ₹{comp['estimated_max_bid']}L"
                        )
                        if comp['reasons']:
                            st.caption(f"  ↳ {', '.join(comp['reasons'][:2])}")
                else:
                    st.markdown("Low competition expected — good chance at base!")
                st.markdown("</div>", unsafe_allow_html=True)

            # AI Quick Insight button
            if st.button("🤖 Get AI Quick Insight", key="ai_quick_live", use_container_width=True):
                with st.spinner("🤖 Asking Gemma3 for advice..."):
                    squad_needs_live = analyze_squad_needs(my_squad_live)
                    auction_log_live = build_auction_log_data()
                    insight = get_live_auction_insight(
                        selected_player, my_squad_live, unsold,
                        my_remaining_live, my_slots_live,
                        squad_needs_live, all_teams_live, auction_log_live
                    )
                    st.markdown("#### 🤖 AI Quick Take")
                    st.markdown(insight)
        else:
            st.success("Your squad is complete! No more slots to fill.")

    # Auction log
    st.divider()
    st.markdown("### 📜 Auction Log")
    if st.session_state.auction_log:
        log_data = []
        for pid, info in reversed(list(st.session_state.auction_log.items())):
            p = next(pl for pl in st.session_state.player_data if pl["id"] == pid)
            log_data.append({
                "Player": p["name"], "Role": p["role"], "Tier": p["tier"],
                "OVR": p["overall"], "Team": info["team"], "Price (₹L)": info["price"],
            })
        st.dataframe(pd.DataFrame(log_data), use_container_width=True, hide_index=True)

        if st.button("↩️ Undo Last Sale"):
            last_pid = list(st.session_state.auction_log.keys())[-1]
            last_name = next(p["name"] for p in st.session_state.player_data if p["id"] == last_pid)
            del st.session_state.auction_log[last_pid]
            st.info(f"Undid sale of {last_name}")
            st.rerun()
    else:
        st.info("No players sold yet. Start the auction above!")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TAB 2 — TEAM DASHBOARD
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
with tab2:
    st.markdown("## 📊 Team Dashboard")

    team_cols = st.columns(4)
    for idx, (tname, tinfo) in enumerate(TEAMS.items()):
        with team_cols[idx]:
            remaining = get_team_remaining(tname)
            auc_count = get_auction_count(tname)
            total_count = auc_count + 2
            full_squad = get_full_squad(tname)

            st.markdown(f"""
            <div class="team-card" style="background: {tinfo['color']};">
                <p class="metric-big">{tinfo['emoji']} {tname}</p>
                <p class="metric-label">Budget: ₹{remaining}L / ₹{BUDGET_PER_TEAM}L</p>
                <p class="metric-big">{total_count}/{SQUAD_SIZE}</p>
                <p class="metric-label">{auc_count}/9 auction · 2 fixed</p>
            </div>
            """, unsafe_allow_html=True)

            # Role breakdown (full squad)
            bat_c = role_count_full(tname, "Batsman")
            bowl_c = role_count_full(tname, "Bowler")
            ar_c = role_count_full(tname, "All-rounder")
            st.markdown(f"🏏 Bat: **{bat_c}** | 🎳 Bowl: **{bowl_c}** | ⭐ AR: **{ar_c}**")

            # Tier breakdown
            t1 = tier_count_full(tname, 1)
            t2 = tier_count_full(tname, 2)
            t3 = tier_count_full(tname, 3)
            t4 = tier_count_full(tname, 4)
            st.markdown(f"🥇T1: **{t1}** | 🥈T2: **{t2}** | 🥉T3: **{t3}** | T4: **{t4}**")

            ma = max_affordable(tname)
            st.caption(f"Max affordable bid: ₹{ma}L")

            # Full squad expander
            if full_squad:
                with st.expander(f"View {tname}'s Full Squad ({len(full_squad)})"):
                    # Captain & VC first
                    for p in full_squad:
                        tag = p.get("tag", "")
                        if tag == "Captain":
                            badge = "🏅 C"
                        elif tag == "Vice-Captain":
                            badge = "🥈 VC"
                        else:
                            badge = {1: "🥇", 2: "🥈", 3: "🥉", 4: "🏷️"}[p["tier"]]
                        price_str = f"₹{p['sold_price']}L" if p.get("sold_price", 0) > 0 else "Pre-assigned"
                        st.markdown(f"{badge} **{p['name']}** — {p['role']} | OVR {p['overall']} | {price_str}")

            # Download button
            csv_data = build_team_csv(tname)
            st.download_button(
                label=f"📥 Download {tname}'s Sheet",
                data=csv_data,
                file_name=f"{tname}_squad.csv",
                mime="text/csv",
                use_container_width=True,
            )

    # Comparison table
    st.divider()
    st.markdown("### 📊 Team Comparison")
    comp_data = []
    for tname in TEAMS:
        squad = get_full_squad(tname)
        avg_ovr = round(sum(p["overall"] for p in squad) / len(squad), 1) if squad else 0
        comp_data.append({
            "Team": tname,
            "Total": len(squad),
            "Auction Bought": get_auction_count(tname),
            "Budget Spent": f"₹{get_team_budget_spent(tname)}L",
            "Budget Left": f"₹{get_team_remaining(tname)}L",
            "Batsmen": role_count_full(tname, "Batsman"),
            "Bowlers": role_count_full(tname, "Bowler"),
            "All-rounders": role_count_full(tname, "All-rounder"),
            "Avg OVR": avg_ovr,
            "Tier 1": tier_count_full(tname, 1),
            "Tier 2": tier_count_full(tname, 2),
            "Tier 3": tier_count_full(tname, 3),
            "Tier 4": tier_count_full(tname, 4),
        })
    st.dataframe(pd.DataFrame(comp_data), use_container_width=True, hide_index=True)

    # Tier 1 team sheet
    st.divider()
    st.markdown("### ⭐ Tier 1 Team Sheet (Captains & Vice-Captains)")
    sheet_rows = []
    for p in CAPTAINS + VICE_CAPTAINS:
        matched = next((pl for pl in st.session_state.player_data if pl["id"] == p["id"]), None)
        sheet_rows.append({
            "Team": p["team"],
            "Player": p["name"],
            "Tag": p["tag"],
            "Role": p.get("forced_role", ""),
            "Tier": "⭐ Tier 1",
            "Batting": matched["batting"] if matched else p["batting"],
            "Bowling": matched["bowling"] if matched else p["bowling"],
            "Fielding": matched["fielding"] if matched else p["fielding"],
            "Overall": matched["overall"] if matched else "",
        })
    st.dataframe(pd.DataFrame(sheet_rows), use_container_width=True, hide_index=True)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TAB 3 — PLAYER POOL
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
with tab3:
    st.markdown("## 📋 Complete Player Pool (44 Players)")

    filter_col1, filter_col2, filter_col3, filter_col4 = st.columns(4)
    with filter_col1:
        role_filter = st.multiselect("Role", ["Batsman", "Bowler", "All-rounder"],
                                     default=["Batsman", "Bowler", "All-rounder"])
    with filter_col2:
        tier_filter = st.multiselect("Tier", [1, 2, 3, 4], default=[1, 2, 3, 4])
    with filter_col3:
        type_filter = st.multiselect("Type", ["Auction", "Captain", "Vice-Captain"],
                                     default=["Auction", "Captain", "Vice-Captain"])
    with filter_col4:
        status_filter = st.radio("Status", ["All", "Unsold Only", "Sold/Assigned"], horizontal=True)

    pool_data = []
    for p in st.session_state.player_data:
        if p["role"] not in role_filter or p["tier"] not in tier_filter:
            continue
        tag = p.get("tag", "Auction")
        if tag not in type_filter:
            continue

        is_pre = p["id"] in PRE_ASSIGNED
        is_auction_sold = p["id"] in st.session_state.auction_log
        if status_filter == "Unsold Only" and (is_pre or is_auction_sold):
            continue
        if status_filter == "Sold/Assigned" and not is_pre and not is_auction_sold:
            continue

        sold_info = st.session_state.auction_log.get(p["id"], {})
        if is_pre:
            status_str = f"🏅 {PRE_ASSIGNED[p['id']]['tag']} → {PRE_ASSIGNED[p['id']]['team']}"
        elif is_auction_sold:
            status_str = f"✅ {sold_info['team']}"
        else:
            status_str = "🔲 Available"

        price_str = f"₹{sold_info['price']}L" if is_auction_sold else ("Fixed" if is_pre else "—")

        pool_data.append({
            "ID": p["id"], "Name": p["name"], "Type": tag,
            "Role": p["role"], "Tier": f"⭐ {p['tier']}",
            "Bat": p["batting"], "Bowl": p["bowling"], "Field": p["fielding"],
            "OVR": p["overall"], "Status": status_str, "Price": price_str,
        })

    pool_df = pd.DataFrame(pool_data)
    if not pool_df.empty:
        pool_df = pool_df.sort_values("OVR", ascending=False)
    st.dataframe(pool_df, use_container_width=True, hide_index=True)
    st.caption(f"Showing {len(pool_df)} of {TOTAL_PLAYERS} players")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TAB 4 — MY STRATEGY (ABHIJEET)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
with tab4:
    st.markdown("## 🏆 Abhijeet's Strategy Console")

    my_team = "Abhijeet"
    my_squad = get_full_squad(my_team)
    my_remaining = get_team_remaining(my_team)
    my_auc_count = get_auction_count(my_team)
    auc_slots_left = AUCTION_SLOTS - my_auc_count

    col_s1, col_s2, col_s3, col_s4 = st.columns(4)
    col_s1.metric("💰 Budget Left", f"₹{my_remaining}L")
    col_s2.metric("👥 Squad", f"{len(my_squad)}/{SQUAD_SIZE}")
    col_s3.metric("🎯 Auction Slots Left", auc_slots_left)
    col_s4.metric("💸 Max Bid", f"₹{max_affordable(my_team)}L")

    st.divider()

    # Current squad
    st.markdown("### 🏏 My Current Squad")
    my_bat = [p for p in my_squad if p["role"] == "Batsman"]
    my_bowl = [p for p in my_squad if p["role"] == "Bowler"]
    my_ar = [p for p in my_squad if p["role"] == "All-rounder"]

    rc1, rc2, rc3 = st.columns(3)
    with rc1:
        st.markdown("#### 🏏 Batsmen")
        for p in my_bat:
            tag_str = f" <span class='captain-badge'>{p['tag']}</span>" if p.get("tag") else ""
            price = f"₹{p['sold_price']}L" if p.get("sold_price", 0) > 0 else "Fixed"
            st.markdown(f"• **{p['name']}** (OVR {p['overall']}) — {price}{tag_str}", unsafe_allow_html=True)
        if not my_bat:
            st.caption("None yet")
    with rc2:
        st.markdown("#### 🎳 Bowlers")
        for p in my_bowl:
            tag_str = f" <span class='captain-badge'>{p['tag']}</span>" if p.get("tag") else ""
            price = f"₹{p['sold_price']}L" if p.get("sold_price", 0) > 0 else "Fixed"
            st.markdown(f"• **{p['name']}** (OVR {p['overall']}) — {price}{tag_str}", unsafe_allow_html=True)
        if not my_bowl:
            st.caption("None yet")
    with rc3:
        st.markdown("#### ⭐ All-rounders")
        for p in my_ar:
            tag_str = f" <span class='captain-badge'>{p['tag']}</span>" if p.get("tag") else ""
            price = f"₹{p['sold_price']}L" if p.get("sold_price", 0) > 0 else "Fixed"
            st.markdown(f"• **{p['name']}** (OVR {p['overall']}) — {price}{tag_str}", unsafe_allow_html=True)
        if not my_ar:
            st.caption("None yet")

    # Squad strength
    if my_squad:
        avg_ovr = round(sum(p["overall"] for p in my_squad) / len(my_squad), 1)
        total_bat = sum(p["batting"] for p in my_squad)
        total_bowl = sum(p["bowling"] for p in my_squad)
        total_field = sum(p["fielding"] for p in my_squad)
        st.divider()
        st.markdown("### 📊 Squad Strength")
        ms1, ms2, ms3, ms4 = st.columns(4)
        ms1.metric("Avg Overall", avg_ovr)
        ms2.metric("Total Batting", total_bat)
        ms3.metric("Total Bowling", total_bowl)
        ms4.metric("Total Fielding", total_field)

    st.divider()
    unsold_available = get_unsold_players()

    if unsold_available and auc_slots_left > 0:
        # ── Squad Needs Analysis ──────────────────────────────────
        analysis = analyze_squad_needs(my_squad)
        st.markdown("### 🔬 Squad Needs Analysis")

        na1, na2, na3, na4 = st.columns(4)
        na1.metric("🎳 Can Bowl", f"{analysis['bowlers_who_can_bowl']}/6",
                   delta=f"Need {analysis['bowlers_needed']} more" if analysis['bowlers_needed'] > 0 else "✅ Met")
        na2.metric("🏏 Batsmen", analysis['bat_count'])
        na3.metric("🎳 Bowlers", analysis['bowl_count'])
        na4.metric("⭐ All-rounders", analysis['ar_count'])

        if analysis['role_needs']:
            need_labels = [n for n in analysis['role_needs'] if n != 'need_bowlers']
            if analysis['bowlers_needed'] > 0:
                need_labels.append(f"Bowling options ({analysis['bowlers_needed']} more needed)")
            st.warning(f"⚠️ Squad gaps: **{', '.join(need_labels)}**")
        else:
            st.success("✅ Squad composition is balanced!")

        # ── MILP Optimal Dream Picks ─────────────────────────────
        st.divider()
        st.markdown("### 🧠 AI Optimal Squad (MILP Solver)")
        st.caption("Mixed Integer Linear Programming finds the mathematically best 9 players within budget.")

        optimal = solve_optimal_squad(unsold_available, my_squad, my_remaining, auc_slots_left)
        if optimal:
            opt_ovr = sum(p['overall'] for p in optimal)
            full_ovr = sum(p['overall'] for p in my_squad) + opt_ovr
            st.markdown(f"**Optimal picks add {opt_ovr:.1f} OVR** → Full squad OVR: **{full_ovr:.1f}**")

            opt_data = []
            for rank, p in enumerate(sorted(optimal, key=lambda x: -x['overall']), 1):
                can_b = "✅" if p['bowling'] >= 4 else "❌"
                opt_data.append({
                    "#": rank, "Name": p['name'], "Role": p['role'],
                    "Tier": f"⭐{p['tier']}", "OVR": p['overall'],
                    "Bat": p['batting'], "Bowl": p['bowling'], "Field": p['fielding'],
                    "Can Bowl": can_b,
                })
            st.dataframe(pd.DataFrame(opt_data), use_container_width=True, hide_index=True)
        else:
            st.info("Solver could not find a feasible solution with current constraints.")

        # ── Per-Player Recommendation ────────────────────────────
        st.divider()
        st.markdown("### 🎯 Player-by-Player Recommendation")
        st.caption("For each available player: should you buy? And up to how much?")

        recs = get_ranked_recommendations(unsold_available, my_squad, my_remaining, auc_slots_left)

        if recs:
            # Summary table
            rec_table = []
            for rank, r in enumerate(recs, 1):
                in_opt = "⭐" if r.get('in_optimal') else ""
                rec_table.append({
                    "Rank": rank,
                    "Player": r['name'],
                    "Role": r['role'],
                    "Tier": r['tier'],
                    "OVR": r['overall'],
                    "Score": r['score'],
                    "Max Bid (₹L)": r['recommended_max'],
                    "Verdict": r['verdict'],
                    "In Optimal": in_opt,
                })
            st.dataframe(pd.DataFrame(rec_table), use_container_width=True, hide_index=True)

            # Detailed per-player cards
            st.divider()
            st.markdown("### 🔍 Detailed Player Analysis")
            st.caption("Select a player to see detailed bid recommendation.")

            player_labels = {f"{r['name']} ({r['role']} | Tier {r['tier']})": r['id'] for r in recs}
            sel_label = st.selectbox("Pick a player to analyze", list(player_labels.keys()), key="rec_player")
            sel_id = player_labels[sel_label]
            sel_p = next(p for p in unsold_available if p['id'] == sel_id)

            bid_info = recommend_max_bid(sel_p, my_squad, unsold_available, my_remaining, auc_slots_left)

            # Verdict card
            verdict_colors = {
                "🟢 MUST BUY": "#28a745",
                "🟡 GOOD BUY": "#ffc107",
                "🟡 NEED-BASED BUY": "#ffc107",
                "🟡 BOWLING NEED": "#ffc107",
                "🔴 SKIP / BASE ONLY": "#dc3545",
            }
            v_color = verdict_colors.get(bid_info['verdict'], "#6c757d")

            st.markdown(f"""
            <div class="team-card" style="background: {v_color}; text-align: left;">
                <p class="metric-big">{bid_info['verdict']}</p>
                <p>{bid_info['verdict_detail']}</p>
                <hr style="opacity:0.3">
                <p>💰 <b>Recommended Max Bid: ₹{bid_info['recommended_max']}L</b> (Hard cap: ₹{bid_info['hard_max']}L)</p>
                <p>📊 Marginal Value: <b>+{bid_info['marginal_value']} OVR</b> | Need Premium: {bid_info['need_premium']} | Tier Bonus: {bid_info['tier_premium']}</p>
                <p>📈 Without: {bid_info['baseline_ovr']} OVR → With: {bid_info['boosted_ovr']} OVR</p>
            </div>
            """, unsafe_allow_html=True)

            # Player stats
            st.markdown("")
            det1, det2, det3, det4 = st.columns(4)
            det1.metric("🏏 Batting", sel_p['batting'])
            det2.metric("🎳 Bowling", sel_p['bowling'])
            det3.metric("🧤 Fielding", sel_p['fielding'])
            det4.metric("📊 Overall", sel_p['overall'])

    elif auc_slots_left == 0:
        st.success("🎉 Squad complete! You have all 11 players.")
    else:
        st.warning("No unsold players remaining.")

    # Download my team
    st.divider()
    csv_data = build_team_csv(my_team)
    st.download_button(
        label="📥 Download My Squad Sheet",
        data=csv_data,
        file_name="Abhijeet_squad.csv",
        mime="text/csv",
        use_container_width=True,
    )

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TAB 5 — BEST TEAM BUILDER (Real-time)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
with tab5:
    st.markdown("## 🎯 Best Team Builder — Real-Time")
    st.markdown("*At every point in the auction, here's the best team you can build.*")

    bt_team = "Abhijeet"
    bt_squad = get_full_squad(bt_team)
    bt_remaining = get_team_remaining(bt_team)
    bt_auc_count = get_auction_count(bt_team)
    bt_slots_left = AUCTION_SLOTS - bt_auc_count
    bt_unsold = get_unsold_players()
    bt_all_teams = build_all_teams_data()

    if bt_slots_left > 0 and bt_unsold:
        snapshot = build_best_team_snapshot(
            bt_squad, bt_unsold, bt_remaining, bt_slots_left, bt_all_teams
        )

        # Overview metrics
        st.markdown("### 📊 Team Rating Forecast")
        fc1, fc2, fc3, fc4 = st.columns(4)
        fc1.metric("Current Squad OVR", snapshot["current_ovr"],
                   delta=f"Avg {snapshot['current_avg']}")
        fc2.metric("Best Possible OVR", snapshot["best_possible_ovr"],
                   delta=f"+{round(snapshot['best_possible_ovr'] - snapshot['current_ovr'], 1)}")
        fc3.metric("Realistic OVR", snapshot["realistic_ovr"],
                   delta=f"Avg {snapshot['realistic_avg']}")
        fc4.metric("Slots to Fill", snapshot["slots_left"],
                   delta=f"₹{snapshot['budget_remaining']}L budget")

        st.divider()

        # Best Possible Dream 11
        st.markdown("### ⭐ Best Possible Dream 11")
        st.caption("If you get all optimal picks at base price — the mathematically best squad.")
        if snapshot["optimal_picks"]:
            dream_data = []
            for i, p in enumerate(sorted(snapshot["best_possible_squad"],
                                         key=lambda x: -x["overall"]), 1):
                tag = p.get("tag", "")
                status = "✅ In Squad" if tag else "🎯 Target"
                can_b = "✅" if p.get("bowling", 0) >= 4 else "❌"
                dream_data.append({
                    "#": i, "Name": p["name"], "Role": p["role"],
                    "Tier": f"⭐{p['tier']}", "OVR": p["overall"],
                    "Bat": p["batting"], "Bowl": p["bowling"],
                    "Field": p["fielding"], "Can Bowl": can_b, "Status": status,
                })
            st.dataframe(pd.DataFrame(dream_data), use_container_width=True, hide_index=True)
        else:
            st.info("No feasible optimal squad found.")

        st.divider()

        # Realistic Team (accounting for competition)
        st.markdown("### 🏟️ Realistic Team (Competition-Adjusted)")
        st.caption("Accounts for other teams' likely bids — who you can realistically get.")
        if snapshot["realistic_picks"]:
            real_data = []
            for i, p in enumerate(sorted(snapshot["realistic_squad"],
                                         key=lambda x: -x["overall"]), 1):
                tag = p.get("tag", "")
                if tag:
                    status = f"✅ {tag}"
                    est_cost = "Fixed"
                    comp = "—"
                    prob = "—"
                elif "estimated_cost" in p:
                    status = "🎯 Target"
                    est_cost = f"₹{p['estimated_cost']}L"
                    comp = p.get("competition_level", "—")
                    prob = f"{int(p.get('acq_probability', 0) * 100)}%"
                else:
                    status = "✅ Bought"
                    est_cost = f"₹{p.get('sold_price', 0)}L"
                    comp = "—"
                    prob = "—"
                real_data.append({
                    "#": i, "Name": p["name"], "Role": p["role"],
                    "Tier": p["tier"], "OVR": p["overall"],
                    "Est. Cost": est_cost, "Competition": comp,
                    "Chance": prob, "Status": status,
                })
            st.dataframe(pd.DataFrame(real_data), use_container_width=True, hide_index=True)

        st.divider()

        # Priority Targets
        st.markdown("### 🎯 Priority Targets (Top 10)")
        st.caption("Players ranked by expected value — factoring in quality AND likelihood of acquisition.")
        if snapshot["priority_targets"]:
            pt_data = []
            for i, t in enumerate(snapshot["priority_targets"], 1):
                in_opt = "⭐" if t["in_optimal"] else ""
                pt_data.append({
                    "Rank": i, "Name": t["name"], "Role": t["role"],
                    "Tier": t["tier"], "OVR": t["overall"],
                    "Est. Price": f"₹{t['estimated_cost']}L",
                    "Competition": t["competition"],
                    "Chance": f"{int(t['acq_probability'] * 100)}%",
                    "Value Score": t["value_score"],
                    "In Optimal": in_opt,
                })
            st.dataframe(pd.DataFrame(pt_data), use_container_width=True, hide_index=True)

        st.divider()

        # Budget Allocation Strategy
        st.markdown("### 💰 Budget Allocation Strategy")
        st.caption(f"How to spend your remaining ₹{bt_remaining}L across {bt_slots_left} slots.")
        if snapshot["budget_allocation"]:
            alloc_data = []
            for a in snapshot["budget_allocation"]:
                alloc_data.append({
                    "Slot": a["slot"], "Type": a["type"],
                    "Target Role": a["target_role"],
                    "Max Budget": f"₹{a['max_budget']}L",
                    "Strategy": a["strategy"],
                })
            st.dataframe(pd.DataFrame(alloc_data), use_container_width=True, hide_index=True)

            total_priority = sum(a["max_budget"] for a in snapshot["budget_allocation"]
                                 if a["type"] == "🎯 Priority")
            total_value = sum(a["max_budget"] for a in snapshot["budget_allocation"]
                             if a["type"] == "💰 Value")
            st.markdown(
                f"**Summary:** Spend up to ₹{total_priority}L on priority picks, "
                f"₹{total_value}L on value picks. "
                f"Keep ₹{bt_remaining - total_priority - total_value}L reserve."
            )

        # AI Best Team Analysis button
        st.divider()
        if st.button("🤖 Get AI Best Team Analysis", key="ai_best_team", use_container_width=True):
            with st.spinner("🤖 Analyzing with Gemma3:4b..."):
                bt_needs = analyze_squad_needs(bt_squad)
                insight = get_best_team_analysis(
                    bt_squad, bt_unsold, bt_remaining, bt_slots_left,
                    bt_needs, snapshot["optimal_picks"], bt_all_teams
                )
                st.markdown("### 🤖 AI Team Building Strategy")
                st.markdown(insight)

    elif bt_slots_left == 0:
        st.success("🎉 Your squad is complete! All 11 players selected.")
        st.markdown("### 📊 Final Squad")
        final_data = []
        for i, p in enumerate(sorted(bt_squad, key=lambda x: -x["overall"]), 1):
            tag = p.get("tag", "Auction")
            price = f"₹{p.get('sold_price', 0)}L" if p.get("sold_price", 0) > 0 else "Fixed"
            final_data.append({
                "#": i, "Name": p["name"], "Role": p["role"],
                "Tier": p["tier"], "OVR": p["overall"],
                "Bat": p["batting"], "Bowl": p["bowling"],
                "Field": p["fielding"], "Type": tag, "Price": price,
            })
        st.dataframe(pd.DataFrame(final_data), use_container_width=True, hide_index=True)
        total_ovr = sum(p["overall"] for p in bt_squad)
        avg_ovr = round(total_ovr / len(bt_squad), 1)
        st.metric("Squad Total OVR", total_ovr)
        st.metric("Squad Avg OVR", avg_ovr)
    else:
        st.info("No unsold players remaining.")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TAB 6 — AI INSIGHTS (Ollama + Gemma3:4b)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
with tab6:
    st.markdown("## 🤖 AI Insights — Powered by Ollama (Gemma3:4b)")
    st.markdown("*Local AI analysis using Google's Gemma3 model via Ollama.*")

    # Ollama status check
    ollama_ok, ollama_msg = check_ollama_status()
    if ollama_ok:
        st.success(ollama_msg)
    else:
        st.error(ollama_msg)
        st.markdown("""
        ### ⚙️ Setup Instructions
        1. **Install Ollama:** `brew install ollama` (macOS)
        2. **Pull the model:** `ollama pull gemma3:4b`
        3. **Start Ollama:** `ollama serve`
        4. **Refresh this page**
        """)

    st.divider()

    ai_team = "Abhijeet"
    ai_squad = get_full_squad(ai_team)
    ai_remaining = get_team_remaining(ai_team)
    ai_slots_left = AUCTION_SLOTS - get_auction_count(ai_team)
    ai_unsold = get_unsold_players()
    ai_all_teams = build_all_teams_data()
    ai_needs = analyze_squad_needs(ai_squad)

    # ── Section 1: Bid Advisor ──
    st.markdown("### 🎯 AI Bid Advisor")
    st.caption("Select any unsold player to get AI-powered bid advice.")

    if ai_unsold and ai_slots_left > 0:
        ai_player_opts = {
            f"{p['name']} (Tier {p['tier']} | {p['role']} | OVR {p['overall']})": p["id"]
            for p in sorted(ai_unsold, key=lambda x: -x["overall"])
        }
        ai_sel_label = st.selectbox("Select Player for AI Analysis",
                                    list(ai_player_opts.keys()), key="ai_bid_player")
        ai_sel_id = ai_player_opts[ai_sel_label]
        ai_sel_player = next(p for p in ai_unsold if p["id"] == ai_sel_id)

        if st.button("🤖 Get AI Bid Advice", key="ai_bid_btn", use_container_width=True):
            with st.spinner("🤖 Analyzing with Gemma3:4b... (may take 15-30 seconds)"):
                optimizer_rec = recommend_max_bid(
                    ai_sel_player, ai_squad, ai_unsold, ai_remaining, ai_slots_left
                )
                advice = get_bid_advice(
                    ai_sel_player, ai_squad, ai_unsold, ai_remaining, ai_slots_left,
                    ai_needs, optimizer_rec, ai_all_teams
                )
                st.markdown(f"### 🤖 AI Bid Advice for {ai_sel_player['name']}")
                st.markdown(advice)
    else:
        if ai_slots_left == 0:
            st.success("Your squad is complete!")
        else:
            st.info("No unsold players available.")

    st.divider()

    # ── Section 2: Player Comparison ──
    st.markdown("### ⚖️ AI Player Comparison")
    st.caption("Compare two players head-to-head — who should you target?")

    if len(ai_unsold) >= 2:
        cmp_col1, cmp_col2 = st.columns(2)
        cmp_opts = {
            f"{p['name']} ({p['role']} | T{p['tier']})": p["id"]
            for p in sorted(ai_unsold, key=lambda x: -x["overall"])
        }
        with cmp_col1:
            cmp1_label = st.selectbox("Player 1", list(cmp_opts.keys()), key="cmp1")
            cmp1_id = cmp_opts[cmp1_label]
        with cmp_col2:
            cmp2_options = [k for k in cmp_opts.keys() if cmp_opts[k] != cmp1_id]
            cmp2_label = st.selectbox("Player 2", cmp2_options, key="cmp2")
            cmp2_id = cmp_opts[cmp2_label]

        if st.button("🤖 Compare Players", key="ai_cmp_btn", use_container_width=True):
            with st.spinner("🤖 Comparing players..."):
                p1 = next(p for p in ai_unsold if p["id"] == cmp1_id)
                p2 = next(p for p in ai_unsold if p["id"] == cmp2_id)
                comparison = get_player_comparison(p1, p2, ai_squad, ai_needs, ai_remaining)
                st.markdown(f"### ⚖️ {p1['name']} vs {p2['name']}")
                st.markdown(comparison)

    st.divider()

    # ── Section 3: Team Review & Power Rankings ──
    st.markdown("### 🏆 AI Power Rankings & Team Review")
    st.caption("Get an AI analysis of all 4 teams — strengths, weaknesses, and predictions.")

    if st.button("🤖 Generate Power Rankings", key="ai_power_btn", use_container_width=True):
        with st.spinner("🤖 Analyzing all teams..."):
            review = get_post_auction_review(ai_squad, ai_remaining, ai_needs, ai_all_teams)
            st.markdown("### 🏆 AI Power Rankings")
            st.markdown(review)

    st.divider()

    # ── Section 4: Full Strategy Brief ──
    st.markdown("### 📋 AI Full Strategy Brief")
    st.caption("Comprehensive AI strategy for the rest of the auction.")

    if ai_unsold and ai_slots_left > 0:
        if st.button("🤖 Generate Full Strategy", key="ai_strategy_btn", use_container_width=True):
            with st.spinner("🤖 Building comprehensive strategy... (may take 30-60 seconds)"):
                optimal = solve_optimal_squad(ai_unsold, ai_squad, ai_remaining, ai_slots_left)
                strategy = get_best_team_analysis(
                    ai_squad, ai_unsold, ai_remaining, ai_slots_left,
                    ai_needs, optimal if optimal else [], ai_all_teams
                )
                st.markdown("### 📋 Full AI Strategy")
                st.markdown(strategy)
    else:
        st.info("Strategy brief available when there are unsold players and open slots.")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TAB 7 — TIER ANALYSIS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
with tab7:
    st.markdown("## 📈 Tier-Level Distribution Analysis")

    # Overall tier distribution
    st.markdown("### 🌐 All 44 Players by Tier")
    tier_summary = {"Tier": [], "Count": [], "Players": []}
    for t in [1, 2, 3, 4]:
        tp = [p for p in st.session_state.player_data if p["tier"] == t]
        tier_summary["Tier"].append(f"Tier {t}")
        tier_summary["Count"].append(len(tp))
        names = []
        for p in sorted(tp, key=lambda x: -x["overall"]):
            tag = ""
            if p.get("tag") == "Captain":
                tag = " 🏅C"
            elif p.get("tag") == "Vice-Captain":
                tag = " 🥈VC"
            names.append(f"{p['name']}{tag}")
        tier_summary["Players"].append(", ".join(names))
    st.dataframe(pd.DataFrame(tier_summary), use_container_width=True, hide_index=True)

    st.divider()

    # Per-team tier distribution
    st.markdown("### 🏷️ Tier Distribution by Team (Full Squad)")
    tier_team_cols = st.columns(4)
    for idx, (tname, tinfo) in enumerate(TEAMS.items()):
        with tier_team_cols[idx]:
            st.markdown(f"#### {tinfo['emoji']} {tname}")
            squad = get_full_squad(tname)
            if not squad:
                st.caption("Only captain & VC (no auction buys)")

            for t in [1, 2, 3, 4]:
                tp = [p for p in squad if p["tier"] == t]
                if tp:
                    tier_emoji = {1: "🥇", 2: "🥈", 3: "🥉", 4: "🏷️"}[t]
                    st.markdown(f"**{tier_emoji} Tier {t}** ({len(tp)})")
                    for p in tp:
                        tag_str = f" [{p['tag']}]" if p.get("tag") else ""
                        st.markdown(f"  • {p['name']}{tag_str} ({p['role']}, OVR {p['overall']})")

    st.divider()

    # Tier-wise spending
    st.markdown("### 💰 Tier-wise Spending Analysis")
    if st.session_state.auction_log:
        spend_data = []
        for tname in TEAMS:
            auc_players = get_auction_players(tname)
            for t in [1, 2, 3, 4]:
                tp = [p for p in auc_players if p["tier"] == t]
                total_spend = sum(p["sold_price"] for p in tp)
                avg_price = round(total_spend / len(tp), 1) if tp else 0
                spend_data.append({
                    "Team": tname, "Tier": f"Tier {t}",
                    "Players": len(tp), "Total Spent": f"₹{total_spend}L",
                    "Avg Price": f"₹{avg_price}L",
                })
        st.dataframe(pd.DataFrame(spend_data), use_container_width=True, hide_index=True)
    else:
        st.info("Spending analysis will appear once auction starts.")

    st.divider()
    st.markdown("### 📖 Tier Classification Guide")
    guide_c1, guide_c2, guide_c3, guide_c4 = st.columns(4)
    with guide_c1:
        st.markdown("""
        <div class="team-card tier-1">
            <p class="metric-big">🥇 Tier 1</p>
            <p>OVR ≥ 7.5 or Captain/VC</p>
            <p class="metric-label">Elite — bid aggressively</p>
        </div>
        """, unsafe_allow_html=True)
    with guide_c2:
        st.markdown("""
        <div class="team-card tier-2">
            <p class="metric-big">🥈 Tier 2</p>
            <p>OVR ≥ 5.5</p>
            <p class="metric-label">Strong — solid value</p>
        </div>
        """, unsafe_allow_html=True)
    with guide_c3:
        st.markdown("""
        <div class="team-card tier-3">
            <p class="metric-big">🥉 Tier 3</p>
            <p>OVR ≥ 3.5</p>
            <p class="metric-label">Decent — fill gaps</p>
        </div>
        """, unsafe_allow_html=True)
    with guide_c4:
        st.markdown("""
        <div class="team-card tier-4">
            <p class="metric-big">🏷️ Tier 4</p>
            <p>OVR &lt; 3.5</p>
            <p class="metric-label">Budget — base price</p>
        </div>
        """, unsafe_allow_html=True)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TAB 8 — EDIT PLAYER RATINGS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
with tab8:
    st.markdown("## ✏️ Edit Player Ratings")
    st.markdown("*Update batting, bowling & fielding ratings. Tier and role auto-recalculate.*")

    # Bulk edit
    st.markdown("### 📝 Bulk Edit (Table)")
    edit_rows = []
    for p in st.session_state.player_data:
        edit_rows.append({
            "ID": p["id"], "Name": p["name"],
            "Type": p.get("tag", "Auction"),
            "Batting": p["batting"], "Bowling": p["bowling"], "Fielding": p["fielding"],
            "Role (auto)": p["role"], "Overall (auto)": p["overall"], "Tier (auto)": p["tier"],
        })

    edit_df = pd.DataFrame(edit_rows)
    edited_df = st.data_editor(
        edit_df,
        column_config={
            "ID": st.column_config.NumberColumn("ID", disabled=True),
            "Name": st.column_config.TextColumn("Name", disabled=True),
            "Type": st.column_config.TextColumn("Type", disabled=True),
            "Batting": st.column_config.NumberColumn("🏏 Batting", min_value=0, max_value=10, step=1),
            "Bowling": st.column_config.NumberColumn("🎳 Bowling", min_value=0, max_value=10, step=1),
            "Fielding": st.column_config.NumberColumn("🧤 Fielding", min_value=0, max_value=10, step=1),
            "Role (auto)": st.column_config.TextColumn("Role", disabled=True),
            "Overall (auto)": st.column_config.NumberColumn("Overall", disabled=True),
            "Tier (auto)": st.column_config.NumberColumn("Tier", disabled=True),
        },
        use_container_width=True, hide_index=True, num_rows="fixed",
        key="player_editor",
    )

    if st.button("💾 Save All Rating Changes", type="primary", use_container_width=True):
        changes = 0
        for _, row in edited_df.iterrows():
            pid = int(row["ID"])
            player = next(p for p in st.session_state.player_data if p["id"] == pid)
            new_bat, new_bowl, new_field = int(row["Batting"]), int(row["Bowling"]), int(row["Fielding"])
            if player["batting"] != new_bat or player["bowling"] != new_bowl or player["fielding"] != new_field:
                player["batting"] = new_bat
                player["bowling"] = new_bowl
                player["fielding"] = new_field
                recalc_player(player)
                changes += 1
        if changes:
            st.success(f"✅ Updated {changes} player(s). Tiers & roles recalculated!")
            st.rerun()
        else:
            st.info("No changes detected.")

    st.divider()

    # Quick edit
    st.markdown("### 🎯 Quick Edit (Single Player)")
    player_names = {f"{p['name']} ({p.get('tag', 'Auction')})": p["id"] for p in st.session_state.player_data}
    selected_name = st.selectbox("Select Player", list(player_names.keys()), key="edit_select")
    sel_player = next(p for p in st.session_state.player_data if p["id"] == player_names[selected_name])

    qe1, qe2, qe3 = st.columns(3)
    with qe1:
        new_batting = st.slider("🏏 Batting", 0, 10, sel_player["batting"], key="qe_bat")
    with qe2:
        new_bowling = st.slider("🎳 Bowling", 0, 10, sel_player["bowling"], key="qe_bowl")
    with qe3:
        new_fielding = st.slider("🧤 Fielding", 0, 10, sel_player["fielding"], key="qe_field")

    preview = {**sel_player, "batting": new_batting, "bowling": new_bowling, "fielding": new_fielding}
    preview_ovr = compute_overall(preview)
    preview_tier = classify_tier(preview)
    preview_role = classify_role(preview)

    pc1, pc2 = st.columns(2)
    with pc1:
        st.markdown(f"**Current:** Role `{sel_player['role']}` | OVR `{sel_player['overall']}` | Tier `{sel_player['tier']}`")
    with pc2:
        changed = (new_batting != sel_player["batting"] or new_bowling != sel_player["bowling"] or new_fielding != sel_player["fielding"])
        st.markdown(f"**Preview {'🔄' if changed else '✅'}:** Role `{preview_role}` | OVR `{preview_ovr}` | Tier `{preview_tier}`")

    if st.button("💾 Save This Player", use_container_width=True):
        sel_player["batting"] = new_batting
        sel_player["bowling"] = new_bowling
        sel_player["fielding"] = new_fielding
        recalc_player(sel_player)
        st.success(f"✅ {sel_player['name']} → Tier {sel_player['tier']} | {sel_player['role']} | OVR {sel_player['overall']}")
        st.rerun()

    # Download all teams
    st.divider()
    st.markdown("### 📥 Download All Team Sheets")
    dl_cols = st.columns(4)
    for idx, tname in enumerate(TEAMS):
        with dl_cols[idx]:
            csv = build_team_csv(tname)
            st.download_button(
                label=f"📥 {tname}",
                data=csv,
                file_name=f"{tname}_squad.csv",
                mime="text/csv",
                use_container_width=True,
                key=f"dl_{tname}",
            )
