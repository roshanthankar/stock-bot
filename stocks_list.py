"""
stocks_list.py
==============
229 best NSE stocks across 28 sectors.
All symbols verified against Fyers API format.

Symbol corrections:
- LTIMINDTREE → LTIM (Fyers symbol)
- AARTI → AARTIIND (Fyers symbol)
- TATAMOTORS verified correct
Last updated: March 2026
"""

# ══════════════════════════════════════════════════════════
# LARGE CAP — Nifty 100
# ══════════════════════════════════════════════════════════

LARGE_CAP = [
    # Banking & Finance
    "HDFCBANK", "ICICIBANK", "KOTAKBANK", "SBIN", "AXISBANK",
    "INDUSINDBK", "BANDHANBNK", "FEDERALBNK", "IDFCFIRSTB", "AUBANK",
    "BAJFINANCE", "BAJAJFINSV", "SHRIRAMFIN", "CHOLAFIN", "MUTHOOTFIN",
    "HDFCLIFE", "SBILIFE", "ICICIGI", "ICICIPRULI", "SBICARD",

    # IT & Technology
    "TCS", "INFY", "HCLTECH", "WIPRO", "TECHM",
    "LTIM", "MPHASIS", "COFORGE", "PERSISTENT", "OFSS",

    # Oil & Gas
    "RELIANCE", "ONGC", "BPCL", "IOC", "HINDPETRO",
    "GAIL", "PETRONET", "OIL",

    # Pharma & Healthcare
    "SUNPHARMA", "DRREDDY", "CIPLA", "DIVISLAB", "LUPIN",
    "AUROPHARMA", "TORNTPHARM", "ALKEM", "IPCALAB", "APOLLOHOSP",

    # Auto & Auto Ancillary
    "MARUTI", "BAJAJ-AUTO", "HEROMOTOCO", "EICHERMOT", "TATAMOTORS",
    "MOTHERSON", "BALKRISIND", "APOLLOTYRE", "CEATLTD", "SUNDRMFAST",

    # FMCG & Consumer
    "HINDUNILVR", "ITC", "NESTLEIND", "BRITANNIA", "DABUR",
    "MARICO", "COLPAL", "EMAMILTD", "GODREJCP", "TATACONSUM",

    # Metals & Mining
    "TATASTEEL", "JSWSTEEL", "HINDALCO", "VEDL", "SAIL",
    "NMDC", "HINDCOPPER", "NATIONALUM", "MOIL", "COALINDIA",

    # Infrastructure & Construction
    "LT", "ULTRACEMCO", "SHREECEM", "ACC", "AMBUJACEM",
    "ADANIPORTS", "CONCOR", "IRCTC",

    # Power & Energy
    "NTPC", "POWERGRID", "TATAPOWER", "ADANIGREEN", "JSWENERGY",
    "TORNTPOWER", "CESC", "NHPC", "SJVN",

    # Telecom
    "BHARTIARTL", "INDUSTOWER",

    # Consumer Durables
    "HAVELLS", "VOLTAS", "BLUESTARCO", "CROMPTON", "VGUARD",
    "WHIRLPOOL", "AMBER",

    # Paints & Chemicals
    "ASIANPAINT", "BERGEPAINT", "PIDILITIND", "SOLARINDS",

    # Retail & Lifestyle
    "TRENT", "TITAN", "NYKAA", "MANYAVAR",
]

# ══════════════════════════════════════════════════════════
# MID CAP — Nifty Midcap 150
# ══════════════════════════════════════════════════════════

MID_CAP = [
    # Banking & Finance
    "UNIONBANK", "BANKBARODA", "CANBK", "PNB", "RBLBANK",
    "KARURVYSYA", "CUB", "DCBBANK", "UJJIVANSFB", "EQUITASBNK",
    "POONAWALLA", "CREDITACC", "MANAPPURAM", "LICHSGFIN", "M&MFIN",

    # IT & Tech
    "KPITTECH", "ZENSARTECH", "MASTEK", "TANLA", "MAPMYINDIA",
    "TATAELXSI", "CYIENT", "SONATSOFTW", "DATAPATTNS", "CARTRADE",

    # Pharma & Healthcare
    "NATCOPHARM", "GLENMARK", "PFIZER", "GLAXO", "SANOFI",
    "ABBOTINDIA", "LALPATHLAB", "METROPOLIS", "MAXHEALTH",

    # Auto & Ancillary
    "ASHOKLEY", "BHARATFORG", "ESCORTS", "TIINDIA", "BOSCHLTD",
    "FORCEMOT", "MRF",

    # Capital Goods & Defence
    "BEL", "HAL", "BHEL", "BEML", "GRSE",
    "COCHINSHIP", "MAZDOCK", "MIDHANI", "ENGINERSIN", "RVNL",
    "IRCON", "NBCC", "HGINFRA", "PNCINFRA", "KNRCON",
    "IRB", "ASHOKA", "NCC", "ELECON", "RATNAMANI",

    # Real Estate
    "DLF", "GODREJPROP", "OBEROIRLTY", "PRESTIGE", "BRIGADE",
    "LODHA", "SOBHA", "PHOENIXLTD", "KOLTEPATIL", "SUNTECK",
    "MAHLIFE",

    # FMCG & Consumer
    "RADICO", "UBL", "VBL", "GILLETTE", "BAJAJCON",
    "JYOTHYLAB", "PATANJALI", "ZYDUSWELL",

    # Chemicals
    "AARTIIND", "DEEPAKNTR", "FINEORG", "NAVINFLUOR",

    # Power & PSU Finance
    "ADANIPOWER", "RECLTD", "PFC", "IRFC", "HUDCO",

    # Logistics
    "DELHIVERY",

    # Media
    "ZEEL", "SUNTV", "PVRINOX",

    # Retail & Apparel
    "PAGEIND", "ABFRL", "RAYMOND",

    # Jewellery
    "KALYANKJIL", "SENCO", "PCJEWELLER", "GOLDIAM",

    # Tech Platforms
    "DIXON", "IDEAFORGE", "ROUTE", "JUSTDIAL",
    "INDIAMART", "POLICYBZR", "PAYTM", "EASEMYTRIP",
    "SWIGGY", "NAUKRI",

    # Consumer Durables
    "BAJAJELEC", "ORIENTELEC", "IFBIND", "SYMPHONY",
    "INDIGOPNTS",

    # Miscellaneous
    "MSTCLTD", "RITES",
]

# ══════════════════════════════════════════════════════════
# SMALL CAP — Best by liquidity + fundamentals
# ══════════════════════════════════════════════════════════

SMALL_CAP = [
    # Banking & NBFC
    "DCBBANK", "KARURVYSYA", "CUB", "EQUITASBNK",

    # IT
    "MASTEK", "TANLA", "CYIENT", "SONATSOFTW",

    # Pharma
    "NATCOPHARM", "IPCALAB", "LALPATHLAB",

    # Capital Goods & Defence
    "MIDHANI", "IDEAFORGE", "ELECON", "RATNAMANI",

    # Infrastructure
    "HGINFRA", "KNRCON", "ASHOKA", "RITES",

    # Consumer
    "BAJAJELEC", "ORIENTELEC", "IFBIND", "SYMPHONY", "JYOTHYLAB",

    # Chemicals
    "AARTIIND", "FINEORG", "NAVINFLUOR",

    # Metals
    "HINDCOPPER", "MOIL",

    # Miscellaneous
    "MSTCLTD", "CARTRADE", "JUSTDIAL", "ROUTE", "GOLDIAM", "SENCO",
]

# ══════════════════════════════════════════════════════════
# SECTOR MAP
# ══════════════════════════════════════════════════════════

SECTOR_MAP = {
    # Banking
    "HDFCBANK":"Banking", "ICICIBANK":"Banking", "KOTAKBANK":"Banking",
    "SBIN":"Banking", "AXISBANK":"Banking", "INDUSINDBK":"Banking",
    "BANDHANBNK":"Banking", "FEDERALBNK":"Banking", "IDFCFIRSTB":"Banking",
    "AUBANK":"Banking", "UNIONBANK":"Banking", "BANKBARODA":"Banking",
    "CANBK":"Banking", "PNB":"Banking", "RBLBANK":"Banking",
    "KARURVYSYA":"Banking", "CUB":"Banking", "DCBBANK":"Banking",
    "UJJIVANSFB":"Banking", "EQUITASBNK":"Banking",

    # Finance
    "BAJFINANCE":"Finance", "BAJAJFINSV":"Finance", "SHRIRAMFIN":"Finance",
    "CHOLAFIN":"Finance", "MUTHOOTFIN":"Finance", "HDFCLIFE":"Finance",
    "SBILIFE":"Finance", "ICICIGI":"Finance", "ICICIPRULI":"Finance",
    "SBICARD":"Finance", "POONAWALLA":"Finance", "CREDITACC":"Finance",
    "MANAPPURAM":"Finance", "LICHSGFIN":"Finance", "M&MFIN":"Finance",

    # IT
    "TCS":"IT", "INFY":"IT", "HCLTECH":"IT", "WIPRO":"IT", "TECHM":"IT",
    "LTIM":"IT", "MPHASIS":"IT", "COFORGE":"IT", "PERSISTENT":"IT",
    "OFSS":"IT", "KPITTECH":"IT", "ZENSARTECH":"IT", "MASTEK":"IT",
    "TANLA":"IT", "MAPMYINDIA":"IT", "TATAELXSI":"IT", "CYIENT":"IT",
    "SONATSOFTW":"IT", "DATAPATTNS":"IT",

    # Oil & Gas
    "RELIANCE":"Oil & Gas", "ONGC":"Oil & Gas", "BPCL":"Oil & Gas",
    "IOC":"Oil & Gas", "HINDPETRO":"Oil & Gas", "GAIL":"Oil & Gas",
    "PETRONET":"Oil & Gas", "OIL":"Oil & Gas",

    # Pharma
    "SUNPHARMA":"Pharma", "DRREDDY":"Pharma", "CIPLA":"Pharma",
    "DIVISLAB":"Pharma", "LUPIN":"Pharma", "AUROPHARMA":"Pharma",
    "TORNTPHARM":"Pharma", "ALKEM":"Pharma", "IPCALAB":"Pharma",
    "NATCOPHARM":"Pharma", "GLENMARK":"Pharma", "PFIZER":"Pharma",
    "GLAXO":"Pharma", "SANOFI":"Pharma", "ABBOTINDIA":"Pharma",

    # Healthcare
    "APOLLOHOSP":"Healthcare", "MAXHEALTH":"Healthcare",
    "LALPATHLAB":"Healthcare", "METROPOLIS":"Healthcare",

    # Auto
    "MARUTI":"Auto", "BAJAJ-AUTO":"Auto", "HEROMOTOCO":"Auto",
    "EICHERMOT":"Auto", "TATAMOTORS":"Auto", "ASHOKLEY":"Auto",
    "BHARATFORG":"Auto", "ESCORTS":"Auto", "FORCEMOT":"Auto", "MRF":"Auto",

    # Auto Ancillary
    "MOTHERSON":"Auto Ancillary", "BALKRISIND":"Auto Ancillary",
    "APOLLOTYRE":"Auto Ancillary", "CEATLTD":"Auto Ancillary",
    "SUNDRMFAST":"Auto Ancillary", "TIINDIA":"Auto Ancillary",
    "BOSCHLTD":"Auto Ancillary",

    # FMCG
    "HINDUNILVR":"FMCG", "ITC":"FMCG", "NESTLEIND":"FMCG",
    "BRITANNIA":"FMCG", "DABUR":"FMCG", "MARICO":"FMCG",
    "COLPAL":"FMCG", "EMAMILTD":"FMCG", "GODREJCP":"FMCG",
    "TATACONSUM":"FMCG", "VBL":"FMCG", "RADICO":"FMCG",
    "UBL":"FMCG", "GILLETTE":"FMCG", "BAJAJCON":"FMCG",
    "JYOTHYLAB":"FMCG", "PATANJALI":"FMCG", "ZYDUSWELL":"FMCG",

    # Metals
    "TATASTEEL":"Metals", "JSWSTEEL":"Metals", "HINDALCO":"Metals",
    "VEDL":"Metals", "SAIL":"Metals", "NMDC":"Metals",
    "HINDCOPPER":"Metals", "NATIONALUM":"Metals", "MOIL":"Metals",
    "COALINDIA":"Metals", "RATNAMANI":"Metals",

    # Infrastructure
    "LT":"Infrastructure", "NBCC":"Infrastructure", "HGINFRA":"Infrastructure",
    "PNCINFRA":"Infrastructure", "KNRCON":"Infrastructure",
    "IRB":"Infrastructure", "ASHOKA":"Infrastructure", "NCC":"Infrastructure",
    "RVNL":"Infrastructure", "IRCON":"Infrastructure", "RITES":"Infrastructure",

    # Cement
    "ULTRACEMCO":"Cement", "SHREECEM":"Cement", "ACC":"Cement",
    "AMBUJACEM":"Cement",

    # Defence
    "BEL":"Defence", "HAL":"Defence", "BEML":"Defence",
    "GRSE":"Defence", "COCHINSHIP":"Defence", "MAZDOCK":"Defence",
    "MIDHANI":"Defence", "IDEAFORGE":"Defence", "DATAPATTNS":"Defence",

    # Capital Goods
    "BHEL":"Capital Goods", "ENGINERSIN":"Capital Goods", "ELECON":"Capital Goods",

    # Power
    "NTPC":"Power", "POWERGRID":"Power", "TATAPOWER":"Power",
    "ADANIGREEN":"Power", "JSWENERGY":"Power", "TORNTPOWER":"Power",
    "CESC":"Power", "NHPC":"Power", "SJVN":"Power", "ADANIPOWER":"Power",

    # PSU Finance
    "RECLTD":"PSU Finance", "PFC":"PSU Finance", "IRFC":"PSU Finance",
    "HUDCO":"PSU Finance",

    # Telecom
    "BHARTIARTL":"Telecom", "INDUSTOWER":"Telecom",

    # Consumer Durables
    "HAVELLS":"Consumer Durables", "VOLTAS":"Consumer Durables",
    "BLUESTARCO":"Consumer Durables", "CROMPTON":"Consumer Durables",
    "VGUARD":"Consumer Durables", "WHIRLPOOL":"Consumer Durables",
    "AMBER":"Consumer Durables", "BAJAJELEC":"Consumer Durables",
    "ORIENTELEC":"Consumer Durables", "IFBIND":"Consumer Durables",
    "SYMPHONY":"Consumer Durables",

    # Paints
    "ASIANPAINT":"Paints", "BERGEPAINT":"Paints", "INDIGOPNTS":"Paints",

    # Chemicals
    "PIDILITIND":"Chemicals", "SOLARINDS":"Chemicals",
    "AARTIIND":"Chemicals", "DEEPAKNTR":"Chemicals",
    "FINEORG":"Chemicals", "NAVINFLUOR":"Chemicals",

    # Retail
    "TRENT":"Retail", "NYKAA":"Retail", "MANYAVAR":"Retail",
    "ABFRL":"Retail", "RAYMOND":"Retail", "PAGEIND":"Retail",

    # Jewellery
    "TITAN":"Jewellery", "KALYANKJIL":"Jewellery", "SENCO":"Jewellery",
    "PCJEWELLER":"Jewellery", "GOLDIAM":"Jewellery",

    # Real Estate
    "DLF":"Real Estate", "GODREJPROP":"Real Estate",
    "OBEROIRLTY":"Real Estate", "PRESTIGE":"Real Estate",
    "BRIGADE":"Real Estate", "LODHA":"Real Estate",
    "SOBHA":"Real Estate", "PHOENIXLTD":"Real Estate",
    "KOLTEPATIL":"Real Estate", "SUNTECK":"Real Estate",
    "MAHLIFE":"Real Estate",

    # Logistics
    "ADANIPORTS":"Logistics", "CONCOR":"Logistics",
    "IRCTC":"Logistics", "DELHIVERY":"Logistics",

    # Media
    "ZEEL":"Media", "SUNTV":"Media", "PVRINOX":"Media",

    # Tech Platforms
    "POLICYBZR":"Tech Platform", "PAYTM":"Tech Platform",
    "EASEMYTRIP":"Tech Platform", "SWIGGY":"Tech Platform",
    "NAUKRI":"Tech Platform", "INDIAMART":"Tech Platform",
    "CARTRADE":"Tech Platform", "JUSTDIAL":"Tech Platform",
    "ROUTE":"Tech Platform",

    # Electronics & Other
    "DIXON":"Electronics", "MSTCLTD":"PSU",
}


# ══════════════════════════════════════════════════════════
# MASTER LIST — Deduplicated
# ══════════════════════════════════════════════════════════

def _build_master():
    seen   = set()
    master = []
    for sym in LARGE_CAP + MID_CAP + SMALL_CAP:
        if sym not in seen:
            seen.add(sym)
            master.append(sym)
    return master

ALL_STOCKS = _build_master()


def get_sector(symbol: str) -> str:
    return SECTOR_MAP.get(symbol, "Other")


def get_all_with_sectors() -> list:
    return [{"symbol": s, "sector": get_sector(s)} for s in ALL_STOCKS]


if __name__ == "__main__":
    print(f"Total stocks: {len(ALL_STOCKS)}")
    sectors = {}
    for s in ALL_STOCKS:
        sec = get_sector(s)
        sectors[sec] = sectors.get(sec, 0) + 1
    print(f"Sectors covered: {len(sectors)}")
    for sec, count in sorted(sectors.items(), key=lambda x: -x[1]):
        print(f"  {sec}: {count}")