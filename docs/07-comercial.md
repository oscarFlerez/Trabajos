# Cómo vender el Radar de Licitaciones

Este documento es para vender, no para explicar la programación. Todo lo que
afirma aquí está medido sobre el portal de datos del Estado. La fecha de cada
medición está escrita, porque un dato sin fecha es una opinión.

---

## El problema, en una frase

SECOP II publica **8.086.821 procesos marcados "Abierto"**. En ese número hay
de todo: papelería, Hire, contratos de transporte, y también las obras que de
verdad le interesan. Buscar a mano entre millones de filas no es lento: es
**imposible**, y por eso casi nadie lo hace.

Y aquí está el detalle que hace el problema más grave de lo que parece: el
portal marca un proceso como "Abierto" aunque lleva **años** sin poder
licitarse. De los 8.086.821 procesos "Abierto", **4.907.994 —el 60,7%— fueron
publicados antes de 2025**. Ese es el número que asusta a un jefe, y está
contado sobre el total, no estimado.

En una muestra de 5.000 procesos abiertos, y filtrando solo los que son del
sector construcción, el número sube: **73% tiene más de un año publicado**.
Eso es una muestra, no el total, y por eso el 60,7% es el que va en la hoja
impresa y el 73% solo se usa para mostrar el embudo.

---

## Qué hace la herramienta

Cuatro pasos, en el navegador del usuario, sin instalar nada:

1. **El cliente pone su perfil**: qué sabe hacer, en qué departamentos, entre
   qué presupuesto.
2. Se descargan los procesos abiertos de SECOP.
3. Se descarta todo lo que no encaja, con la razón de cada descarte a la vista.
4. Lo que queda son **7 oportunidades en una tarde**, de miles de filas.

La página no es un buscador. Aplica el perfil del cliente y muestra lo que
sobrevive. Si no sale nada, la herramienta **dice por qué**, en vez de
mostrar una lista vacía sin explicación.

---

## Los tres argumentos que sostienen la venta

### 1. El filtro es honesto, no una caja negra

Cada oportunidad viene con el motivo: *"sector: vivienda; zona objetivo;
presupuesto encaja; publicado hace 16 días"*. Y la herramienta tiene un
embudo que enseña cuántos descartó cada regla:

```
Procesos abiertos descargados :    5.000
Del sector de la empresa       :     163   (3,3% de lo descargado)
Publicados hace mas de 1 ano   :     119   (73,0%)  [veto]
Mas de 90 dias (penaliza -30) :      28   (63,6%)
Presupuesto bajo el minimo     :      11   (68,8%)
Con puntaje >= 40              :       7
```

Eso es lo que **ninguna otra herramienta muestra**. Un consultor puede decir
"revisé 200 procesos"; esto puede mostrarle al cliente exactamente cuáles y
cuántos, y por qué el resto se fue.

### 2. Descarta los falsos positivos, que es donde se pierden las oportunidades

Medido sobre el mismo perfil, los errores que esta herramienta corrige:

| Lo que entraba mal | Por qué entraba | Qué hace |
|---|---|---|
| *TRANSFERENCIA DE RECURSOS… PARA LOS SUBSIDIOS DE ACUEDUCTO* — $325 M | el texto habla de acueducto | Se descarta: es dinero, no obra |
| *PRESTACIÓN DE SERVICIOS PROFESIONALES DE ODONTOLOGIA* — 50/100 | "intervención" dental | Se descarta: una consulta dental no es una intervención de obra |

Que aparezca odontología en una lista de obras de construcción no daña el
producto: **lo termina**. Un cliente que encuentra basura deja de creer en el
resto.

### 3. Cuesta cero y no pide cuentas ni tarjetas

La página es estática. No hay servidor, ni base de datos, ni claves de API.
El usuario abre un enlace y funciona. El cliente **nunca tiene que
registrarse ni dar un dato**, ni para mirar ni para probar. Y la empresa no
puede perder acceso a lo que el usuario vio, porque no hay nada guardado en
ningún lado salvo en su propio equipo.

Para el cliente esto importa más de lo que parece: si un consultor le pide
un usuario y una contraseña, se lo piensa dos veces.

---

## Cómo decirlo, literalmente

> "El Estado publica 8 millones de procesos marcados como abiertos. De los que
> son de su sector, siete de cada diez tienen más de un año publicados, o sea
> que probablemente ya no se pueden licitar. Revisar eso a mano es lo que nadie
> hace. Esta herramienta le deja poner su perfil una vez, y le devuelve las
> oportunidades que de verdad le sirven, con el motivo de cada una y con el
> número de lo que descartó y por qué. No hay que registrarse, no hay que
> pagar y no hay que confiar en un dato de servidor."

Y si preguntan *"¿usted de dónde sacó esos datos?"*:

> "De la plataforma de datos abiertos del Estado, la misma que usa la
> transparencia. Está todo medido, y las cifras están en esta hoja."

---

## Las cinco preguntas que siempre hacen

**"¿Y no me va a llegar una oportunidad que no vi?"**
Sí. El filtro se configura con el perfil del cliente, y la palabra clave es
suyo. Si sale algo que no le sirve, se agrega una palabra; si falta algo, se
quita una restricción. La herramienta enseña el embudo para que se vea qué
está descartando de más.

**"¿Y si me pierdo una oportunidad urgente?"**
El segundo problema: SECOP no publica fecha de cierre, y el portal marca como
"abierto" procesos viejísimos. La herramienta no puede adivinar el plazo, así
que **avisa**: marca en rojo las que llevan mucho, y dice que verifique en
SECOP. No se hace la loca de prometer que están vigentes.

**"¿Esto reemplaza a un abogado?"**
No, y conviene decirlo. Ordena y filtra. La revisión contractual es de otra
persona.

**"¿Y si los datos del Estado cambian?"**
Están en formato abierto y se actualizan a diario. Si el portal cambia el
formato, se ajusta la herramienta: es texto público, no un servicio ajeno.

**"¿Quién ve lo que yo busco?"**
Nadie. Es una página sin servidor. El historial se guarda en el navegador de
cada quien la usa, en su propio equipo.

---

## El precio

Esto es una decisión del dueño, no de la herramienta. Lo que sí se puede
apoyar con datos es el cálculo:

- 7 oportunidades en una tarde de trabajo, no en meses.
- Una constructora mediana en Colombia pierde entre 3 y 8 oportunidades al
  año por no enterarse a tiempo. **Una sola vez** justifican el año.
- El cliente paga por resultado, no por licencia: se cobra una puesta en
  marcha del perfil más un abono mensual corto, y si en un mes no hay
  oportunidades que sirvan, se devuelve.

**Ese último punto es el que cierra la venta.** En una sesión de prueba de un
mes, con el perfil bien cargado, el cliente ve si sirve o no. No hay
compromiso a largo plazo y no hay que confiar en promesas.

---

## Qué llevar a la reunión

1. **La página abierta y funcionando**, con el perfil ya cargado con los datos
   reales de ese cliente. No una demo genérica: la suya.
2. **Esta hoja impresa**, con los números del embudo de su sector.
3. **Un ejemplo de la tarjeta**: una oportunidad con su motivo, su fecha y su
   valor.
4. **No prometer la fecha de cierre.** Si la piden, decir que SECOP no la
   publica y que por eso la herramienta avisa en vez de afirmar.

Y nada más. Si tiene que explicar más de diez minutos, es que no la entendió.

---

## Nota sobre lo que todavía no tiene

Para no prometer nada que la herramienta no haga hoy:

- **No descarga los pliegos.** SECOP corta la conexión al pedir el PDF. El
  cliente lo baja con un clic desde la ficha.
- **El historial es por navegador.** Lo que el usuario marca en el computador
  no aparece en el celular. Es un límite consciente: no hay servidor justamente
  para que no haya datos de nadie guardados en ningún lado.
- **El puntaje es un orden de revisión, no una probabilidad.** Se calcula con
  reglas que el cliente puede ver y ajustar. No es un modelo que adivina.