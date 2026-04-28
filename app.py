"""
Estructura de mercado en España
Dashboard de análisis sectorial · Economía I
Datos reales 2024/25

Fuentes: CNMC, AENA, NIQ, Worldpanel, ICEA, Unespa, Banco de España, REE, PwC

Para ejecutar:
    pip install -r requirements.txt
    streamlit run app.py
"""

import json
import time
from datetime import datetime
from pathlib import Path

import requests
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np

# CONFIG
st.set_page_config(
    page_title="Estructura de Mercado — España",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# CUSTOM CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&family=IBM+Plex+Mono:wght@400;500&display=swap');

    .stApp {
        font-family: 'DM Sans', sans-serif;
    }

    .main-header {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f172a 100%);
        padding: 2rem 2.5rem;
        border-radius: 16px;
        margin-bottom: 1.5rem;
        border: 1px solid #334155;
    }
    .main-header h1 {
        color: #f1f5f9;
        font-size: 2rem;
        font-weight: 800;
        margin: 0;
        letter-spacing: -0.03em;
    }
    .main-header p {
        color: #94a3b8;
        font-size: 0.9rem;
        margin: 0.3rem 0 0;
    }

    .metric-box {
        background: #1e293b;
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 1.1rem 1.3rem;
        text-align: center;
    }
    .metric-box .label {
        color: #64748b;
        font-size: 0.7rem;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        font-weight: 600;
    }
    .metric-box .value {
        color: #f1f5f9;
        font-size: 1.6rem;
        font-weight: 800;
        line-height: 1.2;
        margin-top: 0.2rem;
    }
    .metric-box .sub {
        color: #94a3b8;
        font-size: 0.75rem;
        margin-top: 0.15rem;
    }

    .insight-card {
        background: #1e293b;
        border: 1px solid #334155;
        border-left: 3px solid #3b82f6;
        border-radius: 8px;
        padding: 0.8rem 1rem;
        margin-bottom: 0.5rem;
        color: #cbd5e1;
        font-size: 0.85rem;
        line-height: 1.5;
    }

    .sector-badge {
        display: inline-block;
        padding: 0.25rem 0.8rem;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 700;
    }

    .interpretation-box {
        background: #1e293b;
        border: 1px solid #334155;
        border-radius: 10px;
        padding: 1.2rem;
        margin-bottom: 0.8rem;
    }
    .interpretation-box h4 {
        margin: 0 0 0.4rem;
        font-size: 0.95rem;
        font-weight: 700;
    }
    .interpretation-box p {
        color: #94a3b8;
        font-size: 0.82rem;
        line-height: 1.6;
        margin: 0;
    }

    div[data-testid="stSidebar"] {
        background: #0f172a;
    }
    div[data-testid="stSidebar"] .stMarkdown p,
    div[data-testid="stSidebar"] .stMarkdown li {
        color: #cbd5e1;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 0;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 0.6rem 1.2rem;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# REFRESH CONTROL
AUTO_REFRESH_INTERVAL = 30 * 60  # 30 minutos

def init_refresh_state() -> None:
    if "last_refresh_ts" not in st.session_state:
        st.session_state.last_refresh_ts = time.time()


def format_last_refresh() -> str:
    return datetime.fromtimestamp(st.session_state.last_refresh_ts).strftime("%d/%m/%Y %H:%M:%S")


def refresh_controls(container):
    init_refresh_state()
    container.markdown("#### 🔄")
    if container.button("Actualiza Datos"):
        st.session_state.last_refresh_ts = time.time()
        st.rerun()

    if time.time() - st.session_state.last_refresh_ts >= AUTO_REFRESH_INTERVAL:
        st.session_state.last_refresh_ts = time.time()
        st.rerun()

    container.markdown(f"<span style='color:#cbd5e1;'>Última actualización: {format_last_refresh()}</span>", unsafe_allow_html=True)
    container.markdown("<span style='color:#94a3b8;font-size:0.85rem;'>Actualización automática cada 30 minutos.</span>", unsafe_allow_html=True)

DATA_FILE = "sector_data.json"
DATA_FEED_URL = st.secrets.get("DATA_FEED_URL", None)


def fetch_json(url: str, timeout: int = 12) -> dict:
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    return response.json()


def load_local_sector_data() -> dict:
    path = Path(DATA_FILE)
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            return payload.get("sectors", payload)
    except Exception:
        pass
    return {}


def merge_sector_data(base: dict, source: dict) -> dict:
    merged = {}
    for sector, base_data in base.items():
        merged[sector] = base_data.copy()
        if sector not in source:
            continue

        source_data = source[sector]
        if isinstance(source_data, dict):
            merged[sector].update({k: v for k, v in source_data.items() if k != "companies"})
            if isinstance(source_data.get("companies"), list):
                live_companies = {c["name"]: c for c in source_data["companies"] if isinstance(c, dict) and c.get("name")}
                merged_companies = []
                for company in base_data["companies"]:
                    match = live_companies.get(company["name"])
                    merged_companies.append({**company, **match} if match else company)
                for company in source_data["companies"]:
                    if company.get("name") not in live_companies:
                        merged_companies.append(company)
                merged[sector]["companies"] = merged_companies
    return merged


def load_sector_data(base_data: dict) -> dict:
    live_data = {}
    if DATA_FEED_URL:
        try:
            payload = fetch_json(DATA_FEED_URL)
            if isinstance(payload, dict):
                live_data = payload.get("sectors", payload)
        except Exception as exc:
            st.sidebar.warning(f"No se pudieron cargar datos en vivo: {exc}")

    local_data = load_local_sector_data()
    if isinstance(local_data, dict) and local_data:
        live_data = merge_sector_data(live_data or {}, local_data)

    return merge_sector_data(base_data, live_data) if live_data else base_data

# DATA
SECTORS = {
    "Telecomunicaciones": {
        "year": "2025",
        "source": "CNMC · MobileWorldLive · Nae",
        "total_market": "63M líneas móviles",
        "market_type": "Oligopolio concentrado",
        "companies": [
            {"name": "MasOrange", "share": 41.24, "revenue": None, "color": "#FF6B00", "clients": "26M líneas"},
            {"name": "Movistar", "share": 26.24, "revenue": None, "color": "#019DF4", "clients": "16.5M líneas"},
            {"name": "Vodafone", "share": 18.50, "revenue": None, "color": "#E60000", "clients": "11.7M líneas"},
            {"name": "Digi", "share": 11.72, "revenue": None, "color": "#7E57C2", "clients": "7.4M líneas"},
            {"name": "OMVs", "share": 2.30, "revenue": None, "color": "#78909C", "clients": "1.4M líneas"},
        ],
        "insights": [
            "Top 3 operadores concentran el **86%** del mercado",
            "Digi es el único operador con **crecimiento neto** sostenido",
            "Tasa de cancelación: Telefónica **3.5%** vs Digi **10.5%**",
            "**534** comercializadoras activas en España",
        ],
        "sub_market": {
            "title": "Banda Ancha Fija (dic 2025) — 19.5M líneas",
            "data": [
                {"name": "Movistar", "share": 32.9, "color": "#019DF4"},
                {"name": "MasOrange", "share": 28.0, "color": "#FF6B00"},
                {"name": "Vodafone", "share": 21.0, "color": "#E60000"},
                {"name": "Digi", "share": 12.1, "color": "#7E57C2"},
                {"name": "Otros", "share": 6.0, "color": "#78909C"},
            ],
        },
        "interpretation": "El HHI más alto (~2.850) refleja la fusión Orange+Más Móvil. Con CR₃ del 86%, el sector opera como un oligopolio de facto con barreras de entrada por infraestructura. La entrada de Digi como cuarto operador es la principal fuerza competitiva.",
    },
    "Banca": {
        "year": "2025",
        "source": "Banco de España · Informes anuales · EBA",
        "total_market": "~€2.4T activos totales",
        "market_type": "Oligopolio (post-consolidación)",
        "companies": [
            {"name": "CaixaBank", "share": 25.5, "revenue": 5786, "color": "#007EAE", "clients": "21M clientes"},
            {"name": "Santander", "share": 24.0, "revenue": 13546, "color": "#EC0000", "clients": "17M cl. ES"},
            {"name": "BBVA", "share": 17.5, "revenue": 10566, "color": "#004481", "clients": "15M cl. ES"},
            {"name": "Sabadell", "share": 9.0, "revenue": 1827, "color": "#0099CC", "clients": "12M clientes"},
            {"name": "Bankinter", "share": 5.2, "revenue": 1060, "color": "#FF6600", "clients": "1.2M clientes"},
            {"name": "Unicaja", "share": 5.0, "revenue": 623, "color": "#00A651", "clients": "4M clientes"},
            {"name": "Otros", "share": 13.8, "revenue": None, "color": "#78909C", "clients": ""},
        ],
        "insights": [
            "**4 grandes** bancos gestionan **67%** de depósitos",
            "Beneficio récord conjunto: **€33.408M** en 2025",
            "De **55 entidades** en 2009 a **~11** en 2025",
            "Top 6 controlan **>75%** de depósitos",
        ],
        "sub_market": {
            "title": "Cuota en Depósitos — ~€1T depositados por hogares",
            "data": [
                {"name": "CaixaBank", "share": 24.0, "color": "#007EAE"},
                {"name": "Santander", "share": 20.0, "color": "#EC0000"},
                {"name": "BBVA", "share": 14.0, "color": "#004481"},
                {"name": "Sabadell", "share": 9.0, "color": "#0099CC"},
                {"name": "Bankinter", "share": 4.5, "color": "#FF6600"},
                {"name": "Unicaja", "share": 4.0, "color": "#00A651"},
                {"name": "Otros", "share": 24.5, "color": "#78909C"},
            ],
        },
        "interpretation": "La consolidación post-2008 (de 55 a ~11 entidades) ha creado un oligopolio bancario con HHI ~1.600. Las barreras regulatorias limitan la entrada, pero la banca digital y las fintech podrían disrumpir el equilibrio actual.",
    },
    "Energía Eléctrica": {
        "year": "2024-2025",
        "source": "CNMC · REE · PwC",
        "total_market": "30.3M puntos de suministro",
        "market_type": "Oligopolio con competencia creciente",
        "companies": [
            {"name": "Iberdrola", "share": 33.0, "revenue": None, "color": "#2E8B57", "clients": "~10M puntos"},
            {"name": "Endesa", "share": 31.5, "revenue": None, "color": "#00A650", "clients": "~9.5M puntos"},
            {"name": "Naturgy", "share": 19.0, "revenue": None, "color": "#FF8C00", "clients": "~5.7M puntos"},
            {"name": "TotalEnergies", "share": 3.8, "revenue": None, "color": "#D32F2F", "clients": "~1.1M puntos"},
            {"name": "Repsol", "share": 2.14, "revenue": None, "color": "#1565C0", "clients": "~650K puntos"},
            {"name": "Otros (534)", "share": 10.56, "revenue": None, "color": "#78909C", "clients": "~3.2M puntos"},
        ],
        "insights": [
            "Top 5 comercializadoras: **84.9%** del mercado",
            "**71.8%** clientes en mercado libre vs **28.2%** regulado (PVPC)",
            "**534** comercializadoras activas — líder europeo",
            "Precio medio 2025: **65.29 €/MWh** (+3.6% interanual)",
        ],
        "sub_market": None,
        "interpretation": "El mercado eléctrico español presenta un oligopolio en generación y distribución, pero alta competencia en comercialización (534 actores). La transición energética y la irrupción de renovables están alterando las dinámicas de poder. El precio marginalista amplifica la volatilidad.",
    },
    "Distribución Alimentaria": {
        "year": "2025",
        "source": "NIQ · Worldpanel by Numerator",
        "total_market": "€131.000M facturación total",
        "market_type": "Cuasi-monopolio del líder + competencia fragmentada",
        "companies": [
            {"name": "Mercadona", "share": 29.5, "revenue": 41858, "color": "#4CAF50", "clients": "93.2% hogares"},
            {"name": "Carrefour", "share": 7.2, "revenue": 11902, "color": "#1565C0", "clients": "63.8% hogares"},
            {"name": "Lidl", "share": 6.2, "revenue": 6952, "color": "#FFC107", "clients": "68.5% hogares"},
            {"name": "Dia", "share": 4.8, "revenue": 5740, "color": "#D32F2F", "clients": "50% hogares"},
            {"name": "Eroski", "share": 4.3, "revenue": None, "color": "#E65100", "clients": ""},
            {"name": "Consum", "share": 4.1, "revenue": 4707, "color": "#FF9800", "clients": "22.8% hogares"},
            {"name": "Alcampo", "share": 2.9, "revenue": 5004, "color": "#0D47A1", "clients": ""},
            {"name": "Aldi", "share": 1.8, "revenue": None, "color": "#0097A7", "clients": "41.2% hogares"},
            {"name": "Regionales", "share": 25.7, "revenue": None, "color": "#795548", "clients": ""},
            {"name": "Otros", "share": 13.5, "revenue": None, "color": "#78909C", "clients": ""},
        ],
        "insights": [
            "Mercadona (**29.5%**) = sus 6 competidores juntos",
            "Marca blanca: **50%** del gasto total (+0.9pp)",
            "Online crece **17.7%**, alcanza **7.3%** del mercado",
            "**25.585** supermercados operativos, **+850** aperturas/año",
        ],
        "sub_market": None,
        "interpretation": "Caso atípico: Mercadona (29.5%) genera un HHI bajo por la fragmentación del resto, pero su poder de mercado real es enorme. El índice de Lerner subestima su capacidad de fijar precios dada su estrategia de marca blanca (50% del gasto en MDD).",
    },
    "Transporte Aéreo": {
        "year": "2025",
        "source": "AENA · DGAC",
        "total_market": "~310M pasajeros/año",
        "market_type": "Competencia oligopolística (low-cost dominante)",
        "companies": [
            {"name": "Ryanair", "share": 22.0, "revenue": None, "color": "#003580", "clients": "68.1M pax"},
            {"name": "Vueling", "share": 16.0, "revenue": None, "color": "#e6b800", "clients": "49.6M pax"},
            {"name": "Iberia", "share": 7.2, "revenue": None, "color": "#D50032", "clients": "22.4M pax"},
            {"name": "Air Europa", "share": 5.5, "revenue": None, "color": "#0072CE", "clients": "~17M pax"},
            {"name": "EasyJet", "share": 5.5, "revenue": None, "color": "#FF6600", "clients": "~17M pax"},
            {"name": "Binter", "share": 3.6, "revenue": None, "color": "#00B0FF", "clients": "9M pax"},
            {"name": "Iberia Express", "share": 3.2, "revenue": None, "color": "#B71C1C", "clients": "~10M pax"},
            {"name": "Jet2.com", "share": 3.0, "revenue": None, "color": "#E91E63", "clients": "~9M pax"},
            {"name": "Otras", "share": 34.0, "revenue": None, "color": "#78909C", "clients": ""},
        ],
        "insights": [
            "Low-cost: **61.8%** del volumen total de pasajeros",
            "Ryanair crece **4.2%** pese a recortes regionales",
            "Binter: mayor crecimiento (**+10.3%**), sorpresa del año",
            "Vueling pierde cuota pese a ser la **#2**",
        ],
        "sub_market": None,
        "interpretation": "El transporte aéreo español muestra competencia oligopolística dominada por low-cost (61.8%). Ryanair lidera pese a conflictos con AENA por tasas. La cola larga de 'Otras' (34%) refleja la fragmentación del tráfico internacional — muchas aerolíneas con cuotas pequeñas.",
    },
    "Seguros": {
        "year": "2025",
        "source": "ICEA · Unespa · IPMARK",
        "total_market": "€85.879M en primas",
        "market_type": "Oligopolio moderado con bancaseguros",
        "companies": [
            {"name": "VidaCaixa", "share": 12.3, "revenue": 10631, "color": "#007EAE", "clients": ""},
            {"name": "Mapfre", "share": 11.1, "revenue": 9547, "color": "#D32F2F", "clients": ""},
            {"name": "Mutua Madrileña", "share": 10.36, "revenue": 8892, "color": "#1B5E20", "clients": ""},
            {"name": "Zurich", "share": 6.83, "revenue": 5868, "color": "#0D47A1", "clients": ""},
            {"name": "Allianz", "share": 4.71, "revenue": 4045, "color": "#003D7A", "clients": ""},
            {"name": "AXA", "share": 4.3, "revenue": 3695, "color": "#00008F", "clients": ""},
            {"name": "Generali", "share": 4.2, "revenue": 3609, "color": "#C62828", "clients": ""},
            {"name": "Catalana Occ.", "share": 4.17, "revenue": 3584, "color": "#FF6F00", "clients": ""},
            {"name": "Otros", "share": 42.03, "revenue": None, "color": "#78909C", "clients": ""},
        ],
        "insights": [
            "Mejor año de la historia: **€85.879M** (+13.7%)",
            "Top 3 acumulan **~34%** de cuota de mercado",
            "Zurich escala de **8ª a 4ª** posición en un año (**+72.4%**)",
            "Vida crece **+20%**, impulsado por bajada de tipos",
        ],
        "sub_market": None,
        "interpretation": "El sector asegurador español es el menos concentrado (HHI ~700), con un 'Otros' del 42%. La bancaseguros (VidaCaixa, Santander Seguros) compite con aseguradoras puras (Mapfre, Mutua). Las alianzas de distribución (MasOrange-Zurich, Carrefour-Mapfre) están redefiniendo el mercado.",
    },
}

# HELPER FUNCTIONS
def calc_hhi(companies: list[dict]) -> float:
    return sum(c["share"] ** 2 for c in companies)


def classify_hhi(hhi: float) -> tuple[str, str]:
    if hhi > 2500:
        return "Altamente concentrado", "#EF5350"
    elif hhi > 1500:
        return "Moderadamente concentrado", "#FFA726"
    return "Competitivo", "#66BB6A"


def calc_cr(companies: list[dict], n: int) -> float:
    sorted_c = sorted(companies, key=lambda c: c["share"], reverse=True)
    return sum(c["share"] for c in sorted_c[:n])


def estimate_lerner(hhi: float) -> float:
    """Rough Lerner index estimate from HHI (simplified Cournot relationship)."""
    return (hhi / 10000) * 0.4 + 0.05


def metric_html(label: str, value: str, sub: str = "", color: str = "#f1f5f9") -> str:
    sub_html = f'<div class="sub">{sub}</div>' if sub else ""
    return f"""
    <div class="metric-box">
        <div class="label">{label}</div>
        <div class="value" style="color: {color}">{value}</div>
        {sub_html}
    </div>
    """

SECTORS = load_sector_data(SECTORS)

# CHARTS
CHART_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="DM Sans, sans-serif", color="#cbd5e1"),
    margin=dict(l=20, r=20, t=40, b=20),
)


def make_donut(companies: list[dict], title: str = "Cuota de Mercado") -> go.Figure:
    fig = go.Figure(go.Pie(
        labels=[c["name"] for c in companies],
        values=[c["share"] for c in companies],
        marker=dict(colors=[c["color"] for c in companies]),
        hole=0.55,
        textinfo="label+percent",
        textfont=dict(size=11, color="#e2e8f0"),
        hovertemplate="<b>%{label}</b><br>Cuota: %{value:.1f}%<extra></extra>",
        sort=False,
    ))
    hhi = calc_hhi(companies)
    fig.add_annotation(
        text=f"<b>HHI</b><br><span style='font-size:20px;color:#60a5fa'>{hhi:,.0f}</span>",
        showarrow=False, font=dict(size=12, color="#94a3b8"),
    )
    fig.update_layout(
        **CHART_LAYOUT,
        title=dict(text=title, font=dict(size=14, color="#94a3b8")),
        showlegend=False,
        height=360,
    )
    return fig


def make_bar(companies: list[dict], metric: str = "share", title: str = "") -> go.Figure:
    filtered = [c for c in companies if c.get(metric) and c[metric] > 0]
    filtered.sort(key=lambda c: c[metric])

    if metric == "share":
        text_vals = [f"{c[metric]}%" for c in filtered]
        x_title = "Cuota (%)"
    else:
        text_vals = [f"€{c[metric]:,.0f}M" for c in filtered]
        x_title = "€ Millones"

    fig = go.Figure(go.Bar(
        y=[c["name"] for c in filtered],
        x=[c[metric] for c in filtered],
        orientation="h",
        marker=dict(
            color=[c["color"] for c in filtered],
            line=dict(width=0),
        ),
        text=text_vals,
        textposition="outside",
        textfont=dict(size=11, color="#e2e8f0"),
        hovertemplate="<b>%{y}</b>: %{x:.1f}<extra></extra>",
    ))
    fig.update_layout(
        **CHART_LAYOUT,
        title=dict(text=title, font=dict(size=14, color="#94a3b8")),
        height=max(220, len(filtered) * 36 + 80),
        xaxis=dict(
            title=x_title, gridcolor="#1e293b", zeroline=False,
            title_font=dict(size=11), tickfont=dict(size=10),
        ),
        yaxis=dict(tickfont=dict(size=11)),
    )
    return fig


def make_scatter_cr_hhi(sectors_data: dict) -> go.Figure:
    names, hhis, cr3s, colors = [], [], [], []
    for key, data in sectors_data.items():
        hhi = calc_hhi(data["companies"])
        cr3 = calc_cr(data["companies"], 3)
        _, col = classify_hhi(hhi)
        names.append(key)
        hhis.append(hhi)
        cr3s.append(cr3)
        colors.append(col)

    fig = go.Figure()

    # Zone backgrounds
    fig.add_vrect(x0=0, x1=1500, fillcolor="#66BB6A", opacity=0.06, line_width=0)
    fig.add_vrect(x0=1500, x1=2500, fillcolor="#FFA726", opacity=0.06, line_width=0)
    fig.add_vrect(x0=2500, x1=4000, fillcolor="#EF5350", opacity=0.06, line_width=0)

    # Threshold lines
    fig.add_vline(x=1500, line_dash="dash", line_color="#475569", line_width=1,
                  annotation_text="HHI 1500", annotation_font_size=10,
                  annotation_font_color="#64748b", annotation_position="top")
    fig.add_vline(x=2500, line_dash="dash", line_color="#475569", line_width=1,
                  annotation_text="HHI 2500", annotation_font_size=10,
                  annotation_font_color="#64748b", annotation_position="top")

    fig.add_trace(go.Scatter(
        x=hhis, y=cr3s,
        mode="markers+text",
        marker=dict(size=20, color=colors, line=dict(width=2, color="#0f172a")),
        text=names,
        textposition="top center",
        textfont=dict(size=11, color="#e2e8f0"),
        hovertemplate="<b>%{text}</b><br>HHI: %{x:,.0f}<br>CR₃: %{y:.1f}%<extra></extra>",
    ))

    fig.update_layout(
        **CHART_LAYOUT,
        title=dict(text="Mapa CR₃ vs HHI — Clasificación de Estructuras de Mercado",
                   font=dict(size=15, color="#cbd5e1")),
        xaxis=dict(title="HHI (Herfindahl-Hirschman)", range=[0, 4000],
                   gridcolor="#1e293b", title_font=dict(size=12), tickfont=dict(size=10)),
        yaxis=dict(title="CR₃ (%)", range=[0, 105],
                   gridcolor="#1e293b", title_font=dict(size=12), tickfont=dict(size=10)),
        height=480,
    )
    return fig


def make_comparative_bar(sectors_data: dict) -> go.Figure:
    rows = []
    for key, data in sectors_data.items():
        hhi = calc_hhi(data["companies"])
        _, col = classify_hhi(hhi)
        rows.append({"sector": key, "hhi": hhi, "color": col})
    df = pd.DataFrame(rows).sort_values("hhi")

    fig = go.Figure(go.Bar(
        y=df["sector"],
        x=df["hhi"],
        orientation="h",
        marker=dict(color=df["color"], line=dict(width=0)),
        text=[f"{h:,.0f}" for h in df["hhi"]],
        textposition="outside",
        textfont=dict(size=12, color="#e2e8f0", family="DM Sans"),
        hovertemplate="<b>%{y}</b><br>HHI: %{x:,.0f}<extra></extra>",
    ))
    fig.add_vline(x=1500, line_dash="dash", line_color="#FFA726", line_width=1.5,
                  annotation_text="Moderado", annotation_font_size=9, annotation_font_color="#FFA726")
    fig.add_vline(x=2500, line_dash="dash", line_color="#EF5350", line_width=1.5,
                  annotation_text="Altamente conc.", annotation_font_size=9, annotation_font_color="#EF5350")

    fig.update_layout(
        **CHART_LAYOUT,
        title=dict(text="Índice HHI por Sector", font=dict(size=15, color="#cbd5e1")),
        height=350,
        xaxis=dict(title="HHI", gridcolor="#1e293b", range=[0, 3500]),
        yaxis=dict(tickfont=dict(size=12)),
    )
    return fig

# SIDEBAR
with st.sidebar:
    refresh_controls(st)
    st.markdown("### 📊 Navegación")
    sector_options = ["🔍 Vista Comparativa"] + list(SECTORS.keys())
    selected = st.radio("Selecciona sector", sector_options, label_visibility="collapsed")

    st.markdown("---")
    st.markdown("### 📚 Conceptos clave")
    st.markdown("""
    - **HHI**: Σ(cuota²). <1500 competitivo, 1500-2500 moderado, >2500 concentrado
    - **CR₃ / CR₄**: Cuota acumulada de las 3 o 4 mayores empresas
    - **Índice de Lerner**: (P−CM)/P — mide poder de mercado (markup)
    - **Oligopolio**: Pocos vendedores, barreras de entrada, interdependencia estratégica
    """)
    st.markdown("---")
    st.markdown(
        "<p style='font-size:0.7rem;color:#64748b;'>Fuentes: CNMC, AENA, NIQ, Worldpanel, "
        "ICEA, Unespa, BdE, REE, PwC<br>Datos 2024-2025</p>",
        unsafe_allow_html=True,
    )


# HEADER
st.markdown("""
<div class="main-header">
    <h1>Estructura de Mercado — España</h1>
    <p>Análisis de concentración sectorial con datos reales 2024-2025 · Economía I</p>
</div>
""", unsafe_allow_html=True)

# COMPARATIVE VIEW

if selected == "🔍 Vista Comparativa":

    # Summary metrics
    all_hhis = {k: calc_hhi(v["companies"]) for k, v in SECTORS.items()}
    most_concentrated = max(all_hhis, key=all_hhis.get)
    least_concentrated = min(all_hhis, key=all_hhis.get)

    cols = st.columns(4)
    cols[0].markdown(metric_html("Sectores analizados", str(len(SECTORS)), "con datos reales"), unsafe_allow_html=True)
    cols[1].markdown(metric_html("Mayor HHI", f"{max(all_hhis.values()):,.0f}",
                                  most_concentrated.split(" ", 1)[1] if " " in most_concentrated else most_concentrated,
                                  "#EF5350"), unsafe_allow_html=True)
    cols[2].markdown(metric_html("Menor HHI", f"{min(all_hhis.values()):,.0f}",
                                  least_concentrated.split(" ", 1)[1] if " " in least_concentrated else least_concentrated,
                                  "#66BB6A"), unsafe_allow_html=True)
    avg_hhi = np.mean(list(all_hhis.values()))
    cols[3].markdown(metric_html("HHI medio", f"{avg_hhi:,.0f}", classify_hhi(avg_hhi)[0],
                                  classify_hhi(avg_hhi)[1]), unsafe_allow_html=True)

    st.markdown("")

    # Charts
    col1, col2 = st.columns([1, 1])
    with col1:
        st.plotly_chart(make_comparative_bar(SECTORS), use_container_width=True)
    with col2:
        st.plotly_chart(make_scatter_cr_hhi(SECTORS), use_container_width=True)

    # Comparative table
    st.markdown("#### 📋 Tabla Comparativa de Métricas")
    table_rows = []
    for key, data in SECTORS.items():
        hhi = calc_hhi(data["companies"])
        label, _ = classify_hhi(hhi)
        table_rows.append({
            "Sector": key,
            "HHI": round(hhi),
            "CR₃ (%)": round(calc_cr(data["companies"], 3), 1),
            "CR₄ (%)": round(calc_cr(data["companies"], 4), 1),
            "Lerner est. (%)": round(estimate_lerner(hhi) * 100, 1),
            "Clasificación": label,
            "Tipo": data["market_type"],
            "Mercado total": data["total_market"],
        })
    df_table = pd.DataFrame(table_rows).sort_values("HHI", ascending=False)
    st.dataframe(df_table, use_container_width=True, hide_index=True)

    # Interpretations
    st.markdown("#### Interpretación Económica")
    for key, data in SECTORS.items():
        _, col = classify_hhi(calc_hhi(data["companies"]))
        st.markdown(f"""
        <div class="interpretation-box" style="border-left: 3px solid {col};">
            <h4 style="color: {col};">{key}</h4>
            <p>{data['interpretation']}</p>
        </div>
        """, unsafe_allow_html=True)

    # Lerner / Markup
    st.markdown("#### Markup y Elasticidad")
    st.markdown("""
    <div class="interpretation-box" style="border-left: 3px solid #AB47BC;">
        <h4 style="color: #AB47BC;">Índice de Lerner y Relación con HHI</h4>
        <p>
            En competencia a la Cournot, el índice de Lerner (L = (P−CM)/P) está relacionado con el HHI
            a través de la elasticidad de la demanda: <b>L = HHI / (ε × 10.000)</b>, donde ε es la elasticidad-precio.
            Nuestras estimaciones usan ε implícita entre 2 y 4 según el sector.<br><br>
            <b>Telecom</b> (baja elasticidad, switching costs altos) → Lerner ~16%<br>
            <b>Alimentación</b> (elasticidad moderada, muchos sustitutos) → Lerner ~9%<br>
            <b>Seguros</b> (alta fragmentación, competencia en precio) → Lerner ~7%<br><br>
            Estas son estimaciones basadas en la estructura de mercado. Los markups reales requieren
            datos de costes marginales que no están disponibles públicamente.
        </p>
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────
# SECTOR DETAIL VIEW
# ─────────────────────────────────────────────
else:
    data = SECTORS[selected]
    companies = data["companies"]
    hhi = calc_hhi(companies)
    hhi_label, hhi_color = classify_hhi(hhi)
    cr3 = calc_cr(companies, 3)
    cr4 = calc_cr(companies, 4)
    lerner = estimate_lerner(hhi)

    # Sector header
    st.markdown(f"**{data['source']}** · {data['year']}")

    # KPI row
    cols = st.columns(6)
    cols[0].markdown(metric_html("Mercado total", data["total_market"]), unsafe_allow_html=True)
    cols[1].markdown(metric_html("HHI", f"{hhi:,.0f}", hhi_label, hhi_color), unsafe_allow_html=True)
    cols[2].markdown(metric_html("CR₃", f"{cr3:.1f}%", "Top 3 empresas"), unsafe_allow_html=True)
    cols[3].markdown(metric_html("CR₄", f"{cr4:.1f}%", "Top 4 empresas"), unsafe_allow_html=True)
    cols[4].markdown(metric_html("Lerner est.", f"{lerner*100:.1f}%", "Markup aprox.", "#CE93D8"), unsafe_allow_html=True)
    cols[5].markdown(metric_html("Tipo", data["market_type"]), unsafe_allow_html=True)

    st.markdown("")

    # Charts row
    col1, col2 = st.columns([2, 3])
    with col1:
        st.plotly_chart(make_donut(companies), use_container_width=True)
    with col2:
        st.plotly_chart(make_bar(companies, "share", "Cuota de Mercado (%)"), use_container_width=True)

    # Revenue chart if available
    companies_with_rev = [c for c in companies if c.get("revenue")]
    if companies_with_rev:
        st.plotly_chart(
            make_bar(companies_with_rev, "revenue", "Facturación / Beneficio neto (€ Millones)"),
            use_container_width=True,
        )

    # Sub-market
    if data.get("sub_market"):
        sub = data["sub_market"]
        st.markdown(f"#### {sub['title']}")
        st.plotly_chart(
            make_bar(sub["data"], "share", ""),
            use_container_width=True,
        )

    # Insights
    st.markdown("#### 💡 Insights clave")
    ins_cols = st.columns(2)
    for i, ins in enumerate(data["insights"]):
        with ins_cols[i % 2]:
            st.markdown(f'<div class="insight-card">{ins}</div>', unsafe_allow_html=True)

    # Interpretation
    st.markdown("#### 🧠 Interpretación")
    st.markdown(f"""
    <div class="interpretation-box" style="border-left: 3px solid {hhi_color};">
        <p>{data['interpretation']}</p>
    </div>
    """, unsafe_allow_html=True)

    # Company table
    st.markdown("#### 📋 Detalle por Empresa")
    table_data = []
    for c in companies:
        row = {
            "Empresa": c["name"],
            "Cuota (%)": c["share"],
            "Clientes": c["clients"] if c["clients"] else "—",
        }
        if companies_with_rev:
            row["Fact./Benef. (€M)"] = f"€{c['revenue']:,.0f}M" if c.get("revenue") else "—"
        row["s² (contribución HHI)"] = round(c["share"] ** 2, 1)
        table_data.append(row)

    st.dataframe(pd.DataFrame(table_data), use_container_width=True, hide_index=True)

# FOOTER
st.markdown("---")
st.markdown(
    "<p style='text-align:center;color:#475569;font-size:0.75rem;'>"
    "Estructura de Mercado en España · Economía I · "
    "Fuentes: CNMC, AENA, NIQ, Worldpanel, ICEA, Unespa, Banco de España, REE, PwC · "
    "Datos 2024/2025"
    "</p>",
    unsafe_allow_html=True,
)
"""
Estructura de mercado en España
Dashboard de análisis sectorial · Economía I
Datos reales 2024/25

Fuentes: CNMC, AENA, NIQ, Worldpanel, ICEA, Unespa, Banco de España, REE, PwC

Para ejecutar:
    pip install -r requirements.txt
    streamlit run app.py
"""

import json
import time
from datetime import datetime
from pathlib import Path

import requests
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np

# CONFIG
st.set_page_config(
    page_title="Estructura de Mercado — España",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# CUSTOM CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&family=IBM+Plex+Mono:wght@400;500&display=swap');

    .stApp {
        font-family: 'DM Sans', sans-serif;
    }

    .main-header {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f172a 100%);
        padding: 2rem 2.5rem;
        border-radius: 16px;
        margin-bottom: 1.5rem;
        border: 1px solid #334155;
    }
    .main-header h1 {
        color: #f1f5f9;
        font-size: 2rem;
        font-weight: 800;
        margin: 0;
        letter-spacing: -0.03em;
    }
    .main-header p {
        color: #94a3b8;
        font-size: 0.9rem;
        margin: 0.3rem 0 0;
    }

    .metric-box {
        background: #1e293b;
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 1.1rem 1.3rem;
        text-align: center;
    }
    .metric-box .label {
        color: #64748b;
        font-size: 0.7rem;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        font-weight: 600;
    }
    .metric-box .value {
        color: #f1f5f9;
        font-size: 1.6rem;
        font-weight: 800;
        line-height: 1.2;
        margin-top: 0.2rem;
    }
    .metric-box .sub {
        color: #94a3b8;
        font-size: 0.75rem;
        margin-top: 0.15rem;
    }

    .insight-card {
        background: #1e293b;
        border: 1px solid #334155;
        border-left: 3px solid #3b82f6;
        border-radius: 8px;
        padding: 0.8rem 1rem;
        margin-bottom: 0.5rem;
        color: #cbd5e1;
        font-size: 0.85rem;
        line-height: 1.5;
    }

    .sector-badge {
        display: inline-block;
        padding: 0.25rem 0.8rem;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 700;
    }

    .interpretation-box {
        background: #1e293b;
        border: 1px solid #334155;
        border-radius: 10px;
        padding: 1.2rem;
        margin-bottom: 0.8rem;
    }
    .interpretation-box h4 {
        margin: 0 0 0.4rem;
        font-size: 0.95rem;
        font-weight: 700;
    }
    .interpretation-box p {
        color: #94a3b8;
        font-size: 0.82rem;
        line-height: 1.6;
        margin: 0;
    }

    div[data-testid="stSidebar"] {
        background: #0f172a;
    }
    div[data-testid="stSidebar"] .stMarkdown p,
    div[data-testid="stSidebar"] .stMarkdown li {
        color: #cbd5e1;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 0;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 0.6rem 1.2rem;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# REFRESH CONTROL
AUTO_REFRESH_INTERVAL = 30 * 60  # 30 minutos

def init_refresh_state() -> None:
    if "last_refresh_ts" not in st.session_state:
        st.session_state.last_refresh_ts = time.time()


def format_last_refresh() -> str:
    return datetime.fromtimestamp(st.session_state.last_refresh_ts).strftime("%d/%m/%Y %H:%M:%S")


def refresh_controls(container):
    init_refresh_state()
    container.markdown("#### 🔄")
    if container.button("Actualiza Datos"):
        st.session_state.last_refresh_ts = time.time()
        st.rerun()

    if time.time() - st.session_state.last_refresh_ts >= AUTO_REFRESH_INTERVAL:
        st.session_state.last_refresh_ts = time.time()
        st.rerun()

    container.markdown(f"<span style='color:#cbd5e1;'>Última actualización: {format_last_refresh()}</span>", unsafe_allow_html=True)
    container.markdown("<span style='color:#94a3b8;font-size:0.85rem;'>Actualización automática cada 30 minutos.</span>", unsafe_allow_html=True)

DATA_FILE = "sector_data.json"
DATA_FEED_URL = st.secrets.get("DATA_FEED_URL", None)


def fetch_json(url: str, timeout: int = 12) -> dict:
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    return response.json()


def load_local_sector_data() -> dict:
    path = Path(DATA_FILE)
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            return payload.get("sectors", payload)
    except Exception:
        pass
    return {}


def merge_sector_data(base: dict, source: dict) -> dict:
    merged = {}
    for sector, base_data in base.items():
        merged[sector] = base_data.copy()
        if sector not in source:
            continue

        source_data = source[sector]
        if isinstance(source_data, dict):
            merged[sector].update({k: v for k, v in source_data.items() if k != "companies"})
            if isinstance(source_data.get("companies"), list):
                live_companies = {c["name"]: c for c in source_data["companies"] if isinstance(c, dict) and c.get("name")}
                merged_companies = []
                for company in base_data["companies"]:
                    match = live_companies.get(company["name"])
                    merged_companies.append({**company, **match} if match else company)
                for company in source_data["companies"]:
                    if company.get("name") not in live_companies:
                        merged_companies.append(company)
                merged[sector]["companies"] = merged_companies
    return merged


def load_sector_data(base_data: dict) -> dict:
    live_data = {}
    if DATA_FEED_URL:
        try:
            payload = fetch_json(DATA_FEED_URL)
            if isinstance(payload, dict):
                live_data = payload.get("sectors", payload)
        except Exception as exc:
            st.sidebar.warning(f"No se pudieron cargar datos en vivo: {exc}")

    local_data = load_local_sector_data()
    if isinstance(local_data, dict) and local_data:
        live_data = merge_sector_data(live_data or {}, local_data)

    return merge_sector_data(base_data, live_data) if live_data else base_data

# DATA
SECTORS = {
    "Telecomunicaciones": {
        "year": "2025",
        "source": "CNMC · MobileWorldLive · Nae",
        "total_market": "63M líneas móviles",
        "market_type": "Oligopolio concentrado",
        "companies": [
            {"name": "MasOrange", "share": 41.24, "revenue": None, "color": "#FF6B00", "clients": "26M líneas"},
            {"name": "Movistar", "share": 26.24, "revenue": None, "color": "#019DF4", "clients": "16.5M líneas"},
            {"name": "Vodafone", "share": 18.50, "revenue": None, "color": "#E60000", "clients": "11.7M líneas"},
            {"name": "Digi", "share": 11.72, "revenue": None, "color": "#7E57C2", "clients": "7.4M líneas"},
            {"name": "OMVs", "share": 2.30, "revenue": None, "color": "#78909C", "clients": "1.4M líneas"},
        ],
        "insights": [
            "Top 3 operadores concentran el **86%** del mercado",
            "Digi es el único operador con **crecimiento neto** sostenido",
            "Tasa de cancelación: Telefónica **3.5%** vs Digi **10.5%**",
            "**534** comercializadoras activas en España",
        ],
        "sub_market": {
            "title": "Banda Ancha Fija (dic 2025) — 19.5M líneas",
            "data": [
                {"name": "Movistar", "share": 32.9, "color": "#019DF4"},
                {"name": "MasOrange", "share": 28.0, "color": "#FF6B00"},
                {"name": "Vodafone", "share": 21.0, "color": "#E60000"},
                {"name": "Digi", "share": 12.1, "color": "#7E57C2"},
                {"name": "Otros", "share": 6.0, "color": "#78909C"},
            ],
        },
        "interpretation": "El HHI más alto (~2.850) refleja la fusión Orange+Más Móvil. Con CR₃ del 86%, el sector opera como un oligopolio de facto con barreras de entrada por infraestructura. La entrada de Digi como cuarto operador es la principal fuerza competitiva.",
    },
    "Banca": {
        "year": "2025",
        "source": "Banco de España · Informes anuales · EBA",
        "total_market": "~€2.4T activos totales",
        "market_type": "Oligopolio (post-consolidación)",
        "companies": [
            {"name": "CaixaBank", "share": 25.5, "revenue": 5786, "color": "#007EAE", "clients": "21M clientes"},
            {"name": "Santander", "share": 24.0, "revenue": 13546, "color": "#EC0000", "clients": "17M cl. ES"},
            {"name": "BBVA", "share": 17.5, "revenue": 10566, "color": "#004481", "clients": "15M cl. ES"},
            {"name": "Sabadell", "share": 9.0, "revenue": 1827, "color": "#0099CC", "clients": "12M clientes"},
            {"name": "Bankinter", "share": 5.2, "revenue": 1060, "color": "#FF6600", "clients": "1.2M clientes"},
            {"name": "Unicaja", "share": 5.0, "revenue": 623, "color": "#00A651", "clients": "4M clientes"},
            {"name": "Otros", "share": 13.8, "revenue": None, "color": "#78909C", "clients": ""},
        ],
        "insights": [
            "**4 grandes** bancos gestionan **67%** de depósitos",
            "Beneficio récord conjunto: **€33.408M** en 2025",
            "De **55 entidades** en 2009 a **~11** en 2025",
            "Top 6 controlan **>75%** de depósitos",
        ],
        "sub_market": {
            "title": "Cuota en Depósitos — ~€1T depositados por hogares",
            "data": [
                {"name": "CaixaBank", "share": 24.0, "color": "#007EAE"},
                {"name": "Santander", "share": 20.0, "color": "#EC0000"},
                {"name": "BBVA", "share": 14.0, "color": "#004481"},
                {"name": "Sabadell", "share": 9.0, "color": "#0099CC"},
                {"name": "Bankinter", "share": 4.5, "color": "#FF6600"},
                {"name": "Unicaja", "share": 4.0, "color": "#00A651"},
                {"name": "Otros", "share": 24.5, "color": "#78909C"},
            ],
        },
        "interpretation": "La consolidación post-2008 (de 55 a ~11 entidades) ha creado un oligopolio bancario con HHI ~1.600. Las barreras regulatorias limitan la entrada, pero la banca digital y las fintech podrían disrumpir el equilibrio actual.",
    },
    "Energía Eléctrica": {
        "year": "2024-2025",
        "source": "CNMC · REE · PwC",
        "total_market": "30.3M puntos de suministro",
        "market_type": "Oligopolio con competencia creciente",
        "companies": [
            {"name": "Iberdrola", "share": 33.0, "revenue": None, "color": "#2E8B57", "clients": "~10M puntos"},
            {"name": "Endesa", "share": 31.5, "revenue": None, "color": "#00A650", "clients": "~9.5M puntos"},
            {"name": "Naturgy", "share": 19.0, "revenue": None, "color": "#FF8C00", "clients": "~5.7M puntos"},
            {"name": "TotalEnergies", "share": 3.8, "revenue": None, "color": "#D32F2F", "clients": "~1.1M puntos"},
            {"name": "Repsol", "share": 2.14, "revenue": None, "color": "#1565C0", "clients": "~650K puntos"},
            {"name": "Otros (534)", "share": 10.56, "revenue": None, "color": "#78909C", "clients": "~3.2M puntos"},
        ],
        "insights": [
            "Top 5 comercializadoras: **84.9%** del mercado",
            "**71.8%** clientes en mercado libre vs **28.2%** regulado (PVPC)",
            "**534** comercializadoras activas — líder europeo",
            "Precio medio 2025: **65.29 €/MWh** (+3.6% interanual)",
        ],
        "sub_market": None,
        "interpretation": "El mercado eléctrico español presenta un oligopolio en generación y distribución, pero alta competencia en comercialización (534 actores). La transición energética y la irrupción de renovables están alterando las dinámicas de poder. El precio marginalista amplifica la volatilidad.",
    },
    "Distribución Alimentaria": {
        "year": "2025",
        "source": "NIQ · Worldpanel by Numerator",
        "total_market": "€131.000M facturación total",
        "market_type": "Cuasi-monopolio del líder + competencia fragmentada",
        "companies": [
            {"name": "Mercadona", "share": 29.5, "revenue": 41858, "color": "#4CAF50", "clients": "93.2% hogares"},
            {"name": "Carrefour", "share": 7.2, "revenue": 11902, "color": "#1565C0", "clients": "63.8% hogares"},
            {"name": "Lidl", "share": 6.2, "revenue": 6952, "color": "#FFC107", "clients": "68.5% hogares"},
            {"name": "Dia", "share": 4.8, "revenue": 5740, "color": "#D32F2F", "clients": "50% hogares"},
            {"name": "Eroski", "share": 4.3, "revenue": None, "color": "#E65100", "clients": ""},
            {"name": "Consum", "share": 4.1, "revenue": 4707, "color": "#FF9800", "clients": "22.8% hogares"},
            {"name": "Alcampo", "share": 2.9, "revenue": 5004, "color": "#0D47A1", "clients": ""},
            {"name": "Aldi", "share": 1.8, "revenue": None, "color": "#0097A7", "clients": "41.2% hogares"},
            {"name": "Regionales", "share": 25.7, "revenue": None, "color": "#795548", "clients": ""},
            {"name": "Otros", "share": 13.5, "revenue": None, "color": "#78909C", "clients": ""},
        ],
        "insights": [
            "Mercadona (**29.5%**) = sus 6 competidores juntos",
            "Marca blanca: **50%** del gasto total (+0.9pp)",
            "Online crece **17.7%**, alcanza **7.3%** del mercado",
            "**25.585** supermercados operativos, **+850** aperturas/año",
        ],
        "sub_market": None,
        "interpretation": "Caso atípico: Mercadona (29.5%) genera un HHI bajo por la fragmentación del resto, pero su poder de mercado real es enorme. El índice de Lerner subestima su capacidad de fijar precios dada su estrategia de marca blanca (50% del gasto en MDD).",
    },
    "Transporte Aéreo": {
        "year": "2025",
        "source": "AENA · DGAC",
        "total_market": "~310M pasajeros/año",
        "market_type": "Competencia oligopolística (low-cost dominante)",
        "companies": [
            {"name": "Ryanair", "share": 22.0, "revenue": None, "color": "#003580", "clients": "68.1M pax"},
            {"name": "Vueling", "share": 16.0, "revenue": None, "color": "#e6b800", "clients": "49.6M pax"},
            {"name": "Iberia", "share": 7.2, "revenue": None, "color": "#D50032", "clients": "22.4M pax"},
            {"name": "Air Europa", "share": 5.5, "revenue": None, "color": "#0072CE", "clients": "~17M pax"},
            {"name": "EasyJet", "share": 5.5, "revenue": None, "color": "#FF6600", "clients": "~17M pax"},
            {"name": "Binter", "share": 3.6, "revenue": None, "color": "#00B0FF", "clients": "9M pax"},
            {"name": "Iberia Express", "share": 3.2, "revenue": None, "color": "#B71C1C", "clients": "~10M pax"},
            {"name": "Jet2.com", "share": 3.0, "revenue": None, "color": "#E91E63", "clients": "~9M pax"},
            {"name": "Otras", "share": 34.0, "revenue": None, "color": "#78909C", "clients": ""},
        ],
        "insights": [
            "Low-cost: **61.8%** del volumen total de pasajeros",
            "Ryanair crece **4.2%** pese a recortes regionales",
            "Binter: mayor crecimiento (**+10.3%**), sorpresa del año",
            "Vueling pierde cuota pese a ser la **#2**",
        ],
        "sub_market": None,
        "interpretation": "El transporte aéreo español muestra competencia oligopolística dominada por low-cost (61.8%). Ryanair lidera pese a conflictos con AENA por tasas. La cola larga de 'Otras' (34%) refleja la fragmentación del tráfico internacional — muchas aerolíneas con cuotas pequeñas.",
    },
    "Seguros": {
        "year": "2025",
        "source": "ICEA · Unespa · IPMARK",
        "total_market": "€85.879M en primas",
        "market_type": "Oligopolio moderado con bancaseguros",
        "companies": [
            {"name": "VidaCaixa", "share": 12.3, "revenue": 10631, "color": "#007EAE", "clients": ""},
            {"name": "Mapfre", "share": 11.1, "revenue": 9547, "color": "#D32F2F", "clients": ""},
            {"name": "Mutua Madrileña", "share": 10.36, "revenue": 8892, "color": "#1B5E20", "clients": ""},
            {"name": "Zurich", "share": 6.83, "revenue": 5868, "color": "#0D47A1", "clients": ""},
            {"name": "Allianz", "share": 4.71, "revenue": 4045, "color": "#003D7A", "clients": ""},
            {"name": "AXA", "share": 4.3, "revenue": 3695, "color": "#00008F", "clients": ""},
            {"name": "Generali", "share": 4.2, "revenue": 3609, "color": "#C62828", "clients": ""},
            {"name": "Catalana Occ.", "share": 4.17, "revenue": 3584, "color": "#FF6F00", "clients": ""},
            {"name": "Otros", "share": 42.03, "revenue": None, "color": "#78909C", "clients": ""},
        ],
        "insights": [
            "Mejor año de la historia: **€85.879M** (+13.7%)",
            "Top 3 acumulan **~34%** de cuota de mercado",
            "Zurich escala de **8ª a 4ª** posición en un año (**+72.4%**)",
            "Vida crece **+20%**, impulsado por bajada de tipos",
        ],
        "sub_market": None,
        "interpretation": "El sector asegurador español es el menos concentrado (HHI ~700), con un 'Otros' del 42%. La bancaseguros (VidaCaixa, Santander Seguros) compite con aseguradoras puras (Mapfre, Mutua). Las alianzas de distribución (MasOrange-Zurich, Carrefour-Mapfre) están redefiniendo el mercado.",
    },
}

# HELPER FUNCTIONS
def calc_hhi(companies: list[dict]) -> float:
    return sum(c["share"] ** 2 for c in companies)


def classify_hhi(hhi: float) -> tuple[str, str]:
    if hhi > 2500:
        return "Altamente concentrado", "#EF5350"
    elif hhi > 1500:
        return "Moderadamente concentrado", "#FFA726"
    return "Competitivo", "#66BB6A"


def calc_cr(companies: list[dict], n: int) -> float:
    sorted_c = sorted(companies, key=lambda c: c["share"], reverse=True)
    return sum(c["share"] for c in sorted_c[:n])


def estimate_lerner(hhi: float) -> float:
    """Rough Lerner index estimate from HHI (simplified Cournot relationship)."""
    return (hhi / 10000) * 0.4 + 0.05


def metric_html(label: str, value: str, sub: str = "", color: str = "#f1f5f9") -> str:
    sub_html = f'<div class="sub">{sub}</div>' if sub else ""
    return f"""
    <div class="metric-box">
        <div class="label">{label}</div>
        <div class="value" style="color: {color}">{value}</div>
        {sub_html}
    </div>
    """

SECTORS = load_sector_data(SECTORS)

# CHARTS
CHART_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="DM Sans, sans-serif", color="#cbd5e1"),
    margin=dict(l=20, r=20, t=40, b=20),
)


def make_donut(companies: list[dict], title: str = "Cuota de Mercado") -> go.Figure:
    fig = go.Figure(go.Pie(
        labels=[c["name"] for c in companies],
        values=[c["share"] for c in companies],
        marker=dict(colors=[c["color"] for c in companies]),
        hole=0.55,
        textinfo="label+percent",
        textfont=dict(size=11, color="#e2e8f0"),
        hovertemplate="<b>%{label}</b><br>Cuota: %{value:.1f}%<extra></extra>",
        sort=False,
    ))
    hhi = calc_hhi(companies)
    fig.add_annotation(
        text=f"<b>HHI</b><br><span style='font-size:20px;color:#60a5fa'>{hhi:,.0f}</span>",
        showarrow=False, font=dict(size=12, color="#94a3b8"),
    )
    fig.update_layout(
        **CHART_LAYOUT,
        title=dict(text=title, font=dict(size=14, color="#94a3b8")),
        showlegend=False,
        height=360,
    )
    return fig


def make_bar(companies: list[dict], metric: str = "share", title: str = "") -> go.Figure:
    filtered = [c for c in companies if c.get(metric) and c[metric] > 0]
    filtered.sort(key=lambda c: c[metric])

    if metric == "share":
        text_vals = [f"{c[metric]}%" for c in filtered]
        x_title = "Cuota (%)"
    else:
        text_vals = [f"€{c[metric]:,.0f}M" for c in filtered]
        x_title = "€ Millones"

    fig = go.Figure(go.Bar(
        y=[c["name"] for c in filtered],
        x=[c[metric] for c in filtered],
        orientation="h",
        marker=dict(
            color=[c["color"] for c in filtered],
            line=dict(width=0),
        ),
        text=text_vals,
        textposition="outside",
        textfont=dict(size=11, color="#e2e8f0"),
        hovertemplate="<b>%{y}</b>: %{x:.1f}<extra></extra>",
    ))
    fig.update_layout(
        **CHART_LAYOUT,
        title=dict(text=title, font=dict(size=14, color="#94a3b8")),
        height=max(220, len(filtered) * 36 + 80),
        xaxis=dict(
            title=x_title, gridcolor="#1e293b", zeroline=False,
            title_font=dict(size=11), tickfont=dict(size=10),
        ),
        yaxis=dict(tickfont=dict(size=11)),
    )
    return fig


def make_scatter_cr_hhi(sectors_data: dict) -> go.Figure:
    names, hhis, cr3s, colors = [], [], [], []
    for key, data in sectors_data.items():
        hhi = calc_hhi(data["companies"])
        cr3 = calc_cr(data["companies"], 3)
        _, col = classify_hhi(hhi)
        names.append(key)
        hhis.append(hhi)
        cr3s.append(cr3)
        colors.append(col)

    fig = go.Figure()

    # Zone backgrounds
    fig.add_vrect(x0=0, x1=1500, fillcolor="#66BB6A", opacity=0.06, line_width=0)
    fig.add_vrect(x0=1500, x1=2500, fillcolor="#FFA726", opacity=0.06, line_width=0)
    fig.add_vrect(x0=2500, x1=4000, fillcolor="#EF5350", opacity=0.06, line_width=0)

    # Threshold lines
    fig.add_vline(x=1500, line_dash="dash", line_color="#475569", line_width=1,
                  annotation_text="HHI 1500", annotation_font_size=10,
                  annotation_font_color="#64748b", annotation_position="top")
    fig.add_vline(x=2500, line_dash="dash", line_color="#475569", line_width=1,
                  annotation_text="HHI 2500", annotation_font_size=10,
                  annotation_font_color="#64748b", annotation_position="top")

    fig.add_trace(go.Scatter(
        x=hhis, y=cr3s,
        mode="markers+text",
        marker=dict(size=20, color=colors, line=dict(width=2, color="#0f172a")),
        text=names,
        textposition="top center",
        textfont=dict(size=11, color="#e2e8f0"),
        hovertemplate="<b>%{text}</b><br>HHI: %{x:,.0f}<br>CR₃: %{y:.1f}%<extra></extra>",
    ))

    fig.update_layout(
        **CHART_LAYOUT,
        title=dict(text="Mapa CR₃ vs HHI — Clasificación de Estructuras de Mercado",
                   font=dict(size=15, color="#cbd5e1")),
        xaxis=dict(title="HHI (Herfindahl-Hirschman)", range=[0, 4000],
                   gridcolor="#1e293b", title_font=dict(size=12), tickfont=dict(size=10)),
        yaxis=dict(title="CR₃ (%)", range=[0, 105],
                   gridcolor="#1e293b", title_font=dict(size=12), tickfont=dict(size=10)),
        height=480,
    )
    return fig


def make_comparative_bar(sectors_data: dict) -> go.Figure:
    rows = []
    for key, data in sectors_data.items():
        hhi = calc_hhi(data["companies"])
        _, col = classify_hhi(hhi)
        rows.append({"sector": key, "hhi": hhi, "color": col})
    df = pd.DataFrame(rows).sort_values("hhi")

    fig = go.Figure(go.Bar(
        y=df["sector"],
        x=df["hhi"],
        orientation="h",
        marker=dict(color=df["color"], line=dict(width=0)),
        text=[f"{h:,.0f}" for h in df["hhi"]],
        textposition="outside",
        textfont=dict(size=12, color="#e2e8f0", family="DM Sans"),
        hovertemplate="<b>%{y}</b><br>HHI: %{x:,.0f}<extra></extra>",
    ))
    fig.add_vline(x=1500, line_dash="dash", line_color="#FFA726", line_width=1.5,
                  annotation_text="Moderado", annotation_font_size=9, annotation_font_color="#FFA726")
    fig.add_vline(x=2500, line_dash="dash", line_color="#EF5350", line_width=1.5,
                  annotation_text="Altamente conc.", annotation_font_size=9, annotation_font_color="#EF5350")

    fig.update_layout(
        **CHART_LAYOUT,
        title=dict(text="Índice HHI por Sector", font=dict(size=15, color="#cbd5e1")),
        height=350,
        xaxis=dict(title="HHI", gridcolor="#1e293b", range=[0, 3500]),
        yaxis=dict(tickfont=dict(size=12)),
    )
    return fig

# SIDEBAR
with st.sidebar:
    refresh_controls(st)
    st.markdown("### 📊 Navegación")
    sector_options = ["🔍 Vista Comparativa"] + list(SECTORS.keys())
    selected = st.radio("Selecciona sector", sector_options, label_visibility="collapsed")

    st.markdown("---")
    st.markdown("### 📚 Conceptos clave")
    st.markdown("""
    - **HHI**: Σ(cuota²). <1500 competitivo, 1500-2500 moderado, >2500 concentrado
    - **CR₃ / CR₄**: Cuota acumulada de las 3 o 4 mayores empresas
    - **Índice de Lerner**: (P−CM)/P — mide poder de mercado (markup)
    - **Oligopolio**: Pocos vendedores, barreras de entrada, interdependencia estratégica
    """)
    st.markdown("---")
    st.markdown(
        "<p style='font-size:0.7rem;color:#64748b;'>Fuentes: CNMC, AENA, NIQ, Worldpanel, "
        "ICEA, Unespa, BdE, REE, PwC<br>Datos 2024-2025</p>",
        unsafe_allow_html=True,
    )


# HEADER
st.markdown("""
<div class="main-header">
    <h1>Estructura de Mercado — España</h1>
    <p>Análisis de concentración sectorial con datos reales 2024-2025 · Economía I</p>
</div>
""", unsafe_allow_html=True)

# COMPARATIVE VIEW

if selected == "🔍 Vista Comparativa":

    # Summary metrics
    all_hhis = {k: calc_hhi(v["companies"]) for k, v in SECTORS.items()}
    most_concentrated = max(all_hhis, key=all_hhis.get)
    least_concentrated = min(all_hhis, key=all_hhis.get)

    cols = st.columns(4)
    cols[0].markdown(metric_html("Sectores analizados", str(len(SECTORS)), "con datos reales"), unsafe_allow_html=True)
    cols[1].markdown(metric_html("Mayor HHI", f"{max(all_hhis.values()):,.0f}",
                                  most_concentrated.split(" ", 1)[1] if " " in most_concentrated else most_concentrated,
                                  "#EF5350"), unsafe_allow_html=True)
    cols[2].markdown(metric_html("Menor HHI", f"{min(all_hhis.values()):,.0f}",
                                  least_concentrated.split(" ", 1)[1] if " " in least_concentrated else least_concentrated,
                                  "#66BB6A"), unsafe_allow_html=True)
    avg_hhi = np.mean(list(all_hhis.values()))
    cols[3].markdown(metric_html("HHI medio", f"{avg_hhi:,.0f}", classify_hhi(avg_hhi)[0],
                                  classify_hhi(avg_hhi)[1]), unsafe_allow_html=True)

    st.markdown("")

    # Charts
    col1, col2 = st.columns([1, 1])
    with col1:
        st.plotly_chart(make_comparative_bar(SECTORS), use_container_width=True)
    with col2:
        st.plotly_chart(make_scatter_cr_hhi(SECTORS), use_container_width=True)

    # Comparative table
    st.markdown("#### 📋 Tabla Comparativa de Métricas")
    table_rows = []
    for key, data in SECTORS.items():
        hhi = calc_hhi(data["companies"])
        label, _ = classify_hhi(hhi)
        table_rows.append({
            "Sector": key,
            "HHI": round(hhi),
            "CR₃ (%)": round(calc_cr(data["companies"], 3), 1),
            "CR₄ (%)": round(calc_cr(data["companies"], 4), 1),
            "Lerner est. (%)": round(estimate_lerner(hhi) * 100, 1),
            "Clasificación": label,
            "Tipo": data["market_type"],
            "Mercado total": data["total_market"],
        })
    df_table = pd.DataFrame(table_rows).sort_values("HHI", ascending=False)
    st.dataframe(df_table, use_container_width=True, hide_index=True)

    # Interpretations
    st.markdown("#### 🧠 Interpretación Económica")
    for key, data in SECTORS.items():
        _, col = classify_hhi(calc_hhi(data["companies"]))
        st.markdown(f"""
        <div class="interpretation-box" style="border-left: 3px solid {col};">
            <h4 style="color: {col};">{key}</h4>
            <p>{data['interpretation']}</p>
        </div>
        """, unsafe_allow_html=True)

    # Lerner / Markup
    st.markdown("#### 📐 Markup y Elasticidad")
    st.markdown("""
    <div class="interpretation-box" style="border-left: 3px solid #AB47BC;">
        <h4 style="color: #AB47BC;">Índice de Lerner y Relación con HHI</h4>
        <p>
            En competencia a la Cournot, el índice de Lerner (L = (P−CM)/P) está relacionado con el HHI
            a través de la elasticidad de la demanda: <b>L = HHI / (ε × 10.000)</b>, donde ε es la elasticidad-precio.
            Nuestras estimaciones usan ε implícita entre 2 y 4 según el sector.<br><br>
            <b>Telecom</b> (baja elasticidad, switching costs altos) → Lerner ~16%<br>
            <b>Alimentación</b> (elasticidad moderada, muchos sustitutos) → Lerner ~9%<br>
            <b>Seguros</b> (alta fragmentación, competencia en precio) → Lerner ~7%<br><br>
            Estas son estimaciones basadas en la estructura de mercado. Los markups reales requieren
            datos de costes marginales que no están disponibles públicamente.
        </p>
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────
# SECTOR DETAIL VIEW
# ─────────────────────────────────────────────
else:
    data = SECTORS[selected]
    companies = data["companies"]
    hhi = calc_hhi(companies)
    hhi_label, hhi_color = classify_hhi(hhi)
    cr3 = calc_cr(companies, 3)
    cr4 = calc_cr(companies, 4)
    lerner = estimate_lerner(hhi)

    # Sector header
    st.markdown(f"**{data['source']}** · {data['year']}")

    # KPI row
    cols = st.columns(6)
    cols[0].markdown(metric_html("Mercado total", data["total_market"]), unsafe_allow_html=True)
    cols[1].markdown(metric_html("HHI", f"{hhi:,.0f}", hhi_label, hhi_color), unsafe_allow_html=True)
    cols[2].markdown(metric_html("CR₃", f"{cr3:.1f}%", "Top 3 empresas"), unsafe_allow_html=True)
    cols[3].markdown(metric_html("CR₄", f"{cr4:.1f}%", "Top 4 empresas"), unsafe_allow_html=True)
    cols[4].markdown(metric_html("Lerner est.", f"{lerner*100:.1f}%", "Markup aprox.", "#CE93D8"), unsafe_allow_html=True)
    cols[5].markdown(metric_html("Tipo", data["market_type"]), unsafe_allow_html=True)

    st.markdown("")

    # Charts row
    col1, col2 = st.columns([2, 3])
    with col1:
        st.plotly_chart(make_donut(companies), use_container_width=True)
    with col2:
        st.plotly_chart(make_bar(companies, "share", "Cuota de Mercado (%)"), use_container_width=True)

    # Revenue chart if available
    companies_with_rev = [c for c in companies if c.get("revenue")]
    if companies_with_rev:
        st.plotly_chart(
            make_bar(companies_with_rev, "revenue", "Facturación / Beneficio neto (€ Millones)"),
            use_container_width=True,
        )

    # Sub-market
    if data.get("sub_market"):
        sub = data["sub_market"]
        st.markdown(f"#### {sub['title']}")
        st.plotly_chart(
            make_bar(sub["data"], "share", ""),
            use_container_width=True,
        )

    # Insights
    st.markdown("#### 💡 Insights clave")
    ins_cols = st.columns(2)
    for i, ins in enumerate(data["insights"]):
        with ins_cols[i % 2]:
            st.markdown(f'<div class="insight-card">{ins}</div>', unsafe_allow_html=True)

    # Interpretation
    st.markdown("#### 🧠 Interpretación")
    st.markdown(f"""
    <div class="interpretation-box" style="border-left: 3px solid {hhi_color};">
        <p>{data['interpretation']}</p>
    </div>
    """, unsafe_allow_html=True)

    # Company table
    st.markdown("#### 📋 Detalle por Empresa")
    table_data = []
    for c in companies:
        row = {
            "Empresa": c["name"],
            "Cuota (%)": c["share"],
            "Clientes": c["clients"] if c["clients"] else "—",
        }
        if companies_with_rev:
            row["Fact./Benef. (€M)"] = f"€{c['revenue']:,.0f}M" if c.get("revenue") else "—"
        row["s² (contribución HHI)"] = round(c["share"] ** 2, 1)
        table_data.append(row)

    st.dataframe(pd.DataFrame(table_data), use_container_width=True, hide_index=True)

# FOOTER
st.markdown("---")
st.markdown(
    "<p style='text-align:center;color:#475569;font-size:0.75rem;'>"
    "Estructura de Mercado en España · Economía I · "
    "Fuentes: CNMC, AENA, NIQ, Worldpanel, ICEA, Unespa, Banco de España, REE, PwC · "
    "Datos 2024/2025"
    "</p>",
    unsafe_allow_html=True,
)
