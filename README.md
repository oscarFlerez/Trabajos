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

Documento consolidado en PDF: [Radar-de-Licitaciones.pdf](Radar-de-Licitaciones.pdf)

### Codigo

```
src/radar.py
```

Sin dependencias externas. Solo biblioteca estandar de Python.

### Uso

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
| — | Lectura del pliego y extraccion de requisitos |

### Riesgo tecnico principal

El campo `conteo_de_respuestas_a_ofertas` llega en **0** mientras el proceso esta
abierto, asi que la regla de "poca competencia" no discrimina. Esta resuelto en el
motor pero **desactivado** de forma consciente hasta tener una fuente real de
competencia.

### Fuente de datos

Dataset publico `p6dx-8zbt` — "SECOP II - Procesos de Contratacion", en
`datos.gov.co`. No requiere API key.

> **Advertencia documentada:** el dataset `w3du-xuur` parece equivalente pero
> **no sirve**: su campo `objeto_a_contratar` viene como `"no definido"` en todos los
> procesos abiertos. Ver seccion 3.2 de la documentacion tecnica.
