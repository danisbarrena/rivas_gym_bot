import os
import sys
import time
from datetime import date
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeoutError
from config import decidir_enlace_y_hora, LOGIN_URL

GYM_USER = os.getenv("GYM_USER")
GYM_PASS = os.getenv("GYM_PASS")

def log(msg: str):
    print(f"[RIVASBOT] {msg}", flush=True)

def _rellenar_login(page):
    """
    Intenta rellenar el formulario de login con selectores robustos.
    """
    # Campo usuario (texto o email)
    try:
        # Si hay label accesible
        page.get_by_label("Usuario", exact=False).fill(GYM_USER, timeout=2000)
    except Exception:
        # Si no, coge el primer input de texto/email visible
        page.locator("input[type='text'], input[type='email']").first.fill(GYM_USER, timeout=4000)

    # Campo contraseña
    try:
        page.get_by_label("Contraseña", exact=False).fill(GYM_PASS, timeout=2000)
    except Exception:
        page.locator("input[type='password']").first.fill(GYM_PASS, timeout=4000)

    # Botón acceder
    try:
        page.get_by_role("button", name="Acceder").click(timeout=4000)
    except Exception:
        page.get_by_text("Acceder", exact=False).click(timeout=4000)

def reservar_para(d: date) -> bool:
    url, hora = decidir_enlace_y_hora(d)
    if not url:
        log(f"{d} → Config: no se reserva (p. ej. domingos de agosto).")
        return True

    log(f"Fecha: {d}  URL: {url}  Hora: {hora}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context()
        page = ctx.new_page()

        try:
            # 1) Página de selección de hora
            page.goto(url, wait_until="domcontentloaded", timeout=60000)

            # 2) Click en la hora objetivo (celda/botón con texto exacto)
            log("Buscando la hora en la tabla…")
            page.get_by_text(hora, exact=True).first.click(timeout=30000)

            # 3) Modal de duración → "90'"
            log("Clic en duración 90'…")
            page.get_by_text("90'", exact=True).first.click(timeout=30000)

            # 4) Puede saltar login ahora
            if LOGIN_URL in page.url:
                if not (GYM_USER and GYM_PASS):
                    raise RuntimeError("Faltan credenciales GYM_USER/GYM_PASS")
                log("Haciendo login…")
                _rellenar_login(page)

            # 5) Esperar pantalla de resumen y pulsar "Reservar"
            log("Esperando botón 'Reservar'…")
            page.get_by_role("button", name="Reservar").first.click(timeout=60000)

            # 6) Confirmación: esperamos estado estable y algún indicio
            log("Esperando confirmación…")
            page.wait_for_load_state("networkidle", timeout=60000)

            # Señales típicas de reserva confirmada
            posibles = [
                "text=Reserva confirmada",
                "text=Reserva realizada",
                "text=Cancelar reserva",
                "text=Mis reservas"
            ]
            ok = False
            for sel in posibles:
                try:
                    if page.locator(sel).first.is_visible(timeout=2000):
                        ok = True
                        break
                except PWTimeoutError:
                    pass

            if not ok:
                log("No encontré texto inequívoco de confirmación. Revisa la captura.")
                page.screenshot(path="fallback_state.png")
                return False

            log("¡Reserva completada!")
            return True

        except Exception as e:
            log(f"ERROR: {e}")
            try:
                page.screenshot(path="error.png")
            except Exception:
                pass
            return False
        finally:
            ctx.close()
            browser.close()

if __name__ == "__main__":
    # Permite pasar fecha YYYY-MM-DD para pruebas
    d = date.today()
    if len(sys.argv) > 1:
        d = date.fromisoformat(sys.argv[1])

    ok = reservar_para(d)
    if not ok:
        log("Reintentando en 15 s…")
        time.sleep(15)
        ok = reservar_para(d)

    sys.exit(0 if ok else 1)
