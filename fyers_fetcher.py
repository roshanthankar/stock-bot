"""
fyers_fetcher.py
================
All market data via Fyers API (official NSE data feed).

Fix: GIFT Nifty now uses dynamic symbol format NSE_IX:NIFTY{YY}{MON}FUT
     which matches what Fyers actually supports.
"""

import os
import time
import json
import base64
import pyotp
import requests
import pandas as pd
from datetime import datetime, timedelta
from urllib.parse import urlparse, parse_qs
from dotenv import load_dotenv

load_dotenv()

APP_ID       = os.getenv("FYERS_APP_ID", "")
SECRET_KEY   = os.getenv("FYERS_SECRET_KEY", "")
CLIENT_ID    = os.getenv("FYERS_CLIENT_ID", "")
PIN          = os.getenv("FYERS_PIN", "")
TOTP_SECRET  = os.getenv("FYERS_TOTP_SECRET", "")
REDIRECT_URI = "https://trade.fyers.in/api-login/redirect-uri/index.html"

_token_cache = {"access_token": None}
TOKEN_FILE   = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".fyers_token.json")


# ══════════════════════════════════════════════════════════
# TOKEN MANAGEMENT
# ══════════════════════════════════════════════════════════

def _encode(val: str) -> str:
    return base64.b64encode(str(val).encode("ascii")).decode("ascii")


def _save_token(token: str):
    try:
        with open(TOKEN_FILE, "w") as f:
            json.dump({"access_token": token, "date": datetime.now().strftime("%Y-%m-%d")}, f)
    except Exception:
        pass


def _load_cached_token() -> str:
    try:
        if os.path.exists(TOKEN_FILE):
            with open(TOKEN_FILE) as f:
                data = json.load(f)
            if data.get("date") == datetime.now().strftime("%Y-%m-%d"):
                print("  Token: loaded from cache ✅")
                return data.get("access_token", "")
    except Exception:
        pass
    return ""


def _auto_login() -> str:
    s = requests.Session()
    s.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})

    try:
        r1 = s.post(
            "https://api-t2.fyers.in/vagator/v2/send_login_otp_v2",
            json={"fy_id": _encode(CLIENT_ID), "app_id": "2"}, timeout=10
        )
        if r1.status_code != 200: return ""
        request_key = r1.json().get("request_key", "")
        if not request_key: return ""

        if int(time.time()) % 30 > 27:
            print("  Waiting for TOTP refresh...")
            time.sleep(4)

        totp = pyotp.TOTP(TOTP_SECRET).now()
        r2 = s.post(
            "https://api-t2.fyers.in/vagator/v2/verify_otp",
            json={"request_key": request_key, "otp": totp}, timeout=10
        )
        if r2.status_code != 200: return ""
        request_key2 = r2.json().get("request_key", "")
        if not request_key2: return ""

        r3 = s.post(
            "https://api-t2.fyers.in/vagator/v2/verify_pin_v2",
            json={"request_key": request_key2, "identity_type": "pin", "identifier": _encode(PIN)},
            timeout=10
        )
        if r3.status_code != 200: return ""
        login_token = r3.json().get("data", {}).get("access_token", "")
        if not login_token: return ""

        r4 = s.post(
            "https://api-t1.fyers.in/api/v3/token",
            headers={"Authorization": f"Bearer {login_token}"},
            json={
                "fyers_id": CLIENT_ID, "app_id": APP_ID[:-4],
                "redirect_uri": REDIRECT_URI, "appType": "100",
                "code_challenge": "", "state": "auto_login",
                "scope": "", "nonce": "", "response_type": "code",
                "create_cookie": True
            },
            timeout=10, allow_redirects=False
        )

        auth_code = ""
        try:
            body = r4.json()
            auth_code = (body.get("auth_code", "")
                         or body.get("data", {}).get("auth_code", "")
                         or body.get("data", {}).get("auth", ""))
            if not auth_code and body.get("Url"):
                auth_code = parse_qs(urlparse(body["Url"]).query).get("auth_code", [""])[0]
        except Exception:
            location  = r4.headers.get("Location", "")
            auth_code = parse_qs(urlparse(location).query).get("auth_code", [""])[0]

        if not auth_code:
            print("  Auto-login Step 4: no auth code")
            return ""

        from fyers_apiv3 import fyersModel
        session = fyersModel.SessionModel(
            client_id=APP_ID, secret_key=SECRET_KEY,
            redirect_uri=REDIRECT_URI, response_type="code",
            grant_type="authorization_code"
        )
        session.set_token(auth_code)
        token_resp   = session.generate_token()
        access_token = token_resp.get("access_token", "")

        if access_token:
            print("  Auto-login: ✅ Success")
            _save_token(access_token)
            return access_token
        return ""

    except Exception as e:
        print(f"  Auto-login exception: {e}")
        return ""


def _manual_login_alert():
    try:
        from fyers_apiv3 import fyersModel
        session = fyersModel.SessionModel(
            client_id=APP_ID, secret_key=SECRET_KEY,
            redirect_uri=REDIRECT_URI, response_type="code", state="manual_login"
        )
        from telegram_sender import send_message
        send_message(
            f"⚠️ *Fyers Auto-Login Failed*\n\nClick to log in manually:\n"
            f"{session.generate_authcode()}\n\n"
            f"Save `auth_code` from redirect URL to `.fyers_token_manual.txt`"
        )
        print("  Manual login alert sent to Telegram.")
    except Exception as e:
        print(f"  Could not send manual login alert: {e}")


def get_fyers_client():
    from fyers_apiv3 import fyersModel

    if _token_cache["access_token"]:
        return fyersModel.FyersModel(client_id=APP_ID, token=_token_cache["access_token"], log_path="")

    token = _load_cached_token()

    if not token:
        print("  Attempting auto-login via TOTP...")
        token = _auto_login()

    if not token:
        manual_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".fyers_token_manual.txt")
        if os.path.exists(manual_file):
            try:
                with open(manual_file) as f:
                    auth_code = f.read().strip()
                if auth_code:
                    print("  Trying manual auth code from file...")
                    session = fyersModel.SessionModel(
                        client_id=APP_ID, secret_key=SECRET_KEY,
                        redirect_uri=REDIRECT_URI, response_type="code",
                        grant_type="authorization_code"
                    )
                    session.set_token(auth_code)
                    resp  = session.generate_token()
                    token = resp.get("access_token", "")
                    if token:
                        _save_token(token)
                        os.remove(manual_file)
                        print("  Manual auth code: ✅ Success")
            except Exception as e:
                print(f"  Manual token error: {e}")

    if not token:
        _manual_login_alert()
        return None

    _token_cache["access_token"] = token
    return fyersModel.FyersModel(client_id=APP_ID, token=token, log_path="")


# ══════════════════════════════════════════════════════════
# SYMBOL FORMAT
# ══════════════════════════════════════════════════════════

_SYMBOL_OVERRIDES = {
    "M&M":        "M&M",
    "BAJAJ-AUTO": "BAJAJ-AUTO",
    "M&MFIN":     "M&MFIN",
}

def to_fyers_symbol(symbol: str) -> str:
    symbol    = symbol.replace(".NS", "").replace(".BO", "").upper().strip()
    fyers_sym = _SYMBOL_OVERRIDES.get(symbol, symbol)
    return f"NSE:{fyers_sym}-EQ"


def _get_gift_nifty_symbol() -> str:
    """
    Build dynamic GIFT Nifty symbol for current month.
    Format: NSE_IX:NIFTY{YY}{MON}FUT
    Example: NSE_IX:NIFTY26MARFUT (March 2026)

    If current month's contract near expiry (after 20th),
    use next month's contract.
    """
    now = datetime.now()
    # Use next month if past 20th (near expiry)
    if now.day > 20:
        if now.month == 12:
            year  = now.year + 1
            month = 1
        else:
            year  = now.year
            month = now.month + 1
    else:
        year  = now.year
        month = now.month

    month_abbr = datetime(year, month, 1).strftime("%b").upper()  # JAN, FEB, MAR...
    year_2d    = str(year)[-2:]                                     # 26, 27...
    return f"NSE_IX:NIFTY{year_2d}{month_abbr}FUT"


# ══════════════════════════════════════════════════════════
# DATA FETCHING
# ══════════════════════════════════════════════════════════

def get_historical_data(symbol: str, days: int = 365, fyers=None) -> pd.DataFrame:
    if fyers is None:
        fyers = get_fyers_client()
    if fyers is None:
        return pd.DataFrame()

    fsym      = to_fyers_symbol(symbol)
    date_to   = datetime.now()
    date_from = date_to - timedelta(days=days)

    try:
        resp = {}
        for attempt in range(3):
            resp = fyers.history({
                "symbol": fsym, "resolution": "D", "date_format": "1",
                "range_from": date_from.strftime("%Y-%m-%d"),
                "range_to":   date_to.strftime("%Y-%m-%d"),
                "cont_flag":  "1"
            })
            if resp.get("s") == "ok":
                break
            msg = resp.get("message", "").lower()
            if "request limit" in msg or "rate" in msg:
                wait = 30 * (attempt + 1)
                print(f"  Rate limit — waiting {wait}s...")
                time.sleep(wait)
            else:
                return pd.DataFrame()

        if resp.get("s") != "ok" or not resp.get("candles"):
            return pd.DataFrame()

        df = pd.DataFrame(resp["candles"], columns=["timestamp","open","high","low","close","volume"])
        df["datetime"] = pd.to_datetime(df["timestamp"], unit="s")
        df.set_index("datetime", inplace=True)
        df.drop(columns=["timestamp"], inplace=True)
        df.sort_index(inplace=True)
        return df

    except Exception as e:
        print(f"  Historical data error for {symbol}: {e}")
        return pd.DataFrame()


def get_hourly_data(symbol: str, days: int = 10, fyers=None) -> pd.DataFrame:
    if fyers is None:
        fyers = get_fyers_client()
    if fyers is None:
        return pd.DataFrame()

    fsym      = to_fyers_symbol(symbol)
    date_to   = datetime.now()
    date_from = date_to - timedelta(days=days)

    try:
        resp = {}
        for attempt in range(3):
            resp = fyers.history({
                "symbol": fsym, "resolution": "60", "date_format": "1",
                "range_from": date_from.strftime("%Y-%m-%d"),
                "range_to":   date_to.strftime("%Y-%m-%d"),
                "cont_flag":  "1"
            })
            if resp.get("s") == "ok":
                break
            msg = resp.get("message", "").lower()
            if "request limit" in msg or "rate" in msg:
                wait = 30 * (attempt + 1)
                print(f"  Rate limit (hourly) — waiting {wait}s...")
                time.sleep(wait)
            else:
                return pd.DataFrame()

        if resp.get("s") != "ok" or not resp.get("candles"):
            return pd.DataFrame()

        df = pd.DataFrame(resp["candles"], columns=["timestamp","open","high","low","close","volume"])
        df["datetime"] = pd.to_datetime(df["timestamp"], unit="s")
        df.set_index("datetime", inplace=True)
        df.drop(columns=["timestamp"], inplace=True)
        df.sort_index(inplace=True)
        return df

    except Exception as e:
        print(f"  Hourly data error for {symbol}: {e}")
        return pd.DataFrame()


def get_weekly_data(daily_df: pd.DataFrame) -> pd.DataFrame:
    if daily_df is None or daily_df.empty:
        return pd.DataFrame()
    try:
        return daily_df.resample("W").agg({
            "open":"first","high":"max","low":"min","close":"last","volume":"sum"
        }).dropna()
    except Exception:
        return pd.DataFrame()


def get_quote(symbol: str, fyers=None) -> dict:
    if fyers is None:
        fyers = get_fyers_client()
    if fyers is None:
        return {}
    fsym = to_fyers_symbol(symbol)
    try:
        resp = fyers.quotes({"symbols": fsym})
        if resp.get("s") != "ok":
            return {}
        data = resp.get("d", [{}])[0].get("v", {})
        return {
            "symbol": symbol, "ltp": data.get("lp", 0),
            "open": data.get("open_price", 0), "high": data.get("high_price", 0),
            "low": data.get("low_price", 0), "close": data.get("prev_close_price", 0),
            "volume": data.get("volume", 0), "change_pct": data.get("ch", 0)
        }
    except Exception as e:
        print(f"  Quote error for {symbol}: {e}")
        return {}


# ══════════════════════════════════════════════════════════
# BATCH FETCH
# ══════════════════════════════════════════════════════════

def fetch_batch(symbols: list, delay: float = 0.5) -> dict:
    fyers = get_fyers_client()
    if fyers is None:
        print("  ❌ Cannot fetch — no Fyers connection")
        return {}

    results = {}
    total   = len(symbols)
    valid   = 0
    failed  = []

    print(f"  Fetching {total} stocks from Fyers...")

    for i, symbol in enumerate(symbols, 1):
        try:
            daily = get_historical_data(symbol, days=365, fyers=fyers)
            if daily.empty or len(daily) < 20:
                failed.append(symbol)
                continue

            weekly = get_weekly_data(daily)
            hourly = get_hourly_data(symbol, days=10, fyers=fyers)

            results[symbol] = {"price_data": daily, "weekly_data": weekly, "hourly_data": hourly, "source": "Fyers"}
            valid += 1

            if i % 50 == 0:
                pause = 20 if i >= 150 else 15
                print(f"  {i}/{total} | valid: {valid}")
                print(f"  Pausing {pause}s to respect rate limits...")
                time.sleep(pause)

            time.sleep(delay)

        except Exception as e:
            print(f"  ❌ {symbol}: {type(e).__name__}: {e}")
            failed.append(symbol)
            continue

    print(f"  Done: {valid}/{total} valid | {len(failed)} failed")
    if failed:
        print(f"  Failed: {', '.join(failed[:10])}{'...' if len(failed) > 10 else ''}")
    return results


# ══════════════════════════════════════════════════════════
# MARKET CONTEXT — Fixed with dynamic GIFT Nifty symbol
# ══════════════════════════════════════════════════════════

def get_market_context(fyers=None) -> dict:
    """
    Pre-market context at 8 AM using:
    - GIFT Nifty futures (dynamic symbol) — today's open estimate
    - Previous day Nifty close — trend
    - India VIX — fear gauge
    """
    if fyers is None:
        fyers = get_fyers_client()
    if fyers is None:
        return {"market_score": 0, "description": "Unknown", "nifty_change": 0, "vix": 15, "gift_nifty_gap": 0}

    score        = 0
    nifty_close  = 0
    nifty_prev   = 0
    nifty_chg    = 0
    gift_gap_pct = 0
    vix          = 15

    try:
        # Previous day Nifty
        nifty_resp  = fyers.quotes({"symbols": "NSE:NIFTY50-INDEX"})
        nifty_data  = nifty_resp.get("d", [{}])[0].get("v", {})
        nifty_close = nifty_data.get("lp", 0)
        nifty_prev  = nifty_data.get("prev_close_price", nifty_close)
        nifty_chg   = nifty_data.get("ch", 0)

        if nifty_chg > 1.5:    score += 2
        elif nifty_chg > 0:    score += 1
        elif nifty_chg < -1.5: score -= 2
        elif nifty_chg < 0:    score -= 1

    except Exception as e:
        print(f"  Nifty fetch error: {e}")

    try:
        # GIFT Nifty — dynamic symbol for current month
        gift_sym  = _get_gift_nifty_symbol()
        gift_resp = fyers.quotes({"symbols": gift_sym})
        gift_data = gift_resp.get("d", [{}])[0].get("v", {})
        gift_price= gift_data.get("lp", 0)

        if gift_price > 0 and nifty_prev > 0:
            gift_gap_pct = round((gift_price - nifty_prev) / nifty_prev * 100, 2)

            if gift_gap_pct > 0.5:    score += 2
            elif gift_gap_pct > 0:    score += 1
            elif gift_gap_pct < -0.5: score -= 2
            elif gift_gap_pct < 0:    score -= 1

            print(f"  GIFT Nifty ({gift_sym}): {gift_price:.0f} | Gap: {gift_gap_pct:+.2f}%")
        else:
            errmsg = gift_data.get("errmsg", "")
            if errmsg:
                print(f"  GIFT Nifty unavailable ({gift_sym}): {errmsg}")

    except Exception as e:
        print(f"  GIFT Nifty error: {e}")

    try:
        vix_resp = fyers.quotes({"symbols": "NSE:INDIAVIX-INDEX"})
        vix_data = vix_resp.get("d", [{}])[0].get("v", {})
        vix      = vix_data.get("lp", 15)

        if vix < 14:   score += 2
        elif vix < 18: score += 1
        elif vix > 25: score -= 2
        elif vix > 20: score -= 1

    except Exception as e:
        print(f"  VIX fetch error: {e}")

    if score >= 4:    desc = "BULL RUN 🟢"
    elif score >= 2:  desc = "POSITIVE DAY 🟢"
    elif score >= 0:  desc = "NEUTRAL DAY 🟡"
    elif score >= -2: desc = "CAUTIOUS DAY 🟠"
    elif score >= -3: desc = "WEAK DAY 🔴"
    else:             desc = "AVOID TODAY 🔴🔴"

    return {
        "market_score":   score,
        "description":    desc,
        "nifty_change":   nifty_chg,
        "nifty_close":    nifty_close,
        "gift_nifty_gap": gift_gap_pct,
        "vix":            vix
    }


if __name__ == "__main__":
    print("Testing Fyers Fetcher...")
    client = get_fyers_client()
    if client:
        # Test GIFT Nifty symbol
        gift_sym = _get_gift_nifty_symbol()
        print(f"\nGIFT Nifty symbol: {gift_sym}")

        ctx = get_market_context(fyers=client)
        print(f"Market context: {ctx}")

        df = get_historical_data("RELIANCE", days=30, fyers=client)
        print(f"\nRELIANCE daily: {len(df)} candles")
    else:
        print("❌ Could not connect to Fyers")