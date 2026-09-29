#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
INFORME SEMANAL - Convierte los datos en algo que el cliente abra.

El radar produce un CSV y el lector produce un JSON. Ninguno de los dos se
vende: lo que se vende es un informe que le dice al cliente que hacer.

Este script junta las tres salidas (oportunidades, analisis de pliego e
historico de precision) y produce un PDF de una pagina por seccion, en
lenguaje de negocio y sin mencionar datasets ni APIs.

Uso:
    python src/informe.py                    -> informe-semanal.pdf
    python src/informe.py --html             -> solo el HTML, sin PDF
    python src/informe.py --cliente "Nombre S.A.S."

Requiere Chrome o Edge en el sistema para el PDF. Con --html no hace falta.
"""

import argparse
import csv
import glob
import html
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import date, datetime

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


def cargar_oportunidades():
    ruta = os.path.join(RAIZ, "oportunidades.csv")
    if not os.path.exists(ruta):
        return None
    with open(ruta, "r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def cargar_pliego():
    ruta = os.path.join(RAIZ, "analisis_pliego.json")
    if not os.path.exists(ruta):
        return None
    with open(ruta, "r", encoding="utf-8") as fh:
        return json.load(fh)


def cargar_precision():
    ruta = os.path.join(RAIZ, "historial.jsonl")
    if not os.path.exists(ruta):
        return None
    utiles = descartadas = pendientes = 0
    with open(ruta, "r", encoding="utf-8") as fh:
        for linea in fh:
            if not linea.strip():
                continue
            for op in json.loads(linea).get("oportunidades", []):
                e = op.get("estado", "pendiente")
                if e == "util":
                    utiles += 1
                elif e == "descartado":
                    descartadas += 1
                else:
                    pendientes += 1
    total = utiles + descartadas
    return {"utiles": utiles, "descartadas": descartadas,
            "pendientes": pendientes, "precision": (utiles / total * 100) if total else None}


def peso(valor):
    try:
        return int(str(valor or "0").replace(".", "").replace(",", ""))
    except ValueError:
        return 0


def e(moneda):
    return "$ {:,}".format(moneda).replace(",", ".")


def corto(texto, n=150):
    texto = (texto or "").strip()
    return texto if len(texto) <= n else texto[:n - 1].rstrip() + "..."


def buscar_navegador():
    candidatos = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ]
    for c in candidatos:
        if os.path.exists(c):
            return c
    for nombre in ("chrome", "msedge", "chromium"):
        ruta = shutil.which(nombre)
        if ruta:
            return ruta
    return None


CSS = """
@page { size: A4; margin: 16mm 14mm; }
body { font-family: "Segoe UI", Arial, sans-serif; font-size: 10pt; color: #1a1a1a; line-height: 1.5; }
.cabecera { border-bottom: 3px solid #0b3d5c; padding-bottom: 12px; margin-bottom: 18px; }
.cabecera h1 { font-size: 20pt; color: #0b3d5c; margin: 0 0 3px; }
.cabecera .sub { color: #666; font-size: 9.5pt; }
h2 { font-size: 13pt; color: #0b3d5c; border-bottom: 1px solid #c9d6dd; padding-bottom: 3px;
     margin: 20px 0 9px; page-break-after: avoid; }
h3 { font-size: 11pt; color: #14506f; margin: 14px 0 6px; page-break-after: avoid; }
table { border-collapse: collapse; width: 100%; font-size: 8.6pt; margin: 8px 0; }
th { background: #0b3d5c; color: #fff; text-align: left; padding: 5px 6px; }
td { padding: 5px 6px; border-bottom: 1px solid #dde5ea; vertical-align: top; }
tr:nth-child(even) td { background: #f6f9fa; }
.kpi { display: flex; gap: 10px; margin: 12px 0; }
.kpi div { flex: 1; border: 1px solid #c9d6dd; border-radius: 4px; padding: 9px 11px; text-align: center; }
.kpi .n { font-size: 19pt; font-weight: 600; color: #0b3d5c; display: block; }
.kpi .t { font-size: 8.2pt; color: #666; text-transform: uppercase; letter-spacing: .4px; }
.alta td:first-child { border-left: 4px solid #1a7f37; }
.media td:first-child { border-left: 4px solid #bf8700; }
.baja td:first-child { border-left: 4px solid #a40e26; }
.caja { border: 1px solid #c9d6dd; border-left: 4px solid #0b3d5c; background: #f6f9fa;
       padding: 10px 13px; margin: 11px 0; }
.alerta { border-left-color: #a40e26; background: #fdf5f6; }
.ok { border-left-color: #1a7f37; background: #f4faf6; }
.accion { border-left: 3px solid #bf8700; background: #fffdf5; padding: 8px 12px; margin: 8px 0; }
.pie { margin-top: 26px; padding-top: 9px; border-top: 1px solid #dde5ea;
       font-size: 8pt; color: #888; }
code { background: #eef2f4; padding: 1px 4px; border-radius: 2px; }
"""


def construir_html(cliente, ops, pliego, precision):
    hoy = date.today()
    lunes = hoy - __import__("datetime").timedelta(days=hoy.weekday())
    p = ['<!DOCTYPE html><html lang="es"><head><meta charset="utf-8">',
         "<title>Informe semanal - " + html.escape(cliente) + "</title>",
         "<style>" + CSS + "</style></head><body>"]

    p.append('<div class="cabecera">'
             "<h1>Oportunidades de licitacion</h1>"
             '<div class="sub">Informe semanal para ' + html.escape(cliente) + "<br>"
             "Semana del " + lunes.strftime("%d/%m/%Y") + " al " + hoy.strftime("%d/%m/%Y")
             + " &nbsp;&middot;&nbsp; generado el " + hoy.strftime("%d/%m/%Y")
             + "</div></div>")

    # ---- Resumen -------------------------------------------------------
    p.append("<h2>Resumen</h2>")
    n = len(ops) if ops else 0
    total_valor = sum(peso(o.get("presupuesto")) for o in ops) if ops else 0
    criticas = sum(1 for o in ops if int(o.get("score") or 0) >= 60) if ops else 0
    p.append('<div class="kpi">'
             '<div><span class="n">%d</span><span class="t">Oportunidades</span></div>'
             '<div><span class="n">%d</span><span class="t">Alta prioridad</span></div>'
             '<div><span class="n">%s</span><span class="t">Valor en juego</span></div>'
             "</div>" % (n, criticas, e(total_valor) if total_valor else "0"))
    if n == 0:
        p.append('<div class="caja">No se detectaron oportunidades que encajen con el '
                 "perfil esta semana. O no las hubo, o hay que ampliar el rango de "
                 "presupuesto o las zonas de operacion.</div>")

    if precision:
        t = '<div class="caja"><b>Precision del filtro:</b> '
        if precision["precision"] is not None:
            t += "%.0f%% (%d utiles de %d revisadas)" % (
                precision["precision"], precision["utiles"],
                precision["utiles"] + precision["descartadas"])
            if precision["utiles"] + precision["descartadas"] < 10:
                t += ". Poca muestra todavia."
        else:
            t += "aun sin medir. Revise y marque las oportunidades de semanas anteriores."
        t += "</div>"
        p.append(t)

    # ---- Analisis de pliego -------------------------------------------
    if pliego:
        v = pliego.get("veredicto", "")
        clase = "alerta" if v == "NO PRESENTAR" else ("ok" if v == "POSTULAR" else "")
        p.append("<h2>Analisis del pliego</h2>")
        p.append('<div class="caja %s"><b>Veredicto: %s</b><br>%s</div>'
                 % (clase, html.escape(v),
                    "El pliego analizado pide %d requisitos, de los cuales %d son criticos."
                    % (pliego.get("total_requisitos", 0), pliego.get("criticos", 0))))
        brechas = [d for d in pliego.get("detalle", []) if d["estado"] == "FALTA"]
        if brechas:
            p.append("<h3>Lo que falta</h3><table><tr><th>Requisito</th><th>Tipo</th><th>Critico</th></tr>")
            for b in brechas:
                p.append("<tr><td>%s</td><td>%s</td><td>%s</td></tr>"
                         % (html.escape(b["nombre"]), html.escape(b["tipo"]),
                            "si" if b["critico"] else "no"))
            p.append("</table>")

    # ---- Oportunidades --------------------------------------------------
    if ops:
        p.append("<h2>Detalle de oportunidades</h2>")
        p.append("<table><tr><th>#</th><th>Entidad</th><th>Que buscan</th><th>Presupuesto</th>"
                 "<th>Zona</th><th>Puntaje</th></tr>")
        for i, o in enumerate(ops[:15], 1):
            sc = int(o.get("score") or 0)
            clase = "alta" if sc >= 60 else ("media" if sc >= 50 else "baja")
            val = peso(o.get("presupuesto"))
            p.append('<tr class="%s"><td>%d</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%d</td></tr>'
                     % (clase, i, html.escape(corto(o.get("entidad"), 42)),
                        html.escape(corto(o.get("objeto"), 120)),
                        e(val) if val else "no publicado",
                        html.escape(corto(o.get("departamento"), 22)), sc))
        p.append("</table>")

    # ---- Que hacer -----------------------------------------------------
    if ops:
        p.append("<h2>Que hacer esta semana</h2>")
        top = ops[0]
        p.append('<div class="accion"><b>1. Abrir el primero y confirmar la fecha de cierre.</b><br>'
                 "%s - %s. Puntaje %s. Verifique en SECOP que siga abierto: "
                 "un proceso cerrado no sirve para nada."
                 % (html.escape(corto(top.get("entidad"), 60)),
                    html.escape(corto(top.get("objeto"), 90)),
                    top.get("score", "?")))
        if pliego and any(d["estado"] == "FALTA" for d in pliego.get("detalle", [])):
            crit = [d["nombre"] for d in pliego["detalle"]
                    if d["estado"] == "FALTA" and d["critico"]]
            p.append('<div class="accion"><b>2. Descartar lo que no cumple.</b><br>'
                     "Faltan requisitos criticos: %s. Si no se pueden cubrir, no se presenta, "
                     "porque se pierde la garantia de seriedad."
                     % html.escape("; ".join(crit)))
        n_alta = sum(1 for o in ops if int(o.get("score") or 0) >= 60)
        p.append('<div class="accion"><b>3. Decidir el filtro con datos.</b><br>'
                 "Esta semana salieron %d oportunidades, %d de alta prioridad. "
                 "Marque cada una como util o descartada para que el proximo informe "
                 "sea mas preciso: <code>python src/historico.py --marcar &lt;referencia&gt; --util</code>"
                 "</div>" % (len(ops), n_alta))

    p.append('<div class="pie">Datos: Plataforma Nacional de Contratacion publica (SECOP II), '
             "fuente abierta del Estado. Informacion de caracter publico, consultada el "
             + hoy.strftime("%d/%m/%Y") + ". Este informe prioriza oportunidades: no garantiza "
             "adjudicacion ni sustituye la revision tecnica del pliego.</div>")
    p.append("</body></html>")
    return "\n".join(p)


def a_pdf(html_txt, salida):
    nav = buscar_navegador()
    if not nav:
        return ("No se encontro Chrome ni Edge, asi que no se pudo generar el PDF.\n"
                "  El HTML quedo en informe-semanal.html, se puede abrir e imprimir como PDF.\n"
                "  Para instalarlo: winget install Google.Chrome")
    tmp = os.path.join(tempfile.gettempdir(), "informe_semanal.html")
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(html_txt)
    cmd = [nav, "--headless", "--disable-gpu", "--no-sandbox",
           "--no-pdf-header-footer", "--print-to-pdf=" + salida,
           "file:///" + tmp.replace("\\", "/")]
    try:
        subprocess.run(cmd, capture_output=True, timeout=180)
    except Exception as exc:
        return "Fallo al invocar el navegador: " + str(exc)
    return ("PDF generado: " + salida) if os.path.exists(salida) else \
        "El navegador no produjo el PDF. Queda el HTML para abrirlo a mano."


def main():
    ap = argparse.ArgumentParser(description="Genera el informe semanal en PDF.")
    ap.add_argument("--cliente", default="su empresa", help="Nombre del cliente")
    ap.add_argument("--html", action="store_true", help="Generar solo el HTML")
    args = ap.parse_args()

    ops = cargar_oportunidades()
    if ops is None:
        print("No existe oportunidades.csv. Corre primero:  python src/radar.py")
        return 1
    pliego = cargar_pliego()
    precision = cargar_precision()

    html_txt = construir_html(args.cliente, ops, pliego, precision)

    ruta_html = os.path.join(RAIZ, "informe-semanal.html")
    with open(ruta_html, "w", encoding="utf-8") as fh:
        fh.write(html_txt)
    print("HTML: " + ruta_html)

    if args.html:
        return 0

    ruta_pdf = os.path.join(RAIZ, "informe-semanal.pdf")
    msg = a_pdf(html_txt, ruta_pdf)
    print(msg)
    return 0 if os.path.exists(ruta_pdf) else 1


if __name__ == "__main__":
    raise SystemExit(main())