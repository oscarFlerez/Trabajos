/* Genera la hoja comercial en PDF usando el mismo mecanismo que informe.py:
   HTML -> Chrome headless --print-to-pdf. Sin dependencias externas.

   El PDF es lo que el cliente se lleva. Debe caber en una hoja y poder leerse
   en un minuto, asi que no lleva el detalle tecnico: solo el problema, los
   numeros medidos y la propuesta. */
import { execFileSync } from "node:child_process";
import { writeFileSync, existsSync, unlinkSync, readFileSync } from "node:fs";
import { join } from "node:path";

const RAIZ = "C:\\Users\\Estudiante 10\\Desktop\\Trabajo\\Trabajos";
const SALIDA = process.argv[2] || join(RAIZ, "Radar-de-Licitaciones-comercial.pdf");
const TEMP_HTML = join(RAIZ, "hoja-comercial.html");

const HTML = `<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8">
<title>Radar de Licitaciones</title>
<style>
  @page { size: A4; margin: 14mm 14mm 12mm 14mm; }
  * { box-sizing: border-box; }
  body { font-family: "Segoe UI", Roboto, Arial, sans-serif; color: #14213d;
         font-size: 10.2pt; line-height: 1.42; margin: 0; }
  h1 { font-size: 19pt; margin: 0 0 2mm; letter-spacing: -.3px; }
  .sub { color: #5b6b84; font-size: 9.5pt; margin: 0 0 5mm; }
  h2 { font-size: 11.5pt; margin: 6mm 0 2mm; color: #0b3d5c;
       border-bottom: 1.5px solid #0b3d5c; padding-bottom: 1.2mm; }
  .cifras { display: flex; gap: 3mm; margin: 3mm 0 1mm; }
  .c { flex: 1; border: 1px solid #d7dee8; border-radius: 2mm;
       padding: 3mm 3.5mm; background: #f8fafc; }
  .c b { display: block; font-size: 16pt; color: #0b3d5c; line-height: 1.1; }
  .c span { font-size: 8.2pt; color: #5b6b84; display: block; margin-top: .8mm; }
  table { width: 100%; border-collapse: collapse; font-size: 9.2pt; margin-top: 1.5mm; }
  th { text-align: left; background: #eef3f8; color: #0b3d5c;
       padding: 1.8mm 2mm; font-size: 8.4pt; text-transform: uppercase;
       letter-spacing: .3px; }
  td { padding: 1.8mm 2mm; border-bottom: 1px solid #e6ebf1; vertical-align: top; }
  .embudo { background: #0b3d5c; color: #fff; border-radius: 2mm;
            padding: 3.5mm 4mm; font-family: Consolas, monospace;
            font-size: 8.8pt; line-height: 1.6; margin-top: 1.5mm; }
  .embudo b { color: #8fd6ff; }
  ul { margin: 1.5mm 0 0; padding-left: 5mm; }
  li { margin-bottom: 1.2mm; }
  .oferta { border: 1.5px solid #0b3d5c; border-radius: 2mm; padding: 3.5mm 4mm;
            background: #f4f8fc; margin-top: 2mm; }
  .pie { margin-top: 6mm; padding-top: 2mm; border-top: 1px solid #d7dee8;
         font-size: 8pt; color: #6b7a90; }
  .fuerte { font-weight: 700; color: #0b3d5c; }
</style></head>
<body>

<h1>Radar de Licitaciones</h1>
<p class="sub">Monitoreo autom&aacute;tico de oportunidades de obra p&uacute;blica en Colombia &middot; Datos abiertos de SECOP II</p>

<h2>El problema</h2>
<p>El Estado tiene <span class="fuerte">8.086.821 procesos marcados como
"Abierto"</span>. Ah&iacute; est&aacute;n las obras que le sirven y est&aacute;n tambi&eacute;n
papeler&iacute;a, Hire y transporte. Revisarlos a mano entre millones de filas no es
lento: es imposible, y por eso casi nadie lo hace.</p>
<p>Y el portal no ayuda: marca como "Abierto" procesos que llevan
<span class="fuerte">a&ntilde;os sin poder licitarse</span>. De los 8.086.821 marcados
como abiertos, <span class="fuerte">4.907.994 (el 60,7%) fueron publicados
antes de 2025</span>.</p>

<div class="cifras">
  <div class="c"><b>8.086.821</b><span>procesos marcados "Abierto"</span></div>
  <div class="c"><b>60,7%</b><span>de esos publicados antes de 2025</span></div>
  <div class="c"><b>7</b><span>oportunidades reales de 5.000 revisadas</span></div>
</div>

<h2>Qu&eacute; hace</h2>
<p>El cliente carga su perfil una vez &mdash; qu&eacute; sabe hacer, d&oacute;nde, entre qu&eacute;
presupuesto &mdash; y la herramienta devuelve solo lo que encaja, con el motivo
de cada oportunidad a la vista. No es un buscador: es un filtro que
<span class="fuerte">tambi&eacute;n ense&ntilde;a lo que descart&oacute; y por qu&eacute;</span>.</p>

<div class="embudo">
<b>5.000</b> procesos abiertos descargados<br>
&nbsp;&nbsp;<b>163</b>&nbsp; del sector de la empresa &nbsp;&nbsp;&nbsp; (3,3%)<br>
&nbsp;&nbsp;<b>119</b>&nbsp; publicados hace m&aacute;s de 1 a&ntilde;o &nbsp;(73,0%)&nbsp; [vetado]<br>
&nbsp;&nbsp;<b>28</b>&nbsp; m&aacute;s de 90 d&iacute;as &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;(penaliza -30)<br>
&nbsp;&nbsp;<b>11</b>&nbsp; presupuesto bajo el m&iacute;nimo<br>
&nbsp;&nbsp;<b>7</b>&nbsp; con puntaje suficiente
</div>

<h2>Lo que casi nadie hace</h2>
<table>
<tr><th>Falso positivo eliminado</th><th>Por qu&eacute; entraba</th><th>C&oacute;mo se descarta</th></tr>
<tr>
<td>Transferencia de recursos para subsidios de acueducto &mdash; $325 M</td>
<td>El texto habla de acueducto</td>
<td>Es dinero, no obra: se busca en el t&iacute;tulo</td>
</tr>
<tr>
<td>Servicios profesionales de odontolog&iacute;a &mdash; 50/100</td>
<td>"Intervenci&oacute;n" dental</td>
<td>Una consulta dental no es intervenci&oacute;n de obra</td>
</tr>
</table>
<p style="font-size:8.6pt;color:#5b6b84;margin-top:1.5mm">
Que aparezca odontolog&iacute;a en una lista de obras no da&ntilde;a el producto:
<strong>lo termina</strong>. Un cliente que encuentra basura deja de creer en el resto.</p>

<p style="font-size:8.6pt;color:#5b6b84;margin-top:2.5mm">
<strong>Nota sobre las cifras.</strong> 8.086.821 y el 60,7% est&aacute;n contados
sobre el total de procesos del portal. El n&uacute;mero 7 sale de revisar
5.000 procesos abiertos, no del total: el portal no permite contar por palabra
clave sin recorrer las ocho millones de filas. El embudo de arriba corresponde
a esa misma muestra de 5.000.</p>

<h2>Propuesta</h2>
<div class="oferta">
<ul>
<li><span class="fuerte">Prueba de un mes, sin compromiso.</span> Perfil cargado con los datos
reales del cliente y sesi&oacute;n de revisi&oacute;n.</li>
<li><span class="fuerte">Sin registros ni tarjetas.</span> P&aacute;gina sin servidor:
el cliente abre un enlace y funciona. Nada se guarda fuera de su equipo.</li>
<li><span class="fuerte">Se paga si sirve.</span> Si en el mes no aparecen oportunidades
que sirvan, se devuelve.</li>
</ul>
</div>

<div class="pie">
Cifras medidas sobre la plataforma de datos abiertos del Estado (datos.gov.co, conjunto
<code style="font-size:7.6pt">p6dx-8zbt</code>), 30 de septiembre de 2026.
SECOP no publica fecha de cierre de los procesos, por lo que la herramienta
advierte la antig&uuml;edad en lugar de afirmar que un proceso sigue vigente.</div>

</body></html>`;

writeFileSync(TEMP_HTML, HTML, "utf8");

const navegadores = [
  "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
  "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
  "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
];
const nav = navegadores.find((p) => existsSync(p));
if (!nav) {
  console.log("No se encontro Chrome ni Edge. Queda " + TEMP_HTML + " para abrir e imprimir.");
  process.exit(1);
}

const perfil = join(RAIZ, ".pdf-perfil-temp");
try {
  execFileSync(nav, [
    "--headless=new", "--disable-gpu", "--no-sandbox",
    "--user-data-dir=" + perfil,
    "--no-pdf-header-footer",
    "--print-to-pdf=" + SALIDA,
    "file:///" + TEMP_HTML.replace(/\\/g, "/"),
  ], { stdio: "ignore", timeout: 120000 });
} finally {
  try { unlinkSync(TEMP_HTML); } catch {}
  try { execFileSync("cmd", ["/c", "rmdir", "/s", "/q", perfil], { stdio: "ignore" }); } catch {}
}

if (existsSync(SALIDA)) {
  const bytes = readFileSync(SALIDA).length;
  console.log("PDF generado: " + SALIDA + "  (" + Math.round(bytes / 1024) + " KB)");
} else {
  console.log("El navegador no produjo el PDF.");
}