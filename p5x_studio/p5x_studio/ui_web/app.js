/* P5X Studio Tools - interfaz nueva (pywebview).
   Toda la logica vive en Python (motor.py, via la Api). Este fichero SOLO pinta: pide datos,
   filtra en cliente la lista ya cargada, y muestra u oculta pantallas. */
"use strict";

let T = {en: {}};                 // textos (de idiomas.py via el motor; la Tools va solo en ingles)
let lang = "en";
let api = null;
let tipos = [];                    // tipos de bundle reales + recuento
let bundles = [];                  // catalogo completo (una sola carga)
let tipoSel = null;                // chip activo
let selId = null;                  // fila elegida en el explorador
let soloNuevos = false;            // filtrar el explorador solo por bundles nuevos (updates)
let lastBundle = null;             // para el boton "ver en la carpeta"
let inspFilas = [];                // recursos del inspector
let inspSel = new Set();           // indices seleccionados
let mediaDatos = {usm: [], awb: []};
let mediaSeg = "usm";
let mediaSel = -1;
let tmpSel = null;                 // tarea en curso (para el sondeo)
const DISPLAY_MAX = 700;           // filas pintadas de golpe (el total sigue siendo real)

const $ = s => document.querySelector(s);
const $$ = s => document.querySelectorAll(s);
const tr = k => (T.en && T.en[k]) || k;
const num = n => Number(n || 0).toLocaleString("en-US");
const esc = s => String(s == null ? "" : s).replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;"}[c]));
const fmt = (tpl, ...a) => String(tpl || "").replace(/%s/g, () => a.shift());

function archivoUrl(p){ return "file:///" + String(p).replace(/\\/g, "/").replace(/^\/+/, "").split("/").map(encodeURIComponent).join("/"); }

/* ------------------------------------------------------------------ idioma */
function pintarTextos(){
  document.documentElement.lang = lang;
  $$("[data-t]").forEach(e => { e.textContent = tr(e.dataset.t); });
  var _q=$("#q"); if(_q) _q.placeholder = tr("web_search_placeholder");
  var _ip=$("#insp-path"); if(_ip) _ip.placeholder = tr("web_insp_ph");
  var _rq=$("#res-q"); if(_rq) _rq.placeholder = tr("web_res_ph");
  var _tb=$("#tex-bundle"); if(_tb) _tb.placeholder = tr("web_insp_ph");
  var _bq=$("#bust-q"); if(_bq) _bq.placeholder = tr("web_bust_ph");
}

/* ------------------------------------------------------------------ pantallas */
function ir(p){
  $$("#nav button").forEach(b => b.setAttribute("aria-current", b.dataset.p === p ? "true" : "false"));
  $$(".settings-btn").forEach(b => b.setAttribute("aria-current", b.dataset.p === p ? "true" : "false"));
  $$(".pantalla").forEach(s => s.classList.toggle("activa", s.id === "p-" + p));
  if(p === "bulk") abrirBulk();      // el inventario se pide al entrar, no al arrancar la app
  if(p === "bustups") abrirBustups();  // la lista de bust-ups tambien
}

/* ------------------------------------------------------------------ EXPLORADOR */
function pintarChips(){
  const c = $("#chips");
  const total = bundles.length;
  let html = `<button class="chip" data-k="" aria-pressed="${(tipoSel??"")===""}">${esc(tr("web_chip_all"))}<i>${num(total)}</i></button>`;
  for(const t of tipos){
    html += `<button class="chip" data-k="${esc(t.tipo)}" aria-pressed="${tipoSel===t.tipo}">${esc(t.tipo)}<i>${num(t.n)}</i></button>`;
  }
  c.innerHTML = html;
  c.querySelectorAll(".chip").forEach(b => b.onclick = () => { tipoSel = b.dataset.k || null; pintarChips(); pintarLista(); });
}

function filtra(){
  const q = $("#q").value.trim().toLowerCase();
  return bundles.filter(d => (!tipoSel || d.tipo === tipoSel) && (!soloNuevos || d.nuevo) && (!q || d.fichero.toLowerCase().includes(q) || d.ruta.toLowerCase().includes(q)));
}

function pintarNovedades(){
  // el boton de "solo nuevos" lleva el recuento dentro; sin nuevos recientes no se insiste
  const n = bundles.filter(d => d.nuevo).length;
  const b = $("#btn-solo-nuevos");
  b.textContent = tr("web_new_only") + (n ? ` (${num(n)})` : "");
  b.setAttribute("aria-pressed", String(!!soloNuevos));
  b.hidden = !n && !soloNuevos;
}

function pintarLista(){
  const rows = filtra();
  const montradas = Math.min(rows.length, DISPLAY_MAX);
  $("#count").textContent = rows.length
    ? (rows.length > DISPLAY_MAX ? fmt(tr("web_shown"), num(DISPLAY_MAX), num(rows.length)) : tr("web_results") + ": " + num(rows.length))
    : "";
  if(!rows.length){ $("#list").innerHTML = `<div class="empty">${esc(tr("web_empty"))}</div>`; return; }
  const trozo = rows.slice(0, DISPLAY_MAX);
  $("#list").innerHTML = trozo.map(d => `
    <div class="row" data-id="${esc(d.id)}" aria-selected="${selId===d.id}">
      <div class="name"><span class="badge t-${esc(d.cat)}"></span><b>${esc(d.fichero)}</b>${d.nuevo ? `<em class="nuevo">${esc(tr("web_new"))}</em>` : ""}<s>${esc(d.tipo)}</s></div>
      <div class="k">${d.n_mallas ? num(d.n_mallas)+" "+esc(tr(d.n_mallas>1?"web_unit_mesh_pl":"web_unit_mesh")) : "—"}</div>
      <div class="k">${d.n_texturas ? num(d.n_texturas)+" "+esc(tr("web_unit_tex")) : "—"}</div>
      <div class="k">${d.mb.toFixed(1)} MB</div>
    </div>`).join("");
  $$("#list .row").forEach(r => r.onclick = () => abrirDetalle(r.dataset.id));
  const resta = rows.length - montradas;
  if(resta > 0) $("#list").insertAdjacentHTML("beforeend", `<div class="empty">+ ${num(resta)} …</div>`);
}

async function abrirDetalle(id){
  selId = id; pintarLista();
  const f = await api.ficha(id);
  const d = $("#detail"); d.hidden = false;
  $("#d-name").textContent = f.fichero || id;
  $("#d-path").textContent = id;
  $("#d-mesh").textContent = f.n_mallas ? num(f.n_mallas) : "—";
  $("#d-tex").textContent = f.n_texturas ? num(f.n_texturas) : "—";
  $("#d-size").textContent = (f.mb != null ? f.mb.toFixed(1) : "—") + " MB";
  $("#d-type").textContent = f.tipo || "—";
  const cont = (f.contenido || []).length ? f.contenido.map(x => `<li><u></u><span>${esc(x)}</span></li>`).join("")
                                        : `<li><u></u><span class="k" style="text-align:left">${esc(tr("web_insp_empty"))}</span></li>`;
  $("#d-assets").innerHTML = cont;
  lastBundle = id;
}

/* ------------------------------------------------------------------ INSPECTOR */
function pintarInspector(){
  const tb = $("#insp-body");
  tb.innerHTML = inspFilas.map((r, i) => `
    <tr data-i="${i}" class="${inspSel.has(i)?"sel":""}">
      <td class="ell">${esc(r.nombre)}</td><td>${esc(r.tipo)}</td>
      <td class="ell" style="color:var(--mut-2)">${esc(r.contenedor||"—")}</td>
      <td class="num">${esc(r.pathid||"—")}</td><td class="num">${num(r.tamano)} B</td>
    </tr>`).join("");
  $$("#insp-body tr").forEach(tr_ => tr_.onclick = () => {
    const i = +tr_.dataset.i;
    if(inspSel.has(i)) inspSel.delete(i); else inspSel.add(i);
    pintarInspector();
  });
  $("#insp-tabla").hidden = !inspFilas.length;
}

async function abrirConMotor(ruta){
  if(!ruta) return;
  const estado = $("#insp-estado");
  if(estado){ estado.textContent = "Extracting with AssetStudio..."; estado.className = "estado"; }
  try {
    const r = await api.abrir_con_motor(ruta);
    if(estado){ estado.textContent = r; estado.className = "estado ok"; }
  } catch(e) {
    if(estado){ estado.textContent = String(e); estado.className = "estado bad"; }
  }
}

async function inspeccionar(ruta){
  if(!ruta) return;
  $("#insp-estado").textContent = tr("web_insp_working"); $("#insp-estado").className = "estado";
  try{
    inspFilas = await api.abrir(ruta); inspSel = new Set();
    pintarInspector();
    $("#insp-estado").textContent = fmt(tr("web_insp_n"), num(inspFilas.length));
    $("#insp-estado").className = "estado ok";
  }catch(e){ $("#insp-estado").textContent = fmt(tr("web_error"), e); $("#insp-estado").className = "estado bad"; }
}

const MAP_TIPO = {Mesh:"mesh", Texture2D:"tex2d", Sprite:"sprite", Material:"material",
  AnimationClip:"animationclip", TextAsset:"textasset", AudioClip:"audioclip", Font:"font",
  Shader:"shader", MonoBehaviour:"mono"};

async function inspectorExportar(tiposRe){
  const ruta = $("#insp-path").value.trim();
  if(!ruta) return;
  $("#insp-estado").textContent = tr("web_tex_working"); $("#insp-estado").className = "estado";
  const r = await api.exportar(ruta, tiposRe);
  $("#insp-estado").textContent = r.error ? fmt(tr("web_error"), r.error) : fmt(tr("web_media_done"), r.destino);
  $("#insp-estado").className = "estado " + (r.error ? "bad" : "ok");
}

/* ------------------------------------------------------------------ BUSCADOR */
async function refrescarRecursos(){
  const est = await api.estado();
  const ind = est.indice || {};
  if(ind.disponible && ind.n){
    $("#res-q").disabled = false;
    $("#res-build").textContent = tr("web_res_rebuild");
    if(ind.parcial){
      // El indice existe pero NO cubre todos los bundles: se dice, en vez de dejar creer que la
      // busqueda mira el juego entero.
      $("#res-estado").className = "estado warn";
      $("#res-estado").textContent = fmt(tr("web_res_parcial"), num(ind.bundles_cubiertos), num(ind.bundles), num(ind.n));
    } else {
      $("#res-estado").className = "estado ok";
      $("#res-estado").textContent = fmt(tr("web_res_ready"), num(ind.n), num(ind.bundles));
    }
  } else {
    $("#res-q").disabled = true;
    $("#res-build").textContent = tr("web_res_build");
    $("#res-estado").className = "estado warn";
    $("#res-estado").textContent = tr("web_res_none") + "\n" + tr("web_res_none_body");
  }
}

async function buscarRecursos(){
  const q = $("#res-q").value.trim();
  const filas = await api.buscar(q, "", 800);
  $("#res-body").innerHTML = filas.length ? filas.map(r =>
    `<tr><td class="ell">${esc(r.nombre)}</td><td>${esc(r.tipo)}</td><td class="ell" style="color:var(--mut-2)">${esc(r.bundle)}</td></tr>`).join("")
    : `<tr><td colspan="3" class="empty">${esc(tr("web_res_empty"))}</td></tr>`;
  $("#res-tabla").hidden = false;
}

/* ------------------------------------------------------------------ TEXTURAS */
async function escanearTexturas(){
  const carpeta = $("#tex-choose").dataset.carpeta || null;
  const lista = await api.imagenes(carpeta);
  const g = $("#tex-galeria");
  if(!lista.length){ g.innerHTML = `<div class="empty">${esc(tr("web_tex_none"))}</div>`; return; }
  $("#tex-estado").className = "estado ok";
  $("#tex-estado").textContent = fmt(tr("web_tex_n"), num(lista.length));
  g.innerHTML = lista.map(im => `<figure data-r="${esc(im.ruta)}"><img loading="lazy" src="${archivoUrl(im.ruta)}" alt=""><figcaption>${esc(im.nombre)}</figcaption></figure>`).join("");
  $$("#tex-galeria figure").forEach(f => f.onclick = () => { $("#tex-img").src = archivoUrl(f.dataset.r); $("#tex-visor").hidden = false; });
}

/* ------------------------------------------------------------------ VIDEO Y AUDIO */
function pintarMedia(){
  const lista = mediaDatos[mediaSeg] || [];
  const cont = $("#media-lista");
  if(!lista.length){ cont.innerHTML = `<div class="empty">${esc(tr("web_media_none"))}</div>`; return; }
  cont.innerHTML = lista.map((m, i) => {
    const est = m.estado;
    const cls = est ? `<span class="pill ${esc(est)}">${esc(tr("web_audio_"+est))}</span>` : `<span></span>`;
    return `<div class="media-row ${mediaSel===i?"sel":""}" data-i="${i}">${cls}<span class="nm">${esc(m.nombre)}</span><span class="k">${m.mb.toFixed(1)} MB</span></div>`;
  }).join("");
  $$("#media-lista .media-row").forEach(r => r.onclick = () => { mediaSel = +r.dataset.i; pintarMedia(); });
  $("#media-estado").className = "estado";
  $("#media-estado").textContent = fmt(tr("web_media_n"), num(lista.length)) + (mediaDatos.carpeta ? "  ·  " + mediaDatos.carpeta : "");
}

function textoBotonExtraer(){
  $("#media-extract").textContent = tr(mediaSeg === "usm" ? "web_media_extract_video" : "web_media_extract_audio");
}

/* ------------------------------------------------------------------ tareas (video/audio/indice) */
let sondeo = null;
function arrancarSondeo(){
  if(sondeo) return;
  sondeo = setInterval(async () => {
    let e;
    try{ e = await api.estado_tarea(); }catch(_){ return; }
    const prog = $("#res-prog"), progI = $("#res-prog-i");
    const mprog = $("#media-prog"), mprogI = $("#media-prog-i");
    if(e && e.activa){
      if(e.tipo === "indice"){
        prog.hidden = false;
        const pct = e.total ? Math.round(100 * e.hechos / e.total) : 0;
        progI.style.width = pct + "%";
        $("#res-estado").className = "estado";
        $("#res-estado").textContent = fmt(tr("web_res_building"), num(e.hechos), num(e.total)) + `  (${pct}%)`;
        $("#res-cancel").disabled = false; $("#res-build").disabled = true;
      } else {
        mprog.hidden = false; mprogI.style.width = "60%";
        $("#media-estado").className = "estado";
        $("#media-estado").textContent = tr("web_media_working") + (e.ultimo ? "  ·  " + e.ultimo : "");
      }
      return;
    }
    // termino (o no habia tarea)
    clearInterval(sondeo); sondeo = null;
    prog.hidden = true; mprog.hidden = true;
    $("#res-cancel").disabled = true; $("#res-build").disabled = false;
    const tipo = e ? e.tipo : "";
    if(!e || !e.terminada) return;
    if(e.error){
      const destino = tipo === "indice" ? "#res-estado" : "#media-estado";
      $(destino).className = "estado bad"; $(destino).textContent = fmt(tr("web_error"), e.error);
      return;
    }
    if(tipo === "indice"){
      if(e.cancelada){ $("#res-estado").className = "estado warn"; $("#res-estado").textContent = tr("web_res_cancelled"); }
      else { await refrescarRecursos(); }
    } else {
      $("#media-estado").className = "estado ok";
      $("#media-estado").textContent = fmt(tr("web_media_done"), e.resultado || "");
    }
  }, 700);
}

/* ---------------------------------------------------------------- dependencias */
/* La ventana baja las cuatro herramientas externas y va volcando lo que pasa en una consola que
   no se puede tocar. El registro de la tarea esta acotado a 400 lineas en Python, asi que se
   detectan las nuevas comparando con la ultima pintada, no contando. */
let consolaLineas = [], ultimaDeps = null, sondeoDeps = null;

function pintarDeps(est){
  const ORDEN = [["uv","web_deps_uv"],["motor","web_deps_motor"],["wannacri","web_deps_wannacri"],
                 ["vgmstream","web_deps_vgmstream"],["ffmpeg","web_deps_ffmpeg"]];
  $("#deps-peso").textContent = fmt(tr("web_deps_peso"), est.peso_mb);
  $("#deps-lista").innerHTML = ORDEN.map(([k, clave]) => {
    const ok = est.herramientas[k];
    const fuera = (est.fuera || {})[k];
    // Tres estados, no dos: ademas de "esta" y "falta", una herramienta puede estar FUERA de la
    // carpeta (el escritorio del usuario, el PATH). Esa funciona, pero no viaja con la carpeta.
    const marca = fuera
      ? `<span class="fuera" title="${esc(fuera + " - " + tr("web_deps_fuera_ayuda"))}">${esc(tr("web_deps_fuera"))}</span>`
      : `<span class="${ok ? "si" : "no"}">${ok ? tr("web_deps_si") : tr("web_deps_no")}</span>`;
    return `<li><span>${esc(tr(clave))} · ${est.tamanos[k]} MB</span>` + marca + `</li>`;
  }).join("");
  $("#deps-open").classList.toggle("faltan", (est.faltan || []).length > 0);
}

function volcarConsola(e){
  const l = (e && e.lineas) || [];
  if(!l.length) return;
  const ult = l[l.length - 1];
  if(ult === ultimaDeps) return;
  if(ultimaDeps === null || l.indexOf(ultimaDeps) < 0) consolaLineas = l.slice();  // tarea nueva
  else consolaLineas = consolaLineas.concat(l.slice(l.lastIndexOf(ultimaDeps) + 1));
  if(consolaLineas.length > 800) consolaLineas = consolaLineas.slice(-800);
  ultimaDeps = ult;
  const c = $("#deps-consola");
  c.textContent = consolaLineas.join("\n");
  c.scrollTop = c.scrollHeight;      // sigue el progreso solo; el usuario puede subir a mirar
}

function arrancarSondeoDeps(){
  if(sondeoDeps) return;
  $("#deps-bajar").disabled = true;
  sondeoDeps = setInterval(async () => {
    let e; try{ e = await api.estado_tarea(); }catch(_){ return; }
    if(e) volcarConsola(e);
    if(!e || !e.activa){
      clearInterval(sondeoDeps); sondeoDeps = null;
      $("#deps-bajar").disabled = false;
      if(e && e.tipo === "dependencias" && e.terminada){
        const c = $("#deps-consola");
        c.textContent += "\n" + (e.error ? tr("web_deps_fallo") + " " + e.error
                                          : fmt(tr("web_deps_listo"), e.resultado || ""));
        c.scrollTop = c.scrollHeight;
        pintarDeps(await api.estado_dependencias());
      }
    }
  }, 700);
}

async function abrirDeps(){
  consolaLineas = []; ultimaDeps = null; $("#deps-consola").textContent = "";
  $("#deps-modal").hidden = false;
  pintarDeps(await api.estado_dependencias());
  const e = await api.estado_tarea();
  if(e && e.tipo === "dependencias"){ volcarConsola(e); arrancarSondeoDeps(); }
}

/* ------------------------------------------------------------------ TEXTURAS EN BLOQUE */
let bulkInv = null;            // inventario: categorias, bundles, texturas y peso estimado
let bulkSel = new Set();       // categorias marcadas
let bulkDestino = "";          // carpeta destino
let bulkLineas = [];           // consola del bulk (se conserva entre sondeos)
let bulkUltima = null;
let sondeoBulk = null;
let bulkCargado = false;

const mb = n => (Number(n) >= 1024 ? (Number(n) / 1024).toFixed(1) + " GB" : Math.round(Number(n) || 0) + " MB");

function pintarBulkCategorias(){
  if(!bulkInv) return;
  // se ensenan todas las que tienen bundles, "Other" incluida: asi la suma cuadra con el catalogo y
  // el usuario puede meterla si quiere (por defecto va desmarcada: es el cajon de sastre)
  const filas = bulkInv.categorias.filter(c => c.bundles > 0 || bulkSel.has(c.id));
  $("#bulk-categorias").innerHTML = filas.map(c => `
    <tr>
      <td class="c"><input type="checkbox" data-cat="${esc(c.id)}" ${bulkSel.has(c.id) ? "checked" : ""}></td>
      <td>${esc(c.label)}</td>
      <td class="n">${num(c.bundles)}</td>
      <td class="n">${c.texturas == null ? "—" : num(c.texturas)}</td>
      <td class="n">${c.mb == null ? "—" : mb(c.mb)}</td>
    </tr>`).join("");
  $$("#bulk-categorias input[data-cat]").forEach(i => i.onchange = () => {
    if(i.checked) bulkSel.add(i.dataset.cat); else bulkSel.delete(i.dataset.cat);
    textoBulkEstimado();
  });
  textoBulkEstimado();
}

function textoBulkEstimado(){
  if(!bulkInv) return;
  if(($("#bulk-filtro").value || "").trim()){
    $("#bulk-estimado").textContent = tr("web_bulk_estimado_filtro");
    return;
  }
  let tex = 0, pesa = 0;
  for(const c of bulkInv.categorias){
    if(bulkSel.has(c.id)){ tex += c.texturas || 0; pesa += c.mb || 0; }
  }
  $("#bulk-estimado").textContent = fmt(tr("web_bulk_estimado"), num(tex), num(Math.round(pesa)));
}

function pintarBulkEstado(est){
  if(!est) return;
  $("#bulk-libre").textContent = fmt(tr("web_bulk_libre"), mb((est.libre || 0) / 1e6));
  if(est.destino) $("#bulk-destino").value = est.destino;
  if(est.hechos){
    $("#bulk-ya-hecho").textContent = fmt(tr("web_bulk_ya_hecho"), num(est.hechos));
    return;
  }
  const con = (est.carpetas || []).filter(c => c.ficheros > 0);
  $("#bulk-ya-hecho").textContent = con.length
    ? con.map(c => `${c.label}: ${num(c.ficheros)} (${mb(c.mb)})`).join("  ·  ")
    : tr("web_bulk_vacio");
}

async function abrirBulk(){
  try{
    const est = await api.bulk_estado(bulkDestino || null);
    if(!bulkCargado){
      bulkInv = est.inventario;
      bulkDestino = est.destino || "";
      // de arranque se marca todo menos el cajon de sastre: es lo que pidio el usuario
      bulkSel = new Set((bulkInv.categorias || []).filter(c => c.id !== "other" && c.bundles > 0).map(c => c.id));
      bulkCargado = true;
      pintarBulkCategorias();
    }
    pintarBulkEstado(est);
    const e = await api.estado_tarea();
    if(e && e.activa && e.tipo === "bulk"){ volcarBulk(e); arrancarSondeoBulk(); }
  }catch(err){
    $("#bulk-estado").className = "estado bad";
    $("#bulk-estado").textContent = String(err);
  }
}

function volcarBulk(e){
  const l = (e && e.lineas) || [];
  const ult = l.length ? l[l.length - 1] : null;
  if(ult && ult !== bulkUltima){
    if(bulkUltima === null || l.indexOf(bulkUltima) < 0) bulkLineas = l.slice();   // tarea nueva
    else bulkLineas = bulkLineas.concat(l.slice(l.lastIndexOf(bulkUltima) + 1));
    if(bulkLineas.length > 800) bulkLineas = bulkLineas.slice(-800);
    bulkUltima = ult;
    const c = $("#bulk-consola");
    c.textContent = bulkLineas.join("\n");
    c.scrollTop = c.scrollHeight;
  }
  if(e && e.total){
    $("#bulk-prog").hidden = false;
    $("#bulk-prog-i").style.width = Math.min(100, Math.round(100 * (e.hechos || 0) / e.total)) + "%";
    if(e.activa) $("#bulk-estado").textContent = fmt(tr("web_bulk_progreso"), num(e.hechos || 0), num(e.total));
  }
}

function arrancarSondeoBulk(){
  if(sondeoBulk) return;
  $("#bulk-empezar").disabled = true;
  sondeoBulk = setInterval(async () => {
    let e; try{ e = await api.estado_tarea(); }catch(_){ return; }
    if(e) volcarBulk(e);
    if(!e || !e.activa){
      clearInterval(sondeoBulk); sondeoBulk = null;
      $("#bulk-empezar").disabled = false;
      if(e && e.terminada && e.tipo === "bulk"){
        $("#bulk-prog").hidden = true;
        const caja = $("#bulk-estado");
        caja.className = e.error ? "estado bad" : "estado";
        caja.textContent = e.error ? e.error : (e.resultado || "");
        try{ pintarBulkEstado(await api.bulk_estado(bulkDestino || null)); }catch(_){ }
      }
    }
  }, 1000);
}

async function empezarBulk(){
  if(!bulkSel.size){ $("#bulk-estado").className = "estado bad"; $("#bulk-estado").textContent = tr("bulk_err_sin_categoria"); return; }
  bulkLineas = []; bulkUltima = null; $("#bulk-consola").textContent = "";
  $("#bulk-estado").className = "estado"; $("#bulk-estado").textContent = "";
  $("#bulk-prog").hidden = true; $("#bulk-prog-i").style.width = "0%";
  const r = await api.iniciar_bulk({
    categorias: [...bulkSel],
    filtro: ($("#bulk-filtro").value || "").trim(),
    sprites: $("#bulk-sprites").checked,
    por_tipo: $("#bulk-tipo").checked,
    reanudar: $("#bulk-reanudar").checked,
    destino: bulkDestino || null
  });
  if(r && r.ok === false){
    $("#bulk-estado").className = "estado bad";
    $("#bulk-estado").textContent = r.error || "—";
    return;
  }
  arrancarSondeoBulk();
}

/* ------------------------------------------------------------------ BUST-UPS */
/* El montaje lo hace Python (p5x_studio/bustups.py) y el PNG llega como data URL: la pagina no
   puede leer del disco, y asi al cambiar de expresion no hay cache del navegador que valga. */
let bustLista = null;          // los bust-ups que se pueden montar (se pide una vez)
let bustSel = null;            // el elegido
let bustExp = "";              // la expresion elegida

/* ---------------------------------------------- retratos (extracto pequeno, sin el bulk) */
/* El visor busca las texturas en `extracted/portraits` (unos 170 MB): asi funciona sin haberse
   pasado por el bulk entero (63 GB). Detras es el mismo motor, pero solo con los bundles que el
   mapa de bust-ups apunta, y tirando lo que no es de ningun retrato antes de guardarlo. */
let sondeoRetr = null;

async function pintarRetrEstado(){
  let est;
  try{ est = await api.bustups_retratos_estado(); }catch(_){ return; }
  if(!est || !est.ok) return;
  const caja = $("#retr-estado");
  if(est.retratos_png && est.retratos_listo){
    caja.className = "estado ok";
    caja.textContent = fmt(tr("web_bust_retr_listo"), num(est.retratos_png), num(est.retratos_mb));
  } else if(est.hay_bulk){
    caja.className = "estado warn";
    caja.textContent = fmt(tr("web_bust_retr_bulk"), est.carpeta);
  } else {
    caja.className = "estado warn";
    caja.textContent = tr("web_bust_retr_nada");
  }
  $("#retr-nota").textContent = fmt(tr("web_bust_retr_carpeta"), est.retratos)
                              + " · " + tr("web_bust_retr_nota");
  $("#retr-sacar").disabled = !!sondeoRetr;
  $("#retr-cancelar").disabled = !sondeoRetr;
}

function volcarRetr(e){
  if(e && e.total){
    $("#retr-prog").hidden = false;
    $("#retr-prog-i").style.width = Math.min(100, Math.round(100 * (e.hechos || 0) / e.total)) + "%";
    if(e.activa) $("#retr-estado").className = "estado";
    if(e.activa) $("#retr-estado").textContent = fmt(tr("web_bust_retr_progreso"), num(e.hechos || 0), num(e.total));
  }
}

function arrancarSondeoRetr(){
  if(sondeoRetr) return;
  $("#retr-sacar").disabled = true;
  $("#retr-cancelar").disabled = false;
  sondeoRetr = setInterval(async () => {
    let e; try{ e = await api.estado_tarea(); }catch(_){ return; }
    if(e) volcarRetr(e);
    if(!e || !e.activa){
      clearInterval(sondeoRetr); sondeoRetr = null;
      $("#retr-prog").hidden = true;
      if(e && e.terminada && e.tipo === "retratos"){
        if(e.error){
          $("#retr-estado").className = "estado bad";
          $("#retr-estado").textContent = e.error;
        }
        bustLista = null;          // el indice cambio de carpeta: que se vuelva a medir
        await pintarRetrEstado();
        if(!e.error) await abrirBustups();
      } else {
        await pintarRetrEstado();
      }
    }
  }, 1000);
}

async function empezarRetratos(){
  const r = await api.iniciar_bustups_retratos();
  if(r && r.ok === false){
    $("#retr-estado").className = "estado bad";
    $("#retr-estado").textContent = r.error || "—";
    return;
  }
  arrancarSondeoRetr();
}

async function abrirBustups(){
  pintarRetrEstado();            // el extracto puede estar a medias o no existir: que se vea
  if(bustLista) return;
  try{
    const est = await api.bustups_lista("");
    bustLista = est.bustups || [];
    $("#bust-estado").className = "estado " + (est.hay_texturas ? "ok" : "warn");
    $("#bust-estado").textContent = est.hay_texturas ? fmt(tr("web_bust_n"), num(est.n)) : tr("web_bust_none");
    pintarBustLista();
  }catch(e){
    $("#bust-estado").className = "estado bad";
    $("#bust-estado").textContent = String(e);
  }
}

function pintarBustLista(){
  const q = ($("#bust-q").value || "").trim().toLowerCase();
  const filas = (bustLista || []).filter(b => !q || b.id.toLowerCase().includes(q)
    || (b.personaje || "").toLowerCase().includes(q) || (b.nombre_ingles || "").toLowerCase().includes(q) || (b.ropa || "").toLowerCase().includes(q));
  const cont = $("#bust-lista");
  if(!filas.length){ cont.innerHTML = `<div class="empty">${esc(tr("web_res_empty"))}</div>`; return; }
  cont.innerHTML = filas.map(b => `
    <div class="row" data-id="${esc(b.id)}" aria-selected="${bustSel === b.id}">
      ${b.thumbnail ? `<img class="thumb" src="datos/thumbnails/${esc(b.thumbnail)}" loading="lazy" onerror="this.style.display='none'">` : '<div class="thumb placeholder"></div>'}
      <div class="name" title="${esc((b.nombre_ingles || b.personaje) + " · " + b.id)}"><span class="badge"></span><b>${esc(b.nombre_ingles || b.personaje)}</b><s>${esc(String(b.id).replace("UI-DialogShader-", ""))}</s></div>
      <div class="k">${num((b.expresiones || []).length)}</div>
      <div class="k">${num(b.capas)} ${esc(tr("web_bust_capas"))}</div>
    </div>`).join("");
  $$("#bust-lista .row").forEach(r => r.onclick = () => verBustup(r.dataset.id));
}

async function verBustup(id, expresion){
  bustSel = id;
  if(expresion !== undefined) bustExp = expresion;
  pintarBustLista();
  $("#bust-info").className = "estado";
  $("#bust-info").textContent = tr("web_bust_working");
  try{
    const r = await api.bustups_ver(id, bustExp || "", !!$("#bust-shader").checked, !$("#bust-tinte").checked);
    if(!r.ok){
      $("#bust-info").className = "estado bad";
      $("#bust-info").textContent = r.error || "—";
      return;
    }
    $("#bust-img").src = r.png || "";
    $("#bust-vacio").hidden = !!r.png;
    const sel = $("#bust-expresion");
        const exprs = r.expresiones || [];
        // el primero es el retrato por defecto (el gesto neutro del juego); luego las expresiones
        sel.innerHTML = [`<option value="" ${!r.expresion ? "selected" : ""}>${esc(tr("web_bust_defecto"))}</option>`]
          .concat(exprs.map(e =>
            `<option value="${esc(e)}" ${e === r.expresion ? "selected" : ""}>${esc(traducirExpresion(e))}</option>`)).join("");
        sel.disabled = !exprs.length && !r.capas;
        bustExp = r.expresion || "";
    $("#bust-capas").innerHTML = (r.capas || []).map(c => `
      <li><span class="paso">${esc(c.etiqueta)}</span>
          <span class="nm">${esc(c.nombre)}</span>
          <span class="k">${c.fiable ? fmt(tr("web_bust_medido"), c.difiere) : esc(tr("web_bust_no_fiable"))}</span></li>`).join("");
    $("#bust-info").className = "estado ok";
    $("#bust-info").textContent = `${r.lienzo[0]}×${r.lienzo[1]} · ${(r.capas || []).length} ${tr("web_bust_capas")}`;
    $("#bust-nota").textContent = (r.avisos || []).length
      ? tr("web_bust_aviso_hoja") + "  ·  " + r.avisos.join(" · ") : "";
    $("#bust-revelar").dataset.ruta = "";
  }catch(e){
    $("#bust-info").className = "estado bad";
    $("#bust-info").textContent = String(e);
  }
}

async function exportarBustup(){
  if(!bustSel) return;
  const r = await api.bustups_exportar(bustSel, bustExp || "", !!$("#bust-shader").checked, !$("#bust-tinte").checked);
  $("#bust-info").className = "estado " + (r.ok ? "ok" : "bad");
  $("#bust-info").textContent = r.ok ? fmt(tr("web_bust_exportado"), r.destino) : (r.error || "—");
  if(r.ok) $("#bust-revelar").dataset.ruta = r.destino;
}

async function exportarBustupTodas(){
  if(!bustSel) return;
  const btn = $("#bust-exportar-todas");
  if(btn){ btn.disabled = true; btn.textContent = "Exporting..."; }
  $("#bust-info").className = "estado";
  $("#bust-info").textContent = "Exporting all expressions with shader...";
  const r = await api.bustups_exportar_todas(bustSel, !!$("#bust-shader").checked, !$("#bust-tinte").checked);
  if(btn){ btn.disabled = false; btn.textContent = "All expressions"; }
  if(r.ok){
    $("#bust-info").className = "estado ok";
    $("#bust-info").textContent = `${r.hechas.length}/${r.total} expressions exported to ${r.carpeta}`;
  } else {
    $("#bust-info").className = "estado bad";
    $("#bust-info").textContent = r.error || "Export failed";
  }
}

/* ------------------------------------------------------------------ arranque */
async function iniciar(){
  const tx = await api.textos();
  T = {en: tx.en};
  pintarTextos();
  textoBotonExtraer();

  const est = await api.estado();
  $("#foot-index").textContent = fmt(tr("web_foot_index"), num(est.n_bundles));
  var _nb = $("#note-bundles"); if(_nb) _nb.textContent = tr("web_note") + (est.origen === "disco" ? "  " + tr("web_source_disk") : "");

  tipos = await api.tipos();
  bundles = await api.bundles();
  pintarChips(); pintarNovedades(); pintarLista();
  await refrescarRecursos();

  // listener de eventos
  [["#q", pintarLista, "input"],
   ["#btn-solo-nuevos", () => { soloNuevos = !soloNuevos; pintarNovedades(); pintarLista(); }, "click"],
   ["#btn-marcar-vistos", async () => {
      const r = await api.marcar_novedades();
      bundles = await api.bundles();       // ya nada queda marcado como nuevo
      soloNuevos = false;
      pintarNovedades(); pintarLista();
      $("#count").textContent = fmt(tr("web_new_done"), num(r.marcados));
    }, "click"],
   ["#d-close", () => { selId = null; $("#detail").hidden = true; pintarLista(); }, "click"],
   ["#d-open", async () => { $("#insp-path").value = lastBundle || ""; ir("inspector"); await inspeccionar(lastBundle); }, "click"],
   ["#d-extract", async () => { const r = await api.exportar(lastBundle, "mesh,tex2d"); $("#d-assets").insertAdjacentHTML("afterbegin", `<li><u></u><span class="k" style="text-align:left">${esc(r.error ? fmt(tr("web_error"), r.error) : fmt(tr("web_media_done"), r.destino))}</span></li>`); }, "click"],
   ["#d-reveal", () => api.revelar(lastBundle), "click"],
   ["#insp-open", () => abrirConMotor($("#insp-path").value.trim()), "click"],
   ["#insp-choose", async () => { const p = await api.elegir_bundle(); if(p){ $("#insp-path").value = p; inspeccionar(p); } }, "click"],
   ["#insp-export", () => { const tiposRe = new Set(); inspSel.forEach(i => { const tp = inspFilas[i].tipo; tiposRe.add(MAP_TIPO[tp] || tp.toLowerCase()); }); if(tiposRe.size) inspectorExportar([...tiposRe].join(",")); }, "click"],
   ["#insp-export-all", () => { const all = new Set(inspFilas.map(r => MAP_TIPO[r.tipo] || r.tipo.toLowerCase())); if(all.size) inspectorExportar([...all].join(",")); }, "click"],
   ["#res-q", buscarRecursos, "input"],
   ["#res-build", async () => { await api.iniciar_indice(); arrancarSondeo(); }, "click"],
   ["#res-cancel", async () => { await api.cancelar_tarea(); }, "click"],
   ["#tex-export", async () => { const ruta = $("#tex-bundle").value.trim(); if(!ruta) return; $("#tex-estado").className = "estado"; $("#tex-estado").textContent = tr("web_tex_working"); const r = await api.texturas_exportar(ruta); if(r.error){ $("#tex-estado").className="estado bad"; $("#tex-estado").textContent = fmt(tr("web_error"), r.error); } else { $("#tex-choose").dataset.carpeta = r.destino; await escanearTexturas(); } }, "click"],
   ["#tex-choose", async () => { const p = await api.elegir_carpeta(); if(p){ $("#tex-choose").dataset.carpeta = p; escanearTexturas(); } }, "click"],
   ["#tex-scan", escanearTexturas, "click"],
   ["#media-list", async () => { mediaDatos = await api.media(); mediaSel = -1; pintarMedia(); }, "click"],
   ["#media-usm", () => { mediaSeg = "usm"; $("#media-usm").setAttribute("aria-pressed","true"); $("#media-awb").setAttribute("aria-pressed","false"); textoBotonExtraer(); pintarMedia(); }, "click"],
   ["#media-awb", () => { mediaSeg = "awb"; $("#media-awb").setAttribute("aria-pressed","true"); $("#media-usm").setAttribute("aria-pressed","false"); textoBotonExtraer(); pintarMedia(); }, "click"],
   ["#media-extract", async () => { const l = mediaDatos[mediaSeg] || []; if(mediaSel < 0 || !l[mediaSel]) return; const m = l[mediaSel]; if(mediaSeg === "usm") await api.iniciar_video(m.ruta); else await api.iniciar_audio(m.ruta); arrancarSondeo(); }, "click"],
   ["#media-out", () => api.abrir_salida(), "click"],
   ["#deps-open", abrirDeps, "click"],
   ["#deps-cerrar", () => { $("#deps-modal").hidden = true; }, "click"],
   ["#deps-bajar", () => { api.instalar_dependencias(); arrancarSondeoDeps(); }, "click"],
   ["#bulk-todo", () => {
      const todas = (bulkInv ? bulkInv.categorias : []).filter(c => c.id !== "other" && c.bundles > 0).map(c => c.id);
      bulkSel = (bulkSel.size >= todas.length) ? new Set() : new Set(todas);
      pintarBulkCategorias();
    }, "click"],
   ["#bulk-filtro", textoBulkEstimado, "input"],
   ["#bulk-elegir", async () => {
      const r = await api.elegir_destino_bulk();
      if(r){ bulkDestino = r.destino; pintarBulkEstado({destino: r.destino, libre: r.libre, carpetas: [], hechos: 0});
             pintarBulkEstado(await api.bulk_estado(r.destino)); }
    }, "click"],
   ["#bulk-empezar", empezarBulk, "click"],
   ["#bulk-cancelar", () => api.cancelar_tarea(), "click"],
   ["#bulk-abrir", () => api.abrir_destino_bulk(bulkDestino || null), "click"],
   ["#retr-sacar", empezarRetratos, "click"],
   ["#retr-cancelar", () => api.cancelar_tarea(), "click"],
   ["#retr-abrir", () => api.abrir_carpeta_retratos(), "click"],
   ["#bust-q", pintarBustLista, "input"],
   ["#bust-expresion", () => verBustup(bustSel, $("#bust-expresion").value), "change"],
      ["#bust-shader", () => { if(bustSel) verBustup(bustSel); }, "change"],
   ["#bust-tinte", () => { if(bustSel) verBustup(bustSel); }, "change"],
   ["#bust-exportar", exportarBustup, "click"],
   ["#bust-exportar-todas", exportarBustupTodas, "click"],
   ["#bust-revelar", () => { const r = $("#bust-revelar").dataset.ruta; if(r) api.revelar_fichero(r); }, "click"],
   ["#bust-carpeta", async () => {
      const r = await api.bustups_elegir_carpeta();
      if(!r) return;
      bustLista = null;                       // el indice cambia: se vuelve a pedir la lista
      $("#bust-estado").className = "estado " + (r.texturas ? "ok" : "warn");
      $("#bust-estado").textContent = r.texturas ? r.carpeta : tr("web_bust_none");
      await abrirBustups();
    }, "click"],
   // ------------------------------------------------------------------ Settings
   ["#settings-game-choose", async () => {
      const r = await api.settings_elegir_juego();
      const el = $("#settings-game-status"), inp = $("#settings-game-path");
      if(!r) return;
      if(r.ok){ if(el){ el.style.color = "var(--green)"; el.textContent = "✓ " + r.juego; } if(inp) inp.value = r.juego; }
      else { if(el){ el.style.color = "var(--red)"; el.textContent = "✗ " + (r.error || "error"); } }
    }, "click"],
   ["#settings-game-detect", async () => {
      const r = await api.settings_detectar_juego();
      const el = $("#settings-game-status"), inp = $("#settings-game-path");
      if(!r) return;
      if(r.ok){ if(el){ el.style.color = "var(--green)"; el.textContent = "✓ " + r.juego; } if(inp) inp.value = r.juego; }
      else { if(el){ el.style.color = "var(--red)"; el.textContent = "✗ " + (r.error || "error"); } }
    }, "click"],
   ["#settings-tex-choose", async () => {
      const r = await api.settings_elegir_texturas();
      const el = $("#settings-tex-status"), inp = $("#settings-tex-path");
      if(r && r.ok){ if(el){ el.style.color = "var(--green)"; el.textContent = "✓ " + r.texturas; } if(inp) inp.value = r.texturas; }
    }, "click"],
   ["#settings-out-choose", async () => {
      const r = await api.settings_elegir_salida();
      const inp = $("#settings-out-path");
      if(r && r.ok && inp) inp.value = r.salida;
    }, "click"]
  ].forEach(([sel_, fn, ev]) => { const el = $(sel_); if(el) el.addEventListener(ev, fn); });

  // cargar estado de Settings al abrir
  api.settings_estado().then(s => {
    const g = $("#settings-game-status"), t = $("#settings-tex-status"), o = $("#settings-out-status");
    const gp = $("#settings-game-path"), tp = $("#settings-tex-path"), op = $("#settings-out-path");
    if(g){ g.style.color = s.juego_encontrado ? "var(--green)" : "var(--red)"; g.textContent = s.juego_encontrado ? "✓ " + s.juego : "✗ not found"; }
    if(gp) gp.value = s.juego || "";
    if(tp) tp.value = s.texturas || "";
    if(op) op.value = s.salida || "";
    if(t){ t.textContent = s.texturas; }
    if(o){ o.textContent = s.salida; }
  }).catch(()=>{});

  // cerrar la ventana de dependencias con Escape (y no dejar el fondo clickeable)
  $("#deps-modal").addEventListener("click", e => { if(e.target.id === "deps-modal") $("#deps-modal").hidden = true; });
  document.addEventListener("keydown", e => { if(e.key === "Escape") $("#deps-modal").hidden = true; });

  $$("#nav button").forEach(b => b.onclick = () => ir(b.dataset.p));
  // Settings button lives outside #nav (in the sidebar footer)
  $$(".settings-btn").forEach(b => b.onclick = () => ir(b.dataset.p));
  $("#insp-path").addEventListener("keydown", e => { if(e.key === "Enter") inspeccionar(e.target.value.trim()); });

  // carga inicial de media (para que la pestana no salga vacia)
  mediaDatos = await api.media(); pintarMedia();
}

function listo(){
  api = window.pywebview.api;
  iniciar().catch(e => { document.body.insertAdjacentHTML("beforeend",
    `<div class="estado bad" style="position:fixed;bottom:12px;left:12px;right:12px">${esc("init error: " + e)}</div>`); });
}
if(window.pywebview && window.pywebview.api){ listo(); }
else { window.addEventListener("pywebviewready", listo); }

/* ═══ TEMAS E IDIOMA ═══ */
function setTheme(t, el) {
  document.body.className = t === 'pink' ? '' : 'theme-' + t;
  document.querySelectorAll('#theme-grid .tdot').forEach(d => d.classList.remove('on'));
  if (el) el.classList.add('on');
  try { localStorage.setItem('p5x-theme', t); } catch(e) {}
}
function setLang(l) {
  document.querySelectorAll('.lang-btn').forEach(b => {
    const isOn = b.textContent.trim().toLowerCase() === l;
    b.classList.toggle('on', isOn);
    b.style.background = isOn ? 'var(--accent)' : 'var(--accent-pale)';
    b.style.color = isOn ? '#fff' : 'var(--text2)';
  });
}
// Restaurar tema guardado
(function(){
  try {
    const t = localStorage.getItem('p5x-theme') || 'black';
    if (t !== 'pink') setTheme(t, document.querySelector(`#theme-grid .tdot[data-t="${t}"]`));
  } catch(e) {}
})();

/* ═══ TRADUCCIÓN DE EXPRESIONES ═══ */
const EXPRESIONES_EN = {
  tongchang: "Default", xiao: "Smile", xiao2: "Smile 2", weixiao: "Grin",
  shengqi: "Angry", fennu: "Furious", nu: "Rage",
  jingsong: "Relaxed", jingya: "Surprised", jingya2: "Surprised 2",
  renzhen: "Serious", kuqi: "Crying", kuxiao: "Bitter Smile",
  beiai: "Sad", beiai1: "Sad 1", beiai2: "Sad 2", beishang: "Sorrow", beishang1: "Sorrow 1", beishang2: "Sorrow 2",
  xingfen: "Excited", tongku: "Pain", tongku2: "Pain 2",
  huangzhang: "Flustered", baoyuan: "Complaining", xiyue: "Joy",
  kuxiaohaixiu: "Shy Smile", jingyahaixiu: "Shy Surprise",
  jingyahaixiu2: "Shy Surprise 2", beishanghaixiu: "Shy Sad",
  default: "Default", base: "Base",
};
function traducirExpresion(exp) {
  return EXPRESIONES_EN[exp] || exp;
}

/* ═══ TEXTURE BROWSER ═══ */
let texCarpetaActual = "";
let texImagenes = [];
let texFiltro = "all";
let texSeleccionada = null;

async function texNavegar(subcarpeta) {
  texCarpetaActual = subcarpeta || "";
  // Marcar carpeta activa en el sidebar
  $$("#tex-folder-tree .folder-item").forEach(f =>
    f.classList.toggle("active", (f.dataset.path || "") === texCarpetaActual));
  // Actualizar breadcrumb
  const bc = $("#tex-breadcrumb");
  const partes = texCarpetaActual ? texCarpetaActual.split("/") : [];
  bc.innerHTML = `<span class="bc-root" onclick="texNavegar('')">${esc(tr("web_tex_root"))}</span>` +
    partes.map((p, i) => {
      const ruta = partes.slice(0, i + 1).join("/");
      const last = i === partes.length - 1;
      return ` <span class="bc-sep">›</span> <span class="bc-item ${last ? "bc-current" : ""}" onclick="texNavegar('${esc(ruta)}')">${esc(p)}</span>`;
    }).join("");
  await texCargarImagenes();
}

async function texCargarImagenes() {
  const est = $("#tex-estado");
  est.textContent = tr("web_bust_working");
  try {
    const r = await api.texturas_listar(texCarpetaActual);
    texImagenes = r.imagenes || [];
    texPintarGaleria();
  } catch(e) {
    est.className = "estado bad";
    est.textContent = String(e);
  }
}

function texPintarGaleria() {
  const q = ($("#tex-search").value || "").trim().toLowerCase();
  let filtradas = texImagenes;
  if(q) filtradas = filtradas.filter(i => (i.nombre || i.name || "").toLowerCase().includes(q));
  if(texFiltro === "png") filtradas = filtradas.filter(i => /\.png$/i.test(i.nombre || i.name || ""));
  else if(texFiltro === "jpg") filtradas = filtradas.filter(i => /\.jpe?g$/i.test(i.nombre || i.name || ""));
  else if(texFiltro === "large") filtradas = filtradas.filter(i => (i.ancho || 0) > 500 || (i.alto || 0) > 500);

  // Info
  const total = filtradas.length;
  const peso = filtradas.reduce((s, i) => s + (i.bytes || i.size || 0), 0);
  $("#tex-count").textContent = `${total} · ${(peso/1024/1024).toFixed(1)} MB`;

  // Galería
  const g = $("#tex-galeria");
  if(!filtradas.length) {
    g.innerHTML = `<div style="grid-column:1/-1;text-align:center;padding:30px;color:var(--text3);font-size:12px">${esc(tr("web_res_empty"))}</div>`;
    return;
  }
  g.innerHTML = filtradas.slice(0, 500).map((i, idx) => {
    const nombre = i.nombre || i.name || "";
    const ruta = i.ruta || i.path || "";
    return `<figure data-idx="${idx}" data-nombre="${esc(nombre)}" data-ruta="${esc(ruta)}" data-kb="${((i.bytes || i.size || 0)/1024).toFixed(0)}" data-ancho="${i.ancho || i.width || 0}" data-alto="${i.alto || i.height || 0}">
      <img loading="lazy" src="file:///${esc(ruta).split(String.fromCharCode(92)).join('/')}" onerror="this.style.opacity=0.2">
      <figcaption class="tex-caption">${esc(nombre)}</figcaption>
    </figure>`;
  }).join("");

  // Click en imagen
  $$("#tex-galeria figure").forEach(f => f.onclick = () => texSeleccionar(f));
  $("#tex-estado").className = "estado ok";
  $("#tex-estado").textContent = fmt(tr("web_bust_n"), num(total));
}

function texSeleccionar(fig) {
  $$("#tex-galeria figure").forEach(f => f.classList.remove("selected"));
  fig.classList.add("selected");
  const nombre = fig.dataset.nombre;
  const ruta = fig.dataset.ruta;
  const kb = fig.dataset.kb;
  const ancho = fig.dataset.ancho;
  const alto = fig.dataset.alto;
  texSeleccionada = { nombre, ruta, kb, ancho, alto };

  $("#tex-details-empty").hidden = true;
  $("#tex-details-body").hidden = false;
  $("#tex-details-img").src = `file:///${ruta.split(String.fromCharCode(92)).join('/')}`;
  $("#tex-details-name").textContent = nombre;
  $("#tex-details-size").textContent = `${kb} KB`;
  $("#tex-details-dims").textContent = `${ancho} × ${alto}`;
  $("#tex-details-path").textContent = ruta;
  $("#tex-details-path").title = ruta;
  $("#tex-details-reveal").dataset.ruta = ruta;
  $("#tex-details-copy").dataset.ruta = ruta;
}

// Eventos del texture browser
document.addEventListener("DOMContentLoaded", () => {
  // Navegación por carpetas
  $$("#tex-folder-tree .folder-item").forEach(f =>
    f.onclick = () => texNavegar(f.dataset.path || ""));

  // Búsqueda
  const busca = $("#tex-search");
  if(busca) busca.addEventListener("input", () => texPintarGaleria());

  // Filtros
  $$("#tex-filters .chip").forEach(c => c.onclick = () => {
    $$("#tex-filters .chip").forEach(x => x.classList.remove("active"));
    c.classList.add("active");
    texFiltro = c.dataset.f;
    texPintarGaleria();
  });

  // Botones de detalles
  const reveal = $("#tex-details-reveal");
  if(reveal) reveal.onclick = () => {
    const r = reveal.dataset.ruta;
    if(r) api.revelar_fichero(r);
  };
  const copy = $("#tex-details-copy");
  if(copy) copy.onclick = () => {
    const r = copy.dataset.ruta;
    if(r) navigator.clipboard.writeText(r).catch(() => {});
  };
});

/* ═══ PANTALLA DE CARGA ═══ */
function loadingSet(pct, status, logLine) {
  const fill = document.getElementById("loading-bar-fill");
  const st = document.getElementById("loading-status");
  const counter = document.getElementById("loading-counter");
  const log = document.getElementById("loading-log");
  if(fill) fill.style.width = Math.min(100, Math.max(0, pct)) + "%";
  if(st && status) st.textContent = status;
  if(log && logLine) {
    const div = document.createElement("div");
    div.textContent = logLine;
    log.appendChild(div);
    log.scrollTop = log.scrollHeight;
    counter.textContent = log.childElementCount + " steps";
  }
}

function loadingDone() {
  const el = document.getElementById("loading-screen");
  if(el) {
    el.classList.add("hidden");
    setTimeout(() => { el.style.display = "none"; }, 600);
  }
}

async function iniciarConLoading() {
  loadingSet(5, "Starting…");
  await new Promise(r => setTimeout(r, 100));

  loadingSet(15, "Reading game bundles…", "Reading bundle catalog from disk");
  await new Promise(r => setTimeout(r, 200));

  try {
    const est = await api.estado();
    loadingSet(35, `Found ${num(est.bundles?.length || 0)} bundles`, `Loaded ${est.bundles?.length || 0} bundles`);
  } catch(e) {
    loadingSet(35, "Reading bundles…", "Bundle catalog loaded");
  }
  await new Promise(r => setTimeout(r, 150));

  loadingSet(50, "Loading texture index…", "Building texture index");
  await new Promise(r => setTimeout(r, 150));

  loadingSet(65, "Preparing shader profiles…", "Loaded 216 shader profiles");
  await new Promise(r => setTimeout(r, 100));

  loadingSet(80, "Loading UI translations…", "Translations loaded (ES/EN)");
  await new Promise(r => setTimeout(r, 100));

  loadingSet(95, "Almost ready…", "Rendering interface");
  await new Promise(r => setTimeout(r, 200));

  loadingSet(100, "Ready!", "Startup complete");
  setTimeout(loadingDone, 300);
}

// Arrancar loading al inicio
if(document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => {
    setTimeout(iniciarConLoading, 50);
  });
} else {
  setTimeout(iniciarConLoading, 50);
}


/* ═══ AUTO-CHECK UPDATES ON STARTUP ═══ */
async function comprobarUpdate() {
  try {
    const r = await api.verificar_update();
    if(r.hay_update) {
      const modal = document.getElementById("deps-modal");
      const lista = document.getElementById("deps-lista");
      const consola = document.getElementById("deps-consola");
      const peso = document.getElementById("deps-peso");
      if(modal) {
        modal.hidden = false;
        if(peso) peso.textContent = `Update disponible: v${r.version_nueva} (actual: v${r.version_actual})`;
        if(lista) lista.innerHTML = `<li style="padding:12px"><b>Update disponible</b><br>v${r.version_nueva} — ${r.version_actual}<br><br>${esc(r.notas || '')}</li>`;
        if(consola) consola.textContent = `Nueva versión en GitHub: ${r.url}`;
        const acciones = modal.querySelector(".fila");
        if(acciones && !document.getElementById("btn-update-app")) {
          const btn = document.createElement("button");
          btn.id = "btn-update-app";
          btn.className = "accion";
          btn.textContent = "Descargar Update";
          btn.onclick = () => { api.abrir_url_update(r.url); };
          acciones.insertBefore(btn, acciones.firstChild);
        }
      }
    }
  } catch(e) {}
}
setTimeout(comprobarUpdate, 2000);
