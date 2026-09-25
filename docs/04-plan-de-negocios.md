# 4. Plan de negocios

## 4.1 Que se vende

No se vende un agente de inteligencia artificial. Se vende **dejar de perder
licitaciones que no se pueden ganar**.

La distincion importa porque el cliente final no sabe lo que es un agente, y porque
"IA" suena a proyecto caro, lento y riesgoso. Lo que suena a negocio es una frase
con numeros: **"te digo cuales puedes ganar y a cuanto le esta pagando tu
competencia"**.

## 4.2 Las tres capas del valor

| Capa | Lo que hace | Por que se paga |
|---|---|---|
| **Filtro** | Descarta lo que no puedes ganar | Ahorra el tiempo del equipo comercial, que es el recurso mas caro |
| **Puntaje** | Ordena lo que si por probabilidad | Convierte Unlimited en una lista corta y accionable |
| **Benchmark** | Precio que pago la competencia, por municipio y objeto | Permite definir la oferta de forma estrategica |

La tercera capa es la que nadie mas ofrece, y la que justifica un precio sostenido
en vez de un proyecto de una vez.

## 4.3 Precios

| Plan | Precio COP | Que incluye |
|---|---|---|
| **Pilotaje** | $900.000 (unica vez) | Radar afinado al perfil del cliente + 30 dias de hallazgos + una sesion de capacitacion |
| **Mensual** | $450.000 / mes | Informe semanal, hasta 3 sectores y 5 departamentos, benchmark de competencia |
| **Por oportunidad** | $180.000 por proceso | Solo las oportunidades que el cliente decida pursuit, sin mensualidad |

La estructura es de **servicio empaquetado**, no cobro por horas. Se cobra por
resultado entregado, que es lo unico que el cliente puede comparar.

## 4.4 Economia unitaria

Con un solo cliente en plan mensual:

| Concepto | Valor COP |
|---|---|
| Ingreso mensual | 450.000 |
| Costo de API (Socrata, publica) | 0 |
| Costo de inferencia (LLM) | ~15.000 (estimado, tokens de clasificacion) |
| Tiempo de operacion | ~4 horas/mes |
| Margen bruto estimado | ~96% antes de mano de obra |

El margen es alto porque el insumo principal —los datos— es publico y gratuito. El
costo real es el tiempo de calibrate el perfil de cada cliente, que es donde entra
el criterio que después se cobra.

## 4.5 Segmento objetivo

**Primario.** Constructoras y empresas de ingenieria de 20 a 200 empleados, con
cartera de obra publica y sin area de licitaciones dedicada. Para ellas, leer 200
paginas de pliego por proceso es un costo de oportunidad real.

**Secundario.** Consultoras de ingenieria, empresas de acueducto y alcantarillado,
intermediarios de subcontractistas, y consultores ambientales que conformen equipos
de postulacion.

**Excluido deliberadamente.** Grandes constructoras con area de licitaciones propia:
tienen el equipo, no te compran.

## 4.6 El mensaje de venta

> Don Fernando, esta semana encontre 6 procesos abiertos de construccion en
> Antioquia y Cundinamarca, por $2.300 millones en total. Tres los esta llevando una
> empresa de Bogota y una de Pereira: le paso a quien se los adjudicaron y por
> cuanto. Dos no tienen ninguna oferta recibida todavia. Le armamos la postulacion a
> esas dos?

El mensaje abre con cifras concretas del negocio del cliente, no con tecnologia.
Cierra con una accion, no con una pregunta abierta.

## 4.7 Por que es dificil de copiar

| Barrera | Detalle |
|---|---|
| **Conocimiento del dato** | Saber que `p6dx-8zbt` sirve y `w3du-xuur` no, y que `estado_de_apertura_del_proceso` evita interpretar cadenas de texto |
| **Calibracion por cliente** | El perfil de cada empresa se ajusta con la experiencia de los anteriores. No es codigo, es tiempo |
| **Historico de adjudicaciones** | El benchmark de precio se construye con meses de datos acumulados |
| **Relacion, no software** | El cliente compra que alguien se haga cargo |

El codigo, por si solo, no es la barrera. Lo que no se copia en una tarde es haber
descubierto que el dataset que todos usan no tiene el texto del objeto.

## 4.8 Via de entrada sugerida

1. **Prueba sin costo.** Correr el motor con un perfil generico de construccion y
   entregar 5 oportunidades reales al primer prospecto. Eso demuestra que el
   producto funciona antes de cobrar un peso.
2. **Piloto pagado.** $900.000, con el perfil afinado a esa empresa concreta.
3. **Suscripcion.** Cuando el piloto produce al menos una postulacion presentada, se
   convierte en mensual.

El paso 3 es el unico que importa: el cliente no compra el software, compra que el
software le genero una postulacion que presento.
