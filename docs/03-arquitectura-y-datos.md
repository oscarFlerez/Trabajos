# 3. Arquitectura, datos y.limitaciones tecnicas

> Documento tecnico. Todo lo que aparece aqui fue **verificado ejecutando** el motor
> contra la API real de datos.gov.co, no consultado en teoria.

## 3.1 La fuente de datos

El servicio se apoya en el portal de datos abiertos del Estado Colombiano, en el
dataset **`p6dx-8zbt` — "SECOP II - Procesos de Contratacion"**.

| Propiedad | Valor |
|---|---|
| Endpoint | `https://www.datos.gov.co/resource/p6dx-8zbt.json` |
| API key | **No requiere.** Es el activo comercial del producto |
| Costo | $0 |
| Licencia | Datos publicos de dominio público |
| Actualizacion | Diaria por parte de la Plataforma Nacional de Contratacion |

Consultar la API publica del Estado es lo que separa este servicio de un scraper
comercial que cobra licencia y se cae cuando cambian el HTML.

## 3.2 Hallazgo critico: el dataset equivocado

El primer dataset localizado, `w3du-xuur` ("SECOP Integrado"), **parecia** servir y
**no sirve**. Medicion real sobre 200 procesos abiertos:

```
objeto_a_contratar  ->  "no definido"  en 200 de 200 registros
```

Ese dataset solo tiene el texto del objeto **despues de adjudicado**. Como la
prospectacion ocurre antes, cualquier producto construido sobre el se queda sin
texto que filtrar. Un proveedor que no mida esto se rompe en la demo del cliente.

El dataset correcto expone ademas un campo de estado limpio:

```
estado_de_apertura_del_proceso = 'Abierto'
```

En vez de interpretar cadenas de texto como `"Convocado"`, `"En ejecucion"` o
`"terminado"`, que es fragile y dependia del idioma.

## 3.3 Campos utilizados

| Campo | Uso en el producto |
|---|---|
| `estado_de_apertura_del_proceso` | Filtro de procesos abiertos |
| `descripci_n_del_procedimiento` | Texto del objeto (matching por sector) |
| `nombre_del_procedimiento` | Referencia corta |
| `precio_base` | Ajuste por presupuesto |
| `departamento_entidad`, `ciudad_entidad` | Ajuste geografico |
| `codigo_principal_de_categoria` | Codigo UNSPSC: sector exacto |
| `modalidad_de_contratacion` | Segmentacion (licitacion, minima cuantia, directo) |
| `conteo_de_respuestas_a_ofertas` | Intensidad de competencia |
| `fecha_de_publicacion_del` | Antiguedad y urgencia |
| `urlproceso` | Enlace directo al pliego en SECOP |

`codigo_principal_de_categoria` es la pieza mas valiosa: al ser un codigo UNSPSC
(por ejemplo `V1.80111500`), permite filtrar por sector sin depender de palabras
clave en español libre. Es la diferencia entre un filtro que funciona y uno que se
rompe con cada abreviatura.

## 3.4 Arquitectura

```
  datos.gov.co (Socrata)
          |
          |  consulta estructurada, sin scraping
          v
  +--------------------------------+
  |  Motor de consulta (radar.py)  |
  |  - filtro estado = 'Abierto'   |
  |  - normaliza texto             |
  |  - calcula puntaje             |
  +--------------------------------+
          |
          +--> Puntaje 0-100 + razones
          |
          v
  +--------------------------------+
  |  Capa de agente (LLM)         |
  |  - limpia nombres sucios       |
  |  - extrae requisitos tecnicos  |
  |  - contrasta con la empresa    |
  |  - redacta memoria tecnica     |
  +--------------------------------+
          |
          v
   Informe semanal (PDF/CSV/email)
```

El motor determinista hace el filtrado grueso y barato. El modelo de lenguaje solo
interviene donde el texto es ambiguo. Esa separacion es deliberada: un LLM no debe
decidir quais de 500 procesos son relevantes, porque seria lento, caro y no
reproducible.

## 3.5 Logica de puntaje

| Criterio | Peso | Detalle |
|---|---|---|
| Ajuste sectorial | 60 | Palabras clave + categoria UNSPSC |
| Zona geografica | 20 | Departamento en la zona de operacion |
| Encaje presupuestal | 20 | `precio_base` dentro del rango del cliente |
| Sin oferentes | +10 | *(desactivado, ver 3.6)* |
| Exceso de oferentes | -20 | Cuando supera el umbral de competencia |
| Fuera de rango | -15 | Contrato muy por encima del perfil |

**Por que importa el ultimo criterio.** La mayoria de los agentes de prospection
muestran todo. El valor esta en **descartar**: si van 40 oferentes, la probabilidad
real es baja y el cliente pierde su tiempo. Descartar es lo que se vende.

## 3.6 Limitaciones conocidas

Estas estan documentadas a proposito. Son el mapa de lo que falta por construir.

| # | Limitacion | Impacto | Mitigacion |
|---|---|---|---|
| L-1 | `conteo_de_respuestas_a_ofertas` llega en **0** mientras el proceso esta abierto | La regla "+10 sin oferentes" no distingue nada | Calcular competencia con la entidad y el historico de adjudicaciones |
| L-2 | `nombre_del_procedimiento` llega sucio: `"OSCAR JOSE CORTES RIVERO"`, `"31117 copia"`, `"021-2023"` | Falsos positivos | Normalizar con LLM + validar contra `descripci_n_del_procedimiento` |
| L-3 | Matching por subcadena produce falsos positivos: `"intervencion"` matchea *"intervenciones de coordinacion"* de enfermeria | Falsos positivos | Anadir categoria UNSPSC como filtro deSupport |
| L-4 | `departamento_entidad` puede venir como `"No Definido"` | Pierde el ajuste geografico | Heredar del `departamento_entidad` de la entidad, via tabla de entidades |
| L-5 | Los procesos interadministrativos no tienen objeto ni detalle de lotes | Oportunidades perdidas | Segundo barrido sobre contratos del adjudicatario |
| L-6 | El barrido trae 500 registros por corrida | Cobertura parcial | Paginar con `$offset` para cubrir el historico completo |

La limitacion L-3 se observo en la ejecucion real: aparecio *"apoyo tecnico en obra"*
con puntaje 45 y tambien *"intervenciones de coordinacion con otros sectores"* de
enfermeria con el mismo puntaje. Un filtro por subcadena no distingue un oficio de
otro.

## 3.7 Verificacion ejecutada

```
[1/2] Descargando procesos ABIERTOS...
  500 procesos abiertos encontrados
[2/2] Analizando contra el perfil...
  13 relevantes
```

Salida real del 25/09/2026, con el perfil de una constructora (palabras clave de obra
civil, acueducto, vivienda; zonas Antioquia, Cundinamarca, Bogota; rango 80M-8.000M COP).
El motor produjo 13 oportunidades con enlace directo al pliego y genero
`oportunidades.csv`.

## 3.8 Pila tecnica

| Componente | Eleccion | Motivo |
|---|---|---|
| Lenguaje | Python 3.11+ | Ecosistema de datos y de IA |
| Dependencias | **Solo biblioteca estandar** (`urllib`, `csv`, `json`) | Cero friccion de instalacion, portabilidad a cualquier equipo |
| Fuente de datos | Socrata / SoQL | Consultas estructuradas, sin scraping |
| Modelo de lenguaje | Gemini / Gemma | Clasificacion y extraccion sobre texto ambiguo |
| Salida | CSV + PDF | Formato que el cliente ya usa |
| Persistencia | Archivo local + Sheets | Suficiente para el volumen actual |

El motor no necesita `requests` ni `pandas` a proposito: con `urllib` el script
funciona en cualquier Python instalado, sin crear un entorno virtual. Eso importa
cuando el cliente quiere correrlo en su propio equipo.
