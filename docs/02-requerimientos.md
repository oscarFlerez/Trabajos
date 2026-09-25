# 2. Requerimientos y requisitos

> La estructura de la seccion 2.1 (codificacion RF-01..RF-12 con MoSCoW) se tomo de una
> propuesta generada con `gemma-4-26b-a4b-it`. El contenido fue reescrito y verificado
> contra la ejecucion real del motor.

---

## 2.1 Requerimientos funcionales

Prioridad segun MoSCoW: **M** = must (sin esto no hay producto), **S** = should,
**C** = could, **W** = wont (fuera de alcance en la version 1).

| ID | Nombre | Descripcion | Prioridad |
|---|---|---|---|
| RF-01 | Extraccion de procesos | Consultar `p6dx-8zbt` y traer procesos con `estado_de_apertura_del_proceso = 'Abierto'` | **M** |
| RF-02 | Perfil de cliente | Configurar por cliente: sector (palabras clave + categoria UNSPSC), departamentos, rango de presupuesto | **M** |
| RF-03 | Calculo de puntaje | Puntaje 0-100 por sector (60), zona (20) y presupuesto (20), con penalizaciones | **M** |
| RF-04 | Explicacion del puntaje | Cada oportunidad incluye las razones que produjeron su puntaje | **M** |
| RF-05 | Enlace al proceso | Incluir `urlproceso` para llevar al cliente directo al pliego | **M** |
| RF-06 | Exportacion CSV | Archivo `oportunidades.csv` con codificacion UTF-8 con BOM, abrir en Excel sin perder acentos | **M** |
| RF-07 | Filtro por modalidad | Separar licitacion publica, minima cuantia y contratacion directa, que compiten distinto | **S** |
| RF-08 | Informe de descartes | Listar los descartados con la causa, para que el cliente verifique que no se le oculto nada | **S** |
| RF-09 | Referencia de precios | Minimo, mediana y maximo de adjudicaciones recientes del mismo sector y zona | **S** |
| RF-10 | Alerta periodica | Ejecucion automatica semanal y envio del informe | **S** |
| RF-11 | Limpieza de texto con LLM | Normalizar objetos sucios y clasificar sector cuando el texto es ambiguo | **S** |
| RF-12 | Historico persistido | Guardar corridas para medir precision y construir el benchmark | **C** |
| RF-13 | Dashboard web | Interfaz visual para el cliente | **W** (v2) |
| RF-14 | Integracion con CRM | Envio directo a HubSpot o Pipedrive | **W** (v2) |

RF-13 y RF-14 estan fuera de alcance a proposito. El cliente actual abre un archivo y
eso es suficiente; una interfaz es trabajo de mantenimiento que no se justifica hasta
tener varios clientes.

## 2.2 Requerimientos no funcionales

| ID | Categoria | Requisito | Metrica de cumplimiento |
|---|---|---|---|
| RNF-01 | Rendimiento | Correr el barrido completo y generar el informe | < 5 minutos para 500 procesos |
| RNF-02 | Rendimiento | Latencia de consulta a Socrata | < 15 s por llamada; usar `$limit` y `$select` para reducir la carga |
| RNF-03 | Disponibilidad | Tolerar caida del portal sin perder el cliente | Reintento con espera creciente y ultimo informe guardado siempre disponible |
| RNF-04 | Seguridad | No exponer credenciales de API en el codigo | Claves por variable de entorno, nunca en el repositorio |
| RNF-05 | Seguridad | Datos de cliente aislados | Un perfil por archivo; sin datos personales de terceros |
| RNF-06 | Mantenibilidad | Cero dependencias externas | Solo biblioteca estandar de Python, para que corra en cualquier equipo |
| RNF-07 | Calidad de datos | Validar campos nulos y sentinel | Tratar `"No Definido"`, `"no definido"` y vacios como ausentes, no como texto |
| RNF-08 | Trazabilidad | Registrar de cada corrida | Fecha, procesos bajados, procesos entregados y URL base consultada |
| RNF-09 | Escalabilidad | Soportar mas clientes | El perfil ya es un parametro; el costo marginal por cliente es bajo |
| RNF-10 | Costo | Mantener el costo variable cerca de cero | API de datos gratis; unica variable, la inferencia del modelo |

RNF-07 tiene un caso concreto que ya costo una iteracion: `departamento_entidad` llega
como `"No Definido"` en parte de los registros. Si se compara contra una lista de
departamentos sin filtrar ese sentinel, el ajuste geografico nunca se concede.

## 2.3 Requisitos tecnicos

| Elemento | Especificacion |
|---|---|
| Lenguaje | Python 3.11 o superior |
| Dependencias | **Ninguna externa.** `urllib`, `csv`, `json`, `datetime` |
| Fuente de datos | `https://www.datos.gov.co/resource/p6dx-8zbt.json` (Socrata / SoQL) |
| Autenticacion | Ninguna. El dataset es publico |
| Modelo de lenguaje | Gemini (`gemini-2.5-flash`) o Gemma, invocado por API |
| Salidas | CSV, Markdown, PDF |
| Persistencia | Archivos locales versionables; `git` para el historico |
| Plataforma objetivo | Windows, Linux o macOS, sin instalacion |

La decision de no usar `pandas` ni `requests` es deliberada: elimina el paso de crear
un entorno virtual, que es donde mas se abandona un proyecto pequeno.

## 2.4 Requisitos de negocio

| ID | Requisito |
|---|---|
| RN-01 | Alcance del contrato: el servicio entrega priorizacion, **no** garantiza adjudicacion |
| RN-02 | El cliente es responsable de la decision de presentar y del contenido de la postulacion |
| RN-03 | El cliente mantiene actualizado su perfil (certificaciones, zona, rango) |
| RN-04 | Funcionamiento de la fuente: si datos.gov.co cambia el schema, el servicio se pausa y se notifica |
| RN-05 | Formato de entrega: informe semanal en dia acordado |

## 2.5 Requisitos legales y de cumplimiento

| ID | Requisito | Fundamento |
|---|---|---|
| RL-01 | Uso exclusivo de datos publicos, sin scrapeo de sitios que lo prohban | Los datos de SECOP en datos.gov.co son publicos y de dominio publico |
| RL-02 | No incluir datos personales de personas naturales en los informes | Ley 1581 de 2012 (Habeas Data) |
| RL-03 | Publicar el origen y la fecha de cada dato usado | Ley 1712 de 2014 (transparencia y acceso a la informacion) |
| RL-04 | Consentimiento expreso del cliente para tratar su informacion comercial | Ley 1581 de 2012 |
| RL-05 | No usar el servicio para identificar ni contactar personas naturales | Proteccion de datos personales |
| RL-06 | Conservar trazabilidad de que dato se consulto y cuando | Permite auditar y defender el origen de una cifra |

**Sobre el tratamiento de personas naturales.** El dataset contiene campos como
`nombre_del_proveedor` y `documento_proveedor`, que identifican a personas. El
servicio **no los expone al cliente**: se usan solo como referencia agregada de
"quien compite" y se omiten del informe. Esta exclusion es deliberada y debe
mantenerse aunque parezca perdida de informacion.

Un segundo punto, relacionado con la reputacion: los campos del adjudicatario a
veces traen errores de transcripcion. Publicar nombres propios a partir de datos
sucios es una via directa paraWidget un error judicial o comercial, asi que el
informe debe mostrar el valor **tal como aparece en la fuente**, con la fecha de
consulta, y nunca "corregirlo" por cuenta propia.

## 2.6 Fuera de alcance (version 1)

- Presentacion automatica de la postulacion.
- Lectura y analisis del pliego en PDF.
- Integracion con SECOP para inscribedjarse como proveedor.
- Prediccion probabilistica de adjudicacion.
- Aplicacion movil.
