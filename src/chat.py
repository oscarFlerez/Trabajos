#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VENTANA DE AGENTE - Chat con una IA externa gratuita.

Idea: el usuario hace preguntas en sus palabras y una IA gratuita las responde,
con el contexto de esta aplicacion ya inyectado. Todos los datos con los que
trabajamos son publicos, asi que no hay nada secreto que compartir.

Que se verifico el 29/09/2026 antes de elegir proveedor:
  - Puter.js        -> HTTP 200, 491 KB, trae chat. VIABLE, sin clave de API.
  - DuckDuckGo AI   -> la pagina carga pero NO entrega el token vqd a una
                       peticion que no sea de navegador. NO VIABLE.
  - api.puter.com   -> 404. No hay REST, solo SDK de navegador.
  - Gemini 2.5 Flash-> 404 para cuentas nuevas, y el modelo disponible por la
                       clave de este equipo repite el prompt en vez de obedecer.

Por eso el agente corre EN EL NAVEGADOR contra Puter, no contra una API propia.
Ventaja: la conversacion no pasa por ningun servidor nuestro y no queda escrita
en ningun lado salvo en la memoria de la pestana.

El contexto es la parte que hace util al agente. Esta en CONTEXTO, y se le puede
enseñar al usuario con el boton "ver que se le dijo" para que no sea una caja
negra.

Uso:
    python src/chat.py            -> sirve solo el chat, en el puerto 8775
    (normalmente se entra por el panel: boton "Agente")
"""

import os
import sys

if "sys" not in dir():
    import sys

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ---------------------------------------------------------------------------
# EL CONTEXTO
# Esto es lo que convierte un chatbot generico en un asistente que sabe de
# este tema. Se le inyecta en cada conversacion.
# ---------------------------------------------------------------------------
CONTEXTO = """Sos un asistente que ayuda a empresas del sector construccion en Colombia a
buscar y evaluar oportunidades de licitacion publica.

## Que datos maneja esta aplicacion

Los datos vienen de la Plataforma Nacional de Contratacion (SECOP II), publicados
como datos abiertos por el Estado en datos.gov.co. Son publicos y libres.

Dataset: "p6dx-8zbt" - SECOP II - Procesos de Contratacion.
Endpoint: https://www.datos.gov.co/resource/p6dx-8zbt.json
No requiere clave de API. Las consultas se hacen en formato SoQL.

## Campos utiles y que significa cada uno

- estado_de_apertura_del_proceso : "Abierto" o "Convocado". OJO, ver la trampa.
- nombre_del_procedimiento       : a veces trae el nombre de la persona que
                                   firmo, o un codigo interno. No es confiable.
- descripci_n_del_procedimiento  : el objeto real. Es el campo que hay que usar.
- precio_base                    : presupuesto estimado.
- departamento_entidad, ciudad_entidad : ubicacion de quien contrata.
- codigo_principal_de_categoria  : codigo UNSPSC. Ver la trampa.
- urlproceso                     : enlace al proceso en SECOP.

## TRAMPAS CONOCIDAS. No te las ignores.

1. "Abierto" NO significa que se pueda licitar. Es el estado interno del proceso.
   Medido: hay 8.086.821 procesos marcados "Abierto" y el 60,7% fueron publicados
   antes de 2025. El mas antiguo sigue "Abierto" desde 2015. Si le piden
   oportunidades, filtra por fecha de publicacion reciente.

2. El dataset NO tiene fecha de cierre. Nadie sabe desde los datos cuando se
   cierra un proceso. Si das por hecho que algo esta vigente,Estas dando
   informacion falsa. Decilo con claridad.

3. El campo de categoria UNSPSC no sirve para saber el sector. Medido: los
   procesos de obra civil se reparten en 156 codigos distintos y el mas comun
   cubre apenas el 14%. El codigo que mas se repite (30% del total) agrupa
   servicios administrativos de apoyo, no construccion. Para el sector hay que
   leer el texto.

4. "conteo_de_respuestas_a_ofertas" llega en 0 mientras el proceso esta
   abierto. No lo uses para decir quanta competencia hay. Solo se llena al
   cerrarse el proceso.

5. "departamento_entidad" y "ciudad_entidad" a veces traen el texto
   "No Definido". Es un valor centinela, no un dato.

6. El codigo de la categoria dice "UNSPECIFIED" en algunos registros.

## Como se busca bien

- Para el sector, buscar en el TEXTO del procedimiento, no en el codigo.
- Para saber si compite, cruzarlo con el valor adjudicado de procesos similares
  ya cerrados, en la misma region.
- Los procesos interadministrativos (interventoria, supervision) casi nunca
  tienen objeto ni detalle, y no son el canal principal.

## Que NO puede hacer esta herramienta

- No presenta la postulacion.
- No dice si va a ganar. Prioriza; la decision es del cliente.
- No reemplaza la lectura del pliego contractual.
- No tiene la fecha de cierre. Por eso SIEMPRE hay que verificar en SECOP.

Cuando no sepas algo, decilo. Es preferible decir "no tengo ese dato" que
inventar una cifra. Un dato inventado en una licitacion cuesta dinero de verdad.

## Como respondes

- En espanol de Colombia, tono profesional y directo.
- Sin relleno. Sin "por supuesto" ni "con gusto". Al grano.
- Con cifras concretas cuando las tengas, y la fuente de donde salen.
- Si la pregunta no se puede responder con datos publicos, dilo y explica que
  haria falta.
"""

MODELO_POR_DEFECTO = "gpt-4o-mini"   # Puter lo resuelve sin clave

CSS_CHAT = """
* { box-sizing: border-box; }
body { margin: 0; font-family: "Segoe UI", system-ui, Arial, sans-serif;
       background: #eef2f4; height: 100vh; display: flex; flex-direction: column; }
.cab { background: #0b3d5c; color: #fff; padding: 13px 22px; display: flex;
       align-items: center; gap: 14px; }
.cab h1 { margin: 0; font-size: 17px; font-weight: 600; }
.cab a { color: #b9d4e4; font-size: 13px; text-decoration: none; }
.cab a:hover { color: #fff; }
.cab .der { margin-left: auto; display: flex; align-items: center; gap: 14px; }
.pill { font-size: 11.5px; background: rgba(255,255,255,.16); border: 1px solid rgba(255,255,255,.3);
        padding: 4px 10px; border-radius: 11px; }
.contexto { max-width: 940px; margin: 14px auto 0; width: calc(100% - 40px); }
.contexto details { background: #fff; border: 1px solid #d5dfe5; border-radius: 7px; }
.contexto summary { padding: 11px 15px; cursor: pointer; color: #0b3d5c; font-size: 13.5px; font-weight: 600; }
.contexto pre { margin: 0; padding: 0 15px 15px; font-size: 12px; line-height: 1.6;
                white-space: pre-wrap; color: #475569; max-height: 330px; overflow: auto; }
.hilo { flex: 1; overflow-y: auto; padding: 20px; max-width: 940px; width: 100%; margin: 0 auto; }
.msg { max-width: 84%; padding: 12px 15px; border-radius: 9px; margin-bottom: 13px;
       line-height: 1.6; white-space: pre-wrap; font-size: 14.5px; }
.msg.yo { background: #0b3d5c; color: #fff; margin-left: auto; }
.msg.ia { background: #fff; border: 1px solid #dbe3e8; }
.msg.aviso { background: #fff8e6; border: 1px solid #e8c877; font-size: 13.5px; }
.escribiendo { color: #94a3b8; font-style: italic; }
.pie { background: #fff; border-top: 1px solid #d5dfe5; padding: 13px 20px; }
.forma { max-width: 940px; margin: 0 auto; display: flex; gap: 10px; }
textarea { flex: 1; border: 1px solid #cbd5e1; border-radius: 7px; padding: 11px 13px;
           font-family: inherit; font-size: 14.5px; resize: none; height: 52px;
           font-family: "Segoe UI", sans-serif; }
textarea:focus { outline: 2px solid #0b3d5c; outline-offset: -1px; }
button { background: #0b3d5c; color: #fff; border: none; border-radius: 7px;
         padding: 0 22px; font-size: 14.5px; cursor: pointer; font-weight: 600; }
button:hover { background: #14506f; }
button:disabled { background: #94a3b8; cursor: not-allowed; }
.opc { max-width: 940px; margin: 0 auto 10px; display: flex; gap: 15px;
       font-size: 12.5px; color: #64748b; align-items: center; }
.ejemplos { max-width: 940px; margin: 0 auto; display: flex; flex-wrap: wrap; gap: 8px; padding: 0 20px; }
.ej { background: #fff; border: 1px solid #cbd5e1; border-radius: 15px; padding: 6px 13px;
      font-size: 12.5px; cursor: pointer; color: #334155; }
.ej:hover { border-color: #0b3d5c; color: #0b3d5c; }
"""


def pagina_chat():
    import html
    return """<!DOCTYPE html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Agente - Consultas sobre licitaciones</title>
<style>__CSS__</style></head><body>

<div class="cab">
  <h1>Agente</h1>
  <a href="/">&larr; Volver a las oportunidades</a>
  <div class="der">
    <span class="pill">IA gratuita &middot; sin clave de API</span>
    <span class="pill" id="estadoIncog">Incongnito: activo</span>
  </div>
</div>

<details class="contexto">
  <summary>Que se le dice al agente (contexto completo)</summary>
  <pre>__CONTEXTO__</pre>
</details>

<div class="opc">
  <label><input type="checkbox" id="incog" checked> Modo incognito: no guardar esta conversacion</label>
  <label style="margin-left:auto">Modelo: <select id="modelo">
    <option value="gpt-4o-mini">gpt-4o-mini</option>
    <option value="gpt-4o">gpt-4o</option>
    <option value="claude-sonnet-4">claude-sonnet-4</option>
    <option value="deepseek-chat">deepseek-chat</option>
    <option value="gemini-2.5-flash">gemini-2.5-flash</option>
  </select></label>
</div>

<div class="hilo" id="hilo"></div>

<div class="ejemplos" id="ejemplos">
  <div class="ej">Cuales son las trampas de estos datos?</div>
  <div class="ej">Como puedo filtrar oportunidades de construccion en Antioquia?</div>
  <div class="ej">Que campos del dataset sirven y cuales no?</div>
  <div class="ej">Por que no hay fecha de cierre y como lo compenso?</div>
</div>

<div class="pie">
  <div class="forma">
    <textarea id="entrada" placeholder="Escribi tu consulta sobre licitaciones..."></textarea>
    <button id="enviar">Enviar</button>
  </div>
</div>

<script src="https://js.puter.com/v2/"></script>
<script>
const CONTEXTO = __CONTEXTO_JSON__;
const hilo = document.getElementById("hilo");
const entrada = document.getElementById("entrada");
const boton = document.getElementById("enviar");
let historial = [];              // vive solo en la memoria de esta pestana
let cargando = false;

function burbuja(texto, clase) {
  const d = document.createElement("div");
  d.className = "msg " + clase;
  d.textContent = texto;
  hilo.appendChild(d);
  hilo.scrollTop = hilo.scrollHeight;
  return d;
}

document.getElementById("ejemplos").addEventListener("click", (e) => {
  if (e.target.classList.contains("ej")) {
    entrada.value = e.target.textContent;
    entrada.focus();
  }
});

entrada.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); mandar(); }
});
boton.addEventListener("click", mandar);

async function mandar() {
  if (cargando) return;
  const texto = entrada.value.trim();
  if (!texto) return;
  entrada.value = "";
  burbuja(texto, "yo");

  if (typeof puter === "undefined") {
    burbuja("No se pudo cargar el servicio de IA (Puter.js). Revisa tu conexion a internet: "
          + "el script se baja de un servidor externo.", "aviso");
    return;
  }

  const destino = burbuja("Escribiendo...", "ia");
  destino.innerHTML = '<span class="escribiendo">consultando...</span>';
  cargando = true;
  boton.disabled = true;

  // El contexto va en el primer mensaje, una sola vez por conversacion.
  const mensajes = [];
  if (historial.length === 0) {
    mensajes.push({ role: "system", content: CONTEXTO });
  }
  for (const m of historial) mensajes.push({ role: m.role, content: m.content });
  mensajes.push({ role: "user", content: texto });

  try {
    let salida = "";
    const modelo = document.getElementById("modelo").value;
    const resp = await puter.ai.chat(mensajes, { model: modelo, stream: false });
    salida = resp.message.content || resp.toString();
    destino.textContent = salida;
    historial.push({ role: "user", content: texto });
    historial.push({ role: "assistant", content: salida });
  } catch (err) {
    destino.className = "msg aviso";
    destino.textContent = "La IA no respondio: " + (err && err.message ? err.message : err)
      + "\\n\\nPuede ser que falte iniciar sesion en Puter, o que el modelo no este "
      + "disponible. Proba con otro modelo del desplegable.";
  } finally {
    cargando = false;
    boton.disabled = false;
    entrada.focus();
  }
}

// Aviso honesto sobre privacidad, en vez de prometer "anonimo" sin matices.
const av = document.createElement("div");
av.className = "msg aviso";
av.style.maxWidth = "940px";
av.style.margin = "0 auto 14px";
av.textContent = "Modo incognito: la conversacion NO se guarda en esta aplicacion ni en "
  + "ningun archivo, y se pierde al cerrar la pestana. Aun asi, la pregunta viaja por "
  + "internet al servicio de Puter: si le escribes el nombre de su empresa, ese dato "
  + "sale de su equipo.";
hilo.appendChild(av);
</script>
</body></html>"""


def html_chat():
    import json
    cuerpo = pagina_chat()
    cuerpo = cuerpo.replace("__CSS__", CSS_CHAT)
    cuerpo = cuerpo.replace("__CONTEXTO_JSON__", json.dumps(CONTEXTO))
    # el <pre> sin json
    import html as h
    cuerpo = cuerpo.replace("__CONTEXTO__", h.escape(CONTEXTO))
    return cuerpo


def main():
    import argparse
    from http.server import BaseHTTPRequestHandler, HTTPServer

    ap = argparse.ArgumentParser(description="Ventana de agente con IA gratuita.")
    ap.add_argument("--puerto", type=int, default=8775)
    ap.add_argument("--sin-navegador", action="store_true")
    args = ap.parse_args()

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_GET(self):
            datos = html_chat().encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(datos)))
            self.end_headers()
            self.wfile.write(datos)

    srv = HTTPServer(("127.0.0.1", args.puerto), H)
    url = "http://127.0.0.1:%d/" % args.puerto
    print("=" * 62)
    print("  VENTANA DE AGENTE")
    print("  " + url)
    print("  " + "-" * 62)
    print("  IA gratuita via Puter, sin clave de API.")
    print("  Modo incognito por defecto: nada se guarda en disco.")
    print("=" * 62)
    import threading
    import webbrowser
    if not args.sin_navegador:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nCerrado.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
