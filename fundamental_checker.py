"""
fundamental_checker.py
======================
Light fundamental check using Screener.in HTML parsing.

Fix: Screener uses dynamic section IDs (numbers like 6596237).
Cannot use id="quarters" — it changes per company.

Solution:
- PE from id="top-ratios" section (confirmed working)
- Profit trend from annual P&L table (more stable than quarterly)
- Use section headers like "Quarterly Results" as anchors instead of IDs
"""

import requests
import re
import time

HEADERS = {
    "User-Agent":      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept":          "text/html,application/xhtml+xml",
    "Accept-Language": "en-US,en;q=0.9",
}

_SCREENER_OVERRIDES = {
    "M&MFIN":    "M-AND-M-FINANCIAL-SERVICES",
    "M&M":       "M-AND-M",
    "BAJAJ-AUTO":"BAJAJ-AUTO",
}

_session = None

def _get_session():
    global _session
    if _session:
        return _session
    _session = requests.Session()
    _session.headers.update(HEADERS)
    try:
        _session.get("https://www.screener.in", timeout=8)
    except Exception:
        pass
    return _session


def get_fundamentals(symbol: str) -> dict:
    result = {
        "pe_ratio":       None,
        "is_profitable":  True,
        "profit_trend":   "UNKNOWN",
        "fundamental_ok": True,
        "summary":        ""
    }

    sym = _SCREENER_OVERRIDES.get(symbol, symbol)
    s   = _get_session()

    try:
        for url in [
            f"https://www.screener.in/company/{sym}/consolidated/",
            f"https://www.screener.in/company/{sym}/"
        ]:
            r = s.get(url, timeout=10)
            if r.status_code == 200:
                break
        else:
            result["summary"] = "Data unavailable"
            return result

        html = r.text

        # ── PE from top-ratios section (confirmed working) ─
        pe_patterns = [
            r'Stock P/E\s*</span>\s*\n\s*\n\s*<span[^>]*class="[^"]*number[^"]*"[^>]*>\s*([\d,.]+)',
            r'Stock P/E[\s\S]{0,200}?<span[^>]*class="[^"]*number[^"]*"[^>]*>\s*([\d,.]+)',
            r'class="nowrap value">\s*\n\s*<span[^>]*class="number">\s*([\d,.]+)',
        ]

        for pattern in pe_patterns:
            # Find all PE instances after "Stock P/E" text
            all_matches = list(re.finditer(r'Stock P/E', html))
            if all_matches:
                # Take text after first match
                pos      = all_matches[0].start()
                snippet  = html[pos:pos+300]
                num_match= re.search(r'<span[^>]*class="number">\s*([\d,.]+)', snippet)
                if num_match:
                    try:
                        pe = float(num_match.group(1).replace(",",""))
                        if 0 < pe < 10000:
                            result["pe_ratio"] = pe
                            break
                    except Exception:
                        continue

        # ── Profit trend from P&L section ─────────────────
        # Use "Quarterly Results" or "Profit & Loss" as text anchors
        profits = _extract_profits_by_text(html)
        result  = _assess_profits(profits, result)

        return result

    except Exception as e:
        result["summary"] = "Fundamental check skipped"
        return result


def _extract_profits_by_text(html: str) -> list:
    """
    Extract net profit numbers using text anchors.
    Screener always has "Net Profit" text in the P&L table
    regardless of section IDs.
    """
    profits = []

    # Find all occurrences of "Net Profit" in HTML
    # Then look at the next table row for numbers
    positions = [m.start() for m in re.finditer(r'Net Profit', html, re.IGNORECASE)]

    for pos in positions[:3]:  # Check first 3 occurrences
        # Get 1000 chars after "Net Profit"
        snippet = html[pos:pos+1000]

        # Look for td cells with numbers (can be negative)
        cells = re.findall(r'<td[^>]*>\s*(-?[\d,]+\.?\d*)\s*</td>', snippet)

        if len(cells) >= 3:  # Found a proper row with data
            for cell in cells[:8]:
                try:
                    val = float(cell.replace(",",""))
                    if val != 0:
                        profits.append(val)
                except Exception:
                    continue

        if len(profits) >= 3:
            break

    # Fallback: look for numbers in script tags (Highcharts data)
    if not profits:
        script_match = re.search(
            r'Net Profit[\s\S]{0,100}data:\s*\[([^\]]+)\]',
            html
        )
        if script_match:
            nums = re.findall(r'-?[\d.]+', script_match.group(1))
            for n in nums[:8]:
                try:
                    profits.append(float(n))
                except Exception:
                    continue

    return profits


def _assess_profits(profits: list, result: dict) -> dict:
    pe = result.get("pe_ratio")

    if profits and len(profits) >= 2:
        negative = sum(1 for p in profits if p < 0)
        total    = len(profits)

        if negative >= 3:
            result["is_profitable"]  = False
            result["profit_trend"]   = "LOSS_MAKING"
            result["fundamental_ok"] = False
            result["summary"]        = f"⚠️ Loss-making: {negative}/{total} quarters in loss"
        elif negative >= 1:
            result["profit_trend"] = "DECLINING"
            result["summary"]      = f"Mixed results — {negative} loss quarter(s)"
        elif len(profits) >= 3 and profits[0] > profits[-1] * 1.1:
            result["profit_trend"] = "GROWING"
            result["summary"]      = "Profits growing consistently ✅"
        else:
            result["profit_trend"] = "STABLE"
            result["summary"]      = "Company is profitable ✅"
    else:
        result["profit_trend"] = "STABLE"
        result["summary"]      = "Profitable company ✅"

    if pe and pe > 0:
        if pe < 15:       pe_note = f"PE {pe:.0f} — attractively valued"
        elif pe < 30:     pe_note = f"PE {pe:.0f} — fairly valued"
        elif pe < 60:     pe_note = f"PE {pe:.0f} — premium valuation"
        else:             pe_note = f"PE {pe:.0f} — expensive"
        result["summary"] += f" | {pe_note}"

    return result


def check_batch(symbols: list, delay: float = 0.5) -> dict:
    results = {}
    if not symbols:
        return results

    print(f"  Checking fundamentals for {len(symbols)} candidates...")

    for symbol in symbols:
        results[symbol] = get_fundamentals(symbol)
        time.sleep(delay)

    passed  = sum(1 for r in results.values() if r["fundamental_ok"])
    blocked = sum(1 for r in results.values() if not r["fundamental_ok"])
    print(f"  Fundamentals: {passed}/{len(symbols)} passed | {blocked} filtered out")
    return results


if __name__ == "__main__":
    for sym in ["HDFCBANK", "RELIANCE", "INFY"]:
        print(f"\n{sym}:")
        r = get_fundamentals(sym)
        print(f"  PE:      {r['pe_ratio']}")
        print(f"  Trend:   {r['profit_trend']}")
        print(f"  OK:      {r['fundamental_ok']}")
        print(f"  Summary: {r['summary']}")
        time.sleep(1)