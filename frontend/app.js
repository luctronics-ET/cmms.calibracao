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
