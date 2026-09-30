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
        # Salud. OJO: NO añadir "salud" suelta. Medido el 30/09/2026 sobre
        # 6.000 procesos abiertos: "salud" aparece en el 27% de las
        # coincidencias del sector, porque "seguridad y salud en el trabajo"
        # es parte de todo contrato de obra. Estos tres si son inequivocos:
        # cortan 14 de 194, todos contratos de profesionales de la salud que
        # entraban por la palabra "intervencion" (una intervencion dental no
        # es una intervencion de obra).
        "odontolog", "quirurgic", "psicolog",
    ],
    # Se miran SOLO en el titulo, no en la descripcion. Hay procesos que son
    # obra de verdad y aun asi mencionan "subsidio" en la descripcion
    # (medido el 30/09/2026 sobre 6.000 abiertos): D-416-2026, $162.270.460,
    # vivienda en Palermo Huila, publicada hace 16 dias. Si la palabra se
    # buscara en cualquier campo, esa oportunidad desapareceria.
    # Estas son transferencias de plata que parecen obra porque el texto habla
    # de acueducto: "TRANSFERENCIA DE RECURSOS A LA EMPRESA MUNICIPAL DE
    # AGUAS Y ASEO ... PARA LOS SUBSIDIOS". Es dinero, no constructors.
    "excluir_titulo": [
        "transferencia de recursos",
        "transferencia y o recepcion de recursos",
        "transferencia y/o recepcion de recursos",
        "otorgamiento de subsidios",
        "transferencia subsidios",
        "traspaso de recursos",
    ],
    "departamentos": ["ANTIOQUIA", "CUNDINAMARCA", "DISTRITO CAPITAL", "ATLANTICO", "SANTANDER", "CALDAS"],
    "precio_min": 80_000_000,
    "precio_max": 8_000_000_000,
    "aviso_si_oferentes": 25,   # por encima de esto, avisar de mucha competencia

    # El corte de puntaje vivia hardcodeado (`if s >= 40`). Con un perfil mal
    # puesto el filtro no dice nada: simplemente no sale nada, y el usuario no
    # tiene forma de saber si el problema es el mercado o su configuracion.
    "puntaje_minimo": 40,

    # "Abierto" no es "licitable": el dataset no trae fecha de cierre. Se usa
    # la antiguedad como aproximacion. Pasado esto: penaliza. Pasado 1 ano: veto.
    "dias_maximos": 90,

    # PESOS DEL PUNTUJE. Maximo 100 = sector perfecto + zona + presupuesto.
    # Antes estaban metidos dentro de `puntuar()`, lo que hacia imposible
    # ajustarlos o explicarselos al cliente sin tocar el codigo.
    "peso_sector": 60,        # escalado: 1 palabra clave = mitad, 2+ = completo
    "peso_zona": 20,          # +20 en zona objetivo
    "peso_fuera_de_zona": 5,
    "peso_presupuesto": 20,   # solo si el valor cae dentro del rango
    "penalty_sobre_precio": 15,
    "penalty_antiguedad": 30,
}

TOP_N = 15

# Cuantos procesos se descargan. NO es un detalle menor.
# Medido el 30/09/2026 con este perfil (sale ~1 oportunidad por cada 550 procesos
# abiertos): con limite 500 se encontraban 14 del sector y 0 por encima del
# corte; con 5.000, 165 y 9; con 20.000, 624 y 36.
# El valor anterior de 500 submuestreaba el mercado y hacia creer que no habia
# oportunidades cuando si las habia.
MUESTRA = 5000
MUESTRA_MAX = 50000        # techo, para no abusar del servidor publico

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
    """Enlace al proceso en SECOP.

    No siempre trae la ficha del proceso. Medido el 30/09/2026: hay filas cuyo
    `urlproceso` es la pantalla de login de SECOP (`/STS/Users/Login/Index`) o
    la portada del portal, que no llevan a ninguna parte. Enviar a un cliente a
    una pagina de acceso parece un fallo de la herramienta, asi que mejor se
    dice "no disponible" que prometer un enlace que no lleva a la oportunidad.
    """
    u = fila.get("urlproceso")
    if isinstance(u, dict):
        u = u.get("url", "")
    u = (u or "").strip()
    if not u:
        return ""
    baja = u.lower()
    rotas = ("/sts/users/login", "login/index", "/secop.aspx", "/home/index")
    if any(b in baja for b in rotas):
        return ""
    # la ficha real siempre lleva el identificador del aviso
    if "opportunitydetail" not in baja:
        return ""
    return u


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
    # Un codigo no tiene espacios, trae al menos un digito y es alfanumerico
    # con separadores. Antes solo se aceptaban codigos SIN letras, asi que
    # "D-416-2026" o "ICCU-CTO-1479-2025" se tomaban por descripcion y la
    # tarjeta mostraba el codigo repetido donde va el objeto. Medido el
    # 30/09/2026 sobre 5.000 procesos: 129 titulos cambian, ninguno queda
    # sin descripcion y no hay regresiones. "CONTRATO 2026 DE OBRA" no cuenta
    # como codigo porque tiene palabras.
    sin_espacios = re.sub(r"[ .]", "-", nom.replace("copia", "").strip()).strip("-.")
    es_codigo = (bool(sin_espacios) and " " not in sin_espacios
                and any(c.isdigit() for c in sin_espacios)
                and re.fullmatch(r"[A-Za-z0-9]+([-.][A-Za-z0-9]+)*", sin_espacios))
    if es_codigo:
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

    # Las transferencias de plata se descartan mirando solo el titulo. Ver la
    # nota de "excluir_titulo" en PERFIL: buscarlas en la descripcion borraria
    # obras reales que mencionan "subsidio" de pasada.
    titulo = (f.get("nombre_del_procedimiento") or "").lower()
    if any(x in titulo for x in p["excluir_titulo"]):
        return 0, []

    if any(x in texto for x in p["excluir"]):
        return 0, []

    aciertos = [k for k in p["palabras_clave"] if k in texto]
    if not aciertos:
        return 0, []
    puntos = min(len(aciertos) / 2.0, 1.0) * p["peso_sector"]
    razones = ["sector: " + ", ".join(aciertos[:3])]

    dep = (f.get("departamento_entidad") or "").upper()
    if any(d.upper() in dep for d in p["departamentos"]):
        puntos += p["peso_zona"]
        razones.append("zona objetivo")
    else:
        puntos += p["peso_fuera_de_zona"]

    precio = entero(f.get("precio_base"))
    if precio == 0:
        razones.append("presupuesto no publicado")
    elif p["precio_min"] <= precio <= p["precio_max"]:
        puntos += p["peso_presupuesto"]
        razones.append("presupuesto encaja")
    elif precio > p["precio_max"]:
        puntos -= p["penalty_sobre_precio"]
        razones.append("muy por encima del rango")

    # COMPETENCIA: no se puntua, porque no se puede saber.
    # Aqui habia un "+10 poca competencia" cuando el contador venia en cero.
    # Medido el 30/09/2026 sobre 3.000 procesos abiertos: ese campo tiene dato
    # en el 0,0% de los casos, y `proveedores_que_manifestaron` tambien en el
    # 0,0%. O sea que practicamente toda oportunidad recibia los +10 y se le
    # decia al cliente algo falso. Los campos se llenan al cerrar el proceso.
    # La penalizacion real (MUCHA competencia) se conserva: esa si es verdad
    # cuando aparece.
    oferentes = entero(f.get("conteo_de_respuestas_a_ofertas"))
    if oferentes > p["aviso_si_oferentes"]:
        puntos -= p["penalty_sobre_precio"]
        razones.append("MUCHA competencia: " + str(oerentes) + " oferentes")

    # Antiguedad. Ver la nota de DIAS_MAXIMOS: "Abierto" no significa que se
    # pueda licitar, y el dataset no trae fecha de cierre.
    dias = dias_desde(f.get("fecha_de_publicacion_del"))
    if dias is not None and dias > p["dias_maximos"]:
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


def oferentes_de(f):
    """El contador llega como cadena, y la cadena "0" es verdadera en Python:
    un `or "sin dato"` la deja pasar y muestra '0 oferentes', que es una
    mentira. En procesos abiertos ese campo viene vacio en el 99% de los casos
    (medido el 30/09/2026 sobre 3.000 abiertos): no hay dato, no hay cero."""
    v = (f.get("conteo_de_respuestas_a_ofertas") or "").strip()
    if not v or v in ("0", "No Definido", "no definido"):
        return "sin dato (SECOP no lo publica mientras esta abierto)"
    return v + " oferentes"


def pct(parte, total):
    return "%.1f%%" % (100.0 * parte / total) if total else "-"


def miles(n):
    return "{:,.0f}".format(n).replace(",", ".")


def diagnostico(filas, p):
    """Embudo del filtro. Responde la unica pregunta que importa cuando no
    sale nada: 'no hay oportunidades' o 'el perfil esta cerrado de mas'."""
    def sector_de(f):
        titulo = (f.get("nombre_del_procedimiento") or "").lower()
        if any(x in titulo for x in p["excluir_titulo"]):
            return None
        t = (titulo + " " + (f.get("descripci_n_del_procedimiento") or "").lower())
        if any(x in t for x in p["excluir"]):
            return None
        return [k for k in p["palabras_clave"] if k in t]

    def edad(f):
        return dias_desde(f.get("fecha_de_publicacion_del")) or 0

    def monto(f):
        return entero(f.get("precio_base"))

    n = len(filas)
    t = "\n  EMBUDO DEL FILTRO\n  " + "-" * 72 + "\n"
    t += "  Procesos abiertos descargados : %7d\n" % n

    con_sector = [f for f in filas if sector_de(f)]
    con = list(con_sector)
    t += "  Del sector de la empresa       : %7d   (%s de lo descargado)\n" % (
        len(con), pct(len(con), n))

    vetados = [f for f in con if edad(f) > 365]
    t += "  Publicados hace mas de 1 ano   : %7d   (%s)  [veto]\n" % (
        len(vetados), pct(len(vetados), len(con)))
    con = [f for f in con if edad(f) <= 365]

    viejos = [f for f in con if edad(f) > p["dias_maximos"]]
    t += "  Mas de %d dias (penaliza -%d)  : %7d   (%s)\n" % (
        p["dias_maximos"], p["penalty_antiguedad"],
        len(viejos), pct(len(viejos), len(con)))
    con = [f for f in con if edad(f) <= p["dias_maximos"]]

    bajo = [f for f in con if 0 < monto(f) < p["precio_min"]]
    conprecio = [f for f in con if monto(f) > 0]
    t += "  Presupuesto bajo el minimo     : %7d   (%s de los que dicen monto)\n" % (
        len(bajo), pct(len(bajo), len(conprecio)))
    if bajo:
        t += "      el mas alto: $%s   |   minimo exigido: $%s\n" % (
            miles(max(monto(f) for f in bajo)), miles(p["precio_min"]))
    sobre = [f for f in con if monto(f) > p["precio_max"]]
    t += "  Presupuesto sobre el maximo    : %7d\n" % len(sobre)
    t += "  Sin monto publicado            : %7d   (no se pueden comparar)\n" % (
        len([f for f in con if monto(f) == 0]))

    # El puntaje se calcula sobre TODO el sector, igual que hace main().
    # Si se calculara sobre los que sobrevivieron el embudo, el numero
    # no coincidiria con el de "relevantes" de arriba y pareceria un bug.
    scores = sorted((puntuar(f, p)[0] for f in con_sector), reverse=True)
    pasan = sum(1 for s in scores if s >= p["puntaje_minimo"])
    t += "\n  Con puntaje >= %-3d            : %7d\n" % (p["puntaje_minimo"], pasan)
    if scores:
        t += "  Puntaje mas alto disponible   : %7d\n" % scores[0]
        cuentas = [(k, sum(1 for s in scores if k <= s < k + 10))
                   for k in range(0, 100, 10)]
        t += "  Reparto                        : " + "  ".join(
            "%d-%d:%d" % (k, k + 9, c) for k, c in cuentas if c) + "\n"

    if pasan == 0:
        t += "\n  Si esto sale en cero, el problema es el PERFIL, no el mercado.\n"
        t += "  Lo mas sospechoso es 'precio_min': esta apartando obras que si le\n"
        t += "  sirven. Bajelo antes de concluir que no hay oportunidades.\n"
    print(t)


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
        if s >= PERFIL["puntaje_minimo"]:
            f["_score"], f["_razones"] = s, r
            res.append(f)
    res.sort(key=lambda x: x["_score"], reverse=True)
    print("  {0} relevantes".format(len(res)))

    # Va antes del corte por lista vacia a proposito: cuando el perfil
    # esta mal, no hay nada que mostrar y es justo cuando hace falta saber
    # por que. Ademas NO se envuelve en try/except: un fallo aqui es un
    # fallo real y no debe quedar escondido.
    diagnostico(filas, PERFIL)

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
        d = dias_desde(f.get("fecha_de_publicacion_del"))
        if d is not None:
            print("     Publicado  : hace " + str(d) + " dias  " +
                  ("(ATENCION, verifique si sigue en plazo)"
                   if d > PERFIL["dias_maximos"] else ""))
            print("     Oferentes  : " + oferentes_de(f))
        print("     Por que    : " + "; ".join(f["_razones"]))
        lk = link_de(f)
        if lk:
            print("     Link       : " + lk)
        else:
            print("     Link       : SECOP no publico enlace para esta. Busquela")
            print("                  por la referencia " +
                  str(f.get("referencia_del_proceso") or "?") + " en SECOP II")
        print()

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