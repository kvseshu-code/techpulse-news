/* TechPulse Master Application Logic — Phase 3 */

const CONFIG = {
  DATA_URL: './news.json',
  CACHE_KEY: 'techpulse_news_cache',
  THEME_KEY: 'techpulse_theme',
  DEBOUNCE_MS: 250
};

// Application State
let state = {
  articles: [],
  filtered: [],
  mainCategory: 'All',
  subCategory: 'All',
  searchQuery: '',
  trendingFilter: null,
  language: 'en',
  speakingArticleId: null
};

// Subcategories Mapping
const SUBCATEGORIES = {
  All: ['All', 'Artificial Intelligence', 'Cybersecurity', 'Cloud & Infrastructure', 'Software & Applications', 'Hardware & Devices', 'Console Gaming', 'Game Releases', 'PC Gaming'],
  Technology: ['All', 'Artificial Intelligence', 'Cybersecurity', 'Cloud & Infrastructure', 'Software & Applications', 'Hardware & Devices'],
  Gaming: ['All', 'Console Gaming', 'Game Releases', 'PC Gaming']
};

document.addEventListener('DOMContentLoaded', () => {
  initTheme();
  setupEventListeners();
  initSubcategoryNav();
  loadNewsData();
  document.getElementById('year').textContent = new Date().getFullYear();
});

/* =====================================================
   DATA FETCHING & CACHING
   ===================================================== */

async function loadNewsData() {
  renderLoadingState();
  try {
    const response = await fetch(`${CONFIG.DATA_URL}?t=${Date.now()}`);
    if (!response.ok) throw new Error(`HTTP Error: ${response.status}`);
    const data = await response.json();
    
    // Cache payload for offline capability
    localStorage.setItem(CONFIG.CACHE_KEY, JSON.stringify(data));
    processNewsData(data);
  } catch (error) {
    console.warn('Network fetch failed. Loading local cache fallback:', error);
    const cached = localStorage.getItem(CONFIG.CACHE_KEY);
    if (cached) {
      processNewsData(JSON.parse(cached));
      updateStatus('Loaded from local cache (Offline)', true);
    } else {
      renderErrorState('Unable to load news. Please check your internet connection.');
    }
  }
}

function processNewsData(data) {
  state.articles = data.articles || [];
  updateStatus(`Updated live • ${data.articles ? data.articles.length : 0} articles available`);
  renderTrendingTopics(data.trendingTopics || []);
  applyFilters();
}

function updateStatus(text, isWarning = false) {
  const statusEl = document.getElementById('statusText');
  const countEl = document.getElementById('articleCount');
  if (statusEl) {
    statusEl.textContent = text;
    statusEl.style.color = isWarning ? 'var(--danger)' : 'var(--muted)';
  }
  if (countEl) countEl.textContent = `${state.filtered.length} articles`;
}

/* =====================================================
   FILTERING & RENDERING PIPELINE
   ===================================================== */

function applyFilters() {
  let list = [...state.articles];

  // Main Category
  if (state.mainCategory !== 'All') {
    list = list.filter(a => a.mainCategory === state.mainCategory);
  }

  // Subcategory
  if (state.subCategory !== 'All') {
    list = list.filter(a => a.category === state.subCategory);
  }

  // Trending Chip Filter
  if (state.trendingFilter) {
    const term = state.trendingFilter.toLowerCase();
    list = list.filter(a => 
      (a.keywords && a.keywords.some(k => k.toLowerCase() === term)) ||
      a.title.toLowerCase().includes(term)
    );
  }

  // Live Search Query
  if (state.searchQuery) {
    const q = state.searchQuery.toLowerCase();
    list = list.filter(a => 
      a.title.toLowerCase().includes(q) || 
      a.description.toLowerCase().includes(q) ||
      (a.source && a.source.toLowerCase().includes(q))
    );
  }

  state.filtered = list;
  updateStatus(`Displaying ${list.length} stories`);
  renderHeroSection(list);
  renderNewsGrid(list.slice(3)); // Top 3 populate the Hero section
}

/* =====================================================
   UI COMPONENT RENDERING
   ===================================================== */

function renderHeroSection(articles) {
  const heroMain = document.getElementById('heroMain');
  const heroSide = document.getElementById('heroSide');
  if (!heroMain || !heroSide) return;

  if (!articles.length) {
    heroMain.style.display = 'none';
    heroSide.style.display = 'none';
    return;
  }

  heroMain.style.display = 'flex';
  heroSide.style.display = 'grid';

  // Hero Article 1 (Primary Highlight)
  const topArticle = articles[0];
  heroMain.onclick = () => window.open(topArticle.url, '_blank', 'noopener,noreferrer');
  heroMain.querySelector('.hero-label').textContent = topArticle.category || 'Featured';
  heroMain.querySelector('.hero-title').textContent = topArticle.title;
  heroMain.querySelector('.hero-summary').textContent = topArticle.description;
  heroMain.querySelector('.hero-meta').textContent = `${topArticle.source} • ${formatDate(topArticle.published)}`;

  // Hero Side Articles (Positions 2 & 3)
  const sideArticles = articles.slice(1, 3);
  heroSide.innerHTML = sideArticles.map(a => `
    <div class="quick-card" onclick="window.open('${escapeHtml(a.url)}', '_blank', 'noopener,noreferrer')">
      <div class="quick-label">${escapeHtml(a.category)}</div>
      <div class="quick-title">${escapeHtml(a.title)}</div>
    </div>
  `).join('');
}

function renderNewsGrid(articles) {
  const container = document.getElementById('newsContainer');
  if (!container) return;

  if (!articles.length && state.filtered.length <= 3) {
    if (!state.filtered.length) {
      container.innerHTML = `
        <div class="empty">
          <div class="empty-icon">🔍</div>
          <h3>No articles found</h3>
          <p>Try adjusting your search query or selecting a different category.</p>
        </div>
      `;
    } else {
      container.innerHTML = ''; // Hero handles the top articles
    }
    return;
  }

  container.innerHTML = `
    <div class="news-grid">
      ${articles.map(createArticleCard).join('')}
    </div>
  `;

  setupAudioListeners();
}

function createArticleCard(article) {
  const isSpeaking = state.speakingArticleId === article.id;
  const keywordBadges = (article.keywords || [])
    .slice(0, 2)
    .map(kw => `<span class="category-badge" style="background:var(--bg);color:var(--text);border:1px solid var(--border);">${escapeHtml(kw)}</span>`)
    .join(' ');

  return `
    <article class="article">
      <div class="article-body">
        <div class="article-top">
          <span class="category-badge">${escapeHtml(article.category)}</span>
          ${article.trending ? '<span class="trending-badge">🔥 Trending</span>' : ''}
        </div>
        <h3 class="article-title">
          <a href="${escapeHtml(article.url)}" target="_blank" rel="noopener noreferrer" style="color:inherit;text-decoration:none;">
            ${escapeHtml(article.title)}
          </a>
        </h3>
        <p class="article-summary">${escapeHtml(article.description)}</p>
        <div style="margin-bottom: 10px;">${keywordBadges}</div>
        <div class="article-meta">
          <span class="source">${escapeHtml(article.source)}</span>
          <span class="time">${formatDate(article.published)}</span>
        </div>
        <div class="listen-row">
          <button class="listen-btn speak-btn" data-id="${article.id}" data-title="${escapeHtml(article.title)}" data-desc="${escapeHtml(article.description)}">
            ${isSpeaking ? '⏹ Stop' : '🔊 Listen'}
          </button>
        </div>
      </div>
    </article>
  `;
}

function renderTrendingTopics(topics) {
  const container = document.getElementById('trendingStrip');
  if (!container || !topics.length) return;

  container.innerHTML = topics.map(topic => `
    <button class="trending-chip ${state.trendingFilter === topic ? 'active' : ''}" data-topic="${escapeHtml(topic)}">
      #${escapeHtml(topic)}
    </button>
  `).join('');

  container.querySelectorAll('.trending-chip').forEach(chip => {
    chip.addEventListener('click', (e) => {
      const topic = e.target.getAttribute('data-topic');
      if (state.trendingFilter === topic) {
        state.trendingFilter = null;
      } else {
        state.trendingFilter = topic;
      }
      renderTrendingTopics(topics);
      applyFilters();
    });
  });
}

/* =====================================================
   NAVIGATION & THEME CONTROLS
   ===================================================== */

function initSubcategoryNav() {
  const container = document.getElementById('subcategoryNav');
  if (!container) return;

  const currentList = SUBCATEGORIES[state.mainCategory] || SUBCATEGORIES.All;
  container.innerHTML = currentList.map(sub => `
    <button class="${state.subCategory === sub ? 'active' : ''}" data-sub="${escapeHtml(sub)}">
      ${escapeHtml(sub)}
    </button>
  `).join('');

  container.querySelectorAll('button').forEach(btn => {
    btn.addEventListener('click', (e) => {
      container.querySelectorAll('button').forEach(b => b.classList.remove('active'));
      e.target.classList.add('active');
      state.subCategory = e.target.getAttribute('data-sub');
      applyFilters();
    });
  });
}

function setupEventListeners() {
  // Main Category Navigation
  document.querySelectorAll('.main-nav button').forEach(btn => {
    btn.addEventListener('click', (e) => {
      document.querySelectorAll('.main-nav button').forEach(b => b.classList.remove('active'));
      e.target.classList.add('active');
      state.mainCategory = e.target.getAttribute('data-main-category');
      state.subCategory = 'All';
      initSubcategoryNav();
      applyFilters();
    });
  });

  // Debounced Search Input
  const searchInput = document.getElementById('search');
  if (searchInput) {
    let timer;
    searchInput.addEventListener('input', (e) => {
      clearTimeout(timer);
      timer = setTimeout(() => {
        state.searchQuery = e.target.value.trim();
        applyFilters();
      }, CONFIG.DEBOUNCE_MS);
    });
  }

  // Refresh Button
  const refreshBtn = document.getElementById('refreshButton');
  if (refreshBtn) {
    refreshBtn.addEventListener('click', async () => {
      refreshBtn.disabled = true;
      refreshBtn.textContent = '⏳ Fetching...';
      await loadNewsData();
      refreshBtn.disabled = false;
      refreshBtn.textContent = '↻ Refresh';
    });
  }

  // Theme Toggle
  const themeBtn = document.getElementById('themeButton');
  if (themeBtn) {
    themeBtn.addEventListener('click', toggleTheme);
  }

  // Language Selector
  const langSelect = document.getElementById('languageSelect');
  if (langSelect) {
    langSelect.addEventListener('change', (e) => {
      state.language = e.target.value;
      if ('speechSynthesis' in window) window.speechSynthesis.cancel();
    });
  }
}

function initTheme() {
  const savedTheme = localStorage.getItem(CONFIG.THEME_KEY);
  const themeBtn = document.getElementById('themeButton');
  if (savedTheme === 'dark') {
    document.body.classList.add('dark');
    if (themeBtn) themeBtn.textContent = '☀️';
  } else {
    document.body.classList.remove('dark');
    if (themeBtn) themeBtn.textContent = '☾';
  }
}

function toggleTheme() {
  const isDark = document.body.classList.toggle('dark');
  const themeBtn = document.getElementById('themeButton');
  localStorage.setItem(CONFIG.THEME_KEY, isDark ? 'dark' : 'light');
  if (themeBtn) themeBtn.textContent = isDark ? '☀️' : '☾';
}

/* =====================================================
   ACCESSIBILITY & TEXT-TO-SPEECH
   ===================================================== */

function setupAudioListeners() {
  document.querySelectorAll('.speak-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      const articleId = btn.getAttribute('data-id');
      const title = btn.getAttribute('data-title');
      const desc = btn.getAttribute('data-desc');

      if (state.speakingArticleId === articleId) {
        stopSpeech();
      } else {
        speakText(articleId, `${title}. ${desc}`);
      }
    });
  });
}

function speakText(id, text) {
  if (!('speechSynthesis' in window)) {
    alert('Speech synthesis is not supported in your browser.');
    return;
  }

  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = state.language || 'en';

  utterance.onend = () => {
    state.speakingArticleId = null;
    applyFilters();
  };

  utterance.onerror = () => {
    state.speakingArticleId = null;
    applyFilters();
  };

  state.speakingArticleId = id;
  window.speechSynthesis.speak(utterance);
  applyFilters();
}

function stopSpeech() {
  if ('speechSynthesis' in window) {
    window.speechSynthesis.cancel();
  }
  state.speakingArticleId = null;
  applyFilters();
}

/* =====================================================
   HELPER UTILITIES
   ===================================================== */

function formatDate(isoStr) {
  if (!isoStr) return '';
  const date = new Date(isoStr);
  const diffMs = Date.now() - date.getTime();
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));

  if (diffHours < 1) return 'Just now';
  if (diffHours < 24) return `${diffHours}h ago`;
  return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

function escapeHtml(str) {
  return String(str || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function renderLoadingState() {
  const container = document.getElementById('newsContainer');
  if (container) {
    container.innerHTML = `
      <div class="loading">
        <div class="spinner"></div>
        Loading latest stories...
      </div>
    `;
  }
}

function renderErrorState(msg) {
  const container = document.getElementById('newsContainer');
  if (container) {
    container.innerHTML = `
      <div class="empty">
        <div class="empty-icon">⚠️</div>
        <h3>Something went wrong</h3>
        <p>${escapeHtml(msg)}</p>
      </div>
    `;
  }
}
