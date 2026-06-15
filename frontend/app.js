// SisCalib — SDK + helpers de UI (vanilla). Inspirado em xcmasm-sdk.js.
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
  ["cadastro.html", "plus-lg", "Novo"],
  ["alertas.html", "bell", "Alertas"],
  ["importar.html", "upload", "Importar"],
];

function montarShell(ativo) {
  const links = NAV.map(([h, ic, lbl]) =>
    `<a href="${h}" class="${h === ativo ? "act" : ""}"><i class="bi bi-${ic}"></i> ${lbl}</a>`
  ).join("");
  document.body.insertAdjacentHTML("afterbegin", `
    <div class="sb">
      <div class="sb-logo"><img src="vendor/Logo_of_the_Brazilian_Navy.svg.png" alt="MB"> SisCalib</div>
      ${links}
    </div>`);
  const main = document.querySelector(".main");
  if (main) {
    main.insertAdjacentHTML("afterbegin",
      `<div class="topbar"><button id="themeToggle" class="theme-toggle" type="button"></button></div>`);
    main.querySelector("#themeToggle").addEventListener("click", alternarTema);
    atualizarIconeTema();
  }
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
    ["Disciplina", i.disciplina], ["Sistema", i.sistema],
    ["Localização", [i.organizacao, i.unidade_org, i.secao, i.bancada].filter(Boolean).join(" → ")],
    ["Ciclo (meses)", i.ciclo_meses],
    ["Última calibração", fmtData(i.data_ultima_calibracao)],
    ["Validade", fmtData(i.data_validade)],
    ["Organização calibradora", i.organizacao_calibradora],
    ["Certificado", i.certificado_ref], ["Observações", i.observacoes],
  ];
  const tabela = linhas.map(([k, v]) =>
    `<tr><th style="width:200px">${k}</th><td>${esc(v) || "—"}</td></tr>`).join("");
  const anexos =
    (i.foto_path ? `<a href="${i.foto_path}" target="_blank">Foto</a> ` : '<span class="muted">Sem foto</span> ') +
    (i.manual_path ? ` · <a href="${i.manual_path}" target="_blank">Manual (PDF)</a>` : ' · <span class="muted">Sem manual</span>');
  return `<div style="margin-bottom:12px">${status}</div>
    <div class="twrap"><table><tbody>${tabela}</tbody></table></div>
    <div style="margin-top:12px"><b>Anexos</b><div style="margin-top:6px">${anexos}</div></div>
    <div style="margin-top:16px"><b>Calibrações</b>
      <span class="muted" style="margin-left:8px">Ciclo: ${i.ciclo_meses ?? 12} meses</span>
      <div id="secaoCalib" data-inst="${i.id}" style="margin-top:8px"></div></div>`;
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
  // Carrega a lista de laboratórios de forma assíncrona ao montar o form.
  (async () => {
    try {
      const dados = await SDK.get("/laboratorios");
      for (const l of dados.itens) selLab.add(new Option(l.razao_social, l.id));
    } catch (err) { /* lista vazia / falha: mantém só a opção vazia */ }
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
