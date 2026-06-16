// sisCalibracao — SDK + helpers de UI (vanilla). Inspirado em xcmasm-sdk.js.
const API = "/api/v1";

// ── Tema (claro/escuro) ─────────────────────────────────────────────────────
const THEME_KEY = "siscalib-theme";
function temaInicial() {
  const s = localStorage.getItem(THEME_KEY);
  if (s === "light" || s === "dark") return s;
  return window.matchMedia && window.matchMedia("(prefers-color-scheme: light)").matches
    ? "light" : "dark";
}
function aplicarTema(t) { document.documentElement.setAttribute("data-theme", t); }
function temaAtual() {
  return document.documentElement.getAttribute("data-theme") === "light" ? "light" : "dark";
}
function atualizarIconeTema() {
  const b = document.getElementById("themeToggle");
  if (!b) return;
  const claro = temaAtual() === "light";
  b.innerHTML = `<i class="bi bi-${claro ? "moon-stars" : "sun"}"></i>`;
  b.title = claro ? "Mudar para modo escuro" : "Mudar para modo claro";
  b.setAttribute("aria-label", b.title);
}
function alternarTema() {
  const novo = temaAtual() === "light" ? "dark" : "light";
  localStorage.setItem(THEME_KEY, novo);
  aplicarTema(novo);
  atualizarIconeTema();
}
// aplica o tema o quanto antes (app.js é o 1º script do body) → evita flash
aplicarTema(temaInicial());

const SDK = {
  async get(path, params) {
    const url = new URL(API + path, location.origin);
    if (params) Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== "") url.searchParams.set(k, v);
    });
    const r = await fetch(url);
    if (!r.ok) throw new Error("HTTP " + r.status);
    return r.json();
  },
  async upload(path, file) {
    const fd = new FormData();
    fd.append("arquivo", file);
    const r = await fetch(API + path, { method: "POST", body: fd });
    if (!r.ok) throw new Error("HTTP " + r.status);
    return r.json();
  },
};

const STATUS_BADGE = {
  VENCIDO: "red", A_VENCER_7: "orange", A_VENCER_30: "amber",
  A_VENCER_60: "amber", VALIDO: "green", SEM_DATA: "slate", BAIXADO: "slate",
};
const STATUS_LABEL = {
  VENCIDO: "Vencido", A_VENCER_7: "A vencer 7d", A_VENCER_30: "A vencer 30d",
  A_VENCER_60: "A vencer 60d", VALIDO: "Válido", SEM_DATA: "Sem data", BAIXADO: "Baixado",
};

function badgeStatus(s) {
  return `<span class="bdg ${STATUS_BADGE[s] || "slate"}">${STATUS_LABEL[s] || s}</span>`;
}
function esc(v) {
  return v == null ? "" : String(v).replace(/[&<>"]/g,
    c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
}
function fmtData(iso) { return iso ? iso.split("-").reverse().join("/") : "—"; }

const NAV = [
  ["index.html", "speedometer2", "Dashboard"],
  ["inventario.html", "list-ul", "Inventário"],
  ["calibracao.html", "clipboard-check", "Calibrações"],
  ["laboratorios.html", "building", "Laboratórios"],
  ["contratos.html", "file-earmark-text", "Contratos"],
  ["catalogo.html", "tags", "Catálogo"],
  ["cadastro.html", "plus-lg", "Novo"],
  ["alertas.html", "bell", "Alertas"],
  ["importar.html", "upload", "Importar"],
];

const SB_KEY = "siscalib-sb-collapsed";

function atualizarIconeCollapse() {
  const sb = document.getElementById("sb");
  const b = document.getElementById("sbCollapse");
  if (!sb || !b) return;
  const col = sb.classList.contains("collapsed");
  b.innerHTML = `<i class="bi bi-chevron-${col ? "right" : "left"}"></i>`;
  b.title = col ? "Expandir menu" : "Recolher menu";
  b.setAttribute("aria-label", b.title);
}

function montarShell(ativo) {
  const links = NAV.map(([h, ic, lbl]) =>
    `<a href="${h}" class="${h === ativo ? "act" : ""}" title="${lbl}"><i class="bi bi-${ic}"></i><span class="lbl">${lbl}</span></a>`
  ).join("");
  document.body.insertAdjacentHTML("afterbegin", `
    <div class="sb" id="sb">
      <div class="sb-logo"><img src="vendor/icons/gauge.png" alt=""><span class="lbl">sisCalibracao</span></div>
      <nav class="sb-nav">${links}</nav>
      <div class="sb-foot">
        <div class="sb-foot-btns">
          <button id="themeToggle" class="sb-btn" type="button"></button>
          <button id="sbCollapse" class="sb-btn" type="button"></button>
        </div>
        <div class="sb-ver">sisCalibracao.v00.26.06.16<br>CMASM-132</div>
      </div>
    </div>`);
  const sb = document.getElementById("sb");
  if (localStorage.getItem(SB_KEY) === "1") sb.classList.add("collapsed");
  document.getElementById("themeToggle").addEventListener("click", alternarTema);
  document.getElementById("sbCollapse").addEventListener("click", () => {
    sb.classList.toggle("collapsed");
    localStorage.setItem(SB_KEY, sb.classList.contains("collapsed") ? "1" : "0");
    atualizarIconeCollapse();
  });
  atualizarIconeTema();
  atualizarIconeCollapse();
}

// ── Domínios e IGP (cadastro) ───────────────────────────────────────────────
SDK.post = async (path, body) => {
  const r = await fetch(API + path, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (r.status === 409) throw new Error("Código patrimonial já existe");
  if (!r.ok) throw new Error("HTTP " + r.status);
  return r.json();
};
SDK.put = async (path, body) => {
  const r = await fetch(API + path, {
    method: "PUT", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (r.status === 409) throw new Error("Código patrimonial já existe");
  if (!r.ok) throw new Error("HTTP " + r.status);
  return r.json();
};

const CLASSE_LABEL = {
  MAXIMA: "Prioridade máxima", MEDIA: "Média", BAIXA: "Baixa",
  MUITO_BAIXA: "Muito baixa", NAO_CLASSIFICADO: "Não classificado",
};

// Espelha backend/criticidade.py
function calcIgpClient(fu, nc, ab, cm, ci) {
  const v = [fu, nc, ab, cm, ci];
  if (v.some(x => !x)) return { igp: null, classe: "NAO_CLASSIFICADO" };
  const igp = fu * 1 + nc * 2 + ab * 1 + cm * 2 + ci * 1;
  let classe = "MUITO_BAIXA";
  if (igp >= 18) classe = "MAXIMA";
  else if (igp >= 14) classe = "MEDIA";
  else if (igp >= 11) classe = "BAIXA";
  return { igp, classe };
}

// ── Tabela reutilizável (busca + filtro + ordenação + export + checkbox) ─────
// cfg: { el, colunas:[{key,label,filtro?,ordenar?(=true),valor?(r),render?(r),ordem?[]}],
//        dados?, buscaValor?(r)=>str, checkbox?, acoes?(r)=>html, onClickLinha?(r),
//        exportNome?, semExport? }
// Reusa as classes CSS .toolbar/.export-grp/.cont-itens/.bi-funnel/.filtro-pop (mesma aparência).
function _semAcento(s) { return String(s ?? "").normalize("NFKD").replace(/[̀-ͯ]/g, "").toLowerCase(); }

function montarTabela(cfg) {
  const cols = cfg.colunas;
  const st = { todos: cfg.dados || [], vis: [], filtros: {}, ord: { col: null, dir: null }, sel: new Set() };
  const idDe = r => r.id ?? r.item_id ?? JSON.stringify(r);
  const val = (r, c) => (c.valor ? c.valor(r) : (r[c.key] == null ? "" : r[c.key]));
  const buscaVal = cfg.buscaValor || (r => cols.map(c => val(r, c)).join(" "));

  const expBtns = cfg.semExport ? "" :
    `<div class="export-grp"><span class="muted">Exportar:</span>
       <button class="btn ghost" data-exp="csv">CSV</button></div>`;
  cfg.el.innerHTML = `
    <div class="toolbar">
      <input type="search" class="tb-busca" placeholder="Buscar...">
      <button class="btn ghost tb-limpar"><i class="bi bi-funnel"></i> Limpar</button>
      ${expBtns}
      <span class="cont-itens tb-cont" style="margin-left:auto"></span>
    </div>
    <div class="twrap"><table class="tb-tab"><thead><tr>
      ${cfg.checkbox ? '<th class="chk"><input type="checkbox" class="tb-all"></th>' : ""}
      ${cols.map(c => `<th data-col="${c.key}"${c.filtro === false ? "" : ` data-filtro="${c.key}"`}>${esc(c.label)}</th>`).join("")}
      ${cfg.acoes ? "<th>Ações</th>" : ""}
    </tr></thead><tbody></tbody></table></div>`;

  const busca = cfg.el.querySelector(".tb-busca");
  const cont = cfg.el.querySelector(".tb-cont");
  const tbody = cfg.el.querySelector("tbody");
  const all = cfg.el.querySelector(".tb-all");
  const ncols = cols.length + (cfg.checkbox ? 1 : 0) + (cfg.acoes ? 1 : 0);

  function cmp(a, b, c) {
    if (c.ordem) return c.ordem.indexOf(String(val(a, c))) - c.ordem.indexOf(String(val(b, c)));
    const x = val(a, c), y = val(b, c);
    if (typeof x === "number" && typeof y === "number") return x - y;
    const sx = _semAcento(x), sy = _semAcento(y);
    return sx < sy ? -1 : sx > sy ? 1 : 0;
  }
  function visiveis() {
    let r = st.todos;
    if (busca.value.trim()) { const b = _semAcento(busca.value); r = r.filter(x => _semAcento(buscaVal(x)).includes(b)); }
    for (const [k, sel] of Object.entries(st.filtros))
      if (sel && sel.size) { const c = cols.find(x => x.key === k); r = r.filter(x => sel.has(String(val(x, c)))); }
    if (st.ord.col) { const c = cols.find(x => x.key === st.ord.col), s = st.ord.dir === "desc" ? -1 : 1; r = [...r].sort((a, b) => s * cmp(a, b, c)); }
    return r;
  }
  function cabecalhos() {
    cfg.el.querySelectorAll("thead th[data-col]").forEach(th => {
      const c = cols.find(x => x.key === th.dataset.col);
      const base = th.dataset.label || (th.dataset.label = th.textContent.trim());
      let ind = th.querySelector(".sort-ind");
      if (!ind) {
        th.textContent = base;
        ind = document.createElement("span"); ind.className = "sort-ind"; th.appendChild(ind);
        if (c.filtro !== false) { const f = document.createElement("i"); f.className = "bi bi-funnel"; f.dataset.filtro = c.key; th.append(" ", f); }
      }
      ind.textContent = st.ord.col === c.key ? (st.ord.dir === "asc" ? " ▲" : " ▼") : "";
      const fn = th.querySelector("i[data-filtro]");
      if (fn) fn.className = st.filtros[c.key]?.size ? "bi bi-funnel-fill ativo" : "bi bi-funnel";
    });
  }
  function render() {
    tbody.innerHTML = st.vis.map(r => `<tr data-id="${esc(idDe(r))}">
      ${cfg.checkbox ? `<td class="chk"><input type="checkbox" class="tb-row" ${st.sel.has(idDe(r)) ? "checked" : ""}></td>` : ""}
      ${cols.map(c => `<td>${c.render ? c.render(r) : esc(val(r, c))}</td>`).join("")}
      ${cfg.acoes ? `<td>${cfg.acoes(r)}</td>` : ""}
    </tr>`).join("") || `<tr><td colspan="${ncols}" class="muted">Nada encontrado.</td></tr>`;
  }
  function refrescar() {
    st.vis = visiveis();
    cont.textContent = `${st.vis.length}/${st.todos.length}`;
    cabecalhos(); render();
    if (all) all.checked = false;
  }

  // ordenação
  cfg.el.querySelector("thead").addEventListener("click", e => {
    if (e.target.closest(".bi-funnel,.bi-funnel-fill")) return;
    const th = e.target.closest("th[data-col]"); if (!th) return;
    const c = cols.find(x => x.key === th.dataset.col); if (c.ordenar === false) return;
    if (st.ord.col !== c.key) st.ord = { col: c.key, dir: "asc" };
    else if (st.ord.dir === "asc") st.ord.dir = "desc";
    else st.ord = { col: null, dir: null };
    refrescar();
  });
  // filtro popover (reusa _tbPopover global)
  cfg.el.addEventListener("click", e => {
    const g = e.target.closest(".bi-funnel,.bi-funnel-fill"); if (!g) return;
    e.stopPropagation();
    const c = cols.find(x => x.key === g.dataset.filtro); if (!c) return;
    _tbPopover(c, g, st, val, refrescar);
  });
  // busca
  let tmr; busca.oninput = () => { clearTimeout(tmr); tmr = setTimeout(refrescar, 200); };
  // limpar
  cfg.el.querySelector(".tb-limpar").onclick = () => { st.filtros = {}; busca.value = ""; st.ord = { col: null, dir: null }; refrescar(); };
  // checkbox
  if (cfg.checkbox) {
    all.onchange = () => { if (all.checked) st.vis.forEach(r => st.sel.add(idDe(r))); else st.sel.clear(); render(); };
    tbody.addEventListener("change", e => {
      if (!e.target.classList.contains("tb-row")) return;
      const id = e.target.closest("tr").dataset.id;
      if (e.target.checked) st.sel.add(id); else st.sel.delete(id);
    });
  }
  // clique linha
  if (cfg.onClickLinha) tbody.addEventListener("click", e => {
    if (e.target.closest("input,button,a")) return;
    const tr = e.target.closest("tr[data-id]"); if (!tr) return;
    const r = st.vis.find(x => String(idDe(x)) === tr.dataset.id); if (r) cfg.onClickLinha(r);
  });
  // export CSV (selecionados, ou todos visíveis)
  if (!cfg.semExport) cfg.el.querySelector(".export-grp").addEventListener("click", e => {
    if (!e.target.closest("[data-exp]")) return;
    const base = st.sel.size ? st.vis.filter(r => st.sel.has(idDe(r))) : st.vis;
    if (!base.length) { alert("Nada a exportar."); return; }
    const cab = cols.map(c => c.label);
    const linhas = base.map(r => cols.map(c => {
      const v = String(val(r, c) ?? "").replace(/"/g, '""');
      return /[",\n]/.test(v) ? `"${v}"` : v;
    }));
    const csv = "﻿" + [cab, ...linhas].map(l => l.join(",")).join("\r\n");
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
    a.download = (cfg.exportNome || "tabela") + ".csv";
    document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(a.href);
  });

  refrescar();
  return { setDados(d) { st.todos = d; st.sel.clear(); refrescar(); }, refrescar, selecionados: () => [...st.sel] };
}

// popover de filtro multi-seleção genérico (usado por montarTabela)
function _tbFechaPop() { document.getElementById("tbPop")?.remove(); document.removeEventListener("click", _tbForaPop, true); }
function _tbForaPop(e) { const p = document.getElementById("tbPop"); if (p && !p.contains(e.target) && !e.target.closest("[data-filtro]")) _tbFechaPop(); }
function _tbPopover(c, ancora, st, val, refrescar) {
  _tbFechaPop();
  let valores = [...new Set(st.todos.map(r => String(val(r, c))).filter(v => v !== ""))];
  if (c.ordem) valores.sort((a, b) => c.ordem.indexOf(a) - c.ordem.indexOf(b)); else valores.sort();
  const sel = st.filtros[c.key] || new Set();
  const rot = v => c.rotulo ? c.rotulo(v) : v;
  const pop = document.createElement("div");
  pop.id = "tbPop"; pop.className = "filtro-pop";
  pop.innerHTML = `<div class="filtro-acts"><button type="button" data-act="all">Marcar todos</button><button type="button" data-act="none">Limpar</button></div>
    <div class="filtro-itens">${valores.map(v => `<label><input type="checkbox" value="${esc(v)}" ${sel.has(v) ? "checked" : ""}> ${esc(rot(v))}</label>`).join("") || '<span class="muted">Sem valores</span>'}</div>`;
  document.body.appendChild(pop);
  const r = ancora.getBoundingClientRect();
  pop.style.top = (r.bottom + scrollY + 4) + "px"; pop.style.left = (r.left + scrollX) + "px";
  pop.addEventListener("change", () => {
    const m = [...pop.querySelectorAll("input:checked")].map(c => c.value);
    if (m.length) st.filtros[c.key] = new Set(m); else delete st.filtros[c.key];
    refrescar();
  });
  pop.querySelector('[data-act="all"]').onclick = () => { pop.querySelectorAll("input").forEach(c => c.checked = true); pop.dispatchEvent(new Event("change")); };
  pop.querySelector('[data-act="none"]').onclick = () => { pop.querySelectorAll("input").forEach(c => c.checked = false); pop.dispatchEvent(new Event("change")); };
  setTimeout(() => document.addEventListener("click", _tbForaPop, true), 0);
}
document.addEventListener("keydown", e => { if (e.key === "Escape") _tbFechaPop(); });

// ── Modal reutilizável ──────────────────────────────────────────────────────
function _escFechar(e) { if (e.key === "Escape") fecharModal(); }

function fecharModal() {
  const ov = document.getElementById("modalOv");
  if (ov) ov.remove();
  document.removeEventListener("keydown", _escFechar);
}

function abrirModal(titulo, conteudoHtml, acoesHtml) {
  fecharModal();
  const ov = document.createElement("div");
  ov.className = "modal-ov";
  ov.id = "modalOv";
  ov.innerHTML = `<div class="modal-card" role="dialog" aria-modal="true">
      <div class="modal-head"><b>${esc(titulo)}</b>
        <button class="modal-x" aria-label="Fechar">&times;</button></div>
      <div class="modal-body">${conteudoHtml}</div>
      <div class="modal-foot">${acoesHtml || ""}</div>
    </div>`;
  document.body.appendChild(ov);
  ov.addEventListener("click", e => { if (e.target === ov) fecharModal(); });
  ov.querySelector(".modal-x").onclick = fecharModal;
  document.addEventListener("keydown", _escFechar);
  return ov;
}

// ── DELETE ──────────────────────────────────────────────────────────────────
SDK.del = async (path) => {
  const r = await fetch(API + path, { method: "DELETE" });
  if (!r.ok) throw new Error("HTTP " + r.status);
  if (r.status === 204) return null;            // No Content (ex.: laboratórios)
  const txt = await r.text();
  return txt ? JSON.parse(txt) : null;
};

// ── PATCH parcial ───────────────────────────────────────────────────────────
SDK.patch = async (path, body) => {
  const r = await fetch(API + path, {
    method: "PATCH", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (r.status === 409) throw new Error("Código patrimonial já existe");
  if (!r.ok) throw new Error("HTTP " + r.status);
  return r.json();
};

// ── Exportação (download de arquivo) ────────────────────────────────────────
SDK.exportar = async (ids, formato) => {
  const r = await fetch(API + "/instrumentos/export", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ids, formato }),
  });
  if (!r.ok) throw new Error("HTTP " + r.status);
  const blob = await r.blob();
  const cd = r.headers.get("Content-Disposition") || "";
  const m = cd.match(/filename="?([^"]+)"?/);
  const nome = m ? m[1] : `inventario.${formato}`;
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = nome;
  document.body.appendChild(a); a.click(); a.remove();
  URL.revokeObjectURL(url);
};

// ── Render compartilhado da ficha (página + modal) ──────────────────────────
function renderFichaResumo(i) {
  const div = i.divergencia_flag ? ' <span class="bdg amber">divergência flag×data</span>' : "";
  const igp = i.igp == null ? "" :
    ` · <span class="bdg slate">IGP ${i.igp} — ${CLASSE_LABEL[i.classe_prioridade]}</span>`;
  const status = badgeStatus(i.status) +
    (i.dias_restantes != null ? ` <span class="muted">(${i.dias_restantes} dias)</span>` : "") +
    ` <span class="bdg slate">${esc(i.status_operacional)}</span>` + div + igp;
  const linhas = [
    ["Patrimônio", i.codigo_patrimonial], ["Série", i.serial],
    ["Marca", i.marca], ["Modelo", i.modelo],
    ["Família", i.familia_nome], ["Tipo", i.tipo_nome],
    ["Grandeza", i.grandeza_nome], ["Unidade", i.unidade_simbolo],
    ["Faixa", [i.faixa_min, i.faixa_max].some(v => v != null) ? `${i.faixa_min ?? ""} … ${i.faixa_max ?? ""}` : i.faixa],
    ["Resolução", i.resolucao], ["EMP", i.emp],
    ["Disciplina", i.disciplina], ["Setor", i.setor],
    ["Localização", [i.organizacao, i.unidade_org, i.secao, i.bancada].filter(Boolean).join(" → ")],
    ["Ciclo (meses)", i.ciclo_meses],
    ["Última calibração", fmtData(i.data_ultima_calibracao)],
    ["Validade", fmtData(i.data_validade)],
    ["Organização calibradora", i.organizacao_calibradora],
    ["Certificado", i.certificado_ref], ["Observações", i.observacoes],
  ];
  const tabela = linhas.map(([k, v]) =>
    `<tr><th style="width:200px">${k}</th><td>${esc(v) || "—"}</td></tr>`).join("");
  return `<div style="margin-bottom:12px">${status}</div>
    <div class="twrap"><table><tbody>${tabela}</tbody></table></div>
    <div style="margin-top:12px"><b>Anexos</b>
      <a class="btn ghost" href="etiquetas.html?ids=${i.id}" target="_blank" style="margin-left:10px"><i class="bi bi-tag"></i> Gerar etiqueta</a>
      <div id="secaoAnexos" data-inst="${i.id}" style="margin-top:6px"></div></div>
    <div style="margin-top:16px"><b>Calibrações</b>
      <span class="muted" style="margin-left:8px">Ciclo: ${i.ciclo_meses ?? 12} meses</span>
      <div id="secaoCalib" data-inst="${i.id}" style="margin-top:8px"></div></div>`;
}

// ── Anexos (foto + manual PDF) — upload na ficha ────────────────────────────
async function montarSecaoAnexos(instId, onChanged) {
  const box = document.getElementById("secaoAnexos");
  if (!box) return;
  let i;
  try { i = await SDK.get("/instrumentos/" + instId); }
  catch (err) { box.innerHTML = `<span class="sev-erro">${esc(err.message)}</span>`; return; }
  const linkFoto = i.foto_path
    ? `<a href="${i.foto_path}" target="_blank">ver foto</a>` : '<span class="muted">sem foto</span>';
  const linkManual = i.manual_path
    ? `<a href="${i.manual_path}" target="_blank">ver manual (PDF)</a>` : '<span class="muted">sem manual</span>';
  box.innerHTML = `
    <div style="display:flex;gap:14px;align-items:center;flex-wrap:wrap;margin-bottom:6px">
      <span><b>Foto:</b> ${linkFoto}</span>
      <label class="btn ghost" style="cursor:pointer">Enviar foto<input type="file" accept="image/*" hidden data-tipo="foto"></label>
    </div>
    <div style="display:flex;gap:14px;align-items:center;flex-wrap:wrap">
      <span><b>Manual:</b> ${linkManual}</span>
      <label class="btn ghost" style="cursor:pointer">Enviar manual (PDF)<input type="file" accept=".pdf,application/pdf" hidden data-tipo="manual"></label>
    </div>
    <div class="sev-erro" id="anexoErro" style="margin-top:6px"></div>`;
  box.querySelectorAll('input[type=file]').forEach(inp => {
    inp.onchange = async () => {
      const arq = inp.files[0];
      if (!arq) return;
      const tipo = inp.dataset.tipo;
      const erro = document.getElementById("anexoErro");
      erro.textContent = "Enviando…";
      try {
        await SDK.upload(`/instrumentos/${instId}/${tipo}`, arq);
        await montarSecaoAnexos(instId, onChanged);
        if (typeof onChanged === "function") await onChanged();
      } catch (err) {
        erro.textContent = err.message.includes("415")
          ? (tipo === "foto" ? "Envie um arquivo de imagem." : "Envie um arquivo PDF.")
          : "Falha no envio: " + err.message;
      }
    };
  });
}

// ── Calibrações (histórico + form + upload) ─────────────────────────────────
const RESULTADO_BADGE = {
  APROVADO: "green", APROVADO_COM_RESTRICOES: "amber", REPROVADO: "red",
};
const RESULTADO_LABEL = {
  APROVADO: "Aprovado", APROVADO_COM_RESTRICOES: "Aprovado c/ restrições",
  REPROVADO: "Reprovado",
};

async function renderHistoricoCalibracoes(instId, container) {
  container.innerHTML = '<span class="muted">Carregando…</span>';
  let dados;
  try {
    dados = await SDK.get(`/instrumentos/${instId}/calibracoes`);
  } catch (err) {
    container.innerHTML = `<span class="sev-erro">Falha ao carregar histórico: ${esc(err.message)}</span>`;
    return;
  }
  if (!dados.itens.length) {
    container.innerHTML = '<p class="muted">Nenhuma calibração registrada.</p>';
    return;
  }
  const linhas = dados.itens.map(c => {
    const res = `<span class="bdg ${RESULTADO_BADGE[c.resultado] || "slate"}">${RESULTADO_LABEL[c.resultado] || esc(c.resultado)}</span>`;
    const cert = c.certificado_path
      ? `<a href="/${esc(c.certificado_path)}" target="_blank" title="Abrir certificado">📎</a>`
      : "—";
    return `<tr>
      <td>${fmtData(c.data_calibracao)}</td>
      <td>${fmtData(c.data_validade)}</td>
      <td>${res}</td>
      <td>${esc(c.laboratorio) || "—"}</td>
      <td>${cert}</td>
      <td><button class="btn ghost calib-del" data-cal="${c.id}" style="padding:2px 8px">Excluir</button></td>
    </tr>`;
  }).join("");
  container.innerHTML = `<div class="twrap"><table>
    <thead><tr><th>Data</th><th>Validade</th><th>Resultado</th><th>Laboratório</th><th>Cert.</th><th>Ação</th></tr></thead>
    <tbody>${linhas}</tbody></table></div>`;
  container.querySelectorAll(".calib-del").forEach(b => b.onclick = async () => {
    if (!confirm("Excluir esta calibração?")) return;
    b.disabled = true;
    try {
      await SDK.del(`/instrumentos/${instId}/calibracoes/${b.dataset.cal}`);
      await renderHistoricoCalibracoes(instId, container);
      if (typeof window._onCalibChanged === "function") await window._onCalibChanged(instId);
    } catch (err) {
      alert("Falha ao excluir: " + err.message);
      b.disabled = false;
    }
  });
}

function renderFormCalibracao(instId, onSaved) {
  const form = document.createElement("form");
  form.className = "calib-form";
  form.innerHTML = `
    <div class="fld"><label>Item de contrato (vigente)</label>
      <select id="calibItem"><option value="">— sem contrato —</option></select>
      <small class="muted">Ao vincular, custo e laboratório vêm do contrato e consomem 1 unidade do saldo.</small></div>
    <div class="fld"><label>Laboratório cadastrado</label>
      <select id="calibLab"><option value="">— laboratório (opcional) —</option></select></div>
    <div class="grid2-calib">
      <div class="fld req"><label>Data da calibração</label><input name="data_calibracao" type="date" required></div>
      <div class="fld"><label>Resultado</label><select name="resultado">
        <option value="APROVADO">Aprovado</option>
        <option value="APROVADO_COM_RESTRICOES">Aprovado c/ restrições</option>
        <option value="REPROVADO">Reprovado</option></select></div>
      <div class="fld"><label>Laboratório (texto livre)</label><input name="laboratorio"></div>
      <div class="fld"><label>Nº certificado</label><input name="numero_certificado"></div>
      <div class="fld"><label>Custo</label><input name="custo" type="number" step="any"></div>
      <div class="fld"><label>Responsável</label><input name="responsavel"></div>
    </div>
    <div class="fld"><label>Observações</label><textarea name="observacoes" rows="2"></textarea></div>
    <div class="fld"><label>Certificado (PDF, opcional)</label><input name="arquivo" type="file" accept=".pdf"></div>
    <div style="display:flex;gap:8px;align-items:center;margin-top:4px">
      <button class="btn" type="submit">Salvar calibração</button>
      <span class="sev-erro calib-erro"></span>
    </div>`;
  const erro = form.querySelector(".calib-erro");
  const selLab = form.querySelector("#calibLab");
  const selItem = form.querySelector("#calibItem");
  // Carrega a lista de laboratórios de forma assíncrona ao montar o form.
  (async () => {
    try {
      const dados = await SDK.get("/laboratorios");
      for (const l of dados.itens) selLab.add(new Option(l.razao_social, l.id));
    } catch (err) { /* lista vazia / falha: mantém só a opção vazia */ }
  })();
  // Itens de contratos VIGENTES (não-vencido, com saldo) para vincular/consumir.
  (async () => {
    try {
      const { itens } = await SDK.get("/contratos");
      for (const c of itens) {
        const vigente = c.status_vigencia !== "VENCIDO" && c.status_saldo !== "ESGOTADO";
        if (!vigente) continue;
        for (const it of (c.itens || [])) {
          if (it.saldo <= 0) continue;
          const rotulo = `${c.numero} · item ${it.numero || it.id} · ${it.descricao || ""} (saldo ${it.saldo})`;
          selItem.add(new Option(rotulo, it.id));
        }
      }
    } catch (err) { /* sem contratos: mantém só "sem contrato" */ }
  })();
  form.onsubmit = async (e) => {
    e.preventDefault();
    erro.textContent = "";
    const fd = new FormData(form);
    const body = {};
    for (const [k, v] of fd.entries()) {
      if (k === "arquivo" || v === "") continue;
      body[k] = k === "custo" ? parseFloat(v) : v;
    }
    if (selLab.value) body.laboratorio_id = Number(selLab.value);
    if (selItem.value) body.item_contrato_id = Number(selItem.value);
    const btn = form.querySelector('button[type="submit"]');
    btn.disabled = true;
    try {
      const res = await SDK.post(`/instrumentos/${instId}/calibracoes`, body);
      const arquivo = form.arquivo.files[0];
      if (arquivo) {
        await SDK.upload(`/instrumentos/${instId}/calibracoes/${res.calibracao.id}/certificado`, arquivo);
      }
      form.reset();
      if (typeof onSaved === "function") await onSaved();
    } catch (err) {
      erro.textContent = "Falha ao salvar: " + err.message;
    } finally {
      btn.disabled = false;
    }
  };
  return form;
}

// Monta a seção de calibrações dentro do nó #secaoCalib (após o modal/ficha no DOM).
// onChanged(instId) é chamado após registrar/excluir, para o caller atualizar a lista.
function montarSecaoCalibracoes(instId, onChanged) {
  const sec = document.getElementById("secaoCalib");
  if (!sec) return;
  window._onCalibChanged = onChanged;
  const hist = document.createElement("div");
  const slotForm = document.createElement("div");
  slotForm.style.marginTop = "10px";
  const btn = document.createElement("button");
  btn.className = "btn ghost";
  btn.style.marginTop = "10px";
  btn.innerHTML = '<i class="bi bi-plus-lg"></i> Registrar calibração';
  btn.onclick = () => {
    if (slotForm.firstChild) { slotForm.innerHTML = ""; return; }
    const form = renderFormCalibracao(instId, async () => {
      slotForm.innerHTML = "";
      await renderHistoricoCalibracoes(instId, hist);
      if (typeof onChanged === "function") await onChanged(instId);
    });
    slotForm.appendChild(form);
  };
  sec.append(hist, btn, slotForm);
  renderHistoricoCalibracoes(instId, hist);
}
