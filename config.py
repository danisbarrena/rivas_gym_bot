from datetime import date
import os
import json
import holidays

# URLs base
URL_ENTRE_SEMANA = "https://deportesrivas.deporsite.net/reservas?IdDeporte=37"
URL_FINDES_FESTIVOS = "https://deportesrivas.deporsite.net/reservas?IdDeporte=56"
LOGIN_URL = "https://deportesrivas.deporsite.net/login"

# Horas objetivo por tipo de día
HORA_ENTRE_SEMANA = "20:30"
HORA_MANANA = "13:30"

def _load_local_json(year: int) -> set[str]:
    """Carga festivos LOCALES (no nacionales/autonómicos) desde json del año."""
    fname = f"festivos_rivas_{year}.json"
    if os.path.exists(fname):
        with open(fname, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()

def es_festivo_rivas(d: date) -> bool:
    """True si el día es festivo (nacional, autonómico Madrid o local Rivas)."""
    es_md = holidays.country_holidays("ES", subdiv="MD", years=[d.year])
    if d in es_md:
        return True
    locales = _load_local_json(d.year)
    return d.isoformat() in locales

def decidir_enlace_y_hora(d: date):
    """
    Devuelve (url, hora) según reglas:
      - L-V → 20:30 con IdDeporte=37
      - Sábado → 13:30 con IdDeporte=56
      - Domingo (excepto AGOSTO) → 13:30 con IdDeporte=56
      - Cualquier festivo (Madrid o local Rivas) → 13:30 con IdDeporte=56
    Si es domingo de agosto, devuelve (None, None) para NO reservar.
    """
    # Domingos de agosto: no reservar
    if d.month == 8 and d.weekday() == 6:
        return None, None

    if es_festivo_rivas(d):
        return URL_FINDES_FESTIVOS, HORA_MANANA

    wd = d.weekday()  # 0=L ... 6=D
    if wd <= 4:
        return URL_ENTRE_SEMANA, HORA_ENTRE_SEMANA
    elif wd == 5:
        return URL_FINDES_FESTIVOS, HORA_MANANA
    else:
        return URL_FINDES_FESTIVOS, HORA_MANANA
