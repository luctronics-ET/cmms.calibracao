// SisCalib — SDK + helpers de UI (vanilla). Inspirado em xcmasm-sdk.js.
const API = "/api/v1";

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
    <div style="margin-top:12px"><b>Anexos</b><div style="margin-top:6px">${anexos}</div></div>`;
}
