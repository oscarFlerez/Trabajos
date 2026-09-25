# 5. Cronograma, presupuesto y riesgos

## 5.1 Cronograma

El proyecto se ejecuta en fases. Cada fase termina con algo que el cliente puede ver.

| Fase | Duracion | Entregable | Criterio de cierre |
|---|---|---|---|
| **F0. Descubrimiento** | 1 semana | Perfil del cliente, sectores, zonas, rango de presupuesto | El cliente firma el perfil por escrito |
| **F1. Motor v1** | 1 semana | `radar.py` corriendo, informe en consola y CSV | 100 procesos abiertos descargados sin error |
| **F2. Calibracion** | 2 semanas | Perfil afinado con los descartes del cliente | Precision (IND-03) >= 70% |
| **F3. Piloto** | 4 semanas | Informe semanal enviado, benchmark de precios | Al menos 1 oportunidad validada por el cliente |
| **F4. Consolidacion** | 2 semanas | Capa de LLM para limpieza y clasificacion | Menos de 2 falsos positivos por semana |
| **F5. Producto** | Continuo | Mejora de cobertura, paginacion, historico | Precision >= 85% sostenido |

**F0 a F2 suman cuatro semanas antes de cobrar la primera mensualidad.** Es la
inversion inicial del proveedor, no del cliente. Por eso el pilotaje se cobra por
adelantado: cubre F0, F1 y parte de F2.

## 5.2 Presupuesto de arranque

Costos del proyecto, no del cliente:

| Concepto | Valor COP | Observacion |
|---|---|---|
| Dominio y correo profesional | 0 | Se usa Gmail al inicio |
| Infraestructura de ejecucion | 0 | Script local; el portal de datos es publico |
| Consumo de API de LLM | ~40.000 | Calibracion y limpieza de texto |
| Dominio `.com` (opcional) | 45.000 anual | Solo si se empieza a marcar la marca |
| Tiempo propio | 4 semanas | No|es facturado al cliente en esta fase |
| **Total en efectivo** | **~85.000 COP** | |

El presupuesto de arranque es deliberadamente bajo. El riesgo real del proyecto no
es economico, es de tiempo: cuatro semanas de trabajo antes del primer ingreso.

### inversion por cliente (fase de piloto)

| Concepto | Valor COP |
|---|---|
| Pilotaje (F0-F2) | 900.000 |
| Mensualidad (F3-F5) | 450.000 / mes |

## 5.3 Punto de equilibrio

Con un coste operativo estimado de 350.000 COP/mes (tiempo de calibracion y soporte)
y un precio de 450.000:

```
Clientes para equilibrio = 350.000 / 450.000 = 0,78  ->  1 cliente
```

El equilibrio lo alcanza **un solo cliente**. Eso significa que el riesgo del negocio
no es economico sino comercial: si no se vende, no hay proyecto. Y tambien significa
que el segundo cliente es casi margen completo.

## 5.4 Riesgos

| ID | Riesgo | Probabilidad | Impacto | Mitigacion | Senal temprana |
|---|---|---|---|---|---|
| R-01 | El cliente no compra porque "no es IA, es un filtro" | Media | Alto | Enfatizar el benchmark de precios, que es informacion que el cliente no tiene | Rechaza el piloto sin preguntas |
| R-02 | El perfil del cliente se calibra mal y llegan falsos positivos | **Alta** (ya ocurrio) | Medio | Mostrar tambien los descartes con su causa; el cliente corrige el perfil | Queja de "esto no me sirve" |
| R-03 | El campo de competencia sigue en 0 y no se puede medir | **Alta** (ya ocurrio) | Medio | Calcular competencia historica por entidad y objeto | Todas las oportunidades con 0 oferentes |
| R-04 | datos.gov.co cambia el schema o cae | Baja | **Alto** | Descargar copia local diaria; el motor debe funcionar sin conexion | Cambios en el nombre de los campos |
| R-05 | El cliente espera ganarle una licitacion y no la gana | Media | **Alto** | Dejar por escrito que el servicio prioriza, no garantiza | "Esto no me sirvio" tras un mes |
| R-06 | Un solo cliente consume todo el tiempo | **Alta** | Medio | Cobrar el piloto; nunca trabajar dos pilots a la vez | Mas de 8 horas/semana sin segundo ingreso |
| R-07 | La API de LLM se encarece o cambia de precio | Baja | Medio | El motor funciona sin LLM; es una capa opcional | Cambios de precio del proveedor |
| R-08 | Se confunde informacion publica con dato verificado | Media | Medio | Mostrar siempre la fecha de consulta y la fuente | Cliente cita un dato sin fecha |

**R-05 es el riesgo que mas mata este negocio.** Un cliente que contrata esperando
adjudicaciones y recibe un buen informe pero no gana, se va y culpa al servicio. Por
eso la clause "prioriza, no garantiza" tiene que estar en el contrato desde el primer
dia, no como nota al pie.

## 5.5 Lo que haria distinto con mas tiempo

1. **Persistencia del historico** para medir la precision del puntaje con datos
   reales y no con la percepcion del cliente.
2. **Competencia indirecta:** quien gano procesos parecidos en la misma region.
   Requiere un segundo barrido sobre el dataset de contratos.
3. **Filtro por categoria UNSPSC** como condicion obligatoria, para eliminar de raiz
   los falsos positivos por subcadena.
4. **Plantilla de memoria tecnica** generada a partir de los requisitos del pliego.
   Es la pieza que mas valor tiene y la mas cercana al cliente.
