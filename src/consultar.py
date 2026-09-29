#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CONSULTAS - Búsquedas puntuales en lenguaje natural.

El radar responde "qué hay esta semana". Esto responde lo otro: las preguntas
sueltas que hace alguien cuando esta trabajando un rato:

    "licitaciones de construcción entre 2020 y 2023"
    "las modernas"
    "antiguas en Antioquia"
    "de construcción con presupuesto mayor a 500 millones"
    "las de acueducto en Bogotá"

Por que NO usa un modelo de lenguaje: la version medida de gemma-4-26b-it via
proxy repite el prompt en vez de responder (probado el 29/09/2026), y
gemini-2.5-flash devuelve 404 para cuentas nuevas. Un LLM aqui no responderia,
solo repetiria la pregunta.

Y no hace falta: casi todo lo que se pide son FILTROS sobre campos concretos
(año, departamento, sector, presupuesto). Eso se resuelve con reglas, al
instante, gratis y sin depender de que un modelo obedezca.

Donde si aporta un modelo es en resumir un pliego en lenguaje llano, y eso lo
hace `requisitos.py`.

Uso:
    python src/consultar.py "licitaciones modernas de construcción"
    python src/consultar.py "antiguas" --departamento Antioquia
    python src/consultar.py "entre 2021 y 2023" --sector acueducto
    python src/consultar.py --interpreta            # muestra qué entendió
"""

import argparse
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime

if "sys" not in dir():
    import sys

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ENDPOINT = "https://www.datos.gov.co/resource/p6dx-8zbt.json"
CAMPOS = ("id_del_proceso,referencia_del_proceso,entidad,departamento_entidad,"
          "ciudad_entidad,nombre_del_procedimiento,descripci_n_del_procedimiento,"
          "precio_base,modalidad_de_contratacion,estado_de_apertura_del_proceso,"
          "fecha_de_publicacion_del,urlproceso")

# Un proceso con mas de esto se considera vigente. Medido: SECOP marca "Abierto"
# procesos de 2015, asi que "Abierto" NO significa que se pueda licitar.
DIAS_VIGENTE = 120

# Palabras que el usuario suele usar para decir un sector
SECTORES = {
    "construccion": ["construccion", "obra", "cimentacion", "concreto", "estructural"],
    "acueducto": ["acueducto", "alcantarillado", "drenaje", "canalizacion", "saneamiento"],
    "vivienda": ["vivienda", "edificacion", "vivienda nueva", "placa huella"],
    "pavimento": ["pavimento", "pavimentacion", "via", "carretera"],
    "consultoria": ["consultoria", "asesoria", "interventoria", "supervision"],
    "salud": ["salud", "hospital", "medico", "enfermeria", "medicamento"],
    "educacion": ["educacion", "escuela", "colegio", "docencia", "formacion"],
    "transporte": ["transporte", "vehiculo", "combustible", "placa"],
    "tecnologia": ["software", "licenciamiento", "computador", "sistema", "informacion"],
}

# Sinonimos que no aportan y solo ensucian la busqueda
RUIDO = {"de", "la", "el", "los", "las", "un", "una", "del", "y", "en", "para", "con",
         "que", "son", "hay", "por", "más", "mas", "sobre", "segun", "cuanto", "cuántos"}

Meses = {"este": 0, "pasado": -1, "anterior": -1}


# --------------------------------------------------------------------------
# GEOGRAFIA
# Adivinar el departamento con un regex es fragile: "de construccion" se
# tomaba como departamento, y "en Bogota con presupuesto mayor a" se comia media
# frase. La solucion es no adivinar: se traen los nombres reales del dataset
# y se busca cual aparece en la frase. 32 departamentos, ~400 ciudades.
# Se cachean porque traerlos cuesta una consulta.
# --------------------------------------------------------------------------
CACHE_GEO = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "geo_cache.json")


def cargar_geo(forzar=False):
    if not forzar and os.path.exists(CACHE_GEO):
        try:
            with open(CACHE_GEO, "r", encoding="utf-8") as fh:
                d = json.load(fh)
            if d.get("departamentos") and d.get("ciudades"):
                return d
        except (ValueError, OSError):
            pass
    url = (ENDPOINT + "?$select=departamento_entidad,ciudad_entidad&$where=" +
           urllib.parse.quote("estado_de_apertura_del_proceso='Abierto'", safe="=,'() ") +
           "&$limit=3000")
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=90) as r:
            filas = json.loads(r.read().decode("utf-8"))
    except Exception:
        return {"departamentos": [], "ciudades": []}
    deps, cius = set(), set()
    for f in filas:
        d = (f.get("departamento_entidad") or "").strip()
        c = (f.get("ciudad_entidad") or "").strip()
        if d and d.lower() != "no definido":
            deps.add(d)
        if c and c.lower() != "no definido":
            cius.add(c)
    datos = {"departamentos": sorted(deps), "ciudades": sorted(cius)}
    try:
        with open(CACHE_GEO, "w", encoding="utf-8") as fh:
            json.dump(datos, fh, ensure_ascii=False)
    except OSError:
        pass
    return datos


def buscar_geo(frase, geo):
    """Nombre mas largo que aparezca en la frase. Gana el mas especifico."""
    t = limpia(frase)
    salida = {}
    for clave, lista in (("ciudad", geo.get("ciudades", [])), ("departamento", geo.get("departamentos", []))):
        mejor = None
        for nombre in lista:
            n = limpia(nombre)
            if len(n) < 4:            # evita "cala", "amba"
                continue
            if n in t:
                if mejor is None or len(n) > len(mejor[1]):
                    mejor = (nombre, n)
        if mejor:
            salida[clave] = mejor[0]
    return salida


def limpia(t):
    for a, b in {"á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u", "ñ": "n"}.items():
        t = t.replace(a, b).lower()
    return re.sub(r"\s+", " ", t.strip())


def donde(hay):
    return "interpretado" if hay else ""


def interpretar(frase, geo):
    """Convierte una frase suelta en filtros. Sin modelo: solo reglas."""
    t = limpia(frase)
    f = {"anios": None, "sector": None, "departamento": None, "ciudad": None,
         "presupuesto_min": None, "vigentes": False, "todas": False,
         "usado": []}

    # --- años: "2020", "entre 2019 y 2022", "de 2021 a 2023" ---
    rango = re.search(r"entre\s+(\d{4})\s*(?:y|a|hasta)\s*(\d{4})", t)
    if rango:
        f["anios"] = (int(rango.group(1)), int(rango.group(2)))
        f["usado"].append("rango de anos %d-%d" % f["anios"])
    else:
        años = re.findall(r"\b(19|20)\d{2}\b", t)
        anios = [int(a) for a in re.findall(r"\b(?:19|20)\d{2}\b", t)]
        if len(anios) == 1:
            f["anios"] = (anios[0], anios[0])
            f["usado"].append("ano %d" % anios[0])
        elif len(anios) >= 2:
            f["anios"] = (min(anios), max(anios))
            f["usado"].append("anos %d-%d" % f["anios"])

    # --- modernas / antiguas / vigentes ---
    if re.search(r"\b(modernas?|recientes|nuevas?|actuales?|vigentes?)\b", t):
        f["vigentes"] = True
        f["usado"].append("solo procesos vigentes (publicados en los ultimos %d dias)" % DIAS_VIGENTE)
    if re.search(r"\b(antiguas?|viejas?|pasadas?|historicas?|anteriores?)\b", t):
        f["vigentes"] = False
        f["anios"] = f["anios"] or (1990, 2019)
        f["usado"].append("procesos antiguos (hasta 2019)")

    # --- sector ---
    for nombre, claves in SECTORES.items():
        if any(c in t for c in claves) or nombre in t:
            f["sector"] = nombre
            f["usado"].append("sector: " + nombre)
            break

    # --- geografia: contra los nombres reales, no con regex ---
    for clave, etiqueta in (("ciudad", "ciudad"), ("departamento", "departamento")):
        if f.get(clave):
            continue
        hallado = buscar_geo(t, geo).get(clave)
        if hallado:
            f[clave] = limpia(hallado)
            f["usado"].append(etiqueta + ": " + f[clave])

    # --- presupuesto ---
    monto = re.search(r"(?:mayor|mas de|superar|sobre|mas)\s*(?:a\s*)?\$?\s*([\d.,]+)\s*(millones|millon|m)?", t)
    if monto:
        try:
            valor = float(monto.group(1).replace(".", "").replace(",", ""))
            if monto.group(2):
                valor *= 1_000_000
            f["presupuesto_min"] = valor
            f["usado"].append("presupuesto minimo $ " + "{:,.0f}".format(valor).replace(",", "."))
        except ValueError:
            pass

    if re.search(r"\b(todas?|todo|complet[oa])\b", t):
        f["todas"] = True
        f["usado"].append("sin filtro de antiguedad: incluye todo")

    return f


def consulta(datos, f, limite=25):
    condiciones = ["estado_de_apertura_del_proceso='Abierto'"]
    if f["anios"]:
        a, b = f["anios"]
        condiciones.append("fecha_de_publicacion_del >= '%d-01-01T00:00:00'" % a)
        condiciones.append("fecha_de_publicacion_del <= '%d-12-31T00:00:00'" % b)
    if f["departamento"]:
        condiciones.append("upper(departamento_entidad) like '%" +
                           f["departamento"].upper() + "%'")
    if f.get("ciudad"):
        condiciones.append("upper(ciudad_entidad) like '%" + f["ciudad"].upper() + "%'")
    if f["sector"]:
        claves = SECTORES[f["sector"]]
        clau = " OR ".join("upper(nombre_del_procedimiento) like '%" + c.upper() + "%'"
                           for c in claves[:4])
        condiciones.append("(" + clau + ")")

    where = " AND ".join(condiciones)
    # El filtro de vigencia y el de presupuesto se aplican en Python: el dataset
    # no tiene indice util para ellos y traer 8 millones de filas no es opcion.
    url = (ENDPOINT + "?$select=" + CAMPOS + "&$where=" +
           urllib.parse.quote(where, safe="=,'()") + "&$limit=2000")
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        filas = json.loads(r.read().decode("utf-8"))

    hoy = datetime.now().date()

    def antiguedad(x):
        try:
            return (hoy - datetime.strptime(
                str(x.get("fecha_de_publicacion_del"))[:10], "%Y-%m-%d").date()).days
        except (ValueError, TypeError):
            return None

    if f["vigentes"]:
        filas = [x for x in filas if (antiguedad(x) or 99999) <= DIAS_VIGENTE]
    if f["presupuesto_min"]:
        def valor(x):
            try:
                return int(str(x.get("precio_base") or 0).replace(".", ""))
            except ValueError:
                return 0
        filas = [x for x in filas if valor(x) >= f["presupuesto_min"]]

    for x in filas:
        x["_dias"] = antiguedad(x)
    filas.sort(key=lambda x: (x["_dias"] is None, x["_dias"]))
    return filas[:limite]


def imprimir(filas, f):
    if not filas:
        print("\n  No hay resultados con esos filtros.")
        print("  Pruebe con menos restricciones, o revise si el anio esta bien.")
        return
    print("\n  " + str(len(filas)) + " resultado(s)")
    for i, x in enumerate(filas, 1):
        url = x.get("urlproceso")
        if isinstance(url, dict):
            url = url.get("url", "")
        d = x.get("_dias")
        aviso = "  [!] hace %d dias, verifique el plazo" % d if (d and d > DIAS_VIGENTE) else ""
        try:
            pres = int(str(x.get("precio_base") or 0).replace(".", ""))
            pres = "$ " + "{:,.0f}".format(pres).replace(",", ".")
        except ValueError:
            pres = "no publicado"
        print("\n  %d. %s" % (i, x.get("referencia_del_proceso") or "?"))
        print("     Entidad : %s" % (x.get("entidad") or "?")[:70])
        print("     Objeto  : %s" % (x.get("nombre_del_procedimiento") or "?")[:110])
        print("     Valor   : %s   Zona: %s" % (pres, x.get("ciudad_entidad") or "?"))
        print("     Published: hace %s dias%s" % (d if d is not None else "?", aviso))
        if url:
            print("     Link    : %s" % url)


def main():
    ap = argparse.ArgumentParser(description="Consultas puntuales sobre licitaciones.")
    ap.add_argument("pregunta", nargs="?", help="La consulta en palabras")
    ap.add_argument("--departamento")
    ap.add_argument("--sector", choices=list(SECTORES))
    ap.add_argument("--vigentes", action="store_true", help="Solo procesos recientes")
    ap.add_argument("--limite", type=int, default=25)
    ap.add_argument("--interpreta", action="store_true",
                    help="Mostrar como se interpretó la consulta y salir")
    args = ap.parse_args()

    if not args.pregunta:
        ap.error("Falta la consulta. Ejemplo: \"licitaciones modernas de construcción\"")
        return 1

    geo = cargar_geo()
    f = interpretar(args.pregunta, geo)
    if args.departamento:
        f["departamento"] = limpia(args.departamento)
        f["usado"].append("departamento (opcion): " + f["departamento"])
    if args.sector:
        f["sector"] = args.sector
        f["usado"].append("sector (opcion): " + args.sector)
    if args.vigentes:
        f["vigentes"] = True

    print("=" * 74)
    print("  CONSULTA: " + args.pregunta)
    print("=" * 74)
    print("\n  " + donde(True) + ":")
    for u in f["usado"]:
        print("    - " + u)
    if not f["usado"]:
        print("    - (sin filtros: devuelve los mas recientes)")

    if args.interpreta:
        return 0

    print("\n  Buscando...")
    try:
        filas = consulta(args.pregunta, f, args.limite)
    except Exception as exc:
        print("  Error consultando: " + str(exc))
        return 1
    imprimir(filas, f)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
