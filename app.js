'use strict';

/*
=========================================================
 TECHPULSE FRONTEND — PHASE 1 RESILIENCE UPGRADE
 Preserves all filtering, dark mode, subcategories, 
 and hero features while adding conditional HTTP caching 
 and offline local storage fallback.
=========================================================
*/

const NEWS_FILE = './news.json';
const AUTO_REFRESH_INTERVAL = 2 * 60 * 1000;
const NEW_ARTICLE_WINDOW = 2 * 60 * 60 * 1000;
const LOCAL_STORAGE_KEY = 'techpulse_news_cache';

let allArticles = [];
let currentMainCategory = 'All';
let currentSubcategory = 'All';
let lastUpdatedAt = null;
let lastModifiedHeader = null;
let firstLoad = true;

const SUBCATEGORIES = {
  Technology: [
    'All Topics', 'Artificial Intelligence', 'Smartphones & Mobile', 
    'Cybersecurity', 'Cloud & Infrastructure', 'Software & Applications', 
    'Hardware & Devices', 'Internet & Web', 'Emerging Technology', 
    'Science & Innovation', 'Business & Technology'
  ],
  Gaming: [
    'All Topics', 'PC Gaming', 'Console Gaming', 'Mobile Gaming', 
    'Game Releases', 'Gaming Hardware', 'Esports', 'Game Development', 
    'Gaming Industry', 'Gaming Updates', 'Reviews & Features'
  ],
  All: ['All Topics']
};

document.addEventListener('DOMContentLoaded', initializePage);

function initializePage() {
  const year = document.getElementById('year');
  if (year) year.textContent = new Date().getFullYear();

  loadSavedTheme();
  buildSubcategoryNav();
  buildTopicChips();
  setupEventListeners();

  loadNews(true);

  setInterval(() => loadNews(false), AUTO_REFRESH_INTERVAL);
  setInterval(refreshVisibleTimes, 60 * 1000);
}

function setupEventListeners() {
  const refreshButton = document.getElementById('refreshButton');
  if (refreshButton) refreshButton.addEventListener('click', manualRefresh);

  const themeButton = document.getElementById('themeButton');
  if (themeButton) themeButton.addEventListener('click', toggleTheme);

  const search = document.getElementById('search');
  if (search) search.addEventListener('input', applyFilters);

  document.querySelectorAll('[data-main-category]').forEach(button => {
    button.addEventListener('click', () => selectMainCategory(button.dataset.mainCategory, button));
  });
}

/* =====================================================
   RESILIENT FETCH WITH IF-MODIFIED-SINCE & CACHE FALLBACK
   ===================================================== */

async function loadNews(forceRefresh = false) {
  const status = document.getElementById('statusText');
  if (status) {
    status.textContent = forceRefresh ? 'Loading latest stories...' : 'Checking for new stories...';
  }

  try {
    const headers = { 'Accept': 'application/json' };
    if (!forceRefresh && lastModifiedHeader) {
      headers['If-Modified-Since'] = lastModifiedHeader;
    }

    const cacheBust = '?t=' + Date.now();
    const response = await fetch(NEWS_FILE + cacheBust, {
      method: 'GET',
      headers: headers
    });

    // 304 Not Modified — Payload unchanged
    if (response.status === 304) {
      if (status) status.textContent = 'News feed is up to date';
      return;
    }

    if (!response.ok) {
      throw new Error(`HTTP Error ${response.status}`);
    }

    if (response.headers.get('Last-Modified')) {
      lastModifiedHeader = response.headers.get('Last-Modified');
    }

    const data = await response.json();
    if (!data || !Array.isArray(data.articles)) {
      throw new Error('Invalid JSON schema format received.');
    }

    // Save to local storage for offline resilience
    try {
      localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(data));
    } catch (e) {
      console.warn('LocalStorage payload quota exceeded.');
    }

    processNewsData(data);

  } catch (error) {
    console.error('TechPulse fetch notice:', error.message);
    
    // Attempt fallback to cached local storage data
    const cachedData = localStorage.getItem(LOCAL_STORAGE_KEY);
    if (cachedData && allArticles.length === 0) {
      try {
        const parsed = JSON.parse(cachedData);
        processNewsData(parsed);
        if (status) status.textContent = 'Loaded from offline storage';
        return;
      } catch (e) {
        // Fall through to error handler
      }
    }

    showError(error.message || 'Unable to load news.');
  }
}

function processNewsData(data) {
  const oldIds = new Set(allArticles.map(a => a.id));
  allArticles = normalizeArticles(data.articles);
  allArticles = removeDuplicates(allArticles);

  allArticles.sort((a, b) => getDateValue(b.published) - getDateValue(a.published));
  lastUpdatedAt = data.updatedAt || new Date().toISOString();

  let newCount = 0;
  if (!firstLoad) {
    newCount = allArticles.filter(a => !oldIds.has(a.id)).length;
  }
  firstLoad = false;

  renderHero();
  buildTopicChips();
  applyFilters();
  renderTrending();
  updateStatus(newCount);
}

function normalizeArticles(articles) {
  return articles.map((article, index) => {
    const title = cleanText(article.title || 'Untitled story');
    const description = cleanText(article.description || 'Read the full story from publisher.');
    const url = String(article.url || article.link || '').trim();
    const published = article.published || new Date().toISOString();
    const category = cleanText(article.category || 'Technology');
    const mainCategory = cleanText(article.mainCategory || detectMainCategory(category));
    const source = cleanText(article.source || 'TechPulse');
    const image = String(article.image || '').trim();
    const id = article.id || createArticleId(title, url, published, index);

    return { id: String(id), title, description, url, image, category, mainCategory, source, published };
  });
}

function removeDuplicates(articles) {
  const seenIds = new Set(), seenUrls = new Set(), seenTitles = new Set();
  return articles.filter(article => {
    const id = article.id;
    const url = normalizeUrl(article.url);
    const title = normalizeTitle(article.title);

    if (seenIds.has(id) || (url && seenUrls.has(url)) || (title && seenTitles.has(title))) {
      return false;
    }

    seenIds.add(id);
    if (url) seenUrls.add(url);
    if (title) seenTitles.add(title);
    return true;
  });
}

function createArticleId(title, url, published, index) {
  const raw = title + '|' + url + '|' + published + '|' + index;
  let hash = 0;
  for (let i = 0; i < raw.length; i++) {
    hash = ((hash << 5) - hash) + raw.charCodeAt(i);
    hash |= 0;
  }
  return 'article-' + Math.abs(hash);
}

function detectMainCategory(category) {
  const val = String(category || '').toLowerCase();
  const keywords = ['gaming', 'game', 'games', 'esports', 'console', 'pc gaming', 'mobile gaming'];
  return keywords.some(k => val.includes(k)) ? 'Gaming' : 'Technology';
}

function selectMainCategory(category, button) {
  currentMainCategory = category;
  currentSubcategory = 'All';

  document.querySelectorAll('.main-nav button').forEach(btn => btn.classList.remove('active'));
  if (button) button.classList.add('active');

  buildSubcategoryNav();
  buildTopicChips();
  updateSectionTitle();
  applyFilters();
}

function selectSubcategory(category, button) {
  currentSubcategory = category === 'All Topics' ? 'All' : category;

  document.querySelectorAll('.subnav button').forEach(btn => btn.classList.remove('active'));
  if (button) button.classList.add('active');

  updateSectionTitle();
  applyFilters();
}

function buildSubcategoryNav() {
  const nav = document.getElementById('subcategoryNav');
  if (!nav) return;

  const categories = SUBCATEGORIES[currentMainCategory] || SUBCATEGORIES.All;
  nav.innerHTML = categories.map((cat, idx) => {
    const val = cat === 'All Topics' ? 'All' : cat;
    const active = (idx === 0 && currentSubcategory === 'All') || currentSubcategory === val;
    return `<button class="${active ? 'active' : ''}" data-subcategory="${escapeHtml(val)}">${escapeHtml(cat)}</button>`;
  }).join('');

  nav.querySelectorAll('[data-subcategory]').forEach(btn => {
    btn.addEventListener('click', () => selectSubcategory(btn.dataset.subcategory, btn));
  });
}

function buildTopicChips() {
  const container = document.getElementById('topicChips');
  if (!container) return;

  const categories = currentMainCategory === 'All' 
    ? ['All Topics', 'Artificial Intelligence', 'Cybersecurity', 'Cloud & Infrastructure', 'Smartphones & Mobile', 'Software & Applications', 'Hardware & Devices', 'PC Gaming', 'Console Gaming', 'Mobile Gaming', 'Game Releases', 'Gaming Hardware', 'Esports']
    : (SUBCATEGORIES[currentMainCategory] || []);

  container.innerHTML = categories.map(cat => {
    const val = cat === 'All Topics' ? 'All' : cat;
    const active = currentSubcategory === val;
    return `<button class="topic-chip ${active ? 'active' : ''}" data-topic="${escapeHtml(val)}">${escapeHtml(cat)}</button>`;
  }).join('');

  container.querySelectorAll('[data-topic]').forEach(btn => {
    btn.addEventListener('click', () => {
      currentSubcategory = btn.dataset.topic;
      buildSubcategoryNav();
      buildTopicChips();
      updateSectionTitle();
      applyFilters();
    });
  });
}

function applyFilters() {
  const searchEl = document.getElementById('search');
  const search = searchEl ? searchEl.value.toLowerCase().trim() : '';

  const filtered = allArticles.filter(article => {
    const mainMatch = currentMainCategory === 'All' || article.mainCategory === currentMainCategory;
    const subMatch = currentSubcategory === 'All' || article.category === currentSubcategory;
    const searchText = (article.title + ' ' + article.description + ' ' + article.category + ' ' + article.mainCategory + ' ' + article.source).toLowerCase();
    const searchMatch = !search || searchText.includes(search);
    return mainMatch && subMatch && searchMatch;
  });

  renderNews(filtered);
  updateArticleCount(filtered.length);
}

function renderNews(articles) {
  const container = document.getElementById('newsContainer');
  if (!container) return;

  if (!articles.length) {
    container.innerHTML = `
      <div class="empty">
        <div class="empty-icon">🔎</div>
        <h3>No stories found</h3>
        <p>Try selecting another category or typing a different search term.</p>
      </div>`;
    return;
  }

  container.innerHTML = `<div class="news-grid">${articles.map(createArticleCard).join('')}</div>`;
}

function createArticleCard(article) {
  const isNew = isRecentlyPublished(article.published);
  const placeholder = article.mainCategory === 'Gaming' ? '🎮' : '⚡';
  
  let imageHtml = `<div class="image-placeholder"><div class="placeholder-icon">${placeholder}</div><div class="placeholder-text">TechPulse</div></div>`;

  if (isValidHttpUrl(article.image)) {
    imageHtml = `
      <img class="article-image" src="${escapeHtml(article.image)}" alt="" loading="lazy" referrerpolicy="no-referrer" onerror="this.style.display='none';this.nextElementSibling.style.display='flex';">
      <div class="image-placeholder" style="display:none;"><div class="placeholder-icon">${placeholder}</div><div class="placeholder-text">TechPulse</div></div>`;
  }

  const safeUrl = isValidHttpUrl(article.url) ? article.url : '#';

  return `
    <article class="article">
      <div class="article-image-wrap">${imageHtml}${isNew ? '<span class="new-badge">NEW</span>' : ''}</div>
      <div class="article-body">
        <div class="article-category"><span class="category-badge">${escapeHtml(article.category)}</span></div>
        <h3 class="article-title"><a href="${escapeHtml(safeUrl)}" target="_blank" rel="noopener noreferrer">${escapeHtml(article.title)}</a></h3>
        <p class="article-description">${escapeHtml(article.description)}</p>
        <a class="read-link" href="${escapeHtml(safeUrl)}" target="_blank" rel="noopener noreferrer">Read Story →</a>
        <div class="article-footer">
          <span class="article-source">${escapeHtml(article.source)}</span>
          <span class="article-time" data-time="${escapeHtml(article.published)}">${formatRelativeTime(article.published)}</span>
        </div>
      </div>
    </article>`;
}

function renderHero() {
  if (!allArticles.length) return;

  const latest = allArticles[0];
  const technology = allArticles.find(a => a.mainCategory === 'Technology');
  const gaming = allArticles.find(a => a.mainCategory === 'Gaming');

  const hero = document.getElementById('heroMain');
  if (hero) {
    const heroUrl = isValidHttpUrl(latest.url) ? latest.url : '';
    hero.innerHTML = `
      <div class="hero-content">
        <div class="hero-label">${isRecentlyPublished(latest.published) ? 'Breaking / Fresh' : 'Latest Story'}</div>
        <div class="hero-title">${escapeHtml(latest.title)}</div>
        <div class="hero-description">${escapeHtml(latest.description)}</div>
        <div class="hero-meta">${escapeHtml(latest.category)} • ${escapeHtml(latest.source)} • ${formatRelativeTime(latest.published)}</div>
      </div>
      ${heroUrl ? `<a class="hero-link" href="${escapeHtml(heroUrl)}" target="_blank" rel="noopener noreferrer" aria-label="Read story">Read story</a>` : ''}`;
  }

  const side = document.getElementById('heroSide');
  if (side) {
    side.innerHTML = `${createQuickHeroCard('Technology', technology)}${createQuickHeroCard('Gaming', gaming)}`;
  }
}

function createQuickHeroCard(label, article) {
  if (!article) {
    return `<div class="quick-card"><div class="quick-label">${escapeHtml(label)}</div><div class="quick-title">No current story available.</div></div>`;
  }
  const safeUrl = isValidHttpUrl(article.url) ? article.url : '';
  return `
    <div class="quick-card">
      <div class="quick-label">${escapeHtml(label)}</div>
      <div class="quick-title">${escapeHtml(article.title)}</div>
      <div class="quick-meta">${escapeHtml(article.source)} • ${formatRelativeTime(article.published)}</div>
      ${safeUrl ? `<a href="${escapeHtml(safeUrl)}" target="_blank" rel="noopener noreferrer" style="position:absolute;inset:0;z-index:5;text-indent:-9999px;" aria-label="Read story">Read story</a>` : ''}
    </div>`;
}

function renderTrending() {
  const container = document.getElementById('trendingStrip') || document.getElementById('trendingGrid');
  if (!container) return;

  const trending = allArticles.slice().sort((a, b) => getTrendingScore(b) - getTrendingScore(a)).slice(0, 6);
  if (!trending.length) {
    container.innerHTML = '';
    return;
  }

  container.innerHTML = trending.map((article, idx) => `
    <div class="trending-chip" onclick="window.open('${escapeHtml(article.url)}', '_blank')">
      <strong>#${idx + 1}</strong> ${escapeHtml(article.title)}
    </div>`).join('');
}

function getTrendingScore(article) {
  const published = getDateValue(article.published);
  if (!published) return 0;
  const ageHours = Math.max(0, (Date.now() - published) / 3600000);
  let score = Math.max(0, 100 - (ageHours * 4));
  if (article.mainCategory === 'Technology' || article.mainCategory === 'Gaming') score += 3;
  return score;
}

function updateSectionTitle() {
  let title = currentMainCategory !== 'All' ? currentMainCategory : 'Latest News';
  if (currentSubcategory !== 'All') title = currentSubcategory;

  const titleEl = document.getElementById('sectionTitle');
  const subtitleEl = document.getElementById('sectionSubtitle');

  if (titleEl) titleEl.textContent = title;
  if (subtitleEl) {
    subtitleEl.textContent = currentMainCategory === 'All' ? 'Fresh technology and gaming stories' : 'Fresh stories from this section';
  }
}

function updateArticleCount(count) {
  const element = document.getElementById('articleCount');
  if (element) element.textContent = `${count} ${count === 1 ? 'article' : 'articles'}`;
}

function updateStatus(newCount) {
  const status = document.getElementById('statusText');
  if (status) {
    status.textContent = newCount > 0 ? `${newCount} ${newCount === 1 ? 'new story' : 'new stories'} detected` : 'News feed active';
  }
}

function formatRelativeTime(value) {
  const date = new Date(value);
  if (isNaN(date.getTime())) return 'Recently';
  const seconds = Math.floor((Date.now() - date.getTime()) / 1000);

  if (seconds < 60) return 'Just now';
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} hr ago`;
  const days = Math.floor(hours / 24);
  return days === 1 ? 'Yesterday' : `${days} days ago`;
}

function refreshVisibleTimes() {
  document.querySelectorAll('.article-time').forEach(el => {
    if (el.dataset.time) el.textContent = formatRelativeTime(el.dataset.time);
  });
  if (allArticles.length) {
    renderHero();
    renderTrending();
  }
}

async function manualRefresh() {
  const button = document.getElementById('refreshButton');
  if (button) {
    button.disabled = true;
    button.textContent = 'Refreshing...';
  }
  try {
    await loadNews(true);
  } finally {
    if (button) {
      button.disabled = false;
      button.textContent = '↻ Refresh';
    }
  }
}

function toggleTheme() {
  document.body.classList.toggle('dark');
  const isDark = document.body.classList.contains('dark');
  try {
    localStorage.setItem('techpulse-theme', isDark ? 'dark' : 'light');
  } catch (e) {}
  updateThemeButton();
}

function loadSavedTheme() {
  let saved = null;
  try {
    saved = localStorage.getItem('techpulse-theme');
  } catch (e) {}
  if (saved === 'dark') document.body.classList.add('dark');
  updateThemeButton();
}

function updateThemeButton() {
  const button = document.getElementById('themeButton');
  if (!button) return;
  const isDark = document.body.classList.contains('dark');
  button.textContent = isDark ? '☀' : '☾';
  button.setAttribute('aria-label', isDark ? 'Switch to light mode' : 'Switch to dark mode');
}

function showError(message) {
  const status = document.getElementById('statusText');
  if (status) status.textContent = 'News service temporarily unavailable';

  const container = document.getElementById('newsContainer');
  if (!container || allArticles.length) return;

  container.innerHTML = `
    <div class="empty">
      <div class="empty-icon">⚠️</div>
      <h3>Unable to load news</h3>
      <p>${escapeHtml(message)}</p>
      <br>
      <button class="refresh-btn" onclick="manualRefresh()">Try Again</button>
    </div>`;
}

function isValidHttpUrl(val) {
  return /^https?:\/\//i.test(String(val || '').trim());
}

function getDateValue(val) {
  const time = new Date(val).getTime();
  return isNaN(time) ? 0 : time;
}

function isRecentlyPublished(val) {
  const time = getDateValue(val);
  if (!time) return false;
  const age = Date.now() - time;
  return age >= 0 && age <= NEW_ARTICLE_WINDOW;
}

function normalizeUrl(val) {
  try {
    const url = new URL(val);
    url.hash = '';
    return url.href.replace(/\/$/, '').toLowerCase();
  } catch (e) {
    return String(val || '').trim().toLowerCase();
  }
}

function normalizeTitle(val) {
  return String(val || '').toLowerCase().replace(/[^a-z0-9\s]/g, '').replace(/\s+/g, ' ').trim();
}

function cleanText(val) {
  return String(val == null ? '' : val).replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim();
}

function escapeHtml(val) {
  return String(val == null ? '' : val)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}
