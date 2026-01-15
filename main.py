import pandas as pd
import yfinance as yf
from gmail_sender import send_email
from collections import defaultdict

# =========================================
# CONFIGURAÇÕES GERAIS
# =========================================
DEST_EMAIL = "seu_email@gmail.com"

# Filtro inteligente
MIN_ALERT_PCT = 3      # mínimo % abaixo do alvo
MAX_ALERT_PCT = 40     # máximo % abaixo do alvo
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


def get_current_price(ticker, symbol):
    try:
        price = ticker.fast_info.get("last_price")
        if price is not None:
            return float(price)
    except Exception:
        pass

    try:
        hist = ticker.history(period="1d")
        if not hist.empty:
            return float(hist["Close"].iloc[-1])
    except Exception:
        pass

    print(f"{symbol} | ERRO: preço indisponível")
    return None


print("\n==============================")
print("Iniciando análise dos ativos")
print("==============================\n")

# ---------- LER CARTEIRA ----------
df = pd.read_csv("portfolio.csv")

alerts = []
ignored_assets = []

# ---------- COLETA DE DADOS ----------
for _, row in df.iterrows():
    symbol = row["symbol"]
    target = float(row["target_price"])
    currency = row["currency"].upper()

    ticker = yf.Ticker(symbol)
    current = get_current_price(ticker, symbol)

    if current is None:
        ignored_assets.append((symbol, "Preço indisponível"))
        continue

    diff_pct = (current - target) / target * 100

    print(
        f"{symbol} | alvo={target:.2f} | atual={current:.2f} | var={diff_pct:.2f}%"
    )

    if current > target:
        ignored_assets.append((symbol, "Acima do preço alvo"))
        continue

    if diff_pct > -MIN_ALERT_PCT:
        ignored_assets.append(
            (symbol, f"Queda menor que {MIN_ALERT_PCT}%")
        )
        continue

    if diff_pct < -MAX_ALERT_PCT:
        ignored_assets.append(
            (symbol, f"Queda maior que {MAX_ALERT_PCT}%")
        )
        continue

    alerts.append({
        "symbol": symbol,
        "currency": currency,
        "target": target,
        "current": current,
        "diff_pct": diff_pct,
        "link": yahoo_link(symbol)
    })

print(f"\nTotal de alertas encontrados: {len(alerts)}")

# ---------- SE NÃO HOUVER ALERTAS ----------
if not alerts:
    print("\nNenhum ativo atende ao critério. E-mail não enviado.")
    exit()

# ---------- AGRUPAR POR MOEDA ----------
grouped_alerts = defaultdict(list)

for a in alerts:
    grouped_alerts[a["currency"]].append(a)

# Ordenar cada grupo por maior desconto
for currency in grouped_alerts:
    grouped_alerts[currency].sort(key=lambda x: x["diff_pct"])

# ---------- HTML DO E-MAIL ----------
html = """
<h2 style="font-family:Arial;">📉 Alerta diário de preços</h2>

<p style="font-family:Arial;font-size:13px;color:#555;">
Ativos abaixo do preço alvo conforme critério definido,
agrupados por moeda e ordenados pelo maior desconto.
</p>
"""

for currency, items in grouped_alerts.items():
    moeda_nome = "Ativos em Reais (BRL)" if currency == "BRL" else "Ativos em Dólar (USD)"

    html += f"""
    <h3 style="font-family:Arial;margin-top:20px;">{moeda_nome}</h3>

    <table style="font-family:Arial;border-collapse:collapse;width:100%;max-width:740px;">
      <tr style="background-color:#1f2933;color:white;">
        <th align="left" style="padding:8px;">Ativo</th>
        <th align="right" style="padding:8px;">Preço Alvo</th>
        <th align="right" style="padding:8px;">Preço Atual</th>
        <th align="right" style="padding:8px;">Variação</th>
      </tr>
    """

    for a in items:
        cor, seta = variation_style(a["diff_pct"])
        html += f"""
        <tr style="border-bottom:1px solid #e5e7eb;">
          <td style="padding:8px;">
            <a href="{a['link']}" target="_blank"
               style="color:#2563eb;text-decoration:none;font-weight:bold;">
               {a['symbol']}
            </a>
          </td>
          <td align="right" style="padding:8px;">
            {format_currency(a['target'], a['currency'])}
          </td>
          <td align="right" style="padding:8px;">
            {format_currency(a['current'], a['currency'])}
          </td>
          <td align="right" style="padding:8px;color:{cor};">
            <b>{seta} {a['diff_pct']:.2f}%</b>
          </td>
        </tr>
        """

    html += "</table>"

# ---------- ATIVOS FORA DO CRITÉRIO ----------
html += f"""
<p style="font-family:Arial;font-size:12px;color:#777;margin-top:16px;">
Critério: entre -{MIN_ALERT_PCT}% e -{MAX_ALERT_PCT}% em relação ao preço alvo.
</p>

<h4 style="font-family:Arial;margin-top:18px;">
Ativos fora do critério de alerta:
</h4>

<ul style="font-family:Arial;font-size:13px;color:#444;">
"""

for sym, reason in ignored_assets:
    html += f"<li><b>{sym}</b> — {reason}</li>"

html += "</ul>"

# ---------- ENVIO ----------
print("\nEnviando e-mail via Gmail API...")

send_email(
    subject="📉 Alerta diário de preços",
    html_body=html,
    to_email=DEST_EMAIL
)

print("E-mail enviado com sucesso.")
