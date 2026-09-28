# Trabajos

Repositorio de proyectos. Cada carpeta es un proyecto independiente con su
documentacion y su codigo.

---

## Proyecto: Radar de Licitaciones

Servicio que detecta, puntua y descarta oportunidades de licitacion publica en
Colombia a partir de los datos abiertos de SECOP II, y entrega un informe semanal
con la referencia de precios de la competencia.

**Estado:** prototipo funcional. El motor corre contra la API real.

### Que problema resuelve

Las constructoras y empresas de ingenieria que viven del sector publico pierden
oportunidades por tres motivos: no se enteran a tiempo, leen procesos que no pueden
ganar, y licitan sin saber a cuanto le cobra la competencia.

### Que lo hace diferente

No resume pliegos: **descarta los que no puedes ganar** y te dice **a cuanto
licitó tu competencia**. La segunda parte es la que justifica un precio sostenido.

### Documentacion

| Documento | Contenido |
|---|---|
| [01 Marco logico](docs/01-marco-logico.md) | Problema, causas, objetivos, metas, indicadores, supuestos, restricciones |
| [02 Requerimientos y requisitos](docs/02-requerimientos.md) | Funcionales (MoSCoW), no funcionales, tecnicos, de negocio y legales |
| [03 Arquitectura y datos](docs/03-arquitectura-y-datos.md) | Fuente de datos, hallazgos, arquitectura, logica de puntaje, limitaciones |
| [04 Plan de negocios](docs/04-plan-de-negocios.md) | Propuesta de valor, precios, economia unitaria, mensaje de venta |
| [05 Cronograma, presupuesto y riesgos](docs/05-cronograma-presupuesto-y-riesgos.md) | Fases, costos, punto de equilibrio, tabla de riesgos |
| [06 El filtro UNSPSC no sirve](docs/06-unspsc-no-sirve.md) | Decision tecnica: por que se descarto un filtro que parecia correcto |

Documento consolidado en PDF: [Radar-de-Licitaciones.pdf](Radar-de-Licitaciones.pdf)

### Codigo

```
src/radar.py          motor de deteccion (sin dependencias)
src/requisitos.py     lector de pliegos (necesita pypdf)
src/historico.py      registro y medicion de la precision
historial.jsonl       bitacora append-only de cada corrida
ejemplos/
  pliego_ejemplo.txt    pliego de prueba
  perfil_empresa.json   perfil de empresa de ejemplo
```

### Uso del detector

```bash
python src/radar.py
```

Antes de la primera corrida, editar el bloque `PERFIL` al inicio del archivo:

| Clave | Que define |
|---|---|
| `empresa` | Nombre del cliente |
| `palabras_clave` | Oficios que la empresa sabe hacer |
| `excluir` | Palabras que descartan el proceso |
| `departamentos` | Zonas donde opera |
| `precio_min`, `precio_max` | Rango de contratos en COP |
| `aviso_si_oferentes` | Umbral a partir del cual se avisa de competencia |

Salida: informe por consola y `oportunidades.csv`.

### Uso del lector de pliegos

Esta es la pieza que mas valor tiene: no resume el pliego, responde **"puedo
presentar esto o no"**, y si no, **que me falta**.

```bash
# 1. Instalar la unica dependencia
uv venv .venv
uv pip install --python .venv/Scripts/python.exe pypdf

# 2. Correr
.venv\Scripts\python.exe src/requisitos.py --pliego ejemplos/pliego_ejemplo.txt --empresa ejemplos/perfil_empresa.json
```

Que hace, en orden:

1. Extrae del pliego los requisitos exigidos (habilitantes, certificaciones,
   capacidad financiera, experiencia, garantias, propuesta, ejecucion).
2. Marca cada uno como **critico** si incumplirlo descalifica.
3. Los cruza contra el perfil JSON de la empresa.
4. Para los campos financieros **compara la cifra**, no solo la existencia.
5. Emite veredicto: `POSTULAR`, `REVISAR ANTES DE POSTULAR` o `NO PRESENTAR`.

Salida por consola mas `analisis_pliego.json` para el informe semanal.

### Medir si el filtro acierta

El radar registra solo cada corrida. Lo que falta es saber si lo que sirvio
**sirvio de verdad**, y eso lo dice el cliente. El ciclo es de tres comandos:

```bash
# 1. el radar ya registro la corrida solo, al terminar
python src/radar.py

# 2. el cliente marca cada oportunidad cuando la revisa
python src/historico.py --marcar FNV-001-2021 --util
python src/historico.py --marcar 021-2023 --descartado "fuera de la zona"

# 3. la precision, y sobre todo el rendimiento de cada palabra clave
python src/historico.py --reporte
```

Primera corrida real (28/09/2026), 13 oportunidades de 500 procesos abiertos:

```
palabra        util  desc  pend  precision
acueducto        1     0     1      100%
vivienda         1     1     3       50%
intervencion     0     1     3        0%   <- a quitar del PERFIL
construccion     0     0     1   sin dato
```

`intervencion` con 0% es exactamente el falso positivo que se habia detectado a
ojo. Aqui sale del dato, no de la intuicion. Con 3 o mas casos marcados, el
reporte dice que palabras **aciertan siempre** y cuales **solo generan ruido** y
conviene borrar del `PERFIL`.

El archivo `historial.jsonl` es append-only y va al repositorio, asi que la
bitacora queda versionada y comparable entre semanas.

### El informe semanal

El radar produce un CSV y el lector produce un JSON. Ninguno de los dos se
vende: lo que se vende es el informe que el cliente abre el lunes.

```bash
python src/informe.py --cliente "Constructora Ejemplo S.A.S."
```

Junta las tres salidas (`oportunidades.csv`, `analisis_pliego.json` e
`historial.jsonl`) y arma un PDF de dos paginas con:

- **Resumen** en KPI: cuantas oportunidades, cuantas de alta prioridad, valor en juego.
- **Precision acumulada** del filtro, si ya hay veredictos del cliente.
- **Analisis del pliego** con el veredicto y la lista de lo que falta.
- **Detalle** de las 15 mejores, con codigo de color segun prioridad.
- **Que hacer esta semana**: tres acciones concretas, no una lista de datos.
- Pie con la fuente, la fecha de consulta y el aviso de que no garantiza adjudicacion.

El texto esta escrito en lenguaje de negocio a proposito: el cliente no
comprende datasets ni API, y el informe no menciona ninguno.

#### Requisitos

El PDF se genera con Chrome o Edge en modo headless, que ya viene en Windows.
Si no se encuentra ninguno, el script lo dice y deja el HTML, que se puede
imprimir a mano. Con `--html` ni siquiera intenta el PDF.

Ultima ejecucion real (28/09/2026):

```
Oportunidades: 13    Alta prioridad: 5    Valor en juego: $ 1.103.709.212
```

#### Nota sobre el PDF y la distribucion

El informe lleva en el pie la fecha de consulta y la advertencia de que no
garantiza adjudicacion. Eso no es decoracion: es lo que separa un servicio de
informacion de una promesa que despues genera una reclamacion.

#### Perfiles de empresa

El perfil es lo que se calibra por cliente. Copiar `ejemplos/perfil_empresa.json`:

| Regla | Significado |
|---|---|
| `true`, o un numero > 0, o texto no vacio | La empresa **lo tiene** |
| `false`, `0`, `""`, `"no"`, `"pendiente"` | **No lo tiene** |
| Campo **ausente** | `NO SE SABE`: hay que confirmarlo antes de decidir |

Un campo ausente nunca se reporta como cumplido. Es deliberado: es preferible
marcar `NO SE SABE` que afirmar un `CUMPLE` que descalifica en la apertura.

#### Limitaciones conocidas

- **Un pliego escaneado no tiene capa de texto.** El lector lo detecta y avisa:
  necesita OCR antes. No devuelve texto vacio en silencio.
- **El indice de liquidez si se compara** contra la cifra del pliego.
- **El patrimonio y los ingresos solo se comparan si el pliego escribe la cifra en
  numeros.** Si la redacta con palabras ("tres mil millones"), el resultado es
  `NO SE SABE` y hay que compararlo a mano. Es preferible asi que suponer que
  cumple.
- La biblioteca de requisitos cubre lo habitual en obra publica. Un pliego con
  redaccion muy atypica se detecta como "sin requisitos"; la solucion es agregar
  el patron a `REQUISITOS` en el propio archivo.

### Verificacion

La ultima ejecucion real (25/09/2026) con un perfil de constructora:

```
500 procesos abiertos  ->  13 oportunidades  ->  oportunidades.csv
```

### Estado tecnico

| Funciona | Pendiente |
|---|---|
| Descarga de procesos abiertos | Cobertura completa (hoy 500 por corrida) |
| Filtro por sector, zona y presupuesto | Filtro por categoria UNSPSC como condicion obligatoria |
| Puntaje con razones explicitas | Competencia real (el campo llega en 0) |
| Exportacion CSV y enlace al pliego | Limpieza de textos sucios con LLM |
| Referencia de precios | Persistencia del historico |
| **Lectura del pliego y extraccion de requisitos** | OCR para pliegos escaneados |
| **Cruce contra el perfil y veredicto** | Comparar patrimonio cuando el pliego lo escribe con palabras |
| **Comparacion de cifras financieras** | Catalogar mas patrones de requisitos |
| **Deteccion de PDF sin capa de texto** | Descarga automatica del pliego desde SECOP |

### Riesgo tecnico principal

El campo `conteo_de_respuestas_a_ofertas` llega en **0** mientras el proceso esta
abierto, asi que la regla de "poca competencia" no discrimina. Esta resuelto en el
motor pero **desactivado** de forma consciente hasta tener una fuente real de
competencia.

### El pliego no se puede bajar de SECOP

`community.secop.gov.co` resetea la conexion a clientes que no son navegador.
Medido el 27/09/2026 por tres vias distintas (Node `fetch`, `webfetch` y
`curl.exe`): las tres reciben *connection reset*. Por eso el lector de pliegos
trabaja sobre el archivo que el cliente ya descargo, y no intenta descargarlo.

### Fuente de datos

Dataset publico `p6dx-8zbt` — "SECOP II - Procesos de Contratacion", en
`datos.gov.co`. No requiere API key.

> **Advertencia documentada:** el dataset `w3du-xuur` parece equivalente pero
> **no sirve**: su campo `objeto_a_contratar` viene como `"no definido"` en todos los
> procesos abiertos. Ver seccion 3.2 de la documentacion tecnica.
