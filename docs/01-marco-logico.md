# 1. Marco logico del proyecto

**Nombre:** Radar de Licitaciones
**Version:** 1.0
**Fecha:** 25 de septiembre de 2026
**Pais de operacion inicial:** Colombia

---

## 1.1 Problema

Las empresas constructoras y de ingenieria que viven del sector publico en Colombia
pierden oportunidades de licitacion por tres motivos que se repiten en cada empresa:

1. **No se enteran a tiempo.** Los procesos se publican en SECOP y se cierran en
   plazos cortos. Quien no esta mirando a diario, se entera cuando ya termino el
   plazo de presentacion.
2. **Leen procesos que no pueden ganar.** El costo de leer y evaluar un pliego de
   150 a 200 paginas es de horas de un profesional. Sin un filtro previo, se gastan
   esas horas en procesos que despues se descartan por falta de certificacion, de
   presupuesto o de EXPERIiencia.
3. **No saben a cuanto licitar.** No existe referenciainternal de lo que la
   competencia cobro por obras similares en su propia region. Terminan licitando a
   ciegas, o Tugurmente, copiando el precio de un processo antiguo.

El resultado agregado es que el equipo comercial se convierte en un filtro manual de
oportunidades, en lugar de un mecanismo de postulacion. Es tiempo caro de un
profesional cualificado que no participa en ninguna postulacion.

## 1.2 Analisis de causa

| Causa raiz | Manifestacion | Es solucionable con datos publicos |
|---|---|---|
| Sin monitoreo sistematico | Depende de que alguien se acuerde de revisar | Si: consulta automatica |
| Sin filtro de pertinencia | Se evalua todo | Si: laEntidad, el objeto y el presupuesto estan publicados |
| Sin referencia de precios | Licitan por intuicion | Si: el valor adjudicado es publico y historico |
| El volumen aplasta al analysta | 500+ procesos abiertos a la vez | Parcialmente: la priorizacion automatica |

La cuarta causa es la unica que no se resuelve por completo con datos: la
decision de a que proceso conviene destinar recursos humanos sigue siendo una decision del cliente.
Por eso el producto ordena y descarta, pero no decide.

## 1.3 Objetivo general

Incrementar la tasa de participacion efectiva en licitaciones publicas por parte de
las empresas constructoras cliente, delivered mediante un sistema que detecta,
prioriza y descarta oportunidades de forma automatica y sostenida.

## 1.4 Objetivos especificos

1. Detectar el **100%** de los procesos de licitacion publicados en la region
   objetivo dentro de las **24 horas** siguientes a su publicacion.
2. Entregar al cliente una lista de **maximo 15 oportunidades priorizadas** por
   corrida, con puntaje de pertinencia y explicacion del puntaje.
3. Reducir el tiempo de evaluacion inicial de un proceso de **4 horas a 15 minutos**.
4. Proporcionar referencia de precio de las **ultimas 12 adjudicaciones** del mismo
   sector y region, para sustentar la decision de oferzar.
5. Alcanzar una precision de filtro de **85% o mas**, medida como proportion de
   oportunidades entregadas que el cliente califico como pertinente.

## 1.5 Metas

| Meta | Indicador | Valor objetivo | Plazo | Linea base |
|---|---|---|---|---|
| M-1 | Tiempo de entrega del informe | Menor a 30 minutos desde la publicacion | 3 meses | 4 dias (revision manual) |
| M-2 | Oportunidades pertinentes entregadas por mes | 20 o mas | 6 meses | 3 (estimacion del cliente) |
| M-3 | Postulaciones presentadas originadas en el servicio | 1 por cliente por trimestre | 12 meses | 0 |
| M-4 | Tasa de renovacion de clientes | 70% de la base al mes 12 | 12 meses | N/A |
| M-5 | precision del filtro | 85% o mas | 6 meses | N/A (medible desde el inicio) |

La linea base de M-2 y M-3 debe confirmarse en la reunion de arranque con cada
cliente: sin ella, la mejora no es demostrable.

## 1.6 Indicadores

| Codigo | Indicador | Formula | Meta | Frecuencia |
|---|---|---|---|---|
| IND-01 | Cobertura de deteccion | Procesos detectados / procesos publicados en el periodo | 100% | Semanal |
| IND-02 | Latencia de deteccion | Hora de entrega - hora de publicacion | < 24 h | Semanal |
| IND-03 | Precision del filtro | Oportunidades marcadas pertinentes / oportunidades entregadas | >= 85% | Mensual |
| IND-04 | Tasa de descarte util | Procesos descartados que el cliente confirma descartables / total descartado | >= 90% | Mensual |
| IND-05 | Tiempo de evaluacion | Tiempo medio del cliente desde recibir el informe hasta decidir | <= 15 min | Mensual |
| IND-06 | Postulaciones viables | Informes que derivaron en una postulacion presentada | >= 1 por trimestre | Trimestral |
| IND-07 | Ingreso recurrente | Suscripciones activas x precio mensual | Segun plan | Mensual |

IND-03 e IND-04 son los unicos que miden el valor real. Los demas miden operacion.
La diferencia importa: un producto que entrega 30 oportunidades y el cliente
considera 3 pertinentes no sirve, aunque haya "mucho volumen".

## 1.7 Supuestos

- El portal de datos abiertos de datos.gov.co mantendra la disponibilidad del
  dataset `p6dx-8zbt` y la calidad actual de sus campos.
- El cliente mantiene actualizado su perfil (certificaciones, zona, rango).
- La empresa cuenta al menos con una persona que decide sobre presentacion.
- Los procesos interadministrativos, que tienen menos detalle, no son el canal
  principal del cliente.

## 1.8 Restricciones

- **Presupuesto inicial limitado.** No hay inversion en software propietario: todo
  corre sobre datos publicos y herramientas gratuitas o de bajo costo.
- **Un solo cliente a la vez.** El servicio es artesanal en su fase de calibracion.
- **Sin acceso a informacion privada.** Todo lo que el sistema sabe es publico. No
  se promise informacion que solo existe dentro de la empresa.
- **Sin garantia de adjudicacion.** El sistema entrega priorizacion, no resultados.
  Esta distincion debe estar escrita en el contrato.
