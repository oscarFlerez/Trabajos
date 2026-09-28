# 6. El filtro por categoria UNSPSC no sirve en este dataset

> Documento de decision tecnica. Registra un camino que se descarto, y por que.
> Se escribe porque el filtro es intuitivamente correcto y cualquiera lo
> implementaria sin medirlo.

## 6.1 La hipotesis

El campo `codigo_principal_de_categoria` trae un codigo UNSPSC. La idea era usar
ese codigo como filtro **obligatorio** de sector, en lugar de depender del
matching por subcadena, que ya habiamos visto producir falsos positivos:

```
"intervencion" matchea tanto "apoyo tecnico en obra"
                  como "intervenciones de coordinacion" (enfermeria)
```

Un codigo normalizado habria resuelto eso. Ademas, 618 codigos distintos con
jerarquia (segmento, division, clase, grupo) permitirian decir "construccion" en
vez de enumerar sinonimos.

## 6.2 La medicion

**Muestra de 3000 procesos abiertos.** De los cuales:

| Medida | Valor |
|---|---|
| Procesos con codigo UNSPSC | 3000 (ninguno vacio) |
| Codigos distintos | 618 |
| Sentinel `UNSPECIFIED` | 23 (0,8%) |
| Segmento 80 | 1788 (**59,6%**) |
| Segmento 85 | 321 (10,7%) |

A primera vista parecia razonable: el 30% de los procesos estan en un solo codigo.
(`V1.80111600`).

## 6.3 La prueba que lo tumbo

Se tomo el subconjunto de procesos cuyo objeto **si** es obra civil, y se miro que
codigos tienen:

| Medida | Valor |
|---|---|
| Procesos de obra civil | 500 |
| Codigos UNSPSC distintos entre ellos | **156** |
| Codigo mas frecuente | cubre solo el **14%** |
| Ese mismo codigo en todos los procesos abiertos | **30%** |

Ademas, al leer el texto de los codigos mas frecuentes, ninguno corresponde a
construccion:

| Codigo | Frecuencia | Texto real que accompany |
|---|---|---|
| `V1.80111600` | 30% | "PRESTACION DE SERVICIOS DE APOYO A LA GESTION" |
| `V1.80111500` | — | "apoyo a la gestion tecnica y administrativa" |
| `V1.85101600` | — | "APOYO A LA GESTION COMO AUXILIAR ENFERMERIA EN AMBULANCIA" |
| `V1.80161500` | — | "PRESTAR LOS SERVICIOS PROFESIONALES A LA UNIDAD DE SERVICIOS PENITENCIARIOS" |

El codigo dominante agrupa **servicios administrativos de apoyo**, no obra
civil. Y un proceso de obra civil puede caer en 156 codigos distintos, ninguno
exclusivo.

## 6.4 Conclusion

**El campo UNSPSC de este dataset no discrimina el sector del objeto.** Almost
cualquier filtro por el habria dejado pasar administrative, personnal y
sanitario, que es precisamente el ruido que se queria eliminar.

Implementarlo habria producido la peor combinacion posible: **sensacion de rigor
sin filtrado real**. El cliente habria visto un filtro "por categoria
normalizada" y followed creyendo que el problema estaba resuelto, cuando el
problema seguia intacto. Ademas habria eliminado de paso procesos legitimos de
construccion, porque su codigo no es el que uno esperaria.

## 6.5 Que se hace en su lugar

La precision se mide, no se supone. Ese es el trabajo de `src/historico.py`:

1. El radar registra automaticamente cada oportunidad que entrega.
2. El cliente marca despues cada una como **util** o **descartada**, con motivo.
3. El reporte calcula la precision real y, sobre todo, **el rendimiento de cada
   palabra clave**.

La primera corrida ya dio la senal que el filtro UNSPSC no habria producido:

```
palabra        util  desc  pend  precision
acueducto        1     0     1      100%
vivienda         1     1     3       50%
intervencion     0     1     3        0%   <- a quitar del PERFIL
construccion     0     0     1   sin dato
```

`intervencion` con 0% es, empiricamente, la palabra que habria que eliminar del
perfil. Eso no se deduce leyendo el dataset: se deduce despues de que el cliente
diga que sirvio y que no.

## 6.6 Regla general

Antes de agregar un filtro por un campo de un dataset de terceros, hay que
medir su poder de discriminacion:

1. Que codigos tienen los elementos que **si** quiero?
2. Que codigos tienen los que **no** quiero?
3. Se solapan? Si se solapan, el campo no sirve y agrega ruido confuso.

Este filtro habria salido del "parece bien, implementemoslo". Tres llamadas a la API
lo evitaron.
