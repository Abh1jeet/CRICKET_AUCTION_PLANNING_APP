"""
🧠 CricBazaar — Squad Optimizer & Recommendation Engine
Uses MILP (Mixed Integer Linear Programming) via scipy.optimize.milp
to recommend optimal squad picks and max bid prices for Abhijeet.

Constraints:
  - Must pick exactly `slots_left` players from unsold pool
  - Total spend ≤ remaining budget
  - Each player costs at least BASE_PRICE
  - At least 6 players who can bowl (bowling >= 4) in the full 11
  - Balanced roles: minimum batsmen, bowlers, all-rounders

Objective: Maximize total squad overall rating.
"""

from scipy.optimize import linprog
import numpy as np
from players import BASE_PRICE, AUCTION_SLOTS, compute_overall


# ── Helpers ──────────────────────────────────────────────────────────
def _can_bowl(player):
    """A player can bowl if bowling rating >= 4."""
    return player["bowling"] >= 4


def _player_value_score(player, squad_needs):
    """
    Composite score for ranking a single player based on:
      - Overall rating (40%)
      - Role need multiplier (30%)
      - Bowling contribution bonus (20%)
      - Tier bonus (10%)
    """
    overall = player["overall"]

    # Role need bonus: if squad needs this role, big boost
    role = player["role"]
    need_mult = 1.5 if role in squad_needs else 1.0

    # Bowling contribution: premium for bowlers when team needs bowling
    bowl_bonus = 0
    if "need_bowlers" in squad_needs and _can_bowl(player):
        bowl_bonus = player["bowling"] * 0.3

    # Tier bonus
    tier_bonus = {1: 2.0, 2: 1.0, 3: 0.3, 4: 0.0}.get(player["tier"], 0)

    return round(overall * 0.4 * need_mult + bowl_bonus * 0.2 + tier_bonus * 0.1, 2)


def analyze_squad_needs(my_squad):
    """Analyze what the current squad is missing."""
    bowlers_who_can_bowl = sum(1 for p in my_squad if _can_bowl(p))
    bat_count = sum(1 for p in my_squad if p["role"] == "Batsman")
    bowl_count = sum(1 for p in my_squad if p["role"] == "Bowler")
    ar_count = sum(1 for p in my_squad if p["role"] == "All-rounder")

    needs = set()
    if bowlers_who_can_bowl < 6:
        needs.add("need_bowlers")
    if bat_count < 3:
        needs.add("Batsman")
    if bowl_count < 2:
        needs.add("Bowler")
    if ar_count < 2:
        needs.add("All-rounder")

    return {
        "bowlers_who_can_bowl": bowlers_who_can_bowl,
        "bowlers_needed": max(0, 6 - bowlers_who_can_bowl),
        "bat_count": bat_count,
        "bowl_count": bowl_count,
        "ar_count": ar_count,
        "role_needs": needs,
    }


def solve_optimal_squad(unsold_players, my_squad, budget_remaining, slots_left):
    """
    MILP solver to find the optimal set of `slots_left` players from
    `unsold_players` that maximizes total overall rating subject to
    budget and bowling constraints.

    Uses scipy.optimize.linprog with integrality constraints (MILP).

    Returns:
        list of dicts: selected players with metadata, or empty list if infeasible.
    """
    n = len(unsold_players)
    if n == 0 or slots_left <= 0:
        return []

    # Current squad bowling count
    current_bowlers = sum(1 for p in my_squad if _can_bowl(p))
    bowlers_still_needed = max(0, 6 - current_bowlers)

    # Decision variables: x_i ∈ {0, 1} for each unsold player
    # Objective: maximize Σ(overall_i * x_i) → minimize Σ(-overall_i * x_i)
    overalls = np.array([p["overall"] for p in unsold_players])
    c = -overalls  # negate for minimization

    # Constraint 1: exactly slots_left players selected
    # Σ x_i = slots_left → as two inequalities: Σ x_i <= slots_left AND Σ -x_i <= -slots_left
    A_eq = np.ones((1, n))
    b_eq = np.array([slots_left])

    # Inequality constraints (A_ub @ x <= b_ub)
    A_ub_list = []
    b_ub_list = []

    # Constraint 2: budget → Σ(BASE_PRICE * x_i) <= budget_remaining
    # (conservative: assume each picked player costs at least BASE_PRICE)
    costs = np.full(n, BASE_PRICE)
    A_ub_list.append(costs)
    b_ub_list.append(budget_remaining)

    # Constraint 3: at least `bowlers_still_needed` bowlers among selected
    # Σ(can_bowl_i * x_i) >= bowlers_still_needed
    # → Σ(-can_bowl_i * x_i) <= -bowlers_still_needed
    if bowlers_still_needed > 0:
        can_bowl_vec = np.array([1.0 if _can_bowl(p) else 0.0 for p in unsold_players])
        A_ub_list.append(-can_bowl_vec)
        b_ub_list.append(-bowlers_still_needed)

    A_ub = np.array(A_ub_list)
    b_ub = np.array(b_ub_list)

    # Bounds: 0 <= x_i <= 1
    bounds = [(0, 1)] * n

    # Integrality: all binary
    integrality = np.ones(n)

    try:
        result = linprog(
            c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq,
            bounds=bounds, integrality=integrality,
            method="highs",
        )
        if result.success:
            selected_indices = [i for i in range(n) if result.x[i] > 0.5]
            return [unsold_players[i] for i in selected_indices]
        else:
            return []
    except Exception:
        return []


def recommend_max_bid(player, my_squad, unsold_players, budget_remaining, slots_left):
    """
    Recommend the maximum price Abhijeet should pay for a specific player.

    Strategy:
      1. Solve MILP *without* this player → get baseline team OVR
      2. Solve MILP *with* this player forced in → get boosted team OVR
      3. Marginal value = (boosted_OVR - baseline_OVR)
      4. Max bid = BASE_PRICE + marginal_value_scaled + need_premium

    Also considers:
      - If team desperately needs bowlers and this player can bowl → premium
      - Role scarcity in remaining pool → premium
      - Tier of the player → premium

    Returns:
        dict with recommendation details.
    """
    analysis = analyze_squad_needs(my_squad)

    # Hard cap: can't bid more than affordable
    hard_max = budget_remaining - (slots_left - 1) * BASE_PRICE if slots_left > 1 else budget_remaining

    # --- Marginal value via MILP ---
    others = [p for p in unsold_players if p["id"] != player["id"]]

    # Baseline: best team WITHOUT this player
    baseline_squad = solve_optimal_squad(others, my_squad, budget_remaining, slots_left)
    baseline_ovr = sum(p["overall"] for p in baseline_squad) if baseline_squad else 0

    # Boosted: best team WITH this player forced in (slots_left - 1 from others)
    remaining_budget = budget_remaining - BASE_PRICE
    boosted_squad = solve_optimal_squad(others, my_squad + [player], remaining_budget, slots_left - 1)
    boosted_ovr = player["overall"] + sum(p["overall"] for p in boosted_squad) if boosted_squad else 0

    marginal_value = max(0, boosted_ovr - baseline_ovr)

    # --- Need-based premium ---
    need_premium = 0
    role = player["role"]

    # Bowling scarcity premium
    if analysis["bowlers_needed"] > 0 and _can_bowl(player):
        # Count how many unsold players can also bowl
        available_bowlers = sum(1 for p in unsold_players if _can_bowl(p))
        scarcity = max(0, analysis["bowlers_needed"] - available_bowlers + 1)
        need_premium += scarcity * 3 + player["bowling"] * 0.5

    # Role scarcity premium
    if role in analysis["role_needs"]:
        same_role_available = sum(1 for p in unsold_players if p["role"] == role)
        if same_role_available <= slots_left:
            need_premium += 5  # scarce role
        else:
            need_premium += 2

    # Tier premium
    tier_premium = {1: 8, 2: 4, 3: 1, 4: 0}.get(player["tier"], 0)

    # --- Compute recommended max bid ---
    raw_max = BASE_PRICE + marginal_value * 1.5 + need_premium + tier_premium

    # Apply diminishing returns for very high bids
    if raw_max > 30:
        raw_max = 30 + (raw_max - 30) * 0.5

    recommended = min(int(round(raw_max)), hard_max)
    recommended = max(recommended, BASE_PRICE)

    # --- Verdict ---
    if marginal_value >= 3:
        verdict = "🟢 MUST BUY"
        verdict_detail = "This player significantly boosts your team's overall rating."
    elif marginal_value >= 1:
        verdict = "🟡 GOOD BUY"
        verdict_detail = "Solid addition — worth bidding above base price."
    elif role in analysis["role_needs"]:
        verdict = "🟡 NEED-BASED BUY"
        verdict_detail = f"Your team needs a {role} — this fills a gap."
    elif _can_bowl(player) and analysis["bowlers_needed"] > 0:
        verdict = "🟡 BOWLING NEED"
        verdict_detail = f"You need {analysis['bowlers_needed']} more bowling options."
    else:
        verdict = "🔴 SKIP / BASE ONLY"
        verdict_detail = "Limited marginal value. Only buy at base price if needed."

    return {
        "player": player,
        "recommended_max": recommended,
        "hard_max": hard_max,
        "marginal_value": round(marginal_value, 1),
        "need_premium": round(need_premium, 1),
        "tier_premium": tier_premium,
        "verdict": verdict,
        "verdict_detail": verdict_detail,
        "baseline_ovr": round(baseline_ovr, 1),
        "boosted_ovr": round(boosted_ovr, 1),
    }


def get_ranked_recommendations(unsold_players, my_squad, budget_remaining, slots_left):
    """
    Rank all unsold players by recommendation score for Abhijeet.

    Returns:
        list of dicts sorted by priority (highest first), each with:
        - player info
        - recommendation score
        - max bid
        - verdict
    """
    if not unsold_players or slots_left <= 0:
        return []

    analysis = analyze_squad_needs(my_squad)

    # Get MILP optimal squad
    optimal_picks = solve_optimal_squad(unsold_players, my_squad, budget_remaining, slots_left)
    optimal_ids = {p["id"] for p in optimal_picks}

    recommendations = []
    for p in unsold_players:
        # Value score
        value = _player_value_score(p, analysis["role_needs"])

        # MILP bonus: if optimizer picked this player
        milp_bonus = 5.0 if p["id"] in optimal_ids else 0.0

        # Bowling need bonus
        bowl_need_bonus = 0
        if analysis["bowlers_needed"] > 0 and _can_bowl(p):
            bowl_need_bonus = analysis["bowlers_needed"] * 2.0

        # Role scarcity
        role_scarcity = 0
        if p["role"] in analysis["role_needs"]:
            same_role = sum(1 for u in unsold_players if u["role"] == p["role"])
            role_scarcity = max(0, 3.0 - same_role * 0.3)

        # Composite score
        score = round(value + milp_bonus + bowl_need_bonus + role_scarcity, 2)

        # Quick bid recommendation
        bid_info = recommend_max_bid(p, my_squad, unsold_players, budget_remaining, slots_left)

        recommendations.append({
            **p,
            "score": score,
            "in_optimal": p["id"] in optimal_ids,
            "recommended_max": bid_info["recommended_max"],
            "verdict": bid_info["verdict"],
            "verdict_detail": bid_info["verdict_detail"],
            "marginal_value": bid_info["marginal_value"],
        })

    recommendations.sort(key=lambda x: -x["score"])
    return recommendations
