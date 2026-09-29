#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PROGRAMACION SEMANAL - Deja la aplicacion corriendo sola.

Sin esto, el radar sirve unicamente el dia que alguien se acuerde de abrirlo.
Y un servicio que hay que recordar es un servicio que no se paga.

Registra una tarea del Programador de tareas de Windows que:
  - corre la aplicacion todos los lunes a las 7:00
  - actualiza los datos y genera el informe semanal en PDF
  - NO abre el panel (abrirlo en una tarea programada dejaria el proceso colgado)
  - guarda un log para poder revisar que paso

Usa schtasks, que viene con Windows. No instala nada.

Uso:
    python src/programar.py --instalar
    python src/programar.py --estado
    python src/programar.py --desinstalar
    python src/programar.py --instalar --dia lunes --hora 9:30
"""

import argparse
import os
import subprocess
import sys
from datetime import datetime

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
PYTHON = os.path.join(RAIZ, ".venv", "Scripts", "python.exe")
APP = os.path.join(RAIZ, "src", "app.py")
LOG = os.path.join(RAIZ, "programacion.log")

TAREA = "RadarLicitaciones"
DIAS = {"lunes": "MON", "martes": "TUE", "miercoles": "WED", "jueves": "THU",
        "viernes": "FRI", "sabado": "SAT", "domingo": "SUN"}


def ruta_python():
    if os.path.exists(PYTHON):
        return PYTHON
    return sys.executable


def comando():
    """Comando que la tarea programada va a ejecutar.

    El `cmd /c` NO es opcional: schtasks ejecuta el comando directamente, sin
    shell, asi que un `>>` se pasaria a Python como argumento literal en vez de
    redirigir la salida, y el log nunca se escribiria. El fallo es silencioso:
    la tarea dice "CORRECTO" y no hay log.
    """
    py = ruta_python()
    return 'cmd /c ""%s" "%s" --sin-panel >> "%s" 2>&1"' % (py, APP, LOG)


def instalar(dia, hora):
    if not os.path.exists(os.path.dirname(PYTHON)):
        print("Falta el entorno virtual. Crear con:")
        print("    cd \"%s\"" % RAIZ)
        print("    uv venv .venv")
        print("    uv pip install --python .venv\\Scripts\\python.exe pypdf")
        return 1

    hh, mm = hora.split(":")
    clave = DIAS.get(dia.lower())
    if not clave:
        print("Dia no valido. Usa: " + ", ".join(DIAS))
        return 1
    if not (0 <= int(hh) <= 23 and 0 <= int(mm) <= 59):
        print("Hora no valida. Formato: HH:MM")
        return 1

    desinstalar(silencioso=True)

    cmd = ["schtasks", "/create", "/tn", TAREA, "/tr", comando(),
           "/sc", "weekly", "/d", clave, "/st", "%02d:%02d" % (int(hh), int(mm)),
           "/f"]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode == 0:
        print("Tarea programada instalada.")
        print("   Nombre   : " + TAREA)
        print("   Cuando   : cada %s a las %s" % (dia.lower(), hora))
        print("   Que hace  : actualiza datos y genera el informe semanal")
        print("   Log      : " + LOG)
        print("")
        print("  Para probarla ahora mismo sin esperar al lunes:")
        print("     schtasks /run /tn " + TAREA)
        return 0
    print("No se pudo crear la tarea:")
    print("  " + (r.stdout or "").strip())
    print("  " + (r.stderr or "").strip())
    return 1


def desinstalar(silencioso=False):
    r = subprocess.run(["schtasks", "/delete", "/tn", TAREA, "/f"],
                       capture_output=True, text=True)
    if not silencioso:
        if r.returncode == 0:
            print("Tarea programada eliminada.")
        else:
            print("No habia ninguna tarea programada instalada.")
    return r.returncode == 0


def estado():
    r = subprocess.run(["schtasks", "/query", "/tn", TAREA, "/v", "/fo", "list"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print("No hay ninguna tarea programada instalada.")
        print("  Instalar con:  python src/programar.py --instalar")
        return 1
    print("Tarea programada activa:")
    for linea in r.stdout.splitlines():
        if any(k in linea for k in ("Nombre", "TaskName", "Programar", "Schedule",
                                    "Estado", "Status", " proxima", "Next")):
            print("  " + linea.strip())
    if os.path.exists(LOG):
        tam = os.path.getsize(LOG)
        ult = datetime.fromtimestamp(os.path.getmtime(LOG))
        print("\n  Log: %d bytes, ultima escritura %s" % (tam, ult.strftime("%d/%m/%Y %H:%M")))
    return 0


def main():
    ap = argparse.ArgumentParser(description="Programacion semanal de la aplicacion.")
    ap.add_argument("--instalar", action="store_true")
    ap.add_argument("--desinstalar", action="store_true")
    ap.add_argument("--estado", action="store_true")
    ap.add_argument("--dia", default="lunes", help="lunes, martes, ... domingo")
    ap.add_argument("--hora", default="07:00", help="HH:MM, 24 horas")
    args = ap.parse_args()

    if args.instalar:
        return instalar(args.dia, args.hora)
    if args.desinstalar:
        return 0 if desinstalar() else 1
    return estado()


if __name__ == "__main__":
    raise SystemExit(main())