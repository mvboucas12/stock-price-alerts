import pandas as pd
import yfinance as yf
from gmail_sender import send_email

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


print("\n==============================")
print("Iniciando análise dos ativos")
print("==============================\n")

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
        if current is None:
            raise ValueError("Preço retornado como None")
    except Exception as e:
        print(f"{symbol} | ERRO: preço não disponível ({e})")
        continue

    diff_pct = (current - target) / target * 100

    print(
        f"{symbol} | alvo={target:.2f} | atual={current:.2f} | var={diff_pct:.2f}%"
    )

    # ========= DEBUG DO FILTRO =========
    if current > target:
        print(f"  → IGNORADO: acima do preço alvo\n")
        continue

    if diff_pct > -MIN_ALERT_PCT:
        print(f"  → IGNORADO: queda menor que {MIN_ALERT_PCT}%\n")
        continue

    if diff_pct < -MAX_ALERT_PCT:
        print(f"  → IGNORADO: queda maior que {MAX_ALERT_PCT}%\n")
        continue

    # ========= PASSOU EM TODAS AS REGRAS =========
    print("  → OK: ALERTA GERADO\n")

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

# ---------- HTML DO E-MAIL ----------
html = """
<h2 style="font-family:Arial;margin-bottom:10px;">
📉 Alerta diário de preços
</h2>

<p style="font-family:Arial;font-size:13px;color:#555;">
Ativos abaixo do preço alvo conforme critério definido.
Clique no ticker para abrir no Yahoo Finance.
</p>

<table style="
    font-family:Arial;
    border-collapse:collapse;
    width:100%;
    max-width:740px;
    font-size:14px;
">
  <tr style="background-color:#1f2933;color:white;">
    <th align="left" style="padding:8px;">Ativo</th>
    <th align="right" style="padding:8px;">Preço Alvo</th>
    <th align="right" style="padding:8px;">Preço Atual</th>
    <th align="right" style="padding:8px;">Variação</th>
  </tr>
"""

for a in alerts:
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

html += f"""
</table>

<p style="font-family:Arial;font-size:12px;color:#777;margin-top:12px;">
Critério: entre -{MIN_ALERT_PCT}% e -{MAX_ALERT_PCT}% em relação ao preço alvo.
</p>
"""

# ---------- ENVIO ----------
print("\nEnviando e-mail via Gmail API...")

send_email(
    subject="📉 Alerta diário de preços",
    html_body=html,
    to_email=DEST_EMAIL
)

print("E-mail enviado com sucesso.")
