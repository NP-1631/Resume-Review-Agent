/* ═══════════════════════════════════════════════════
   Resume Review Agent — Frontend Logic
   ═══════════════════════════════════════════════════ */

const API_BASE = "";

// ── DOM Refs ────────────────────────────────────────
const dropZone       = document.getElementById("drop-zone");
const fileInput      = document.getElementById("resume-file");
const fileSelected   = document.getElementById("file-selected");
const fileNameEl     = document.getElementById("file-name");
const clearFileBtn   = document.getElementById("clear-file");
const userIdInput    = document.getElementById("user-id-input");
const jdToggle       = document.getElementById("jd-toggle");
const jdInputArea    = document.getElementById("jd-input-area");
const jdTextarea     = document.getElementById("jd-textarea");
const analyzeBtn     = document.getElementById("analyze-btn");
const btnText        = analyzeBtn.querySelector(".btn-text");
const btnLoader      = analyzeBtn.querySelector(".btn-loader");
const errorBanner    = document.getElementById("error-banner");
const uploadSection  = document.getElementById("upload-section");
const resultsSection = document.getElementById("results-section");
const resetBtn       = document.getElementById("reset-btn");

// Score display
const scoreNumber    = document.getElementById("score-number");
const ringFill       = document.getElementById("ring-fill");
const atsBadge       = document.getElementById("ats-badge");
const scoreVerdict   = document.getElementById("score-verdict");

// Tab panels
const tabs           = document.querySelectorAll(".tab");
const panels         = document.querySelectorAll(".tab-panel");
const tabMatch       = document.getElementById("tab-match");

// Lists
const strengthsList  = document.getElementById("strengths-list");
const weaknessesList = document.getElementById("weaknesses-list");
const keywordsContainer = document.getElementById("keywords-container");
const rewritesContainer = document.getElementById("rewrites-container");

// JD match
const matchPctLabel  = document.getElementById("match-pct-label");
const matchBar       = document.getElementById("match-bar");
const matchExplanation = document.getElementById("match-explanation");
const matchedKeywords  = document.getElementById("matched-keywords");
const missingMatchKw   = document.getElementById("missing-match-keywords");

// ── State ───────────────────────────────────────────
let selectedFile = null;
let resumeId     = null;

// ── Ring Circumference ──────────────────────────────
const RING_CIRCUMFERENCE = 2 * Math.PI * 52; // r=52
ringFill.style.strokeDasharray = RING_CIRCUMFERENCE;
ringFill.style.strokeDashoffset = RING_CIRCUMFERENCE;

// ── Drag & Drop ─────────────────────────────────────
dropZone.addEventListener("click", () => fileInput.click());
dropZone.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") fileInput.click(); });

dropZone.addEventListener("dragover", (e) => { e.preventDefault(); dropZone.classList.add("drag-over"); });
dropZone.addEventListener("dragleave", () => dropZone.classList.remove("drag-over"));
dropZone.addEventListener("drop", (e) => {
  e.preventDefault();
  dropZone.classList.remove("drag-over");
  const file = e.dataTransfer?.files[0];
  if (file) setFile(file);
});

fileInput.addEventListener("change", () => {
  if (fileInput.files[0]) setFile(fileInput.files[0]);
});

clearFileBtn.addEventListener("click", clearFile);

function setFile(file) {
  selectedFile = file;
  fileNameEl.textContent = file.name;
  fileSelected.classList.remove("hidden");
  dropZone.classList.add("has-file");
  analyzeBtn.disabled = false;
  hideError();
}

function clearFile() {
  selectedFile = null;
  fileInput.value = "";
  fileSelected.classList.add("hidden");
  dropZone.classList.remove("has-file");
  analyzeBtn.disabled = true;
}

// ── JD Toggle ───────────────────────────────────────
jdToggle.addEventListener("change", () => {
  jdInputArea.classList.toggle("hidden", !jdToggle.checked);
});

// ── Tabs ────────────────────────────────────────────
tabs.forEach(tab => {
  tab.addEventListener("click", () => {
    tabs.forEach(t => t.classList.remove("active"));
    panels.forEach(p => p.classList.remove("active"));
    tab.classList.add("active");
    document.getElementById(`panel-${tab.dataset.tab}`).classList.add("active");
  });
});

// ── Analyze Button ───────────────────────────────────
analyzeBtn.addEventListener("click", runAnalysis);

async function runAnalysis() {
  if (!selectedFile) return;

  setLoading(true);
  hideError();

  try {
    // ① Upload resume
    const formData = new FormData();
    formData.append("file", selectedFile);
    formData.append("user_id", userIdInput.value.trim() || "anonymous");

    const uploadRes = await fetchJSON(`${API_BASE}/upload`, {
      method: "POST",
      body: formData,
    });
    resumeId = uploadRes.resume_id;

    // ② Review resume
    const reviewRes = await fetchJSON(`${API_BASE}/review`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        resume_id: resumeId,
        user_id: userIdInput.value.trim() || "anonymous",
      }),
    });

    renderReview(reviewRes.result);

    // ③ JD Match (optional)
    if (jdToggle.checked && jdTextarea.value.trim()) {
      const matchRes = await fetchJSON(`${API_BASE}/match`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          resume_id: resumeId,
          job_description: jdTextarea.value.trim(),
          user_id: userIdInput.value.trim() || "anonymous",
        }),
      });
      renderMatch(matchRes);
      tabMatch.style.display = "";
    }

    showResults();
  } catch (err) {
    showError(err.message || "An unexpected error occurred. Is the backend running?");
  } finally {
    setLoading(false);
  }
}

// ── Helpers ─────────────────────────────────────────
async function fetchJSON(url, options = {}) {
  const res = await fetch(url, options);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.detail || `HTTP ${res.status}`);
  }
  return data;
}

function setLoading(on) {
  analyzeBtn.disabled = on;
  btnText.classList.toggle("hidden", on);
  btnLoader.classList.toggle("hidden", !on);
}

function showError(msg) {
  errorBanner.textContent = `⚠️ ${msg}`;
  errorBanner.classList.remove("hidden");
}

function hideError() {
  errorBanner.classList.add("hidden");
}

function showResults() {
  uploadSection.classList.add("hidden");
  resultsSection.classList.remove("hidden");
  resultsSection.scrollIntoView({ behavior: "smooth" });
}

// ── Render Review ────────────────────────────────────
function renderReview(result) {
  animateScore(result.overall_score);
  renderATSBadge(result.ats_compatibility);
  scoreVerdict.textContent = getVerdict(result.overall_score);

  renderList(strengthsList, result.strengths);
  renderList(weaknessesList, result.weaknesses);
  renderKeywords(keywordsContainer, result.missing_keywords, "chip");
  renderRewrites(rewritesContainer, result.suggested_rewrites);
}

function animateScore(target) {
  const circumference = RING_CIRCUMFERENCE;
  let current = 0;
  const duration = 1500;
  const start = performance.now();

  // Set ring color based on score
  const color = target >= 80 ? "#06d6a0" : target >= 60 ? "#ffd166" : "#ff6b6b";
  ringFill.style.stroke = color;

  function tick(now) {
    const elapsed = now - start;
    const progress = Math.min(elapsed / duration, 1);
    const eased = 1 - Math.pow(1 - progress, 3); // ease-out-cubic
    current = Math.round(target * eased);
    scoreNumber.textContent = current;
    const offset = circumference - (current / 100) * circumference;
    ringFill.style.strokeDashoffset = offset;
    if (progress < 1) requestAnimationFrame(tick);
  }
  requestAnimationFrame(tick);
}

function renderATSBadge(ats) {
  atsBadge.textContent = `ATS: ${ats}`;
  atsBadge.className = "ats-badge";
  if (ats === "High")   atsBadge.classList.add("ats-high");
  if (ats === "Medium") atsBadge.classList.add("ats-medium");
  if (ats === "Low")    atsBadge.classList.add("ats-low");
}

function getVerdict(score) {
  if (score >= 80) return "🏆 Exceptional resume — ready for top-tier applications.";
  if (score >= 60) return "👍 Good resume — a few targeted improvements will make it stand out.";
  if (score >= 40) return "⚠️ Needs work — address the weaknesses to improve your chances.";
  return "❌ Major issues — consider a significant rewrite using the suggestions below.";
}

function renderList(el, items) {
  el.innerHTML = "";
  items.forEach((item, i) => {
    const li = document.createElement("li");
    li.textContent = item;
    li.style.animationDelay = `${i * 60}ms`;
    el.appendChild(li);
  });
}

function renderKeywords(container, keywords, chipClass = "chip") {
  container.innerHTML = "";
  keywords.forEach((kw, i) => {
    const chip = document.createElement("span");
    chip.className = chipClass;
    chip.textContent = kw;
    chip.style.animationDelay = `${i * 40}ms`;
    container.appendChild(chip);
  });
}

function renderRewrites(container, rewrites) {
  container.innerHTML = "";
  rewrites.forEach((r, i) => {
    const card = document.createElement("div");
    card.className = "rewrite-card";
    card.style.animationDelay = `${i * 80}ms`;
    card.innerHTML = `
      <div class="rewrite-block">
        <div class="rewrite-tag tag-original">✗ Original</div>
        <div class="rewrite-text">${escapeHtml(r.original)}</div>
      </div>
      <div class="rewrite-block">
        <div class="rewrite-tag tag-improved">✓ Improved</div>
        <div class="rewrite-text rewrite-text-improved">${escapeHtml(r.improved)}</div>
      </div>`;
    container.appendChild(card);
  });
}

// ── Render JD Match ──────────────────────────────────
function renderMatch(data) {
  const pct = data.match_percentage;
  matchPctLabel.textContent = `${pct}%`;
  setTimeout(() => { matchBar.style.width = `${pct}%`; }, 100);
  matchExplanation.textContent = data.explanation;

  renderKeywords(matchedKeywords, data.matched_keywords, "chip chip-good");
  renderKeywords(missingMatchKw, data.missing_keywords, "chip chip-bad");
}

// ── Reset ────────────────────────────────────────────
resetBtn.addEventListener("click", () => {
  clearFile();
  jdToggle.checked = false;
  jdInputArea.classList.add("hidden");
  jdTextarea.value = "";
  tabMatch.style.display = "none";
  userIdInput.value = "";
  resumeId = null;
  scoreNumber.textContent = "0";
  ringFill.style.strokeDashoffset = RING_CIRCUMFERENCE;
  [strengthsList, weaknessesList, keywordsContainer, rewritesContainer,
   matchedKeywords, missingMatchKw].forEach(el => { el.innerHTML = ""; });
  matchBar.style.width = "0%";
  matchPctLabel.textContent = "0%";
  tabs.forEach((t, i) => t.classList.toggle("active", i === 0));
  panels.forEach((p, i) => p.classList.toggle("active", i === 0));
  resultsSection.classList.add("hidden");
  uploadSection.classList.remove("hidden");
  uploadSection.scrollIntoView({ behavior: "smooth" });
});

// ── XSS guard ────────────────────────────────────────
function escapeHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
