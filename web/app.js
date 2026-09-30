/* app.js - Logica del radar, portada a JavaScript.
   Es el mismo algoritmo de src/radar.py, sin servidor: el navegador consulta
   la API publica de datos.gov.co directamente (esa API permite CORS).

   Portar, no reescribir: los pesos y las reglas son los mismos del radar, para
   que la version web y la de escritorio den el mismo resultado. */

import { PERFIL_POR_DEFECTO } from "./contexto.js";

const API = "https://www.datos.gov.co/resource/p6dx-8zbt.json";

const CAMPOS = [
  "id_del_proceso", "referencia_del_proceso", "entidad", "departamento_entidad",
  "ciudad_entidad", "nombre_del_procedimiento", "descripci_n_del_procedimiento",
  "precio_base", "modalidad_de_contratacion", "estado_de_apertura_del_proceso",
  "fecha_de_publicacion_del", "urlproceso", "conteo_de_respuestas_a_ofertas",
].join(",");

/* ---------------------------------------------------------------- consulta */

export function construirUrl(where, limite = 800, offset = 0) {
  // Los $ de SoQL NO se codifican: solo el valor del $where.
  const w = encodeURIComponent(where);
  return `${API}?$select=${CAMPOS}&$where=${w}&$limit=${limite}&$offset=${offset}`;
}

export function whereAbiertos() {
  return "estado_de_apertura_del_proceso='Abierto'";
}

export async function traerProcesos(where, limite = 800, onProgress) {
  const salida = [];
  for (let off = 0; off < limite; off += 800) {
    const r = await fetch(construirUrl(where, 800, off));
    if (!r.ok) throw new Error("El portal de datos respondió " + r.status);
    const lote = await r.json();
    salida.push(...lote);
    if (onProgress) onProgress(salida.length);
    if (lote.length < 800) break;
  }
  return salida.slice(0, limite);
}

/* ---------------------------------------------------------------- limpieza */

const NO_ES_PERSONA = [
  "CONTRATO", "CONTRATACION", "PRESTACION", "PRESTA", "SERVICIO", "SERVICIOS",
  "SUMINISTRO", "COMPRA", "VENTA", "OBRA", "CONSTRUCCION", "MANTENIMIENTO",
  "INTERADMINISTRATIVO", "DIRECTO", "DIRECTA", "PROFESIONAL", "PROFESIONALES",
  "APOYO", "GESTION", "DOTACION", "ALQUILER", "TRANSPORTE", "CONSULTORIA",
  "INTERVENCION", "REHABILITACION", "MEJORAMIENTO", "AMPLIACION",
  "COSTRUCCION", "ADQUISICION", "EVALUACION", "IMPLEMENTACION", "CAPACITACION",
  "ARRENDAMIENTO", "REPARACION", "INSTALACION", "DISENO",
];

const GENERICOS = [
  "PRESTACION DE SERVICIOS", "CONTRATO DE PRESTACION DE SERVICIOS",
  "PRESTACION DE SERVICIOS PROFESIONALES", "CONTRATACION DIRECTA",
  "CONTRATO INTERADMINISTRATIVO", "SERVICIOS", "PRESTACION", "CONTRATO",
  "SUMINISTRO", "COMPRA", "SERVICIOS PROFESIONALES",
];

/* Devuelve el objeto tal como se debe mostrar. `nombre_del_procedimiento` a
   veces trae un nombre de persona o un codigo; en ese caso se usa la
   descripcion, que si es el objeto real. */
export function objetoLimpio(f) {
  const nom = (f.nombre_del_procedimiento || "").trim();
  const desc = (f.descripci_n_del_procedimiento || "").trim();
  if (!nom) return { texto: desc || "(sin objeto)", nota: "sin nombre, se uso la descripcion" };

  const soloNumeros = nom.replace(/copia/gi, "").trim();
  if (soloNumeros && /^[0-9\-\s/.]+$/.test(soloNumeros)) {
    if (desc) return { texto: desc, nota: "el nombre era un codigo, se uso la descripcion" };
    return { texto: nom, nota: "el nombre es un codigo y no hay descripcion" };
  }

  const tokens = nom.split(/\s+/).filter(Boolean);
  if (tokens.length >= 2 && tokens.length <= 6) {
    const mayus = tokens.filter((t) => t === t.toUpperCase() && t.length > 2).length;
    const tieneVerbo = NO_ES_PERSONA.some((k) => nom.toUpperCase().includes(k));
    if (!tieneVerbo && mayus >= Math.max(2, tokens.length - 1)) {
      if (desc) return { texto: desc, nota: "el nombre traia una persona, se uso la descripcion" };
      return { texto: nom, nota: "el nombre parece una persona y no hay descripcion" };
    }
  }

  if (GENERICOS.includes(nom.toUpperCase().replace(/[ .]+$/, "")) && desc) {
    return { texto: desc, nota: "el nombre era generico, se uso la descripcion" };
  }
  return { texto: nom, nota: "" };
}

export function diasDesde(fecha) {
  if (!fecha) return null;
  const d = new Date(String(fecha).split("T")[0] + "T00:00:00");
  if (isNaN(d)) return null;
  return Math.floor((Date.now() - d.getTime()) / 86400000);
}

export function entero(v) {
  const n = parseInt(String(v || "0").replace(/[^\d]/g, ""), 10);
  return isNaN(n) ? 0 : n;
}

/* ---------------------------------------------------------------- puntaje */

export function puntuar(f, p) {
  const texto = ((f.nombre_del_procedimiento || "") + " " +
                 (f.descripci_n_del_procedimiento || "")).toLowerCase();
  if (!texto.trim()) return { score: 0, razones: ["sin descripcion"] };
  if (p.excluir.some((x) => texto.includes(x.toLowerCase()))) return { score: 0, razones: [] };

  const aciertos = p.palabras_clave.filter((k) => texto.includes(k.toLowerCase()));
  if (!aciertos.length) return { score: 0, razones: [] };

  let puntos = Math.min(aciertos.length / 2, 1) * p.peso_sector;
  const razones = ["sector: " + aciertos.slice(0, 3).join(", ")];

  const dep = (f.departamento_entidad || "").toUpperCase();
  if (p.departamentos.some((d) => dep.includes(d.toUpperCase()))) {
    puntos += p.peso_zona;
    razones.push("zona objetivo");
  } else {
    puntos += p.peso_fuera_de_zona;
  }

  const precio = entero(f.precio_base);
  if (precio === 0) {
    razones.push("presupuesto no publicado");
  } else if (precio >= p.precio_min && precio <= p.precio_max) {
    puntos += p.peso_presupuesto;
    razones.push("presupuesto encaja");
  } else if (precio > p.precio_max) {
    puntos -= p.penalty_sobre_precio;
    razones.push("muy por encima del rango");
  }

  /* COMPETENCIA: no se puntua, porque no se puede saber. El contador de
     oferentes tiene dato en el 0,0% de los procesos abiertos (medido sobre
     3.000 el 30/09/2026) y `proveedores_que_manifestaron` tambien. Antes el
     codigo daba +10 cuando venía en cero, o sea que practicamente todo
     recibia puntos y se le decia "poca competencia" sin base. La penalizacion
     por mucha competencia si se conserva: esa es verdad cuando aparece. */
  const oferentes = entero(f.conteo_de_respuestas_a_ofertas);
  if (oferentes > p.aviso_si_oferentes) {
    puntos -= p.penalty_sobre_precio;
    razones.push("MUCHA competencia: " + oferentes + " oferentes");
  }

  /* "Abierto" no significa que se pueda licitar: el 60,7% de esos procesos
     fueron publicados antes de 2025. Por eso la antiguedad pesa tanto. */
  const dias = diasDesde(f.fecha_de_publicacion_del);
  if (dias !== null && dias > p.dias_maximos) {
    if (dias > 365) return { score: 0, razones: ["descartado: publicado hace " + dias + " dias, el plazo ya vencio"] };
    puntos -= p.penalty_antiguedad;
    razones.push("ATENCION: publicado hace " + dias + " dias");
  } else if (dias !== null && dias > 0) {
    razones.push("publicado hace " + dias + " dias");
  }

  return { score: Math.max(0, Math.min(100, Math.round(puntos))), razones };
}

/* No siempre trae la ficha del proceso. Hay filas cuyo `urlproceso` es la
   pantalla de login de SECOP o la portada, que no llevan a ninguna parte.
   Enviar a un cliente a una pagina de acceso parece fallo de la herramienta. */
export function linkDe(f) {
  let u = (typeof f.urlproceso === "object" && f.urlproceso)
    ? (f.urlproceso.url || "")
    : (f.urlproceso || "");
  u = String(u).trim();
  if (!u) return "";
  const baja = u.toLowerCase();
  const rotas = ["/sts/users/login", "login/index", "/secop.aspx", "/home/index"];
  if (rotas.some((b) => baja.includes(b))) return "";
  if (!baja.includes("opportunitydetail")) return "";
  return u;
}

export function analizar(filas, perfil = PERFIL_POR_DEFECTO) {
  const out = [];
  for (const f of filas) {
    const { score, razones } = puntuar(f, perfil);
    if (score >= (perfil.puntaje_minimo ?? 40)) {
      out.push({
        ...f,
        score,
        razones,
        objeto: objetoLimpio(f).texto,
        dias: diasDesde(f.fecha_de_publicacion_del),
        link: linkDe(f),
      });
    }
  }
  out.sort((a, b) => b.score - a.score);
  return out;
}

/* ------------------------------------------------------- marcas del cliente */

const CLAVE = "radar_marcas_v1";

export function leerMarcas() {
  try { return JSON.parse(localStorage.getItem(CLAVE) || "{}"); }
  catch { return {}; }
}

export function marcar(ref, estado) {
  const m = leerMarcas();
  m[ref] = { estado, fecha: new Date().toISOString() };
  localStorage.setItem(CLAVE, JSON.stringify(m));
  return m;
}

export function precision(marcas) {
  const v = Object.values(marcas);
  const u = v.filter((x) => x.estado === "util").length;
  const d = v.filter((x) => x.estado === "descartado").length;
  return { utiles: u, descartadas: d, pendientes: v.length - u - d, precision: (u + d) ? (u / (u + d)) * 100 : null };
}

/* ------------------------------------------------------------- consultas */

const SECTORES = {
  construccion: ["construccion", "obra", "cimentacion", "concreto", "estructural"],
  acueducto: ["acueducto", "alcantarillado", "drenaje", "canalizacion", "saneamiento"],
  vivienda: ["vivienda", "edificacion", "placa huella"],
  pavimento: ["pavimento", "pavimentacion", "via", "carretera"],
  consultoria: ["consultoria", "asesoria", "interventoria", "supervision"],
  salud: ["salud", "hospital", "medico", "enfermeria", "medicamento"],
  educacion: ["educacion", "escuela", "colegio", "docencia", "formacion"],
  transporte: ["transporte", "vehiculo", "combustible"],
  tecnologia: ["software", "licenciamiento", "computador", "sistema"],
};

export function interpretar(frase) {
  const t = frase.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
  const f = { anios: null, sector: null, departamento: null, soloVigentes: false, nota: [] };

  const rango = t.match(/entre\s+(\d{4})\s*(?:y|a|hasta)\s*(\d{4})/);
  if (rango) {
    f.anios = [+rango[1], +rango[2]];
    f.nota.push("rango de anos " + f.anios[0] + "-" + f.anios[1]);
  } else {
    const anios = (t.match(/\b(?:19|20)\d{2}\b/g) || []).map(Number);
    if (anios.length === 1) { f.anios = [anios[0], anios[0]]; f.nota.push("ano " + anios[0]); }
    else if (anios.length >= 2) { f.anios = [Math.min(...anios), Math.max(...anios)]; f.nota.push("anos " + f.anios[0] + "-" + f.anios[1]); }
  }

  if (/modernas?|recientes|nuevas|actuales|vigentes/.test(t)) { f.soloVigentes = true; f.nota.push("solo recientes"); }
  if (/antiguas?|viejas?|historicas/.test(t)) { f.soloVigentes = false; f.anios = f.anios || [1990, 2019]; f.nota.push("antiguas (hasta 2019)"); }

  for (const [nombre, claves] of Object.entries(SECTORES)) {
    if (claves.some((c) => t.includes(c)) || t.includes(nombre)) { f.sector = nombre; f.nota.push("sector: " + nombre); break; }
  }
  return f;
}
