const API = "/api/papers";

// ── State ──────────────────────────────────────────────────────────────────
let papers = [];
let activeFilters = { topic: "", year: "", method: "", status: "", q: "" };
let viewMode = "card"; // "card" | "table"
const pollingIds = new Map(); // paper_id → intervalId

// ── Bootstrap ──────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  loadPapers();

  document.getElementById("file-input").addEventListener("change", onFileSelect);
  document.getElementById("search-input").addEventListener("input", (e) => {
    activeFilters.q = e.target.value.trim();
    renderGrid();
  });
  document.getElementById("filter-topic").addEventListener("change", (e) => {
    activeFilters.topic = e.target.value;
    renderGrid();
  });
  document.getElementById("filter-year").addEventListener("change", (e) => {
    activeFilters.year = e.target.value;
    renderGrid();
  });
  document.getElementById("filter-method").addEventListener("change", (e) => {
    activeFilters.method = e.target.value;
    renderGrid();
  });
  document.getElementById("filter-status").addEventListener("change", (e) => {
    activeFilters.status = e.target.value;
    renderGrid();
  });
  document.getElementById("modal-close").addEventListener("click", closeModal);
  document.getElementById("modal-overlay").addEventListener("click", (e) => {
    if (e.target === document.getElementById("modal-overlay")) closeModal();
  });

  document.getElementById("btn-card").addEventListener("click", () => setViewMode("card"));
  document.getElementById("btn-table").addEventListener("click", () => setViewMode("table"));
});

function setViewMode(mode) {
  viewMode = mode;
  document.getElementById("btn-card").classList.toggle("view-btn--active", mode === "card");
  document.getElementById("btn-table").classList.toggle("view-btn--active", mode === "table");
  renderGrid();
}

// ── Data fetching ──────────────────────────────────────────────────────────
async function loadPapers() {
  const resp = await fetch(API);
  if (!resp.ok) return;
  papers = await resp.json();
  refreshFilters();
  renderGrid();
  papers
    .filter((p) => p.analysis_status === "pending" || p.analysis_status === "running")
    .forEach((p) => startPolling(p.paper_id));
}

async function fetchPaper(id) {
  const resp = await fetch(`${API}/${id}`);
  if (!resp.ok) return null;
  return resp.json();
}

// ── Upload ─────────────────────────────────────────────────────────────────
async function onFileSelect(e) {
  const file = e.target.files[0];
  if (!file) return;
  e.target.value = "";

  const form = new FormData();
  form.append("file", file);
  const resp = await fetch(`${API}/upload`, { method: "POST", body: form });
  if (!resp.ok) {
    alert("Upload failed: " + (await resp.text()));
    return;
  }
  const paper = await resp.json();
  papers.unshift(paper);
  refreshFilters();
  renderGrid();
  startPolling(paper.paper_id);
}

// ── Polling ────────────────────────────────────────────────────────────────
function startPolling(id) {
  if (pollingIds.has(id)) return;
  const intervalId = setInterval(async () => {
    const updated = await fetchPaper(id);
    if (!updated) return;
    const idx = papers.findIndex((p) => p.paper_id === id);
    if (idx !== -1) papers[idx] = updated;
    refreshFilters();
    renderGrid();
    if (updated.analysis_status === "done" || updated.analysis_status === "failed") {
      clearInterval(pollingIds.get(id));
      pollingIds.delete(id);
    }
  }, 3000);
  pollingIds.set(id, intervalId);
}

// ── Filters ────────────────────────────────────────────────────────────────
function refreshFilters() {
  const topics = [...new Set(papers.flatMap((p) => p.topics || []))].sort();
  const years = [...new Set(papers.map((p) => p.year).filter(Boolean))].sort((a, b) => b - a);
  const methods = [...new Set(papers.map((p) => p.methodology).filter(Boolean))].sort();

  populateSelect("filter-topic", topics, activeFilters.topic);
  populateSelect("filter-year", years.map(String), activeFilters.year);
  populateSelect("filter-method", methods, activeFilters.method);
}

function populateSelect(id, options, selected) {
  const el = document.getElementById(id);
  const first = el.options[0];
  el.innerHTML = "";
  el.appendChild(first);
  options.forEach((o) => {
    const opt = document.createElement("option");
    opt.value = o;
    opt.textContent = o;
    if (o === selected) opt.selected = true;
    el.appendChild(opt);
  });
}

function filteredPapers() {
  return papers.filter((p) => {
    if (activeFilters.status && p.analysis_status !== activeFilters.status) return false;
    if (activeFilters.year && String(p.year) !== activeFilters.year) return false;
    if (activeFilters.method && p.methodology !== activeFilters.method) return false;
    if (activeFilters.topic && !(p.topics || []).includes(activeFilters.topic)) return false;
    if (activeFilters.q) {
      const q = activeFilters.q.toLowerCase();
      const inTitle = (p.title || p.filename).toLowerCase().includes(q);
      const inSummary = (p.one_line_summary || "").toLowerCase().includes(q);
      if (!inTitle && !inSummary) return false;
    }
    return true;
  });
}

// ── Rendering ──────────────────────────────────────────────────────────────
function renderGrid() {
  const container = document.getElementById("paper-grid");
  const visible = filteredPapers();

  if (visible.length === 0) {
    container.className = viewMode === "card" ? "paper-grid" : "paper-table-wrap";
    container.innerHTML = `<p style="color:#6b7280;padding:2rem 0">No papers match the current filters.</p>`;
    return;
  }

  if (viewMode === "card") {
    container.className = "paper-grid";
    container.innerHTML = visible.map(renderCard).join("");
  } else {
    container.className = "paper-table-wrap";
    container.innerHTML = renderTableHTML(visible);
  }

  container.querySelectorAll("[data-detail]").forEach((el) => {
    el.addEventListener("click", () => openModal(el.dataset.detail));
  });
  container.querySelectorAll("[data-delete]").forEach((btn) => {
    btn.addEventListener("click", () => deletePaper(btn.dataset.delete));
  });
  container.querySelectorAll("[data-reanalyze]").forEach((btn) => {
    btn.addEventListener("click", () => reanalyze(btn.dataset.reanalyze));
  });
  container.querySelectorAll("[data-filter-topic]").forEach((chip) => {
    chip.addEventListener("click", () => {
      activeFilters.topic = chip.dataset.filterTopic;
      document.getElementById("filter-topic").value = chip.dataset.filterTopic;
      renderGrid();
    });
  });
}

function renderTableHTML(visible) {
  return `
  <table class="paper-table">
    <thead><tr>
      <th>Status</th>
      <th>Title</th>
      <th>Authors</th>
      <th>Year</th>
      <th>Venue</th>
      <th>Method</th>
      <th>Topics</th>
      <th>Actions</th>
    </tr></thead>
    <tbody>${visible.map(renderTableRow).join("")}</tbody>
  </table>`;
}

function renderTableRow(p) {
  const status = p.analysis_status;
  const title = p.title || p.filename;
  const authorList = p.authors || [];
  const authors = authorList.slice(0, 2).join("; ") + (authorList.length > 2 ? " et al." : "");
  const chips = (p.topics || []).slice(0, 3)
    .map((t) => `<span class="chip" data-filter-topic="${esc(t)}">${esc(t)}</span>`)
    .join("");

  if (status === "pending" || status === "running") {
    return `<tr>
      <td><span class="badge badge--${status}">${status === "running" ? "Analyzing…" : "Pending"}</span></td>
      <td class="table-title">${esc(p.filename)}</td>
      <td colspan="5"><div class="skeleton" style="height:0.75em;width:55%"></div></td>
      <td></td>
    </tr>`;
  }

  if (status === "failed") {
    return `<tr>
      <td><span class="badge badge--failed">Failed</span></td>
      <td class="table-title">${esc(p.filename)}</td>
      <td colspan="5" style="color:#991b1b">${esc(p.error_message || "Analysis failed")}</td>
      <td class="table-actions">
        <button class="btn btn--subtle" data-reanalyze="${p.paper_id}">Retry</button>
        <button class="btn btn--danger"  data-delete="${p.paper_id}">Delete</button>
      </td>
    </tr>`;
  }

  return `<tr>
    <td><span class="badge badge--done">Done</span></td>
    <td class="table-title" data-detail="${p.paper_id}">${esc(title)}</td>
    <td class="table-meta">${esc(authors)}</td>
    <td class="table-meta">${p.year || ""}</td>
    <td class="table-venue" title="${esc(p.venue || "")}">${esc(p.venue || "")}</td>
    <td class="table-meta">${esc(p.methodology || "")}</td>
    <td class="chip-list">${chips}</td>
    <td class="table-actions">
      <button class="btn btn--primary" data-detail="${p.paper_id}">Details</button>
      <button class="btn btn--danger"  data-delete="${p.paper_id}">Delete</button>
    </td>
  </tr>`;
}

function renderCard(p) {
  const status = p.analysis_status;
  const title = p.title || p.filename;
  const authorList = p.authors || [];
  const authors = authorList.slice(0, 2).join("; ") + (authorList.length > 2 ? " et al." : "");
  const chips = (p.topics || [])
    .map((t) => `<span class="chip" data-filter-topic="${esc(t)}">${esc(t)}</span>`)
    .join("");

  if (status === "pending" || status === "running") {
    return `
    <div class="paper-card">
      <div class="card-header">
        <span class="badge badge--${status}">${status === "running" ? "Analyzing…" : "Pending"}</span>
      </div>
      <div class="card-title">${esc(p.filename)}</div>
      <div class="skeleton" style="height:0.75em;width:60%;margin-top:0.25rem"></div>
      <div class="skeleton" style="height:0.75em;width:80%"></div>
    </div>`;
  }

  if (status === "failed") {
    return `
    <div class="paper-card">
      <div class="card-header">
        <span class="badge badge--failed">Failed</span>
      </div>
      <div class="card-title">${esc(p.filename)}</div>
      <div style="font-size:0.78rem;color:#991b1b;margin-top:0.25rem">${esc(p.error_message || "Analysis failed")}</div>
      <div class="card-actions">
        <button class="btn btn--subtle" data-reanalyze="${p.paper_id}">Retry</button>
        <button class="btn btn--danger"  data-delete="${p.paper_id}">Delete</button>
      </div>
    </div>`;
  }

  return `
  <div class="paper-card">
    <div class="card-header">
      <span class="card-title">${esc(title)}</span>
      <span class="card-year">${p.year || ""}</span>
    </div>
    <span class="badge badge--done" style="align-self:flex-start">Done</span>
    ${authors ? `<div class="card-authors">${esc(authors)}</div>` : ""}
    ${p.venue ? `<div class="card-venue">${esc(p.venue)}</div>` : ""}
    ${p.one_line_summary ? `<div class="card-summary">"${esc(p.one_line_summary)}"</div>` : ""}
    <div class="chip-list">${chips}</div>
    <div class="card-actions">
      <button class="btn btn--primary" data-detail="${p.paper_id}">Details</button>
      <button class="btn btn--danger"  data-delete="${p.paper_id}">Delete</button>
    </div>
  </div>`;
}

// ── Modal ──────────────────────────────────────────────────────────────────
function openModal(paperId) {
  const p = papers.find((x) => x.paper_id === paperId);
  if (!p) return;

  const contributions = (p.key_contributions || []).map((c) => `<li>${esc(c)}</li>`).join("");
  const citationList = (p.citations || []).map((c) => `<li>${esc(c)}</li>`).join("");
  const allChips = (p.topics || []).map((t) => `<span class="chip">${esc(t)}</span>`).join("");

  document.getElementById("modal-content").innerHTML = `
    <h2>${esc(p.title || p.filename)}</h2>
    <div style="font-size:0.82rem;color:#6b7280;margin:0.4rem 0 0.6rem">
      ${esc((p.authors || []).join(", "))}
      ${p.year ? `· ${p.year}` : ""}
      ${p.venue ? `· ${esc(p.venue)}` : ""}
      ${p.methodology ? `· <em>${esc(p.methodology)}</em>` : ""}
    </div>
    <div class="chip-list">${allChips}</div>
    ${p.abstract ? `
    <div class="section">
      <div class="section-title">Abstract</div>
      <p class="abstract-text">${esc(p.abstract)}</p>
    </div>` : ""}
    ${contributions ? `
    <div class="section">
      <div class="section-title">Key Contributions</div>
      <ul>${contributions}</ul>
    </div>` : ""}
    ${citationList ? `
    <div class="section">
      <details>
        <summary>References (${p.citations.length})</summary>
        <ul style="margin-top:0.5rem">${citationList}</ul>
      </details>
    </div>` : ""}
  `;

  document.getElementById("modal-overlay").classList.remove("hidden");
}

function closeModal() {
  document.getElementById("modal-overlay").classList.add("hidden");
}

// ── Actions ────────────────────────────────────────────────────────────────
async function deletePaper(id) {
  if (!confirm("Delete this paper?")) return;
  const resp = await fetch(`${API}/${id}`, { method: "DELETE" });
  if (resp.ok) {
    papers = papers.filter((p) => p.paper_id !== id);
    refreshFilters();
    renderGrid();
  }
}

async function reanalyze(id) {
  await fetch(`${API}/${id}/analyze`, { method: "POST" });
  const updated = await fetchPaper(id);
  if (updated) {
    const idx = papers.findIndex((p) => p.paper_id === id);
    if (idx !== -1) papers[idx] = updated;
    renderGrid();
    startPolling(id);
  }
}

// ── Helpers ────────────────────────────────────────────────────────────────
function esc(str) {
  return String(str ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
