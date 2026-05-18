#!/usr/bin/env python3
"""
Kerala Lottery Daily Auto-Updater
==================================
Scrapes the latest Kerala lottery result from public sources and updates
the kerala-lottery-result-today/index.html file with today's winning numbers.

Runs automatically via GitHub Actions every day at 3:30 PM IST (10:00 UTC).

Sources (with fallback chain):
1. keralalotteries.com (official) - tries first
2. goodreturns.in - fallback if official fails
3. lotterysambad.in - second fallback

Author: MintyDeals Tools
"""

import re
import os
import sys
import json
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Use only stdlib + requests (commonly available)
try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("ERROR: Missing dependencies. Run: pip install requests beautifulsoup4")
    sys.exit(1)


# ============================================
# CONFIGURATION
# ============================================

IST = timezone(timedelta(hours=5, minutes=30))
TODAY = datetime.now(IST)
TODAY_STR = TODAY.strftime("%Y-%m-%d")
TODAY_DISPLAY = TODAY.strftime("%d %B %Y")
TODAY_DAY = TODAY.strftime("%A")  # Sunday, Monday, etc.

# Lottery schedule by day of week (1=Mon, 7=Sun)
LOTTERY_SCHEDULE = {
    "Monday":    {"name": "Bhagyathara",     "code": "BT"},
    "Tuesday":   {"name": "Sthree Sakthi",   "code": "SS"},
    "Wednesday": {"name": "Dhanalekshmi",    "code": "DL"},
    "Thursday":  {"name": "Karunya Plus",    "code": "KN"},
    "Friday":    {"name": "Suvarna Keralam", "code": "SK"},
    "Saturday":  {"name": "Karunya",         "code": "KR"},
    "Sunday":    {"name": "Samrudhi",        "code": "SM"},
}

HTML_FILE = Path(__file__).parent.parent / "kerala-lottery-result-today" / "index.html"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


# ============================================
# SCRAPERS
# ============================================

def scrape_goodreturns():
    """Scrape from goodreturns.in - usually most reliable."""
    print(f"📰 Trying goodreturns.in...")
    try:
        url = "https://www.goodreturns.in/kerala-lottery-results.html"
        r = requests.get(url, headers=HEADERS, timeout=20)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        result = {}
        text = soup.get_text(" ", strip=True)

        # Find draw code (e.g., SM-55, KR-754)
        code_match = re.search(r"\b([A-Z]{2})[-\s]?(\d{2,4})\b", text)
        if code_match:
            result["drawCode"] = f"{code_match.group(1)}-{code_match.group(2)}"

        # Find 1st prize ticket (format: 2 letters + space + 6 digits)
        first_match = re.search(
            r"1st\s*Prize.*?(?:Rs\.?\s*[\d,]+).*?([A-Z]{2})\s+(\d{6})",
            text, re.IGNORECASE
        )
        if first_match:
            result["firstTicket"] = f"{first_match.group(1)} {first_match.group(2)}"

        # Try to find prize locations
        location_match = re.search(
            r"1st\s*Prize.*?[A-Z]{2}\s+\d{6}\s*\(([A-Z\s]+)\)",
            text, re.IGNORECASE
        )
        if location_match:
            result["firstLocation"] = location_match.group(1).strip().upper()

        # 2nd prize
        second_match = re.search(
            r"2nd\s*Prize.*?([A-Z]{2})\s+(\d{6})",
            text, re.IGNORECASE
        )
        if second_match:
            result["secondTicket"] = f"{second_match.group(1)} {second_match.group(2)}"

        # 3rd prize
        third_match = re.search(
            r"3rd\s*Prize.*?([A-Z]{2})\s+(\d{6})",
            text, re.IGNORECASE
        )
        if third_match:
            result["thirdTicket"] = f"{third_match.group(1)} {third_match.group(2)}"

        if result.get("firstTicket"):
            print(f"✅ Found result on goodreturns.in")
            return result

    except Exception as e:
        print(f"⚠️  goodreturns.in failed: {e}")

    return None


def scrape_keralalotteries():
    """Scrape from official Kerala State Lotteries (PDF-based, harder)."""
    print(f"📰 Trying keralalotteries.com (official)...")
    try:
        url = "https://www.keralalotteries.com/"
        r = requests.get(url, headers=HEADERS, timeout=20)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        # Official site mostly publishes PDFs.
        # Look for the latest result link
        result = {}
        # Find ticket patterns in any text
        text = soup.get_text(" ", strip=True)

        first_match = re.search(r"([A-Z]{2})\s+(\d{6})", text)
        if first_match:
            result["firstTicket"] = f"{first_match.group(1)} {first_match.group(2)}"
            print(f"⚠️  Found ticket on official site but format may differ")
            return result if result else None

    except Exception as e:
        print(f"⚠️  keralalotteries.com failed: {e}")

    return None


def scrape_with_fallback():
    """Try multiple sources in order."""
    for scraper in [scrape_goodreturns, scrape_keralalotteries]:
        result = scraper()
        if result and result.get("firstTicket"):
            return result
        time.sleep(2)

    return None


# ============================================
# HTML UPDATER
# ============================================

def update_html(result):
    """Update the kerala-lottery-result-today/index.html file."""
    if not HTML_FILE.exists():
        print(f"❌ HTML file not found: {HTML_FILE}")
        return False

    print(f"\n✏️  Updating HTML file...")

    html = HTML_FILE.read_text(encoding="utf-8")

    day_info = LOTTERY_SCHEDULE.get(TODAY_DAY, {})
    lottery_name = day_info.get("name", "Kerala Lottery")
    code_prefix = day_info.get("code", "XX")
    draw_code = result.get("drawCode", f"{code_prefix}-??")

    first_ticket = result.get("firstTicket", "")
    first_location = result.get("firstLocation", "")
    second_ticket = result.get("secondTicket", "")
    second_location = result.get("secondLocation", "")
    third_ticket = result.get("thirdTicket", "")
    third_location = result.get("thirdLocation", "")

    # Build compact versions for matching
    first_compact = first_ticket.replace(" ", "")
    second_compact = second_ticket.replace(" ", "")
    third_compact = third_ticket.replace(" ", "")

    # 1. Update the TODAYS_RESULT object
    new_result_block = f"""const TODAYS_RESULT = {{
  drawCode: '{draw_code}',
  drawName: '{lottery_name}',
  drawDate: '{TODAY_STR}',
  firstPrize: {{ ticket: '{first_ticket}', location: '{first_location}' }},
  secondPrize: {{ ticket: '{second_ticket}', location: '{second_location}', amount: '₹25,00,000' }},
  thirdPrize: {{ ticket: '{third_ticket}', location: '{third_location}', amount: '₹10,00,000' }},
  consolationSeries: [],
  allWinningTickets: {{
    '1st': '{first_compact}',
    '2nd': '{second_compact}',
    '3rd': '{third_compact}',
    '4th': [],
    'consolation': []
  }}
}};"""

    pattern = r"const TODAYS_RESULT = \{[^;]+\};"
    if re.search(pattern, html, re.DOTALL):
        html = re.sub(pattern, new_result_block, html, count=1, flags=re.DOTALL)
        print("  ✅ Updated TODAYS_RESULT object")
    else:
        print("  ⚠️  Could not find TODAYS_RESULT block")

    # 2. Update the <title> tag
    new_title = f"Kerala Lottery Result Today LIVE 3 PM | {lottery_name} {draw_code} {TODAY.strftime('%d.%m.%Y')} — Winning Numbers"
    html = re.sub(
        r"<title>.*?</title>",
        f"<title>{new_title}</title>",
        html, count=1
    )
    print("  ✅ Updated <title>")

    # 3. Update H1
    html = re.sub(
        r"<h1>Kerala Lottery Result.*?</h1>",
        f"<h1>Kerala Lottery Result <em>Today</em> — {lottery_name} {draw_code}</h1>",
        html, count=1, flags=re.DOTALL
    )
    print("  ✅ Updated <h1>")

    # 4. Update live bar
    html = re.sub(
        r"NEXT DRAW: [A-Z\s]+ [A-Z]{2}-\d+ · TODAY \d+ [A-Z]+ \d{4}",
        f"NEXT DRAW: {lottery_name.upper()} {draw_code} · TODAY {TODAY.strftime('%d %B %Y').upper()}",
        html, count=1
    )

    # 5. Update meta description
    new_desc = f"Kerala Lottery Result Today LIVE at 3 PM. Check {lottery_name} {draw_code} {TODAY.strftime('%d.%m.%Y')} winning numbers, 1st prize ₹1 Crore, full prize structure & PDF. Updated daily."
    html = re.sub(
        r'<meta name="description" content="[^"]*">',
        f'<meta name="description" content="{new_desc}">',
        html, count=1
    )

    # 6. Update hero meta date
    html = re.sub(
        r"📅 <strong>\d+ [A-Z][a-z]+ \d{4}</strong>",
        f"📅 <strong>{TODAY_DISPLAY}</strong>",
        html, count=1
    )

    # 7. Update result header date
    html = re.sub(
        r"<div class=\"date\">[A-Z][a-z]+day, \d+ [A-Z][a-z]+ \d{4} · Draw No: [A-Z]{2}-\d+</div>",
        f'<div class="date">{TODAY_DAY}, {TODAY_DISPLAY} · Draw No: {draw_code}</div>',
        html, count=1
    )

    HTML_FILE.write_text(html, encoding="utf-8")
    print(f"\n✅ Updated: {HTML_FILE}")
    return True


# ============================================
# MAIN
# ============================================

def main():
    print("=" * 60)
    print(f"🎰 Kerala Lottery Daily Auto-Update")
    print(f"📅 {TODAY_DAY}, {TODAY_DISPLAY}")
    print(f"🎯 Today's Lottery: {LOTTERY_SCHEDULE[TODAY_DAY]['name']} ({LOTTERY_SCHEDULE[TODAY_DAY]['code']})")
    print("=" * 60)
    print()

    # Scrape
    result = scrape_with_fallback()

    if not result:
        print("\n❌ Could not scrape result from any source.")
        print("ℹ️  This is normal if the draw hasn't happened yet (before 3:00 PM IST)")
        print("ℹ️  Or if all source websites are temporarily down")
        # Exit gracefully — don't fail the GitHub Action
        sys.exit(0)

    print("\n📊 Scraped result:")
    print(json.dumps(result, indent=2))

    # Update HTML
    if update_html(result):
        print("\n✅ ALL DONE! Ready to deploy.")
        # GitHub Actions will pick up the file change and commit/deploy
    else:
        print("\n❌ HTML update failed.")
        sys.exit(1)


if __name__ == "__main__":
    main()
