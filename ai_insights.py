"""
🤖 CricBazaar — AI Insights Engine (Ollama + Gemma3:4b)
Connects to local Ollama instance running gemma3:4b model
to provide natural language auction strategy insights.
"""

import requests
import json


OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "gemma3:4b"


def _call_ollama(prompt, timeout=60):
    """
    Call local Ollama API with gemma3:4b model.
    Returns the generated text or an error message.
    """
    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL_NAME,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "num_predict": 1024,
                },
            },
            timeout=timeout,
        )
        if response.status_code == 200:
            data = response.json()
            return data.get("response", "No response generated.")
        else:
            return f"⚠️ Ollama returned status {response.status_code}: {response.text}"
    except requests.exceptions.ConnectionError:
        return (
            "⚠️ Cannot connect to Ollama. Make sure Ollama is running locally.\n\n"
            "**Setup instructions:**\n"
            "1. Install Ollama: `brew install ollama` (macOS) or visit https://ollama.ai\n"
            "2. Pull the model: `ollama pull gemma3:4b`\n"
            "3. Start Ollama: `ollama serve`\n"
            "4. Refresh this page."
        )
    except requests.exceptions.Timeout:
        return "⚠️ Ollama request timed out. The model might be loading — try again in a few seconds."
    except Exception as e:
        return f"⚠️ Error calling Ollama: {str(e)}"


def check_ollama_status():
    """Check if Ollama is running and gemma3:4b model is available."""
    try:
        # Check if Ollama is running
        resp = requests.get("http://localhost:11434/api/tags", timeout=5)
        if resp.status_code != 200:
            return False, "Ollama is not responding."

        models = resp.json().get("models", [])
        model_names = [m.get("name", "") for m in models]

        # Check for gemma3:4b (might be listed as gemma3:4b or gemma3:4b-latest)
        has_model = any("gemma3" in name for name in model_names)
        if not has_model:
            return False, f"Model gemma3:4b not found. Available: {', '.join(model_names) if model_names else 'None'}. Run `ollama pull gemma3:4b`."

        return True, "✅ Ollama is running with gemma3:4b model."
    except requests.exceptions.ConnectionError:
        return False, "Ollama is not running. Start it with `ollama serve`."
    except Exception as e:
        return False, f"Error checking Ollama: {str(e)}"


def _format_squad_summary(squad):
    """Format squad data into a concise text summary for the LLM."""
    if not squad:
        return "Empty squad"
    lines = []
    for p in squad:
        tag = f" [{p.get('tag', 'Auction')}]" if p.get('tag') else ""
        price = f", Price: ₹{p['sold_price']}L" if p.get('sold_price', 0) > 0 else ""
        lines.append(
            f"  - {p['name']}{tag}: {p['role']}, "
            f"Bat={p['batting']}, Bowl={p['bowling']}, Field={p['fielding']}, "
            f"OVR={p['overall']}, Tier {p['tier']}{price}"
        )
    return "\n".join(lines)


def _format_player_summary(player):
    """Format a single player for the prompt."""
    return (
        f"{player['name']}: {player['role']}, "
        f"Bat={player['batting']}, Bowl={player['bowling']}, Field={player['fielding']}, "
        f"OVR={player['overall']}, Tier {player['tier']}"
    )


def _format_unsold_pool(unsold_players, limit=36):
    """Format the unsold player pool for the prompt."""
    lines = []
    for p in sorted(unsold_players, key=lambda x: -x['overall'])[:limit]:
        lines.append(
            f"  - {p['name']}: {p['role']}, "
            f"Bat={p['batting']}, Bowl={p['bowling']}, Field={p['fielding']}, "
            f"OVR={p['overall']}, Tier {p['tier']}"
        )
    return "\n".join(lines) if lines else "No unsold players remaining."


def _format_all_teams(all_teams_data):
    """Format all teams data for context."""
    lines = []
    for team_name, team_info in all_teams_data.items():
        lines.append(f"\n**{team_name}** (Budget left: ₹{team_info['budget_left']}L, "
                      f"Slots left: {team_info['slots_left']}/9):")
        for p in team_info['squad']:
            tag = f" [{p.get('tag', '')}]" if p.get('tag') else ""
            lines.append(f"  - {p['name']}{tag}: {p['role']}, OVR={p['overall']}")
    return "\n".join(lines)


def _format_auction_log(auction_log_data):
    """Format auction log for context."""
    if not auction_log_data:
        return "No players sold yet."
    lines = []
    for entry in auction_log_data:
        lines.append(f"  - {entry['name']} → {entry['team']} for ₹{entry['price']}L "
                      f"(Tier {entry['tier']}, {entry['role']}, OVR={entry['overall']})")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════
# PUBLIC API — AI INSIGHT FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════

def get_bid_advice(
    player,
    my_squad,
    unsold_players,
    budget_remaining,
    slots_left,
    squad_needs,
    optimizer_recommendation,
    all_teams_data,
):
    """
    Get AI advice on how much to bid for the current player.
    Considers team needs, player value, competition from other teams,
    remaining budget, and future players in the pool.
    """
    prompt = f"""You are an expert cricket auction strategist advising team captain "Abhijeet" in a fantasy cricket auction.

## AUCTION RULES:
- 4 teams, each gets 11 players (2 pre-assigned: Captain + Vice-Captain, 9 from auction)
- Each team starts with ₹100L budget
- Base price: ₹5L per player, Bid increment: ₹1L
- Player ratings: Batting, Bowling, Fielding (0-10 scale)
- Overall = Bat*40% + Bowl*35% + Field*25%

## CURRENT PLAYER UP FOR AUCTION:
{_format_player_summary(player)}

## ABHIJEET'S CURRENT SQUAD:
{_format_squad_summary(my_squad)}

## SQUAD NEEDS:
- Budget remaining: ₹{budget_remaining}L
- Auction slots left: {slots_left}/9
- Batsmen: {squad_needs['bat_count']} | Bowlers: {squad_needs['bowl_count']} | All-rounders: {squad_needs['ar_count']}
- Bowlers who can bowl (bowl≥4): {squad_needs['bowlers_who_can_bowl']}/6 needed
- Gaps: {', '.join(squad_needs['role_needs']) if squad_needs['role_needs'] else 'None'}

## OPTIMIZER RECOMMENDATION:
- Verdict: {optimizer_recommendation.get('verdict', 'N/A')}
- Recommended max bid: ₹{optimizer_recommendation.get('recommended_max', 'N/A')}L
- Marginal value: +{optimizer_recommendation.get('marginal_value', 0)} OVR
- In optimal squad: {optimizer_recommendation.get('in_optimal', False)}

## OTHER TEAMS (they will also bid based on player ratings):
{_format_all_teams(all_teams_data)}

## REMAINING UNSOLD PLAYERS (future auction picks):
{_format_unsold_pool(unsold_players)}

## YOUR TASK:
Analyze and provide:
1. **BID RECOMMENDATION**: Exact max bid amount (₹L) with reasoning
2. **COMPETITION ANALYSIS**: Which other teams likely want this player and why (based on their needs & budgets)
3. **RISK ASSESSMENT**: What happens if you overpay vs. miss this player
4. **ALTERNATIVE PLAYERS**: Better/cheaper alternatives still in the pool
5. **STRATEGY**: Should you bid aggressively, conservatively, or skip?

Be specific with numbers. Keep it concise and actionable. Use cricket auction terminology."""

    return _call_ollama(prompt)


def get_best_team_analysis(
    my_squad,
    unsold_players,
    budget_remaining,
    slots_left,
    squad_needs,
    optimal_picks,
    all_teams_data,
):
    """
    Get AI analysis of the best possible team Abhijeet can build
    from the current position.
    """
    optimal_text = _format_squad_summary(optimal_picks) if optimal_picks else "No optimal picks available."

    prompt = f"""You are an expert cricket team builder advising "Abhijeet" in a fantasy cricket auction.

## AUCTION RULES:
- 4 teams, 11 players each (2 fixed + 9 auction), ₹100L budget per team
- Ratings: Batting, Bowling, Fielding (0-10), Overall = Bat*40% + Bowl*35% + Field*25%
- Need at least 6 players who can bowl (bowl≥4) in final 11

## ABHIJEET'S CURRENT SQUAD ({len(my_squad)}/11):
{_format_squad_summary(my_squad)}

## SQUAD STATUS:
- Budget remaining: ₹{budget_remaining}L
- Auction slots left: {slots_left}
- Batsmen: {squad_needs['bat_count']} | Bowlers: {squad_needs['bowl_count']} | All-rounders: {squad_needs['ar_count']}
- Can bowl: {squad_needs['bowlers_who_can_bowl']}/6

## MILP OPTIMIZER'S BEST PICKS:
{optimal_text}

## OTHER TEAMS' SQUADS:
{_format_all_teams(all_teams_data)}

## ALL UNSOLD PLAYERS:
{_format_unsold_pool(unsold_players)}

## YOUR TASK:
Provide a comprehensive analysis:
1. **DREAM TEAM**: The ideal 11 Abhijeet should target (current squad + best picks from unsold pool)
2. **PRIORITY TARGETS**: Top 3 must-buy players ranked by importance, with max bid for each
3. **BUDGET STRATEGY**: How to distribute ₹{budget_remaining}L across {slots_left} slots (spend big on who, save on who)
4. **THREAT ANALYSIS**: Which players will other teams fight for, driving up prices?
5. **BACKUP PLAN**: If top targets are sniped, who are the fallback options?
6. **TEAM RATING FORECAST**: Expected squad overall rating if strategy succeeds

Be specific, use player names and numbers. Think like an IPL team strategist."""

    return _call_ollama(prompt, timeout=90)


def get_live_auction_insight(
    current_player,
    my_squad,
    unsold_players,
    budget_remaining,
    slots_left,
    squad_needs,
    all_teams_data,
    auction_log_data,
):
    """
    Real-time AI insight during live auction — quick actionable advice.
    """
    prompt = f"""You are a quick-thinking cricket auction advisor. Give FAST, ACTIONABLE advice.

## PLAYER ON THE BLOCK:
{_format_player_summary(current_player)}

## MY TEAM (Abhijeet):
- Squad: {len(my_squad)}/11 | Budget: ₹{budget_remaining}L | Slots left: {slots_left}
- Needs: {', '.join(squad_needs['role_needs']) if squad_needs['role_needs'] else 'Balanced'}
- Can bowl count: {squad_needs['bowlers_who_can_bowl']}/6

## RECENT AUCTION SALES:
{_format_auction_log(auction_log_data[-5:] if len(auction_log_data) > 5 else auction_log_data)}

## COMPETITION:
{_format_all_teams(all_teams_data)}

## KEY UNSOLD PLAYERS (similar role):
{_format_unsold_pool([p for p in unsold_players if p['role'] == current_player['role']][:5])}

Give a QUICK 3-line response:
1. 🎯 BID or SKIP? (and max amount)
2. 💡 Why? (one sentence)
3. ⚠️ Watch out for? (which team will compete)"""

    return _call_ollama(prompt, timeout=30)


def get_post_auction_review(
    my_squad,
    budget_remaining,
    squad_needs,
    all_teams_data,
):
    """
    Post-auction or mid-auction team review and power ranking.
    """
    prompt = f"""You are a cricket analyst reviewing all 4 teams after/during an auction.

## ABHIJEET'S SQUAD:
{_format_squad_summary(my_squad)}
Budget remaining: ₹{budget_remaining}L

## ALL TEAMS:
{_format_all_teams(all_teams_data)}

## SQUAD NEEDS (Abhijeet):
- Batsmen: {squad_needs['bat_count']} | Bowlers: {squad_needs['bowl_count']} | ARs: {squad_needs['ar_count']}
- Can bowl: {squad_needs['bowlers_who_can_bowl']}/6

Provide:
1. **POWER RANKINGS**: Rank all 4 teams with strengths & weaknesses
2. **ABHIJEET'S GRADE**: A-F grade with justification
3. **BEST BUYS**: Top 3 value-for-money picks across all teams
4. **OVERPAYS**: Any players bought above fair value
5. **PREDICTION**: Which team looks strongest for the tournament?

Be honest and analytical. Use player names and stats."""

    return _call_ollama(prompt, timeout=90)


def get_player_comparison(player1, player2, my_squad, squad_needs, budget_remaining):
    """
    Compare two players head-to-head for auction decision.
    """
    prompt = f"""Compare these two cricket players for team "Abhijeet":

## PLAYER 1:
{_format_player_summary(player1)}

## PLAYER 2:
{_format_player_summary(player2)}

## MY TEAM NEEDS:
- Batsmen: {squad_needs['bat_count']} | Bowlers: {squad_needs['bowl_count']} | ARs: {squad_needs['ar_count']}
- Can bowl: {squad_needs['bowlers_who_can_bowl']}/6 needed
- Budget: ₹{budget_remaining}L
- Gaps: {', '.join(squad_needs['role_needs']) if squad_needs['role_needs'] else 'None'}

## CURRENT SQUAD:
{_format_squad_summary(my_squad)}

Compare:
1. **HEAD TO HEAD**: Stats comparison
2. **FIT FOR TEAM**: Who fills gaps better?
3. **VALUE**: Who's worth more in auction?
4. **VERDICT**: Pick one and explain why

Keep it short and decisive."""

    return _call_ollama(prompt, timeout=30)
