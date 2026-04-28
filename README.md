# Estructura de Mercado — España
## Dashboard de Análisis Sectorial · Economía I

Dashboard interactivo con datos reales (2024-2025) sobre la estructura de mercado de 6 sectores clave de la economía española.

### Sectores cubiertos
| 📡 Telecomunicaciones | CNMC | MasOrange 41.2%, HHI ~2.850 |
| 🏦 Banca | Banco de España | Top 4 = 67% depósitos |
| ⚡ Energía Eléctrica | CNMC / REE | 534 comercializadoras |
| 🛒 Distribución Alimentaria | NIQ / Worldpanel | Mercadona 29.5% |
| ✈️ Transporte Aéreo | AENA | Ryanair 22%, low-cost 61.8% |
| 🛡️ Seguros | ICEA / Unespa | €85.879M primas, récord |

### Métricas calculadas
- **HHI** (Herfindahl-Hirschman Index)
- **CR₃ / CR₄** (Concentration Ratios)
- **Índice de Lerner** estimado (markup)
- Clasificación de estructura de mercado

---

## Ejecución local

```bash
# 1. Instalar dependencias
pip install -r requirements.txt

# 2. Ejecutar
streamlit run app.py
```

---

## 🌐 Despliegue en Streamlit Cloud

1. Sube `app.py`, `requirements.txt` y la carpeta `.streamlit` a un repositorio de GitHub
2. Ve a [share.streamlit.io](https://share.streamlit.io)
3. Conecta tu repo y selecciona `app.py` como archivo principal
4. ¡Listo! Se despliega automáticamente

> El archivo `.streamlit/config.toml` configura el modo `headless` y un tema oscuro compatible con el diseño del dashboard.

---

## 🔄 Actualización automática de datos (futuro)

Para conectar fuentes en tiempo real, puedes añadir funciones de fetch:

```python
import requests

def fetch_cnmc_telecom():
    """Ejemplo: datos abiertos CNMC."""
    url = "https://data.cnmc.es/api/..."  # endpoint real
    response = requests.get(url)
    return response.json()

def fetch_ine_data(table_id):
    """API del INE (INEbase)."""
    url = f"https://servicios.ine.es/wstempus/js/ES/DATOS_TABLA/{table_id}"
    response = requests.get(url)
    return response.json()
```

Configura `st.cache_data(ttl=3600)` para cachear las llamadas y `st.experimental_rerun` o un cron job para refrescar periódicamente.

---

## 📚 Fuentes
- CNMC — data.cnmc.es
- AENA — aena.es/estadisticas
- NIQ (Nielsen) — Panel de consumo
- Worldpanel by Numerator — Balance de la Distribución
- ICEA / Unespa — Rankings aseguradores
- Banco de España — Estadísticas de instituciones financieras
- REE — Sistema eléctrico español
- PwC — Informe mercado minorista electricidad
