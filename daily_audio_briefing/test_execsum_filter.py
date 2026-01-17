#!/usr/bin/env python3
"""Test script to verify ExecSum filtering logic against known content."""

import json
import os

# Load the config
config_path = os.path.join(os.path.dirname(__file__), 'extraction_instructions', 'execsum.json')
with open(config_path, 'r') as f:
    config = json.load(f)

# Combined training data from Dec 24 + Dec 29 newsletters
test_items = [
    # === DEC 24 NEWSLETTER ===
    {"title": "Wall Street is making markets for tariff refund rights", "context": "Tariff refund rights market (RT)", "expected": False},
    {"title": "Trump says anybody that disagrees with him will never be Fed chair", "context": "Trump on Fed chair (RT)", "expected": False},
    {"title": "US economy grew 4.3% YoY in Q3 at fastest pace in two years", "context": "GDP growth report (CNBC)", "expected": True},
    {"title": "US consumer confidence fell for a fifth-straight month", "context": "Consumer confidence data (BBG)", "expected": True},
    {"title": "US accused China of unfair chip trade practices", "context": "US-China chip trade (FT)", "expected": False},
    {"title": "Major central banks delivered biggest easing since 2008 crisis this year", "context": "Central bank easing (RT)", "expected": True},
    {"title": "Bessent wants to revamp Fed hard 2% inflation target", "context": "Fed inflation target (BBG)", "expected": True},
    {"title": "US investment grade bond sales teased record with $1.7T year", "context": "Bond sales record (FT)", "expected": False},
    {"title": "Global tech bond sales surged to a record $430B on AI frenzy", "context": "Tech bond sales AI (RT)", "expected": False},
    {"title": "US-listed ETF inflows hit a record $1.4T this year", "context": "ETF inflows record (BBG)", "expected": False},
    {"title": "Ares is looking to acquire a big PE firm amid mega fund competition", "context": "Ares PE acquisition (FT)", "expected": False},
    {"title": "Private credit firms pile into consumer debt as risk-taking mounts", "context": "Private credit consumer debt (FT)", "expected": False},
    {"title": "DoubleLine warned of brewing collision for developed economies", "context": "DoubleLine economic warning (BBG)", "expected": False},
    {"title": "CIOs see Australia private credit getting riskier amid property bets", "context": "Australia private credit (BBG)", "expected": False},
    {"title": "Foreigners bought most India stocks in two months as rupee recovers", "context": "India stocks foreign buying (BBG)", "expected": False},
    {"title": "JPMorgan took top spot in India ECM for first time since Covid", "context": "JPMorgan India ECM (BBG)", "expected": False},
    {"title": "Jane Street hired DC lobbyists", "context": "Jane Street lobbyists (BBG)", "expected": False},
    {"title": "UK richest person James Dyson is revamping his family office", "context": "Dyson family office (BBG)", "expected": False},
    {"title": "25k people expressed interest in joining new US Tech Force", "context": "US Tech Force hiring (RT)", "expected": False},
    {"title": "Luxury apartments are bringing down rent", "context": "Luxury apartments rent (BBG)", "expected": False},
    {"title": "Epstein named ex-Barclays CEO Jes Staley and ex-Harvard president Larry Summers as executors of his will", "context": "Epstein will executors (FT)", "expected": False},

    # === DEC 29 NEWSLETTER - MARKETS SECTION (user wants all) ===
    {"title": "US stocks notched fresh ATHs as Santa rally came to fruition; S&P best week in a month", "context": "Market summary - ATHs and Santa rally", "expected": True},
    {"title": "US high-yield spreads at 275 bps near 25-year lows; Italy-Germany and Spain-Germany spreads at 16-year lows", "context": "Credit spreads tightening - risk appetite", "expected": True},
    {"title": "Gold silver platinum rocketed to new ATHs on geopolitical concerns - metals up 71% 167% 169% YTD", "context": "Precious metals surge - safe haven buying", "expected": True},
    {"title": "Palladium climbed to a three-year high", "context": "Precious metals - palladium", "expected": True},
    {"title": "Dollar posted its worst week since June", "context": "Dollar weakness", "expected": True},

    # === DEC 29 NEWSLETTER - HEADLINE ROUNDUP ===
    {"title": "Trump met with Zelensky after productive call with Putin", "context": "Trump-Putin-Zelensky diplomacy (BBG)", "expected": False},
    {"title": "Japan will slow pace of QT", "context": "Japan monetary policy - QT slowdown (BBG)", "expected": True},  # User said this is fine to include
    {"title": "Investors warn of rot in PE as funds strike circular deals", "context": "PE circular deals warning (NYT)", "expected": False},
    {"title": "PE has more housecleaning to do in 2026", "context": "PE outlook 2026 (WSJ)", "expected": False},
    {"title": "PE GP stake sales are set to climb after record year", "context": "PE GP stake sales (WSJ)", "expected": False},
    {"title": "LPs bet on smaller MM PE funds as industry slows", "context": "PE fundraising shift to MM (FT)", "expected": False},
    {"title": "Tech firms moved $120B of AI debt off balance sheets via SPVs", "context": "AI debt off balance sheet SPVs (FT)", "expected": False},
    {"title": "Global dealmaking hit $4.5T in second-best year ever", "context": "M&A dealmaking record (FT)", "expected": False},
    {"title": "US tech billionaires net worth surged by $550B this year on AI boom", "context": "Tech billionaire wealth surge AI (FT)", "expected": True},
    {"title": "AI startups amassed a record $150B in funding this year", "context": "AI startup funding record (FT)", "expected": True},
    {"title": "Family offices are the new power players on Wall Street", "context": "Family offices influence (WSJ)", "expected": False},
    {"title": "Investor risk could rise as crypto and private credit go mainstream", "context": "Crypto private credit mainstream risk (RT)", "expected": False},
    {"title": "Mutual funds shed $1T in eleventh-straight annual outflow", "context": "Mutual fund outflows $1T (BBG)", "expected": False},
    {"title": "Retail inflows are set to break records this year", "context": "Retail inflows record (RT)", "expected": True},
    {"title": "Banks and traders race to capitalize on golds historic rally", "context": "Gold rally banks trading (FT)", "expected": True},  # User said this is fine to include
    {"title": "Japan small IPOs fell to a twelve-year low amid market reforms", "context": "Japan IPO decline (BBG)", "expected": False},
    {"title": "Apollo separated its lending unit from its buyout unit", "context": "Apollo restructuring (FT)", "expected": False},
    {"title": "Goldman Sachs BDC is struggling to clean up soured bets", "context": "Goldman BDC troubles (WSJ)", "expected": False},
    {"title": "15% of FTSE 100 firms replaced their CEO", "context": "FTSE CEO turnover (FT)", "expected": False},
    {"title": "Goldman Sachs client data was exposed in law firm data breach", "context": "Goldman data breach (BBG)", "expected": False},
    {"title": "North Sea suffers worst year since 1970s as drillers freeze investment", "context": "North Sea oil investment decline (FT)", "expected": False},
    {"title": "Luxury brands push into mass-market sports despite shift to exclusivity", "context": "Luxury brands sports marketing (FT)", "expected": False},
    {"title": "US and EU are officially beefing on free speech and tech regulations", "context": "US-EU tech regulation dispute (BBG)", "expected": False},
    {"title": "Tech billionaires and Congressman Khanna are beefing on a wealth tax", "context": "Wealth tax debate tech billionaires (FT)", "expected": False},

    # === DEC 29 NEWSLETTER - DEAL FLOW (mostly FALSE, except AI deals) ===
    {"title": "Nvidia will acqui-hire AI chip startup Groq in a $20B deal", "context": "Nvidia Groq acquisition $20B (DEAL)", "expected": True},
    {"title": "KKR and PAG to acquire Sapporo Real Estate for $3B", "context": "KKR Sapporo real estate $3B (DEAL)", "expected": False},
    {"title": "Honda to buy out LG battery JV assets for $2.9B", "context": "Honda LG battery $2.9B (DEAL)", "expected": False},
]


def matches_include_pattern(text, config):
    include_patterns = config.get('include_patterns', [])
    if not include_patterns:
        return True
    text_lower = text.lower()
    return any(pattern.lower() in text_lower for pattern in include_patterns)


def matches_exclude_pattern(text, config):
    exclude_patterns = config.get('exclude_patterns', [])
    text_lower = text.lower()
    return any(pattern.lower() in text_lower for pattern in exclude_patterns)


def would_include(item, config):
    """Determine if item would be included based on config."""
    combined_text = item['title'] + ' ' + item['context']

    # Check exclude patterns first
    if matches_exclude_pattern(combined_text, config):
        return False, "excluded by pattern"

    # Check include patterns if required
    if config.get('require_include_pattern', False):
        if not matches_include_pattern(combined_text, config):
            return False, "no include pattern match"

    return True, "included"


# Run the test
print("=" * 70)
print("ExecSum Filter Test Results (Dec 24 + Dec 29 Training Data)")
print("=" * 70)
print()

correct = 0
incorrect = 0
included_items = []
errors = []

for item in test_items:
    included, reason = would_include(item, config)
    expected = item['expected']

    if included == expected:
        correct += 1
    else:
        incorrect += 1
        errors.append({
            'title': item['title'][:60],
            'expected': expected,
            'got': included,
            'reason': reason
        })

    if included:
        included_items.append(item)

# Print errors first
if errors:
    print("ERRORS (Mismatches):")
    print("-" * 70)
    for err in errors:
        exp_str = "TRUE" if err['expected'] else "FALSE"
        got_str = "INCLUDE" if err['got'] else "EXCLUDE"
        print(f"✗ Expected {exp_str}, got {got_str}: {err['title']}...")
        print(f"   Reason: {err['reason']}")
    print()

print("=" * 70)
print(f"Accuracy: {correct}/{len(test_items)} ({100*correct/len(test_items):.1f}%)")
print(f"Correct: {correct}, Incorrect: {incorrect}")
print("=" * 70)
print()
print("ITEMS THAT WOULD BE INCLUDED:")
print("-" * 70)
for item in included_items:
    print(f"  • {item['title']}")
print()
print(f"Total included: {len(included_items)}")
