#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HISTORICO - Convierte el radar en algo que se puede medir.

Por que existe: un detector de oportunidades es fácil de construir y facil de
vender. Lo dificil es demostrar que acierta. Sin registro de que paso con cada
oportunidad entregada, la precision del filtro es una opinion.

Este modulo guarda cada corrida, deja que el cliente marque que hizo con cada
oportunidad, y calcula la precision real. De ahi sale la calibracion: que
palabras clave producen aciertos y cuales producen ruido.

La razon de ser del filtro UNSPSC se documento en docs/06-unspsc-no-sirve.md:
se descarto. Aqui esta el mecanismo que de verdad permite medirlo.

Uso:
    python src/historico.py --registrar            (lo llama radar.py al terminar)
    python src/historico.py --marcar <referencia> --util
    python src/historico.py --marcar <referencia> --descartado "fuera de zona"
    python src/historico.py --reporte
"""

import argparse
import json
import os
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARCHIVO = os.path.join(RAIZ, "historial.jsonl")


def _ahora():
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def normalizar(texto):
    mapa = {"á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u", "ü": "u", "ñ": "n"}
    for k, v in mapa.items():
        texto = texto.replace(k, v)
    return re.sub(r"\s+", " ", texto.lower())


def registrar(corridas, perfil_nombre="", criterios=None):
    """Agrega una corrida al historico. Una linea JSON por corrida.

    corridas: lista de dicts con al menos 'referencia' y 'score'.
    """
    reg = {
        "tipo": "corrida",
        "fecha": _ahora(),
        "perfil": perfil_nombre,
        "criterios": criterios or {},
        "total": len(corridas),
        "oportunidades": [
            {"referencia": c.get("referencia", ""),
             "entidad": c.get("entidad", ""),
             "objeto": (c.get("objeto") or "")[:200],
             "departamento": c.get("departamento", ""),
             "presupuesto": c.get("presupuesto", ""),
             "score": c.get("score", 0),
             "razones": c.get("razones", []),
             "estado": "pendiente"}
            for c in corridas
        ],
    }
    nueva = not os.path.exists(ARCHIVO)
    with open(ARCHIVO, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(reg, ensure_ascii=False) + "\n")
    return len(corridas), nueva


def marcar(referencia, estado, motivo=""):
    """El cliente dice que hizo con una oportunidad. Actualiza TODAS las corridas
    donde aparezca, porque una misma referencia puede repetirse entre semanas."""
    if not os.path.exists(ARCHIVO):
        print("No hay historial todavia.")
        return 0

    with open(ARCHIVO, "r", encoding="utf-8") as fh:
        lineas = [json.loads(l) for l in fh if l.strip()]

    objetivo = normalizar(referencia)
    tocados = 0
    for reg in lineas:
        for op in reg.get("oportunidades", []):
            if normalizar(op.get("referencia", "")) == objetivo:
                op["estado"] = estado
                op["motivo"] = motivo
                op["marcado"] = _ahora()
                tocados += 1

    if tocados:
        tmp = ARCHIVO + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            for reg in lineas:
                fh.write(json.dumps(reg, ensure_ascii=False) + "\n")
        os.replace(tmp, ARCHIVO)
    return tocados


def _agrupar_por_palabra(regs):
    """Que palabra clave aparece en cada oportunidad entregada."""
    mapa = defaultdict(lambda: {"util": 0, "descartado": 0, "pendiente": 0})
    for reg in regs:
        for op in reg.get("oportunidades", []):
            razones = " ".join(op.get("razones", []))
            for razon in op.get("razones", []):
                m = re.match(r"sector:\s*(.+)", razon)
                if not m:
                    continue
                for palabra in [p.strip() for p in m.group(1).split(",")]:
                    if palabra:
                        mapa[palabra][op.get("estado", "pendiente")] += 1
    return mapa


def reporte():
    if not os.path.exists(ARCHIVO):
        print("No hay historial todavia. Corre radar.py primero.")
        return 0
    with open(ARCHIVO, "r", encoding="utf-8") as fh:
        regs = [json.loads(l) for l in fh if l.strip()]

    total = sum(r["total"] for r in regs)
    estados = Counter()
    for r in regs:
        for op in r.get("oportunidades", []):
            estados[op.get("estado", "pendiente")] += 1

    print("=" * 74)
    print("  HISTORICO DEL RADAR")
    print("  " + datetime.now().strftime("%Y-%m-%d %H:%M"))
    print("=" * 74)
    print("\n  Corridas registradas : %d" % len(regs))
    print("  Oportunidades entregadas: %d" % total)
    print("  Marcadas por el cliente: %d" % (estados["util"] + estados["descartado"]))
    print("    utiles    : %d" % estados["util"])
    print("    descartadas: %d" % estados["descartado"])
    print("    pendientes : %d" % estados["pendiente"])

    judged = estados["util"] + estados["descartado"]
    if judged == 0:
        print("\n  Todavia no hay veredicto del cliente, asi que la precision")
        print("  no se puede calcular. Marca algunas con --marcar.")
        print("\n  Mientras tanto, la palabra clave mas productiva segun el historico:")
        mapa = _agrupar_por_palabra(regs)
        for palabra, c in sorted(mapa.items(), key=lambda kv: -kv[1]["pendiente"])[:8]:
            print("    %-28s entregadas %d" % (palabra, sum(c.values())))
        return 0

    precision = estados["util"] / judged * 100
    print("\n  PRECISION DEL FILTRO: %.0f%%  (%d utiles de %d marcadas)"
          % (precision, estados["util"], judged))
    if judged < 10:
        print("  Poca muestra: con menos de 10 veredictos la cifra no es confiable aun.")

    print("\n  RENDIMIENTO POR PALABRA CLAVE")
    print("  " + "-" * 70)
    print("  %-30s %6s %6s %6s %8s" % ("palabra", "util", "desc", "pend", "precision"))
    mapa = _agrupar_por_palabra(regs)
    filas = []
    for palabra, c in mapa.items():
        j = c["util"] + c["descartado"]
        prec = (c["util"] / j * 100) if j else None
        filas.append((prec if prec is not None else -1, palabra, c, j))
    filas.sort(key=lambda t: (-t[0], -t[3]))
    for prec, palabra, c, j in filas[:15]:
        txt = ("%.0f%%" % prec) if prec >= 0 else "sin dato"
        print("  %-30s %6d %6d %6d %8s" % (palabra[:30], c["util"], c["descartado"],
                                           c["pendiente"], txt))

    utiles = [palabra for _p, palabra, c, j in filas
              if j >= 3 and c["util"] > 0 and c["descartado"] == 0]
    ruido = [palabra for _p, palabra, c, j in filas
             if j >= 3 and c["util"] == 0 and c["descartado"] > 0]
    if utiles:
        print("\n Palabras que ACERTAN siempre (con 3+ casos):")
        for p in utiles:
            print("   - " + p)
    if ruido:
        print("\n  Palabras que solo generan RUIDO (con 3+ casos): quitarlas del PERFIL")
        for p in ruido:
            print("   - " + p)
    return 0


def main():
    ap = argparse.ArgumentParser(description="Registro y medicion del radar de licitaciones.")
    ap.add_argument("--registrar", action="store_true",
                    help="Registrar una corrida (lo invoca radar.py)")
    ap.add_argument("--entrada", help="JSON con las oportunidades de la corrida")
    ap.add_argument("--perfil", default="", help="Nombre del perfil cliente")
    ap.add_argument("--marcar", help="Referencia del proceso a marcar")
    ap.add_argument("--util", action="store_true", help="La oportunidad fue sirve")
    ap.add_argument("--descartado", help="La oportunidad no sirve, con el motivo")
    ap.add_argument("--reporte", action="store_true", help="Ver precision acumulada")
    args = ap.parse_args()

    if args.marcar:
        if args.util:
            n = marcar(args.marcar, "util")
        elif args.descartado is not None:
            n = marcar(args.marcar, "descartado", args.descartado)
        else:
            ap.error("Con --marcar hace falta --util o --descartado 'motivo'")
        print("Actualizadas %d apariciones de %s" % (n, args.marcar))
        return 0

    if args.registrar:
        if not args.entrada:
            ap.error("--registrar necesita --entrada con el JSON de la corrida")
        with open(args.entrada, "r", encoding="utf-8") as fh:
            datos = json.load(fh)
        corridas = datos if isinstance(datos, list) else datos.get("oportunidades", [])
        criterios = datos.get("criterios", {}) if isinstance(datos, dict) else {}
        n, nueva = registrar(corridas, args.perfil, criterios)
        print("Registradas %d oportunidades%s" % (n, " (archivo nuevo)" if nueva else ""))
        return 0

    if args.reporte or True:
        return reporte()


if __name__ == "__main__":
    raise SystemExit(main())
