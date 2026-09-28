#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LECTOR DE PLIEGOS - Cruza lo que pide la licitacion contra lo que tiene la empresa.

Que hace:
  1. Lee el pliego (PDF con texto, o .txt) y le extrae los requisitos exigidos.
  2. Los cruza contra el perfil de la empresa.
  3. Devuelve: lo que cumples, lo que te FALTA, y lo que no se puede determinar.

Por que existe: el valor no esta en resumir el pliego, esta en responder
"puedo presentar esto o no". Un requisito que no cumples y no viste a tiempo
te descalifica; uno que cumples te da ventaja frente a quien no lo leyo.

Uso:
    python src/requisitos.py --pliego pliego.pdf --empresa ConstructoraEjemplo.json
    python src/requisitos.py --pliego pliego.pdf --demo     (perfil de ejemplo)

Instalacion:
    uv venv .venv && uv pip install --python .venv/Scripts/python.exe pypdf
"""

import argparse
import json
import os
import re
import sys

# --------------------------------------------------------------------------
# BIBLIOTECA DE REQUISITOS
# Este es el activo del producto: el conocimiento de que pide una licitacion
# publica en Colombia. Se enriquece con cada cliente que se calibraciona.
#
#   patron     : regex sobre el texto en minusculas (sin acentos)
#   tipo       : agrupacion para el informe
#   critico    : si incumplirlo descalifica. Es lo que hay que mirar primero.
# --------------------------------------------------------------------------
REQUISITOS = [
    # --- Habilitacion (el filtro mas duro: sin esto no se ni se presenta) ---
    (r"rup\b|registro de unicidad de proveedores", "Habilitacion", True, "RUP vigente"),
    (r"matriculad[oa]|inscripci[oó]n en el r[uú]g", "Habilitacion", True, "Matricula / RUG"),
    (r"no estar incurso|antecedentes fiscales|antecedentesjudiciales|paz y salvo",
     "Habilitacion", True, "Antecedentes y paz y salvo"),

    # --- Certificaciones ---
    (r"iso\s*9001", "Certificaciones", True, "ISO 9001 (calidad)"),
    (r"iso\s*14001", "Certificaciones", True, "ISO 14001 (ambiental)"),
    (r"iso\s*45001|iso\s*18001", "Certificaciones", False, "ISO 45001 (seguridad y salud)"),
    (r"iso\s*27001", "Certificaciones", False, "ISO 27001 (seguridad informacion)"),
    (r"\bsgs\b|calidad\s+certificada", "Certificaciones", False, "Certificacion SGS o equivalente"),
    (r"certificad[oa]\s+en\s+gesti[oó]n", "Certificaciones", False, "Certificacion en gestion"),

    # --- Capacidad financiera ---
    (r"patrimonio.{0,40}(m[ií]nimo|igual|mayor)|patrimonio\s+l[ií]quido",
     "Financiero", True, "Patrimonio minimo exigido"),
    (r"[ií]ndice de liquidez|raz[oó]n de liquidez", "Financiero", True, "Indice de liquidez minimo"),
    (r"ingresos.{0,40}(brutos|totales).{0,40}(m[ií]nimo|igual|mayor)|utilidad neta",
     "Financiero", True, "Ingresos / utilidad minima"),
    (r"kope|c[oó]digo de ", "Financiero", False, "KOPE o codigo de entidad"),
    (r"certificado de ingresos brutos|estados financieros|balance",
     "Financiero", False, "Estados financieros / ingresos brutos"),

    # --- Experiencia y capacidad tecnica ---
    (r"experiencia.{0,60}(m[ií]nima|m[i¡]nimo|al menos)",
     "Experiencia", True, "Experiencia minima en el objeto"),
    (r"contratos? (ejecutad|celebrad)|contratos? anteriores",
     "Experiencia", True, "Contratos previos del mismo objeto"),
    (r"equipo (de|para) (la )?ejecuci[oó]n|personal (t[eé]cnico|calificado)",
     "Experiencia", False, "Equipo tecnico asignado"),
    (r"profesional(?:es)? (especialist|-certificad)|licencia de construcci[oó]n|matr[ií]cula profesional",
     "Experiencia", True, "Profesionales con matricula / licencia"),
    (r"certificado de cumplimiento|contratos cumplidos|contratos ejecutados", "Experiencia", False, "Certificados de cumplimiento"),

    # --- Garantias y economicas ---
    (r"garant[ií]a de cumplimiento|p[oó]liza de cumplimiento",
     "Garantias", True, "Poliza de cumplimiento"),
    (r"garant[ií]a de calidad|estabilidad", "Garantias", False, "Garantia de estabilidad / calidad"),
    (r"retenci[oó]n en la fuente|r[eo]tenci[oó]n", "Garantias", False, "Retencion en la fuente"),
    (r"anticipo", "Garantias", False, "Anticipo"),

    # --- Requisitos de la propuesta ---
    (r"garant[ií]a de seriedad|dep[oó]sito|estampilla", "Propuesta", True, "Garantia de seriedad de la propuesta"),
    (r"apertura de la propuesta|presentaci[oó]n de la propuesta", "Propuesta", False, "Apertura y presentacion de propuesta"),
    (r"acta de compromisos|compromiso de \*no ofertar\*|declaraci[oó]n jurada",
     "Propuesta", False, "Acta de compromisos / declaraciones"),

    # --- Entorno y condiciones ---
    (r"seguridad y salud en el trabajo|sg-sst|salud ocupacional",
     "Ejecucion", True, "PESST / SG-SST vigente"),
    (r"plan de trabajo|cronograma de obra|cronograma de ejecuci[oó]n",
     "Ejecucion", False, "Plan de trabajo y cronograma"),
    (r"licencia de construcci[oó]n|licencia de edificaci[oó]n",
     "Ejecucion", True, "Licencia de construccion (si aplica)"),
    (r"p[oó]liza de cumplimiento|seguridad integral", "Ejecucion", False, "Póliza de seguridad"),
    (r"certificado de traducci[oó]n", "Ejecucion", False, "Traduccion oficial si aplica"),
]

# Campos que el perfil de la empresa debe declarar
CAMPOS_PERFIL = [
    "nombre", "rup", "iso_9001", "iso_14001", "iso_45001", "iso_27001", "sgs",
    "antecedentes", "patrimonio", "indice_liquidez", "utilidad_neta",
    "ingresos_brutos", "kope", "experiencia_anios", "contratos_previos",
    "profesionales_matriculados", "poliza_cumplimiento", "garantia_estabilidad",
    "garantia_seriedad", "pesst", "licencia_construccion", "plan_trabajo",
]


def normalizar(texto):
    """Minusculas y sin acentos, para que los patrones no dependan de tildes."""
    mapa = {"á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u", "ü": "u",
            "ñ": "n", "Á": "a", "É": "e", "Í": "i", "Ó": "o", "Ú": "u", "Ñ": "n"}
    for k, v in mapa.items():
        texto = texto.replace(k, v)
    return re.sub(r"\s+", " ", texto.lower())


def leer_pliego(ruta):
    """Devuelve (texto, aviso). El aviso explica si algo quedo fuera."""
    ext = os.path.splitext(ruta)[1].lower()
    if ext in (".txt", ".md"):
        with open(ruta, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read(), ""
    if ext != ".pdf":
        return None, "Formato no soportado: %s (usa .pdf o .txt)" % ext

    try:
        from pypdf import PdfReader
    except ImportError:
        return None, ("Falta pypdf. Instala con:\n"
                      "    uv pip install --python .venv/Scripts/python.exe pypdf")

    try:
        lector = PdfReader(ruta)
    except Exception as exc:
        return None, "No se pudo abrir el PDF: %s" % exc

    if lector.is_encrypted:
        try:
            lector.decrypt("")
        except Exception:
            return None, "El PDF esta protegido con contrasena."

    paginas, vacias = [], 0
    for p in lector.pages:
        try:
            t = p.extract_text() or ""
        except Exception:
            t = ""
        if not t.strip():
            vacias += 1
        paginas.append(t)
    texto = "\n".join(paginas)

    aviso = ""
    if not texto.strip():
        return "", ("El PDF no tiene capa de texto: es un ESCANEO y hay que pasarle OCR.\n"
                    "  Convierte a texto con OCR y vuelve a lanzar con el .txt resultante.")
    if vacias > len(paginas) * 0.4:
        aviso = ("Aviso: %d de %d paginas vinieron sin texto (escaneadas). "
                "Los requisitos de esas paginas NO se detectaron." % (vacias, len(paginas)))
    return texto, aviso


def detectar(texto):
    """Devuelve la lista de requisitos hallados, con el fragmento que los delata."""
    plano = normalizar(texto)
    hallados, vistos = [], set()
    for patron, tipo, critico, etiqueta in REQUISITOS:
        m = re.search(patron, plano)
        if not m:
            continue
        if etiqueta in vistos:
            continue
        vistos.add(etiqueta)
        ini = max(0, m.start() - 70)
        ctx = texto[ini:m.end() + 280].replace("\n", " ").strip()
        hallados.append({"tipo": tipo, "critico": critico, "nombre": etiqueta, "contexto": ctx})
    hallados.sort(key=lambda r: (not r["critico"], r["tipo"], r["nombre"]))
    return hallados


# Que clave del perfil responde a cada requisito detectado
CLAVE_DE = {
    "RUP vigente": "rup", "Matricula / RUG": "rup",
    "Antecedentes y paz y salvo": "antecedentes",
    "ISO 9001 (calidad)": "iso_9001", "ISO 14001 (ambiental)": "iso_14001",
    "ISO 45001 (seguridad y salud)": "iso_45001",
    "ISO 27001 (seguridad informacion)": "iso_27001",
    "Certificacion SGS o equivalente": "sgs",
    "Patrimonio minimo exigido": "patrimonio", "Indice de liquidez minimo": "indice_liquidez",
    "Ingresos / utilidad minima": "utilidad_neta", "KOPE o codigo de entidad": "kope",
    "Estados financieros / ingresos brutos": "ingresos_brutos",
    "Experiencia minima en el objeto": "experiencia_anios",
    "Contratos previos del mismo objeto": "contratos_previos",
    "Profesionales con matricula / licencia": "profesionales_matriculados",
    "Poliza de cumplimiento": "poliza_cumplimiento",
    "Garantia de estabilidad / calidad": "garantia_estabilidad",
    "Garantia de seriedad de la propuesta": "garantia_seriedad",
    "PESST / SG-SST vigente": "pesst",
    "Licencia de construccion (si aplica)": "licencia_construccion",
    "Plan de trabajo y cronograma": "plan_trabajo",
}


# Valores que significan "la empresa no lo tiene"
AUSENTES = {"", "no", "false", "false ", "n/a", "na", "ninguno", "0", "-", "pendiente"}


def _pasa_presencia(valor):
    """True si el campo esta informado de que la empresa lo tiene.

    Antes esto solo aceptaba booleanos y cadenas, y por eso un indice de liquidez
    de 2.4 (numero) salia como FALTA. Ahora cualquier valor informado cuenta,
    incluidos numeros, y solo se marca ausente lo que esta vacio o dice 'no'.
    """
    if valor is None or valor is False:
        return False
    if valor is True:
        return True
    if isinstance(valor, (int, float)):
        return valor > 0
    if isinstance(valor, (list, tuple, dict)):
        return len(valor) > 0
    if isinstance(valor, str):
        return valor.strip().lower() not in AUSENTES
    return bool(valor)


def _a_numero(valor):
    """Convierte '$1.850.000.000' o '1850000000' en 1850000000. None si no se puede."""
    if isinstance(valor, (int, float)):
        return float(valor)
    if not isinstance(valor, str):
        return None
    limpio = re.sub(r"[^\d.,]", "", valor)
    if not limpio:
        return None
    # '$1.850.000.000' -> los puntos son separadores de miles
    if "." in limpio and "," not in limpio:
        limpio = limpio.replace(".", "")
    else:
        limpio = limpio.replace(",", "").replace(".", "")
    try:
        return float(limpio)
    except ValueError:
        return None


# Requisitos cuyo valor hay que COMPARAR contra una cifra que pide el pliego.
NUMERICOS = {
    "Patrimonio minimo exigido": "patrimonio",
    "Ingresos / utilidad minima": "ingresos_brutos",
}


def _exigencia_numerica(contexto):
    """Saca el monto que el pliego exige, del texto alrededor del requisito.

    Solo maneja '$1.850.000.000' y '1.850.000.000'. Si el pliego lo redacta con
    palabras ('tres mil millones') no lo deduce y devuelve None, para que el
    resultado sea NO SE SABE en vez de un CUMPLE falso.
    """
    if not contexto:
        return None
    cifras = re.findall(r"\$\s*([\d.,]{7,})", contexto)
    if not cifras:
        cifras = re.findall(r"\b([\d.,]{9,})\b", contexto)
    if not cifras:
        return None
    mejor = None
    for c in cifras:
        n = _a_numero(c)
        if n and (mejor is None or n > mejor):
            mejor = n
    return mejor


def cruzar(hallados, perfil):
    """Clasifica cada requisito en CUMPLE / FALTA / NO SE SABE."""
    salida = []
    for r in hallados:
        nombre = r["nombre"]
        clave = CLAVE_DE.get(nombre)
        if clave is None or clave not in perfil:
            estado = "NO SE SABE"
            nota = "el perfil no declara este campo"
        else:
            valor = perfil[clave]
            if not _pasa_presencia(valor):
                estado = "FALTA"
                nota = "el perfil lo declara ausente"
            elif nombre in NUMERICOS:
                # Hay que comparar, no solo ver que el campo existe.
                exigido = _exigencia_numerica(r.get("contexto"))
                propio = _a_numero(valor)
                if exigido and propio is not None:
                    if propio >= exigido:
                        estado = "CUMPLE"
                        nota = "declara %s, el pliego exige %s" % (
                            "{:,.0f}".format(propio).replace(",", "."),
                            "{:,.0f}".format(exigido).replace(",", "."))
                    else:
                        estado = "FALTA"
                        nota = "declara %s, el pliego exige %s (le falta %.0f%%)" % (
                            "{:,.0f}".format(propio).replace(",", "."),
                            "{:,.0f}".format(exigido).replace(",", "."),
                            (exigido - propio) / exigido * 100)
                else:
                    estado = "NO SE SABE"
                    nota = "hay que comparar a mano: el pliego no expresa la cifra en numero"
            elif nombre == "Indice de liquidez minimo":
                propio = _a_numero(valor)
                m = re.search(r"liquidez[^\d]{0,40}(\d[.,]\d)", normalizar(r.get("contexto", "")))
                if propio is not None and m:
                    exigido = float(m.group(1).replace(",", "."))
                    if propio >= exigido:
                        estado, nota = "CUMPLE", "indice %s, el pliego exige %s" % (propio, exigido)
                    else:
                        estado, nota = "FALTA", "indice %s, el pliego exige %s" % (propio, exigido)
                elif propio is not None:
                    estado, nota = "NO SE SABE", "falta la cifra minima en el pliego para comparar"
                else:
                    estado, nota = "NO SE SABE", "el indice no es un numero"
            else:
                estado = "CUMPLE"
                nota = ""
        r["estado"] = estado
        r["clave"] = clave
        r["nota"] = nota
        salida.append(r)
    return salida


def veredicto(filas):
    criticos = [f for f in filas if f["critico"]]
    faltan_crit = [f for f in criticos if f["estado"] == "FALTA"]
    desconocen = [f for f in criticos if f["estado"] == "NO SE SABE"]

    if faltan_crit:
        return ("NO PRESENTAR", faltan_crit, desconocen,
                "Falta%s %d requisito%s critico%s. Presentar sin ellos es gasto de tiempo y "
                "de GARANTIA: se pierde la poliza de seriedad."
                % ("" if len(faltan_crit) == 1 else "n", len(faltan_crit),
                   "" if len(faltan_crit) == 1 else "s", "" if len(faltan_crit) == 1 else "s"))
    if desconocen:
        return ("REVISAR ANTES DE POSTULAR", [], desconocen,
                "Hay %d requisitos criticos sin verificar. Confirmalos antes de decidir."
                % len(desconocen))
    crit_ok = len(criticos)
    return ("POSTULAR", [], [],
            "Cumple los %d requisitos criticos detectados en el pliego." % crit_ok)


def imprimir(filas, nombre_empresa, ruta):
    print("=" * 78)
    print("  LECTOR DE PLIEGOS  -  " + nombre_empresa)
    print("  " + os.path.basename(ruta))
    print("=" * 78)

    if not filas:
        print("\n  No se detecto ningun requisito reconocible.")
        print("  Puede ser que el pliego use otra redaccion, o que sea una escaneo sin OCR.")
        return 0

    criticos = [f for f in filas if f["critico"]]
    no_criticos = [f for f in filas if not f["critico"]]

    def bloque(titulo, grupo):
        if not grupo:
            return
        print("\n  " + titulo)
        print("  " + "-" * 74)
        for f in grupo:
            marca = {"CUMPLE": "[ CUMPLE ]", "FALTA": "[ FALTA  ]",
                     "NO SE SABE": "[ ????  ]"}[f["estado"]]
            print("  %s %-38s %s" % (marca, f["nombre"], f["tipo"]))
            if f.get("nota"):
                print("           %s" % f["nota"])

    bloque("REQUISITOS CRITICOS (si falla uno, descalifica)", criticos)
    bloque("OTROS REQUISITOS DETECTADOS", no_criticos)

    est, faltan, desconocen, texto = veredicto(filas)
    print("\n" + "=" * 78)
    print("  VEREDICTO: " + est)
    print("=" * 78)
    print("  " + texto)

    if faltan:
        print("\n  Brechas criticas:")
        for f in faltan:
            print("   - " + f["nombre"])
            if f["contexto"]:
                print("     en el pliego: ..." + f["contexto"][:150] + "...")
    if desconocen:
        print("\n  Por confirmar en el perfil de la empresa:")
        for f in desconocen:
            print("   - " + f["nombre"] + "   (campo: %s)" % f["clave"])

    # salida para el informe semanal
    salida = {
        "empresa": nombre_empresa, "pliego": os.path.basename(ruta),
        "veredicto": est, "total_requisitos": len(filas),
        "criticos": len(criticos),
        "detalle": [{"nombre": f["nombre"], "tipo": f["tipo"],
                     "critico": f["critico"], "estado": f["estado"]} for f in filas],
    }
    with open("analisis_pliego.json", "w", encoding="utf-8") as fh:
        json.dump(salida, fh, ensure_ascii=False, indent=2)
    print("\n  Guardado: analisis_pliego.json")
    return 0


PERFIL_DEMO = {
    "nombre": "Constructora Ejemplo S.A.S. (perfil de ejemplo)",
    "rup": True, "antecedentes": True, "iso_9001": True, "iso_14001": False,
    "iso_45001": True, "sgs": False, "pesst": True, "plan_trabajo": True,
    "poliza_cumplimiento": True, "garantia_seriedad": True,
    "profesionales_matriculados": True, "contratos_previos": 6,
    "experiencia_anios": 12, "patrimonio": "$850.000.000",
    "indice_liquidez": 2.4, "utilidad_neta": "$190.000.000",
    "ingresos_brutos": "$2.400.000.000",
}


def main():
    ap = argparse.ArgumentParser(description="Cruza los requisitos de un pliego contra el perfil de la empresa.")
    ap.add_argument("--pliego", required=True, help="PDF con texto o .txt")
    ap.add_argument("--empresa", help="JSON con el perfil de la empresa")
    ap.add_argument("--demo", action="store_true", help="Usar el perfil de ejemplo")
    args = ap.parse_args()

    if not os.path.exists(args.pliego):
        print("No existe el archivo: " + args.pliego)
        return 1

    if args.empresa:
        with open(args.empresa, "r", encoding="utf-8") as fh:
            perfil = json.load(fh)
    elif args.demo:
        perfil = PERFIL_DEMO
    else:
        print("Falta --empresa o --demo.")
        return 1

    faltantes = [c for c in CAMPOS_PERFIL if c != "nombre" and c not in perfil]
    if faltantes:
        print("NOTA: el perfil no declara estos campos, se marcaran como NO SE SABE:")
        print("      " + ", ".join(faltantes) + "\n")

    texto, aviso = leer_pliego(args.pliego)
    if aviso:
        print("AVISO: " + aviso + "\n")
    if not texto:
        return 1

    filas = cruzar(detectar(texto), perfil)
    return imprimir(filas, perfil.get("nombre", "Empresa"), args.pliego)


if __name__ == "__main__":
    sys.exit(main())
