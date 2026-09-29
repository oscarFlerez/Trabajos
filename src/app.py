#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
APLICACION - Un solo comando.

Hasta ahora la aplicacion se usaba en tres pasos:
    radar.py -> informe.py -> panel.py
Eso es comodo para quien la desarrollo y una barrera para el cliente.

Este script hace los tres y deja el panel abierto. Ademas revisa que falte
nada antes de arrancar, y explica en voz alta que esta haciendo y que
salio, porque una aplicacion que no dice nada parece estar colgada.

Uso:
    python src/app.py
    python src/app.py --sin-actualizar     (no baja datos, solo abre el panel)
    python src/app.py --actualizar         (solo actualiza y sale)
    python src/app.py --puerto 9000
"""

import argparse
import importlib
import os
import subprocess
import sys
import threading
import time
import webbrowser

# La salida va con caracteres del castellano (acentos, enie, simbolos). Cuando el
# programa corre SIN consola —por ejemplo desde una tarea programada— Python usa
# cp1252 y se cae al imprimir: "UnicodeEncodeError: charmap codec can't encode".
# Se fuerza UTF-8 tolerante para que funcione igual en los dos casos.
if "sys" not in dir():
    import sys

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(RAIZ, "src")
sys.path.insert(0, SRC)

VERDE, AMARILLO, ROJO, GRIS, FIN = "\033[32m", "\033[33m", "\033[31m", "\033[90m", "\033[0m"
if os.name == "nt" and not sys.stdout.isatty():
    VERDE = AMARILLO = ROJO = GRIS = FIN = ""


def paso(n, texto):
    print("\n" + GRIS + "[%d/3]" % n + FIN + " " + texto)


def ok(texto):
    print("      " + VERDE + "OK" + FIN + "   " + texto)


def aviso(texto):
    print("      " + AMARILLO + "AVISO" + FIN + " " + texto)


def error(texto):
    print("      " + ROJO + "FALLO" + FIN + " " + texto)


def revisar_entorno():
    """Comprueba lo que falta ANTES de arrancar, no a mitad del trabajo."""
    faltantes = []
    if not os.path.exists(os.path.join(RAIZ, ".venv")):
        print(ROJO + "No existe el entorno virtual." + FIN)
        print("  Crear con:")
        print("    cd " + RAIZ)
        print("    uv venv .venv")
        print("    uv pip install --python .venv/Scripts/python.exe pypdf")
        return False
    try:
        importlib.import_module("pypdf")
    except ImportError:
        faltantes.append("pypdf (para leer pliegos en PDF)")
    if faltantes:
        aviso("Falta: " + ", ".join(faltantes))
        print("      El resto de la aplicacion funciona igual.")
    return True


def correr(modulo, argumentos=()):
    ruta = os.path.join(SRC, modulo)
    # Sin este flush, la salida del proceso hijo aparece ANTES que la del padre
    # y los pasos se ven desordenados.
    sys.stdout.flush()
    sys.stderr.flush()
    proc = subprocess.run([sys.executable, ruta] + list(argumentos),
                         capture_output=True, text=True, encoding="utf-8",
                         errors="replace")
    if proc.stdout:
        print(proc.stdout)
    if proc.returncode != 0 and proc.stderr:
        # Sin esto solo se ve "FALLO"; el motivo real se pierde y hay que
        # adivinar. En una tarea programada es la unica pista que queda.
        print("      " + ROJO + "detalle del error:" + FIN)
        for linea in proc.stderr.strip().splitlines()[-6:]:
            print("        " + linea)
    sys.stdout.flush()
    return proc.returncode == 0


def resumen():
    """Lee el CSV y cuenta, para poder decirlo en voz alta."""
    import csv
    ruta = os.path.join(RAIZ, "oportunidades.csv")
    if not os.path.exists(ruta):
        return None
    with open(ruta, "r", encoding="utf-8-sig", newline="") as fh:
        filas = list(csv.DictReader(fh))
    if not filas:
        return {"n": 0, "alta": 0, "valor": 0}
    valor = 0
    for f in filas:
        try:
            valor += int(str(f.get("presupuesto") or "0").replace(".", "").replace(",", ""))
        except ValueError:
            pass
    alta = sum(1 for f in filas if int(f.get("score") or 0) >= 60)
    return {"n": len(filas), "alta": alta, "valor": valor}


def main():
    ap = argparse.ArgumentParser(description="Radar de licitaciones: actualiza y abre el panel.")
    ap.add_argument("--sin-actualizar", action="store_true", help="No bajar datos, solo abrir el panel")
    ap.add_argument("--actualizar", action="store_true", help="Solo actualizar y salir")
    ap.add_argument("--puerto", type=int, default=8765)
    ap.add_argument("--sin-navegador", action="store_true")
    ap.add_argument("--sin-panel", action="store_true",
                    help="Actualiza y genera el informe, pero no abre el panel. Es lo que usa la tarea programada.")
    args = ap.parse_args()

    print("=" * 66)
    print("  RADAR DE LICITACIONES - aplicacion local")
    print("=" * 66)

    paso(1, "Revisando que este todo en su sitio...")
    if not revisar_entorno():
        return 1
    ok("Entorno correcto")

    paso(2, "Buscando procesos abiertos en SECOP...")
    exito = True
    if args.sin_actualizar:
        aviso("Omitido por --sin-actualizar")
    else:
        inicio = time.time()
        exito = correr("radar.py")
        if exito:
            r = resumen()
            if r and r["n"]:
                ok("%d oportunidades, %d de alta prioridad, $ %s en juego (%.0fs)"
                   % (r["n"], r["alta"], "{:,}".format(r["valor"]).replace(",", "."),
                      time.time() - inicio))
            elif r:
                aviso("No salio ninguna oportunidad con el perfil actual")
        else:
            error("La busqueda fallo. Revisa la conexion a internet.")

    if args.actualizar and not args.sin_panel:
        print()
        return 0 if exito else 1

    paso(3, "Preparando el informe...")
    if exito:
        if correr("informe.py", ["--cliente", "su empresa"]):
            pdf = os.path.join(RAIZ, "informe-semanal.pdf")
            ok("Informe semanal listo: " + os.path.basename(pdf)) if os.path.exists(pdf) \
                else aviso("No se genero el PDF; quedo el HTML")
        else:
            aviso("No se genero el informe. El panel funciona igual.")

    # ---- Panel ----
    if args.sin_panel:
        print("\n  " + GRIS + "Panel no abierto (--sin-panel). "
              "Datos e informe actualizados." + FIN)
        print("")
        return 0 if exito else 1

    url = "http://127.0.0.1:%d/" % args.puerto
    print("\n" + "=" * 66)
    print("  " + VERDE + "LISTO" + FIN)
    print("  " + url)
    print("  " + GRIS + "-" * 62)
    print("  Elija si cada oportunidad 'Sirvio' o 'No sirvio'.")
    print("  Eso es lo unico que necesita hacer, y hace que la semana")
    print("  que viene el filtro sea mas preciso.")
    print("  Para cerrar: Ctrl+C" + FIN)
    print("=" * 66)

    import panel
    from http.server import HTTPServer
    srv = HTTPServer(("127.0.0.1", args.puerto), panel.Manejador)
    if not args.sin_navegador:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nAplicacion cerrada.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())