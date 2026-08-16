/**
 * TechPulse frontend
 *
 * news.json  -->  fetch()  -->  render sections  -->  filter/search client-side
 *
 * No backend calls at runtime - everything here reads the single static
 * news.json file that scripts/fetch_news.py + the GitHub Actions workflow
 * regenerate on a schedule. This file just fetches it, renders it, and
 * re-fetches periodically so the page updates without a manual reload.
 */

const NEWS_JSON_URL = "news.json";
const AUTO_REFRESH_MINUTES = 10;

let allArticles = [];
let currentCategory = "All";
let lastUpdatedIso = null;

const els = {
  statusText: document.getElementById("statusText"),
  refreshBtn: document.getElementById("refreshBtn"),
  heroSection: document.getElementById("heroSection"),
  techGrid: document.getElementById("techGrid"),
  gamingGrid: document.getElementById("gamingGrid"),
  searchSection: document.getElementById("searchSection"),
  searchGrid: document.getElementById("searchGrid"),
  techSection: document.getElementById("techSection"),
  gamingSection: document.getElementById("gamingSection"),
  catTabs: document.getElementById("catTabs"),
  searchInput: document.getElementById("searchInput"),
  themeToggle: document.getElementById("themeToggle"),
};

// ---------------------------------------------------------------------
// Data loading
// ---------------------------------------------------------------------
async function loadNews(isManualRefresh) {
  if (isManualRefresh) els.statusText.textContent = "Refreshing...";
  try {
    const res = await fetch(NEWS_JSON_URL + "?t=" + Date.now(), { cache: "no-store" });
    if (!res.ok) throw new Error("HTTP " + res.status);
    const data = await res.json();

    allArticles = data.articles || [];
    lastUpdatedIso = data.last_updated || null;
    renderStatus(data);
    renderAll();
  } catch (err) {
    els.statusText.textContent = "Could not load news.json - " + err.message;
    if (allArticles.length === 0) {
      els.heroSection.innerHTML = `<div class="error-state">Couldn't load the latest stories. news.json may not exist yet -
        the GitHub Actions workflow needs to run at least once. Try again shortly.</div>`;
    }
  }
}

function renderStatus(data) {
  const updated = lastUpdatedIso ? new Date(lastUpdatedIso) : null;
  const timeStr = updated ? updated.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "unknown";
  const okSources = (data.sources || []).filter(s => s.ok).length;
  const totalSources = (data.sources || []).length;
  els.statusText.textContent =
    `Last updated ${timeStr} · ${data.article_count} articles · ${okSources}/${totalSources} sources healthy · auto-refreshes every ${AUTO_REFRESH_MINUTES} min`;
}

// ---------------------------------------------------------------------
// Rendering
// ---------------------------------------------------------------------
function timeAgo(iso) {
  const diffMs = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diffMs / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return mins + "m ago";
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return hrs + "h ago";
  return Math.floor(hrs / 24) + "d ago";
}

function tagsHtml(article) {
  const chips = [`<span class="tag cat-${article.category}">${article.category}</span>`];
  (article.tags || []).forEach(t => chips.push(`<span class="tag tag-${t}">${t}</span>`));
  if (article.trending) chips.push(`<span class="tag trending">🔥 Trending</span>`);
  return `<div class="tag-row">${chips.join("")}</div>`;
}

function thumbHtml(article) {
  if (article.image) {
    return `<img class="thumb" src="${article.image}" alt="" loading="lazy" onerror="this.outerHTML='<div class=&quot;thumb placeholder&quot;>${article.source}</div>'" />`;
  }
  return `<div class="thumb placeholder">${article.source}</div>`;
}

function cardHtml(article, featured) {
  return `
  <a class="story-card${featured ? " featured" : ""}" href="${article.url}" target="_blank" rel="noopener">
    ${thumbHtml(article)}
    <div class="body">
      ${tagsHtml(article)}
      <p class="headline">${escapeHtml(article.title)}</p>
      ${featured ? `<p class="excerpt">${escapeHtml(article.description)}</p>` : ""}
      <div class="meta-row">
        <span class="src">${article.source}</span>
        <span>${timeAgo(article.published)}</span>
      </div>
    </div>
  </a>`;
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str || "";
  return div.innerHTML;
}

function renderHero(list) {
  if (list.length === 0) {
    els.heroSection.innerHTML = `<div class="empty-state">No stories yet for this view.</div>`;
    return;
  }
  const [main, ...rest] = list;
  const side = rest.slice(0, 3);
  els.heroSection.innerHTML = `
    <h2 class="section-title">Top Stories</h2>
    <div class="hero-grid">
      ${cardHtml(main, true)}
      <div class="side-list">${side.map(a => cardHtml(a, false)).join("")}</div>
    </div>`;
}

function renderGrid(el, list, limit) {
  const slice = list.slice(0, limit || list.length);
  el.innerHTML = slice.length
    ? slice.map(a => cardHtml(a, false)).join("")
    : `<div class="empty-state">No stories in this category yet.</div>`;
}

function renderAll() {
  const searching = els.searchInput.value.trim().length > 0;
  els.searchSection.style.display = searching ? "block" : "none";
  els.techSection.style.display = searching ? "none" : "block";
  els.gamingSection.style.display = searching ? "none" : "block";
  els.heroSection.style.display = searching ? "none" : "block";

  if (searching) {
    renderSearch();
    return;
  }

  const filtered = currentCategory === "All" ? allArticles : allArticles.filter(a => a.category === currentCategory);
  renderHero(filtered.slice(0, 4));
  renderGrid(els.techGrid, allArticles.filter(a => a.category === "Technology"), 9);
  renderGrid(els.gamingGrid, allArticles.filter(a => a.category === "Gaming"), 9);

  // When a specific category tab is active (not "All"), hide the other section.
  els.techSection.style.display = currentCategory === "Gaming" ? "none" : "block";
  els.gamingSection.style.display = currentCategory === "Technology" ? "none" : "block";
}

function renderSearch() {
  const q = els.searchInput.value.trim().toLowerCase();
  const results = allArticles.filter(a =>
    a.title.toLowerCase().includes(q) ||
    (a.description || "").toLowerCase().includes(q) ||
    (a.tags || []).some(t => t.toLowerCase().includes(q))
  );
  els.searchGrid.innerHTML = results.length
    ? results.map(a => cardHtml(a, false)).join("")
    : `<div class="empty-state">No stories match "${escapeHtml(q)}".</div>`;
}

// ---------------------------------------------------------------------
// Interactions
// ---------------------------------------------------------------------
els.catTabs.addEventListener("click", (e) => {
  const btn = e.target.closest(".cat-tab");
  if (!btn) return;
  document.querySelectorAll(".cat-tab").forEach(b => b.classList.remove("active"));
  btn.classList.add("active");
  currentCategory = btn.dataset.cat;
  els.searchInput.value = "";
  renderAll();
});

els.searchInput.addEventListener("input", renderAll);

els.refreshBtn.addEventListener("click", () => loadNews(true));

els.themeToggle.addEventListener("click", () => {
  const body = document.body;
  const current = body.getAttribute("data-theme");
  const next = current === "dark" ? "light" : "dark";
  body.setAttribute("data-theme", next);
  els.themeToggle.textContent = next === "dark" ? "☾" : "☀";
  try { localStorage.setItem("techpulse_theme", next); } catch (e) {}
});

// Restore saved theme preference
try {
  const saved = localStorage.getItem("techpulse_theme");
  if (saved) {
    document.body.setAttribute("data-theme", saved);
    els.themeToggle.textContent = saved === "dark" ? "☾" : "☀";
  }
} catch (e) {}

// ---------------------------------------------------------------------
// Init + auto-refresh (STEP 8/9: periodic re-check, no manual reload needed)
// ---------------------------------------------------------------------
loadNews(false);
setInterval(() => loadNews(false), AUTO_REFRESH_MINUTES * 60 * 1000);
