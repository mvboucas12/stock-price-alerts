import pandas as pd
import yfinance as yf
import requests
from gmail_sender import send_email

# =========================================
# CONFIGURAÇÕES GERAIS
# =========================================
DEST_EMAIL = "seu_email@gmail.com"

MIN_ALERT_PCT = 3
MAX_ALERT_PCT = 40
# =========================================


def format_currency(value, currency):
    symbol = "R$" if currency.upper() == "BRL" else "$"
    return f"{symbol}{value:,.2f}"


def variation_style(diff_pct):
    if diff_pct <= -20:
        return "#b00020", "⬇⬇"
    elif diff_pct <= -10:
        return "#d35400", "⬇"
    else:
        return "#e67e22", "⬇"


def yahoo_link(symbol):
    return f"https://finance.yahoo.com/quote/{symbol}"


# =========================================
# BUSCA DE PREÇO
# =========================================
def get_price_yahoo(symbol):
    try:
        ticker = yf.Ticker(symbol)

        price = ticker.fast_info.get("last_price")
        if price is not None:
            return float(price), "Yahoo (fast)"

        hist = ticker.history(period="1d")
        if not hist.empty:
            return float(hist["Close"].iloc[-1]), "Yahoo (history)"
    except Exception:
        pass

    return None, None


def get_price_brapi(symbol):
    # BRAPI NÃO usa .SA
    br_symbol = symbol.replace(".SA", "")

    try:
        url = f"https://brapi.dev/api/quote/{br_symbol}"
        r = requests.get(url, timeout=10)
        data = r.json()

        if "results" in data and data["results"]:
            price = data["results"][0].get("regularMarketPrice")
            if price is not None:
                return float(price), "BRAPI"
    except Exception as e:
        print(f"{symbol} | erro BRAPI: {e}")

    return None, None


def get_current_price(symbol):
    price, source = get_price_yahoo(symbol)
    if price is not None:
        return price, source

    price, source = get_price_brapi(symbol)
    if price is not None:
        return price, source

    return None, "INDISPONÍVEL"


# =========================================
# EXECUÇÃO
# =========================================
print("\n==============================")
print("Iniciando análise dos ativos")
print("==============================\n")

df = pd.read_csv("portfolio.csv")

alerts = []
ignored = []

for _, row in df.iterrows():
    symbol = row["symbol"]
    target = float(row["target_price"])
    currency = row["currency"]

    current, source = get_current_price(symbol)

    if current is None:
        print(f"{symbol} | ERRO: preço indisponível em todas as fontes\n")
        ignored.append((symbol, "Preço indisponível"))
        continue

    diff_pct = (current - target) / target * 100

    print(
        f"{symbol} | alvo={target:.2f} | atual={current:.2f} | "
        f"var={diff_pct:.2f}% | fonte={source}"
    )

    if current > target:
        ignored.append((symbol, "Acima do preço alvo"))
        continue

    if diff_pct > -MIN_ALERT_PCT:
        ignored.append((symbol, f"Queda < {MIN_ALERT_PCT}%"))
        continue

    if diff_pct < -MAX_ALERT_PCT:
        ignored.append((symbol, f"Queda > {MAX_ALERT_PCT}%"))
        continue

    alerts.append({
        "symbol": symbol,
        "currency": currency,
        "target": target,
        "current": current,
        "diff_pct": diff_pct,
        "link": yahoo_link(symbol)
    })

print(f"\nTotal de alertas: {len(alerts)}")

if not alerts:
    print("\nNenhum ativo atende ao critério. E-mail não enviado.")
    exit()


# =========================================
# HTML
# =========================================
html = f"""
<h2 style="font-family:Arial;">📉 Alerta diário de preços</h2>

<table style="font-family:Arial;border-collapse:collapse;width:100%;max-width:740px;">
<tr style="background-color:#1f2933;color:white;">
<th align="left">Ativo</th>
<th align="right">Preço Alvo</th>
<th align="right">Preço Atual</th>
<th align="right">Variação</th>
</tr>
"""

for a in sorted(alerts, key=lambda x: x["diff_pct"]):
    cor, seta = variation_style(a["diff_pct"])

    html += f"""
<tr>
<td><a href="{a['link']}" target="_blank"><b>{a['symbol']}</b></a></td>
<td align="right">{format_currency(a['target'], a['currency'])}</td>
<td align="right">{format_currency(a['current'], a['currency'])}</td>
<td align="right" style="color:{cor};"><b>{seta} {a['diff_pct']:.2f}%</b></td>
</tr>
"""

html += "</table>"

html += """
<p style="font-family:Arial;font-size:13px;margin-top:14px;">
<b>Ativos fora do critério de alerta:</b>
</p>
<ul style="font-family:Arial;font-size:13px;color:#555;">
"""

for sym, reason in ignored:
    html += f"<li>{sym} — {reason}</li>"

html += "</ul>"

html += f"""
<p style="font-family:Arial;font-size:12px;color:#777;">
Critério: entre -{MIN_ALERT_PCT}% e -{MAX_ALERT_PCT}% em relação ao preço alvo.
</p>
"""

# =========================================
# ENVIO
# =========================================
print("\nEnviando e-mail...")

send_email(
    subject="📉 Alerta diário de preços",
    html_body=html,
    to_email=DEST_EMAIL
)

print("E-mail enviado com sucesso.")
