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
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime

AMARILLO, ROJO, VERDE, FIN = "\033[33m", "\033[31m", "\033[32m", "\033[0m"

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


# --------------------------------------------------------------------------
# LIMPIEZA DEL OBJETO
# `nombre_del_procedimiento` a veces no es el objeto: trae el nombre de la
# persona que firmo, o un codigo interno, o un texto vacio de sentido.
# Ejemplos medidos en datos.gov.co:
#     "OSCAR JOSE CORTES RIVERO"   (persona)
#     "31117 copia"                (codigo interno)
#     "021-2023"                   (solo el numero)
#     "PRESTACION DE SERVICIOS"    (correcto pero no dice nada)
# Cuando pasa eso se usa `descripci_n_del_procedimiento`, que si trae el objeto.
# --------------------------------------------------------------------------

# Si aparece alguna de estas, el nombre NO es el de una persona.
NO_ES_PERSONA = (
    "CONTRATO", "CONTRATACION", "PRESTACION", "PRESTA", "SERVICIO", "SERVICIOS",
    "SUMINISTRO", "COMPRA", "VENTA", "OBRA", "CONSTRUCCION", "MANTENIMIENTO",
    "INTERADMINISTRATIVO", "DIRECTO", "DIRECTA", "PROFESIONAL", "PROFESIONALES",
    "APOYO", "GESTION", "SUMINISTRO DE", "DOTACION", "ALQUILER", "TRANSPORTE",
    "CONSULTORIA", "INTERVENCION", "REHABILITACION", "MEJORAMIENTO", "AMPLIACION",
    "COSTRUCCION", "ADQUISICION", "EVALUACION", "IMPLEMENTACION", "CAPACITACION",
    "ARRENDAMIENTO", "REPARACION", "INSTALACION", "DISEÑO", "DISENO",
)

# Textos correctos pero que no sirven para decidir nada.
GENERICOS = (
    "PRESTACION DE SERVICIOS", "CONTRATO DE PRESTACION DE SERVICIOS",
    "PRESTACION DE SERVICIOS PROFESIONALES", "CONTRATACION DIRECTA",
    "CONTRATO INTERADMINISTRATIVO", "SERVICIOS", "PRESTACION", "CONTRATO",
    "SUMINISTRO", "COMPRA", "SERVICIOS PROFESIONALES",
)


def objeto_limpio(f):
    """Devuelve (texto, nota). El texto es el objeto tal como se debe mostrar."""
    nom = (f.get("nombre_del_procedimiento") or "").strip()
    desc = (f.get("descripci_n_del_procedimiento") or "").strip()

    if not nom:
        return (desc or "(sin objeto)"), "no venia nombre, se uso la descripcion"

    # Solo numeros, guiones o la palabra "copia": es un codigo interno.
    sin_numeros = nom.replace("COPIA", "").replace("copia", "").strip()
    if sin_numeros and all(c in "0123456789- /." for c in sin_numeros):
        if desc:
            return desc, "el nombre era un codigo, se uso la descripcion"
        return nom, "el nombre es un codigo y no hay descripcion"

    # 2 a 6 palabras, casi todas en mayuscula, sin palabras institucionales
    # ni verbos: es un nombre de persona.
    tokens = [t for t in nom.split() if t]
    if 2 <= len(tokens) <= 6:
        mayusculas = sum(1 for t in tokens if t.isupper() and len(t) > 2)
        tiene_verbos = any(k in nom.upper() for k in NO_ES_PERSONA)
        if not tiene_verbos and mayusculas >= max(2, len(tokens) - 1):
            if desc:
                return desc, "el nombre traia una persona, se uso la descripcion"
            return nom, "el nombre parece una persona y no hay descripcion"

    # Correcto pero inutil: mejor la descripcion si es mas extensa.
    if nom.upper().rstrip(" .") in [g.rstrip(" .") for g in GENERICOS] and desc:
        return desc, "el nombre era generico, se uso la descripcion"

    return nom, ""

# --------------------------------------------------------------------------
# ANTIGUEDAD DEL PROCESO
# Este es el dato mas importante, y el que FALTA en la fuente.
#
# `estado_de_apertura_del_proceso = 'Abierto'` NO significa "se puede licitar".
# Es el estado interno del proceso en SECOP. Medido el 29/09/2026:
#   - 8.086.821 procesos marcados "Abierto"
#   - 4.907.994 (60,7%) publicados antes de 2025
#   - el mas antiguo sigue "Abierto" desde 2015
#
# El dataset NO tiene fecha de cierre. Sin ella, mostrar estos procesos como
# oportunidad es danino: el cliente hace clic, lo encuentra cerrado y pierde la
# confianza en la herramienta a la primera.
#
# Mitigacion: mostrar siempre la antiguedad, castigar lo viejo, y decirle al
# usuario que verifique el plazo en SECOP.
# --------------------------------------------------------------------------
DIAS_MAXIMOS = 90   # por encima de esto, casi seguro el plazo ya vencio


def dias_desde(fecha_texto):
    """Dias desde la publicacion. None si no se puede leer la fecha."""
    if not fecha_texto:
        return None
    try:
        solo_fecha = str(fecha_texto).split("T")[0]
        return (datetime.now().date() - datetime.strptime(solo_fecha, "%Y-%m-%d").date()).days
    except (ValueError, TypeError):
        return None


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

    # Antiguedad. Ver la nota de DIAS_MAXIMOS: "Abierto" no significa que se
    # pueda licitar, y el dataset no trae fecha de cierre.
    dias = dias_desde(f.get("fecha_de_publicacion_del"))
    if dias is not None and dias > DIAS_MAXIMOS:
        if dias > 365:
            return 0, ["descartado: publicado hace %d dias, el plazo ya vencio" % dias]
        puntos -= 30
        razones.append("ATENCION: publicado hace %d dias" % dias)
    elif dias is not None and dias > 0:
        razones.append("publicado hace %d dias" % dias)

    return max(0, min(100, int(puntos))), razones


# --------------------------------------------------------------------------
# ESCRITURA SEGURA
# Guardar el CSV directamente falla si el archivo esta abierto. Pasa de verdad:
# el cliente abre el CSV en Excel, o la corrida anterior sigue escribiendo.
# La salida es un archivo temporal y luego se renombra, que en Windows es atomico:
# o queda el nuevo completo o queda el anterior, nunca uno a medio escribir.
# --------------------------------------------------------------------------
def escribir_csv(ruta, cabecera, filas):
    """Escribe el CSV sin dejar archivos a medias. Devuelve la ruta escrita."""
    import tempfile
    import time
    directorio = os.path.dirname(os.path.abspath(ruta)) or "."
    ultimo_error = None
    for intento in range(4):
        tmp = os.path.join(directorio, ".tmp_" + os.path.basename(ruta))
        try:
            with open(tmp, "w", newline="", encoding="utf-8-sig") as fh:
                w = csv.writer(fh)
                w.writerow(cabecera)
                for f in filas:
                    w.writerow(f)
            os.replace(tmp, ruta)
            return ruta
        except PermissionError as exc:
            ultimo_error = exc
            time.sleep(0.6 * (intento + 1))
        except OSError as exc:
            ultimo_error = exc
            break
        finally:
            if os.path.exists(tmp):
                try:
                    os.remove(tmp)
                except OSError:
                    pass
    # Ultimo recurso: no perder los datos aunque el destino este bloqueado.
    copia = ruta.replace(".csv", "_%s.csv" % datetime.now().strftime("%Y%m%d_%H%M%S"))
    import shutil
    shutil.copyfile(ruta, copia) if os.path.exists(ruta) else None
    raise PermissionError("No se pudo escribir %s: %s" % (ruta, ultimo_error))


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
        print("     Que buscan : " + objeto_limpio(f)[0][:140])
        pre = entero(f.get("precio_base"))
        print("     Presupuesto: " + ("$ " + "{:,.0f}".format(pre).replace(",", ".")
                                     if pre else "no publicado"))
        print("     Zona       : " + (f.get("ciudad_entidad") or "?") + " / " + (f.get("departamento_entidad") or "?"))
    _d = dias_desde(f.get("fecha_de_publicacion_del"))
    if _d is not None:
        print("    Publicado  : hace " + str(_d) + " dias  " + ("(ATENCION, verifique si sigue en plazo)" if _d > DIAS_MAXIMOS else ""))
        print("     Oferentes  : " + (f.get("conteo_de_respuestas_a_ofertas") or "0"))
        print("     Por que    : " + "; ".join(f["_razones"]))
        lk = link_de(f)
        if lk:
            print("     Link       : " + lk)

    salida = "oportunidades.csv"
    try:
        escribir_csv(
            salida,
            ["score", "referencia", "entidad", "ciudad", "departamento",
             "objeto", "presupuesto", "dias_publicado", "oferentes", "razones", "link"],
            [[f["_score"], f.get("referencia_del_proceso"), f.get("entidad"),
              f.get("ciudad_entidad"), f.get("departamento_entidad"),
              objeto_limpio(f)[0], f.get("precio_base"),
              dias_desde(f.get("fecha_de_publicacion_del")),
              f.get("conteo_de_respuestas_a_ofertas"),
              "; ".join(f["_razones"]), link_de(f)] for f in res])
        print("\n  Guardado: " + salida)
    except PermissionError as exc:
        print("\n  " + AMARILLO + "AVISO: no se pudo guardar " + salida + FIN)
        print("        " + str(exc))
        print("        Cierre Excel o el explorador que lo tenga abierto y vuelve a correr.")

    # --- Registro en el historico -------------------------------------------
    # Sin esto no hay forma de saber si el filtro acierta. El cliente marca
    # despues cada oportunidad como util o descartada, y de ahi sale la
    # calibracion real del PERFIL.
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import historico
        payload = [{"referencia": f.get("referencia_del_proceso"),
                    "entidad": f.get("entidad"),
                    "objeto": objeto_limpio(f)[0],
                    "departamento": f.get("departamento_entidad"),
                    "presupuesto": f.get("precio_base"),
                    "score": f["_score"],
                    "razones": f["_razones"]} for f in res]
        criterios = {"departamentos": PERFIL["departamentos"],
                     "precio_min": PERFIL["precio_min"],
                     "precio_max": PERFIL["precio_max"],
                     "palabras_clave": PERFIL["palabras_clave"]}
        n, _ = historico.registrar(payload, PERFIL["empresa"], criterios)
        print("  Historico: " + str(n) + " oportunidades registradas")
        print("  Revision de acierto:  python src/historico.py --reporte")
    except Exception as exc:
        print("  (aviso: no se pudo registrar en el historico: " + str(exc) + ")")

    print("")
    return 0


if __name__ == "__main__":
    sys.exit(main())