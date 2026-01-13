import pandas as pd
import yfinance as yf
from gmail_sender import send_email

# =========================================
# CONFIGURAÇÕES GERAIS
# =========================================
DEST_EMAIL = "seu_email@gmail.com"
ALERT_THRESHOLD_PCT = 0        # 0 = abaixo do preço alvo
# exemplo: -5 = só alerta se cair mais de 5%
# =========================================


def format_currency(value, currency):
    symbol = "R$" if currency.upper() == "BRL" else "$"
    return f"{symbol}{value:,.2f}"


print("Iniciando análise dos ativos...\n")

# ---------- LER CARTEIRA ----------
df = pd.read_csv("portfolio.csv")

alerts = []

# ---------- COLETA DE DADOS ----------
for _, row in df.iterrows():
    symbol = row["symbol"]
    target = float(row["target_price"])
    currency = row["currency"]

    ticker = yf.Ticker(symbol)

    try:
        current = ticker.fast_info["last_price"]
    except Exception as e:
        print(f"{symbol} | erro ao obter preço: {e}")
        continue

    diff_pct = (current - target) / target * 100

    print(
        f"{symbol} | alvo={target:.2f} | atual={current:.2f} | var={diff_pct:.2f}%"
    )

    if diff_pct < ALERT_THRESHOLD_PCT:
        alerts.append({
            "symbol": symbol,
            "currency": currency,
            "target": target,
            "current": current,
            "diff_pct": diff_pct
        })

print(f"\nTotal de alertas encontrados: {len(alerts)}")

# ---------- SE NÃO HOUVER ALERTAS ----------
if not alerts:
    print("Nenhum ativo abaixo do critério. E-mail não enviado.")
    exit()

# ---------- HTML DO E-MAIL ----------
html = """
<h2 style="font-family:Arial;">📉 Alerta diário de preços</h2>

<table style="
    font-family:Arial;
    border-collapse:collapse;
    width:100%;
    max-width:700px;
">
  <tr style="background-color:#222;color:white;">
    <th align="left" style="padding:8px;">Ativo</th>
    <th align="right" style="padding:8px;">Preço Alvo</th>
    <th align="right" style="padding:8px;">Preço Atual</th>
    <th align="right" style="padding:8px;">Variação</th>
  </tr>
"""

for a in alerts:
    cor = "#b00020" if a["diff_pct"] < -10 else "#d35400"

    html += f"""
    <tr style="border-bottom:1px solid #ddd;">
      <td style="padding:6px;"><b>{a['symbol']}</b></td>
      <td align="right" style="padding:6px;">
        {format_currency(a['target'], a['currency'])}
      </td>
      <td align="right" style="padding:6px;">
        {format_currency(a['current'], a['currency'])}
      </td>
      <td align="right" style="padding:6px;color:{cor};">
        <b>{a['diff_pct']:.2f}%</b>
      </td>
    </tr>
    """

html += "</table>"

# ---------- ENVIO VIA GMAIL API ----------
print("\nEnviando e-mail via Gmail API...")

send_email(
    subject="📉 Alerta diário de preços",
    html_body=html,
    to_email=DEST_EMAIL
)

print("E-mail enviado com sucesso.")
