#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RADAR DE LICITACIONES - Colombia (SECOP II, datos abiertos de datos.gov.co)

Que hace:
  1. Descarga los procesos que estan ABIERTOS para recibir ofertas.
  2. Puntua cada uno contra el perfil de una empresa (sector, zona, presupuesto).
  3. Entrega los mejor<A>adaptados, con el link directo al proceso.
  4. Avisa cuantos_ofrecentes hay: si van 40, casi seguro no se gana.

Fuente publica, sin API key, sin scraping. Solo consultas estructuradas.
Dataset: p6dx-8zbt "SECOP II - Procesos de Contratacion"
"""

import csv
import json
import sys
import urllib.parse
import urllib.request
from datetime import datetime

ENDPOINT = "https://www.datos.gov.co/resource/p6dx-8zbt.json"

# ------------------------------------------------------------------ PERFIL
# Esto es lo unico que cambias por cliente. Es tu producto.
PERFIL = {
    "empresa": "Constructora Ejemplo S.A.S.",
    "palabras_clave": [
        "construccion", "contratacion de obra", "obra civil", "cimentacion",
        "concreto", "estructural", "edificacion", "vivienda", "vivienda nueva",
        "pavimento", "pavimentacion", "acueducto", "drenaje", "canalizacion",
        "consultoria de ingenieria", "intervencion", "rehabilitacion",
        "placa huella", "cerramiento", "demolicion",
    ],
    "excluir": [
        "dotacion", "alimento", "medicamento", "fotocopia", "papeleria",
        "capacitacion", "software", "licenciamiento", "servicio de limpieza",
        "seguridad fisica", "combustible",
    ],
    "departamentos": ["ANTIOQUIA", "CUNDINAMARCA", "DISTRITO CAPITAL", "ATLANTICO", "SANTANDER", "CALDAS"],
    "precio_min": 80_000_000,
    "precio_max": 8_000_000_000,
    "aviso_si_oferentes": 25,   # por encima de esto, la probabilidad baja mucho
}

TOP_N = 15
MUESTRA = 500

CAMPOS = ("id_del_proceso,referencia_del_proceso,entidad,departamento_entidad,"
          "ciudad_entidad,nombre_del_procedimiento,descripci_n_del_procedimiento,"
          "precio_base,modalidad_de_contratacion,codigo_principal_de_categoria,"
          "estado_de_apertura_del_proceso,proveedores_que_manifestaron,"
          "conteo_de_respuestas_a_ofertas,fecha_de_publicacion_del,urlproceso")


def pedir(where, limite):
    url = (ENDPOINT + "?$select=" + CAMPOS
           + "&$where=" + urllib.parse.quote(where, safe="=,'() ")
           + "&$limit=" + str(limite))
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode("utf-8"))


def link_de(fila):
    u = fila.get("urlproceso")
    if isinstance(u, dict):
        return u.get("url", "")
    return u or ""


def entero(valor, por_defecto=0):
    try:
        return int(str(valor).replace(",", "").strip())
    except (TypeError, ValueError):
        return por_defecto


def puntuar(f, p):
    """(score 0-100, razones). 0 = descartado."""
    texto = ((f.get("nombre_del_procedimiento") or "") + " " +
             (f.get("descripci_n_del_procedimiento") or "")).lower()
    if not texto.strip():
        return 0, ["sin descripcion"]

    if any(x in texto for x in p["excluir"]):
        return 0, []

    aciertos = [k for k in p["palabras_clave"] if k in texto]
    if not aciertos:
        return 0, []
    puntos = min(len(aciertos) / 2.0, 1.0) * 60
    razones = ["sector: " + ", ".join(aciertos[:3])]

    dep = (f.get("departamento_entidad") or "").upper()
    if any(d.upper() in dep for d in p["departamentos"]):
        puntos += 20
        razones.append("zona objetivo")
    else:
        puntos += 5

    precio = entero(f.get("precio_base"))
    if precio == 0:
        razones.append("presupuesto no publicado")
    elif p["precio_min"] <= precio <= p["precio_max"]:
        puntos += 20
        razones.append("presupuesto encaja")
    elif precio > p["precio_max"]:
        puntos -= 15
        razones.append("muy por encima del rango")

    oferentes = entero(f.get("conteo_de_respuestas_a_ofertas"))
    if oferentes > p["aviso_si_oferentes"]:
        puntos -= 20
        razones.append("MUCHA competencia: " + str(oferentes) + " oferentes")
    elif oferentes == 0:
        puntos += 10
        razones.append("sin oferentes aun: poca competencia")

    return max(0, min(100, int(puntos))), razones


def main():
    print("=" * 76)
    print("  RADAR DE LICITACIONES  -  " + PERFIL["empresa"])
    print("  " + datetime.now().strftime("%Y-%m-%d %H:%M"))
    print("=" * 76)

    print("\n[1/2] Descargando procesos ABIERTOS...")
    try:
        filas = pedir("estado_de_apertura_del_proceso='Abierto'", MUESTRA)
    except Exception as exc:
        print("  ERROR al consultar la API: " + str(exc))
        return 1
    print("  {0} procesos abiertos encontrados".format(len(filas)))

    print("[2/2] Analizando contra el perfil...")
    res = []
    for f in filas:
        s, r = puntuar(f, PERFIL)
        if s >= 40:
            f["_score"], f["_razones"] = s, r
            res.append(f)
    res.sort(key=lambda x: x["_score"], reverse=True)
    print("  {0} relevantes".format(len(res)))

    print("\n" + "=" * 76)
    print("  OPORTUNIDADES")
    print("=" * 76)
    if not res:
        print("\n  Nada coincidio. Ajusta PERFIL en radar.py y vuelve a correr.")
        return 0

    for i, f in enumerate(res[:TOP_N], 1):
        print("\n  {0}. [{1}/100]  {2}".format(i, f["_score"], f.get("referencia_del_proceso") or "?"))
        print("     Entidad    : " + (f.get("entidad") or "?")[:70])
        print("     Que buscan : " + (f.get("nombre_del_procedimiento") or "?")[:140])
        pre = entero(f.get("precio_base"))
        print("     Presupuesto: " + ("$ " + "{:,.0f}".format(pre).replace(",", ".")
                                     if pre else "no publicado"))
        print("     Zona       : " + (f.get("ciudad_entidad") or "?") + " / " + (f.get("departamento_entidad") or "?"))
        print("     Oferentes  : " + (f.get("conteo_de_respuestas_a_ofertas") or "0"))
        print("     Por que    : " + "; ".join(f["_razones"]))
        lk = link_de(f)
        if lk:
            print("     Link       : " + lk)

    salida = "oportunidades.csv"
    with open(salida, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(["score", "referencia", "entidad", "ciudad", "departamento",
                    "objeto", "presupuesto", "oferentes", "razones", "link"])
        for f in res:
            w.writerow([f["_score"], f.get("referencia_del_proceso"), f.get("entidad"),
                        f.get("ciudad_entidad"), f.get("departamento_entidad"),
                        f.get("nombre_del_procedimiento"), f.get("precio_base"),
                        f.get("conteo_de_respuestas_a_ofertas"),
                        "; ".join(f["_razones"]), link_de(f)])
    print("\n  Guardado: " + salida)
    print("")
    return 0


if __name__ == "__main__":
    sys.exit(main())
