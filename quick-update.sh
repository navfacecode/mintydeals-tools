#!/bin/bash
set -e

if [ "$#" -ne 8 ]; then
  echo "Usage: ./quick-update.sh DRAW_CODE LOTTERY_NAME 1ST_TICKET 1ST_LOC 2ND_TICKET 2ND_LOC 3RD_TICKET 3RD_LOC"
  exit 1
fi

DRAW_CODE="$1"
LOTTERY_NAME="$2"
FIRST_TICKET="$3"
FIRST_LOC="$4"
SECOND_TICKET="$5"
SECOND_LOC="$6"
THIRD_TICKET="$7"
THIRD_LOC="$8"

DATE=$(date +%Y-%m-%d)
DATE_DISPLAY=$(date +"%d %B %Y")
DATE_UPPER=$(date +"%d %B %Y" | tr '[:lower:]' '[:upper:]')
DAY_NAME=$(date +"%A")
DATE_NUMERIC=$(date +"%d.%m.%Y")

FIRST_COMPACT=$(echo "$FIRST_TICKET" | tr -d ' ')
SECOND_COMPACT=$(echo "$SECOND_TICKET" | tr -d ' ')
THIRD_COMPACT=$(echo "$THIRD_TICKET" | tr -d ' ')

LOTTERY_UPPER=$(echo "$LOTTERY_NAME" | tr '[:lower:]' '[:upper:]')

echo ""
echo "Updating: $LOTTERY_NAME $DRAW_CODE ($DAY_NAME, $DATE_DISPLAY)"
echo "  1st: $FIRST_TICKET ($FIRST_LOC)"
echo "  2nd: $SECOND_TICKET ($SECOND_LOC)"
echo "  3rd: $THIRD_TICKET ($THIRD_LOC)"
echo ""

FILE="kerala-lottery-result-today/index.html"
cp "$FILE" "$FILE.bak"

DRAW_CODE="$DRAW_CODE" LOTTERY_NAME="$LOTTERY_NAME" LOTTERY_UPPER="$LOTTERY_UPPER" \
FIRST_TICKET="$FIRST_TICKET" FIRST_LOC="$FIRST_LOC" \
SECOND_TICKET="$SECOND_TICKET" SECOND_LOC="$SECOND_LOC" \
THIRD_TICKET="$THIRD_TICKET" THIRD_LOC="$THIRD_LOC" \
DATE="$DATE" DATE_DISPLAY="$DATE_DISPLAY" DATE_UPPER="$DATE_UPPER" DAY_NAME="$DAY_NAME" DATE_NUMERIC="$DATE_NUMERIC" \
FIRST_COMPACT="$FIRST_COMPACT" SECOND_COMPACT="$SECOND_COMPACT" THIRD_COMPACT="$THIRD_COMPACT" \
FILE="$FILE" \
python3 << 'PYEOF'
import re, os

DRAW_CODE = os.environ['DRAW_CODE']
LOTTERY_NAME = os.environ['LOTTERY_NAME']
LOTTERY_UPPER = os.environ['LOTTERY_UPPER']
FIRST_TICKET = os.environ['FIRST_TICKET']
FIRST_LOC = os.environ['FIRST_LOC']
SECOND_TICKET = os.environ['SECOND_TICKET']
SECOND_LOC = os.environ['SECOND_LOC']
THIRD_TICKET = os.environ['THIRD_TICKET']
THIRD_LOC = os.environ['THIRD_LOC']
DATE = os.environ['DATE']
DATE_DISPLAY = os.environ['DATE_DISPLAY']
DATE_UPPER = os.environ['DATE_UPPER']
DAY_NAME = os.environ['DAY_NAME']
DATE_NUMERIC = os.environ['DATE_NUMERIC']
FIRST_COMPACT = os.environ['FIRST_COMPACT']
SECOND_COMPACT = os.environ['SECOND_COMPACT']
THIRD_COMPACT = os.environ['THIRD_COMPACT']
FILE = os.environ['FILE']

with open(FILE, "r") as f:
    html = f.read()

# 1. Update TODAYS_RESULT JS object
new_result = f"""const TODAYS_RESULT = {{
  drawCode: '{DRAW_CODE}',
  drawName: '{LOTTERY_NAME}',
  drawDate: '{DATE}',
  firstPrize: {{ ticket: '{FIRST_TICKET}', location: '{FIRST_LOC}' }},
  secondPrize: {{ ticket: '{SECOND_TICKET}', location: '{SECOND_LOC}', amount: '\u20B930 Lakh' }},
  thirdPrize: {{ ticket: '{THIRD_TICKET}', location: '{THIRD_LOC}', amount: '\u20B95 Lakh' }},
  consolationSeries: [],
  allWinningTickets: {{
    '1st': '{FIRST_COMPACT}',
    '2nd': '{SECOND_COMPACT}',
    '3rd': '{THIRD_COMPACT}',
    '4th': [],
    'consolation': []
  }}
}};"""

pattern = r'const TODAYS_RESULT = \{[^;]+\};'
html = re.sub(pattern, new_result, html, count=1, flags=re.DOTALL)

# 2. Update <title>
new_title = f"Kerala Lottery Result Today LIVE 3 PM | {LOTTERY_NAME} {DRAW_CODE} {DATE_NUMERIC} \u2014 Winning Numbers"
html = re.sub(r'<title>.*?</title>', f'<title>{new_title}</title>', html, count=1)

# 3. Update H1
html = re.sub(
    r'<h1>Kerala Lottery Result.*?</h1>',
    f'<h1>Kerala Lottery Result <em>Today</em> \u2014 {LOTTERY_NAME} {DRAW_CODE}</h1>',
    html, count=1, flags=re.DOTALL
)

# 4. Update top live bar
html = re.sub(
    r'NEXT DRAW:\s*[A-Z\s]+?\s+[A-Z]{2}-\d+\s*\u00B7\s*TODAY\s+\d+\s+[A-Z]+\s+\d{4}\s*AT\s*3:00\s*PM',
    f'NEXT DRAW: {LOTTERY_UPPER} {DRAW_CODE} \u00B7 TODAY {DATE_UPPER} AT 3:00 PM',
    html, count=1
)

# 5. Update hero tag "LIVE · 17 MAY 2026 · 3:00 PM IST"
html = re.sub(
    r'LIVE\s*\u00B7\s*\d+\s+[A-Z]+\s+\d{4}\s*\u00B7\s*3:00\s*PM\s*IST',
    f'LIVE \u00B7 {DATE_UPPER} \u00B7 3:00 PM IST',
    html, count=1
)

# 6. Update hero date "📅 **17 May 2026**"
html = re.sub(
    r'\ud83d\udcc5\s*<strong>\d+\s+[A-Za-z]+\s+\d{4}</strong>',
    f'\ud83d\udcc5 <strong>{DATE_DISPLAY}</strong>',
    html, count=1
)

# 7. Update result card H2 "Samrudhi SM-55 — Today's Result"
html = re.sub(
    r'<h2>[A-Za-z\s]+\s+[A-Z]{2}-\d+\s*\u2014\s*Today\'s Result</h2>',
    f"<h2>{LOTTERY_NAME} {DRAW_CODE} \u2014 Today's Result</h2>",
    html, count=1
)

# 8. Update result card subtitle "Sunday, 17 May 2026 · Draw No: SM-55"
html = re.sub(
    r'<div class="date">[A-Za-z]+day,\s*\d+\s+[A-Za-z]+\s+\d{4}\s*\u00B7\s*Draw No:\s*[A-Z]{2}-\d+</div>',
    f'<div class="date">{DAY_NAME}, {DATE_DISPLAY} \u00B7 Draw No: {DRAW_CODE}</div>',
    html, count=1
)

# 9. Update meta description
new_desc = f"Kerala Lottery Result Today LIVE at 3 PM. Check {LOTTERY_NAME} {DRAW_CODE} {DATE_NUMERIC} winning numbers, 1st prize \u20B91 Crore, full prize structure & PDF. Scan ticket instantly. Updated daily."
html = re.sub(
    r'<meta name="description" content="[^"]*">',
    f'<meta name="description" content="{new_desc}">',
    html, count=1
)

# 10. Update og:title  
html = re.sub(
    r'<meta property="og:title" content="[^"]*">',
    f'<meta property="og:title" content="Kerala Lottery Result Today LIVE 3 PM \u2014 {LOTTERY_NAME} {DRAW_CODE} Winning Numbers">',
    html, count=1
)

# 11. Update prize structure heading "Complete Prize Structure — Samrudhi SM-55"
html = re.sub(
    r'(Complete <em>Prize Structure</em>\s*\u2014\s*)[A-Za-z\s]+\s+[A-Z]{2}-\d+',
    lambda m: f'{m.group(1)}{LOTTERY_NAME} {DRAW_CODE}',
    html, count=1
)

# 12. Update footer "Last updated: 17 May 2026 at 3:00 PM IST"
html = re.sub(
    r'Last updated:\s*\d+\s+[A-Za-z]+\s+\d{4}\s+at\s+3:00 PM IST',
    f'Last updated: {DATE_DISPLAY} at 3:00 PM IST',
    html, count=1
)

with open(FILE, "w") as f:
    f.write(html)

print("HTML updated with all date/label fields")
PYEOF

echo ""
echo "Pushing to GitHub..."
git add "$FILE"
git commit -m "Daily: $LOTTERY_NAME $DRAW_CODE - $DATE_DISPLAY" || echo "Nothing to commit"
git push

echo ""
echo "DONE! Live at: https://tools.mintydeals.com/kerala-lottery-result-today/"
