#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PANEL LOCAL - La aplicacion que ve el cliente.

Los scripts de terminal son para quien la construye. El area comercial de una
constructora no va a instalar un entorno virtual. Este panel hace lo mismo en el
navegador: mirar las oportunidades, entender que significan, y decir si sirvio.

Es un servidor local. No se publica en internet y no sale de este equipo.

Uso:
    python src/panel.py
    python src/panel.py --puerto 8765
    python src/panel.py --sin-navegador
"""

import argparse
import csv
import json
import os
import sys
import threading
import webbrowser
from datetime import date
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, quote, urlparse

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "src"))

import historico  # noqa: E402

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

PUERTO = 8765


def opportunities():
    ruta = os.path.join(RAIZ, "oportunidades.csv")
    if not os.path.exists(ruta):
        return None
    with open(ruta, "r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def estado_de(refs):
    """Devuelve {referencia: estado} con lo que ya se ha marcado."""
    ruta = os.path.join(RAIZ, "historial.jsonl")
    salida = {}
    if not os.path.exists(ruta):
        return salida
    with open(ruta, "r", encoding="utf-8") as fh:
        for linea in fh:
            if not linea.strip():
                continue
            for op in json.loads(linea).get("oportunidades", []):
                salida[op.get("referencia", "")] = op.get("estado", "pendiente")
    return salida


def precision():
    ruta = os.path.join(RAIZ, "historial.jsonl")
    if not os.path.exists(ruta):
        return None
    u = d = p = 0
    with open(ruta, "r", encoding="utf-8") as fh:
        for linea in fh:
            if not linea.strip():
                continue
            for op in json.loads(linea).get("oportunidades", []):
                e = op.get("estado", "pendiente")
                if e == "util":
                    u += 1
                elif e == "descartado":
                    d += 1
                else:
                    p += 1
    total = u + d
    return {"utiles": u, "descartadas": d, "pendientes": p,
            "precision": (u / total * 100) if total else None,
            "muestra": total}


def esc(t):
    return (str(t or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def pesos(v):
    try:
        return int(str(v or "0").replace(".", "").replace(",", ""))
    except ValueError:
        return 0


CSS = """
* { box-sizing: border-box; }
body { margin: 0; font-family: "Segoe UI", system-ui, Arial, sans-serif;
       background: #f1f4f6; color: #1a1a1a; }
.barra { background: #0b3d5c; color: #fff; padding: 15px 26px; }
.barra h1 { margin: 0; font-size: 19px; font-weight: 600; }
.barra p { margin: 3px 0 0; font-size: 12.5px; opacity: .85; }
.envoltura { max-width: 1180px; margin: 22px auto 60px; padding: 0 20px; }
.tarjetas { display: flex; gap: 13px; margin-bottom: 20px; flex-wrap: wrap; }
.tarjeta { flex: 1; min-width: 165px; background: #fff; border: 1px solid #dbe3e8;
           border-radius: 7px; padding: 15px 17px; }
.tarjeta .n { font-size: 27px; font-weight: 600; color: #0b3d5c; }
.tarjeta .t { font-size: 11.5px; color: #64748b; text-transform: uppercase; letter-spacing: .5px; }
h2 { font-size: 15px; color: #0b3d5c; margin: 26px 0 9px; }
details.explica { background: #fff; border: 1px solid #dbe3e8; border-radius: 7px;
                  margin-bottom: 20px; }
details.explica summary { padding: 13px 17px; cursor: pointer; font-weight: 600;
                          color: #0b3d5c; font-size: 14px; list-style: none; }
details.explica summary::-webkit-details-marker { display: none; }
details.explica summary:before { content: "\\25B8  "; color: #94a3b8; }
details.explica[open] summary:before { content: "\\25BE  "; }
.explica .cuerpo { padding: 0 17px 16px; font-size: 13.5px; line-height: 1.65; color: #334; }
.explica .cuerpo li { margin-bottom: 7px; }
table { width: 100%; border-collapse: collapse; background: #fff; font-size: 13px;
        border: 1px solid #dbe3e8; border-radius: 7px; overflow: hidden; }
th { background: #eef3f6; color: #0b3d5c; text-align: left; padding: 10px 12px; font-size: 12px;
     text-transform: uppercase; letter-spacing: .4px; }
td { padding: 11px 12px; border-top: 1px solid #e8edf1; vertical-align: top; }
tr.alta td:first-child { box-shadow: inset 3px 0 0 #1a7f37; }
tr.media td:first-child { box-shadow: inset 3px 0 0 #bf8700; }
tr.baja td:first-child { box-shadow: inset 3px 0 0 #94a3b8; }
.score { font-weight: 600; font-size: 15px; }
.objeto { color: #475569; font-size: 12.5px; margin-top: 3px; }
.btn { display: inline-block; border: 1px solid #cbd5e1; background: #fff; color: #334155;
       padding: 5px 11px; border-radius: 5px; font-size: 12px; cursor: pointer; margin: 2px 3px 2px 0;
       text-decoration: none; }
.btn.si { border-color: #1a7f37; color: #1a7f37; font-weight: 600; background: #f2f9f4; }
.btn.no { border-color: #a40e26; color: #a40e26; font-weight: 600; background: #fdf5f6; }
.btn:hover { filter: brightness(.96); }
.marca { font-size: 11.5px; color: #64748b; margin-top: 5px; }
.vacio { background: #fff; border: 1px dashed #cbd5e1; border-radius: 7px; padding: 30px;
         text-align: center; color: #64748b; }
.pie { margin-top: 30px; font-size: 12px; color: #94a3b8; line-height: 1.6; }
a.enlace { color: #0b3d5c; }
.agente { float: right; display: inline-block; background: rgba(255,255,255,.14);
  color: #fff; border: 1px solid rgba(255,255,255,.4); padding: 6px 13px; border-radius: 5px;
  font-size: 12.5px; text-decoration: none; margin-right: 8px; }
.agente:hover { background: rgba(255,255,255,.26); }

.descarga { float: right; display: inline-block; background: rgba(255,255,255,.14);
  color: #fff; border: 1px solid rgba(255,255,255,.4); padding: 6px 13px; border-radius: 5px;
  font-size: 12.5px; text-decoration: none; }
.descarga:hover { background: rgba(255,255,255,.26); }
.contador { float: right; margin-right: 10px; color: rgba(255,255,255,.85); font-size: 12.5px;
  padding: 7px 0; }

"""


def pagina(ops, prec, marcados, error):
    hoy = date.today()
    h = ['<!DOCTYPE html><html lang="es"><head><meta charset="utf-8">',
         '<meta name="viewport" content="width=device-width, initial-scale=1">',
         "<title>Oportunidades de licitacion</title><style>" + CSS + "</style></head><body>"]

    pend = sum(1 for v in marcados.values() if v == "pendiente") if marcados else 0
    hay_pdf = os.path.exists(os.path.join(RAIZ, "informe-semanal.pdf"))
    h.append('<div class="barra">')
    h.append('<a class="agente" href="/chat">Agente (IA gratis)</a>')
    if hay_pdf:
        h.append('<a class="descarga" href="/informe.pdf">Descargar informe (PDF)</a>')
    if marcados:
        h.append('<span class="contador">%d sin revisar</span>' % pend)
    h.append('<h1>Oportunidades de licitacion publica</h1>'
             "<p>Informacion de la Plataforma Nacional de Contratacion (SECOP II) &middot; "
             "consultada el " + hoy.strftime("%d/%m/%Y") + "</p></div>")

    h.append('<div class="envoltura">')

    if error:
        h.append('<div class="explica" style="border-left:4px solid #a40e26">'
                 "<b>No se pudo completar:</b> " + esc(error) + "</div>")

    # ---- Explicacion: lo que el cliente necesita saber para usarlo ----
    h.append('<details class="explica"><summary>Como funciona esta aplicacion</summary>'
             '<div class="cuerpo">'
             "<p>Esta pantalla revisa todos los procesos de licitacion publica que estan "
             "<b>abiertos</b> y le muestra solo los que podrian servirle. No es un buscador: "
             "los procesos que no encajan ya fueron descartados.</p>"
             "<ul>"
             "<li><b>El numero grande es la prioridad.</b> Va de 0 a 100. Un 60 o mas "
             "significa que encaja bien en su sector, su zona y su rango de presupuesto. "
             "Un 45 o menos es una coincidencia debil.</li>"
             "<li><b>La entidad</b> es quien contrata: el municipio, el hospital, el "
             "departamento. Si no es una entidad a la que usted suele licitar, "
             "probablemente no sea para usted.</li>"
             "<li><b>Por que aparece aqui</b> es el motivo del puntaje. Si ve "
             "<i>presupuesto encaja</i> o <i>zona objetivo</i>, esa es la razon.</li>"
             "<li><b>Sirvio o no sirvio.</b> Al final de cada fila hay dos botones. "
             "Marcalos segun haya revisado la oportunidad. Eso es lo unico que la "
             "aplicacion necesita de usted, y es lo que hace que la proxima semana "
             "las oportunidades sean mas precisas.</li>"
             "</ul>"
             "<p><b>Lo que esta aplicacion NO hace:</b> no presenta su postulacion, no "
             "calcula si va a ganar, y no reemplaza la lectura del pliego. Le ahorra "
             "tiempo de busqueda. La decision sigue siendo suya.</p>"
             "</div></details>")

    # ---- Indicadores ----
    n = len(ops) if ops else 0
    valor = sum(pesos(o.get("presupuesto")) for o in ops) if ops else 0
    alta = sum(1 for o in ops if int(o.get("score") or 0) >= 60) if ops else 0
    pc = prec["precision"] if prec and prec["precision"] is not None else None
    pc_txt = ("%.0f%%" % pc) if pc is not None else "sin medir"
    if prec and prec["muestra"] < 10 and pc is not None:
        pc_txt += " *"

    h.append('<div class="tarjetas">'
             '<div class="tarjeta"><div class="n">%d</div><div class="t">Oportunidades</div></div>'
             '<div class="tarjeta"><div class="n">%d</div><div class="t">Alta prioridad</div></div>'
             '<div class="tarjeta"><div class="n">%s</div><div class="t">Valor en juego</div></div>'
             '<div class="tarjeta"><div class="n">%s</div><div class="t">Precision del filtro</div></div>'
             "</div>"
             % (n, alta, ("$ {:,}".format(valor).replace(",", ".")) if valor else "0", pc_txt))

    if prec and prec["muestra"] < 10:
        h.append('<p class="marca">* Todavia se han marcado pocas oportunidades. '
                 "La precision es orientativa hasta llegar a 10.</p>")

    # ---- Tabla ----
    h.append("<h2>Detalle</h2>")
    if not ops:
        h.append('<div class="vacio">Esta semana no salio ninguna oportunidad que encaje con '
                 "el perfil configurado.<br>Puede ser que no las haya, o que convenga ampliar "
                 "las zonas o el rango de presupuesto.</div>")
    else:
        h.append("<table><tr><th style='width:52px'>Prior.</th><th>Entidad y objeto</th>"
                 "<th style='width:96px'>Presupuesto</th><th style='width:110px'>Zona</th>"
                 "<th style='width:190px'>Sirvio?</th></tr>")
        for o in ops:
            try:
                sc = int(o.get("score") or 0)
            except ValueError:
                sc = 0
            clase = "alta" if sc >= 60 else ("media" if sc >= 50 else "baja")
            ref = o.get("referencia", "")
            # La referencia puede traer espacios ("IE. BTAJ 008 - 2024"); sin
            # codificar rompe el query string y el clic nunca llega al servidor.
            refq = quote(ref, safe="")
            v = pesos(o.get("presupuesto"))
            ya = marcados.get(ref, "pendiente")
            botones = ""
            if ya == "util":
                botones = ('<span class="btn si">&#10003; Sirvio</span>'
                           '<a class="btn" href="/marcar?ref=%s&estado=descartado&motivo=corregido">Corregir</a>'
                           % refq)
            elif ya == "descartado":
                botones = ('<span class="btn no">&#10007; No sirvio</span>'
                           '<a class="btn" href="/marcar?ref=%s&estado=util&motivo=corregido">Corregir</a>'
                           % refq)
            else:
                botones = ('<a class="btn si" href="/marcar?ref=%s&estado=util">Sirvio</a>'
                           '<a class="btn no" href="/marcar?ref=%s&estado=descartado">No sirvio</a>'
                           % (refq, refq))
            razones = esc(o.get("razones")) or "sin detalle"
            h.append('<tr class="%s"><td><span class="score">%d</span></td>'
                     "<td><b>%s</b><div class='objeto'>%s</div>"
                     "<div class='objeto'><i>Por que: %s</i></div></td>"
                     "<td>%s</td><td>%s</td><td>%s</td></tr>"
                     % (clase, sc, esc(o.get("entidad")), esc(o.get("objeto")), razones,
                        ("$ {:,}".format(v).replace(",", ".")) if v else "no publicado",
                        esc(o.get("departamento")), botones))
        h.append("</table>")

    h.append('<p class="pie">Datos publicos de la Plataforma Nacional de Contratacion (SECOP II). '
             "Esta aplicacion prioriza oportunidades: <b>no garantiza adjudicacion</b> y no "
             "sustituye la revision tecnica del pliego ni la presentacion de la propuesta.<br>"
             "Panel local, servido solo desde este equipo.</p>")
    h.append("</div></body></html>")
    return "\n".join(h)


class Manejador(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass  # silencio: no ensuciar la consola

    def _enviar(self, texto, codigo=200):
        datos = texto.encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(datos)))
        self.end_headers()
        self.wfile.write(datos)

    def do_GET(self):
        u = urlparse(self.path)
        if u.path == "/marcar":
            q = parse_qs(u.query)
            ref = (q.get("ref") or [""])[0]
            estado = (q.get("estado") or [""])[0]
            motivo = (q.get("motivo") or [""])[0]
            if ref and estado in ("util", "descartado"):
                historico.marcar(ref, estado, motivo)
            self.send_response(303)
            self.send_header("Location", "/")
            self.end_headers()
            return
        if u.path == "/chat":
            import chat
            datos = chat.html_chat().encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(datos)))
            self.end_headers()
            self.wfile.write(datos)
            return
        if u.path == "/informe.pdf":
            ruta = os.path.join(RAIZ, "informe-semanal.pdf")
            if os.path.exists(ruta):
                with open(ruta, "rb") as fh:
                    datos = fh.read()
                self.send_response(200)
                self.send_header("Content-Type", "application/pdf")
                self.send_header("Content-Length", str(len(datos)))
                self.end_headers()
                self.wfile.write(datos)
            else:
                self._enviar("<h1>Aun no hay informe generado</h1>", 404)
            return
        ops = opportunities()
        self._enviar(pagina(ops, precision(), estado_de([o.get("referencia", "") for o in ops] if ops else []),
                             None if ops else
                             "No existe el archivo oportunidades.csv. Corra primero: python src/radar.py"))


def main():
    ap = argparse.ArgumentParser(description="Panel local de oportunidades de licitacion.")
    ap.add_argument("--puerto", type=int, default=PUERTO)
    ap.add_argument("--sin-navegador", action="store_true")
    args = ap.parse_args()

    ops = opportunities()
    if ops is None:
        print("Aun no hay datos. Corra primero:  python src/radar.py")
        print("Luego vuelva a correr:          python src/panel.py")
        return 1

    srv = HTTPServer(("127.0.0.1", args.puerto), Manejador)
    url = "http://127.0.0.1:%d/" % args.puerto
    print("=" * 62)
    print("  PANEL DE OPORTUNIDADES")
    print("  " + url)
    print("  " + "-" * 62)
    print("  Ctrl+C para cerrar.")
    print("  Solo escucha en este equipo (127.0.0.1), no se publica.")
    print("=" * 62)

    if not args.sin_navegador:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nCerrado.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())