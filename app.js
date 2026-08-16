'use strict';


/* =========================================================
   TECHPULSE FRONTEND
   GitHub Pages + news.json
   ========================================================= */

const NEWS_FILE = './news.json';

const AUTO_REFRESH_INTERVAL = 2 * 60 * 1000;

let allArticles = [];

let currentMainCategory = 'All';

let currentSubcategory = 'All';

let lastUpdatedAt = null;


/* =========================================================
   SUBCATEGORIES
   ========================================================= */

const SUBCATEGORIES = {

  Technology: [
    'All Topics',
    'Artificial Intelligence',
    'Smartphones & Mobile',
    'Cybersecurity',
    'Cloud & Infrastructure',
    'Software & Applications',
    'Hardware & Devices',
    'Internet & Web',
    'Emerging Technology',
    'Science & Innovation',
    'Business & Technology'
  ],

  Gaming: [
    'All Topics',
    'PC Gaming',
    'Console Gaming',
    'Mobile Gaming',
    'Game Releases',
    'Gaming Hardware',
    'Esports',
    'Game Development',
    'Gaming Industry',
    'Gaming Updates',
    'Reviews & Features'
  ],

  All: [
    'All Topics'
  ]

};


/* =========================================================
   START
   ========================================================= */

document.addEventListener(
  'DOMContentLoaded',
  () => {

    document.getElementById('year').textContent =
      new Date().getFullYear();

    loadSavedTheme();

    buildSubcategoryNav();

    loadNews(true);


    setInterval(
      () => {
        loadNews(false);
      },
      AUTO_REFRESH_INTERVAL
    );


    setInterval(
      refreshVisibleTimes,
      60 * 1000
    );


    document
      .getElementById('themeButton')
      .addEventListener(
        'click',
        toggleTheme
      );


    document
      .getElementById('refreshButton')
      .addEventListener(
        'click',
        manualRefresh
      );


    document
      .getElementById('search')
      .addEventListener(
        'input',
        applyFilters
      );


    document
      .querySelectorAll(
        '[data-main-category]'
      )
      .forEach(
        button => {

          button.addEventListener(
            'click',
            () => {

              selectMainCategory(
                button.dataset.mainCategory,
                button
              );

            }
          );

        }
      );

  }
);


/* =========================================================
   LOAD NEWS
   ========================================================= */

async function loadNews(forceRefresh = false) {

  const status =
    document.getElementById('statusText');

  if (status) {

    status.textContent =
      forceRefresh
        ? 'Loading latest news...'
        : 'Checking for new stories...';

  }


  try {

    const response =
      await fetch(
        NEWS_FILE + '?t=' + Date.now(),
        {
          method: 'GET',
          cache: 'no-store',
          headers: {
            'Accept': 'application/json'
          }
        }
      );


    if (!response.ok) {

      throw new Error(
        `Unable to load news.json. HTTP ${response.status}`
      );

    }


    const data =
      await response.json();


    if (
      !data ||
      !Array.isArray(data.articles)
    ) {

      throw new Error(
        'Invalid news.json format.'
      );

    }


    const previousIds =
      new Set(
        allArticles.map(
          article => article.id
        )
      );


    allArticles =
      normalizeArticles(
        data.articles
      );


    allArticles.sort(
      (a, b) =>
        new Date(b.published) -
        new Date(a.published)
    );


    lastUpdatedAt =
      data.updatedAt ||
      new Date().toISOString();


    renderHero();

    applyFilters();


    const newArticles =
      allArticles.filter(
        article =>
          !previousIds.has(article.id)
      );


    if (status) {

      if (
        previousIds.size &&
        newArticles.length
      ) {

        status.textContent =
          `${newArticles.length} new ${
            newArticles.length === 1
              ? 'story'
              : 'stories'
          } found • Updated ${formatTime(lastUpdatedAt)}`;

      } else {

        status.textContent =
          `News updated ${formatTime(lastUpdatedAt)}`;

      }

    }

  } catch (error) {

    console.error(
      'TechPulse error:',
      error
    );

    showError(
      error.message
    );

  }

}


/* =========================================================
   NORMALIZE
   ========================================================= */

function normalizeArticles(articles) {

  return articles
    .map(
      (article, index) => {

        const title =
          String(
            article.title ||
            'Untitled story'
          );


        const url =
          String(
            article.url ||
            article.link ||
            '#'
          );


        const published =
          article.published ||
          article.pubDate ||
          new Date().toISOString();


        return {

          id:
            String(
              article.id ||
              createArticleId(
                title,
                url,
                published,
                index
              )
            ),

          title,

          description:
            cleanText(
              article.description ||
              'Read the latest story from the original publisher.'
            ),

          url,

          image:
            String(
              article.image ||
              ''
            ),

          category:
            String(
              article.category ||
              'Technology'
            ),

          mainCategory:
            String(
              article.mainCategory ||
              detectMainCategory(
                article.category
              )
            ),

          source:
            String(
              article.source ||
              'News Source'
            ),

          published

        };

      }
    );

}


/* =========================================================
   CATEGORY
   ========================================================= */

function detectMainCategory(category) {

  const value =
    String(
      category || ''
    ).toLowerCase();


  const gamingKeywords = [
    'gaming',
    'game',
    'games',
    'esports',
    'console',
    'pc gaming',
    'mobile gaming'
  ];


  if (
    gamingKeywords.some(
      keyword =>
        value.includes(keyword)
    )
  ) {

    return 'Gaming';

  }


  return 'Technology';

}


/* =========================================================
   MAIN CATEGORY
   ========================================================= */

function selectMainCategory(
  category,
  button
) {

  currentMainCategory =
    category;

  currentSubcategory =
    'All';


  document
    .querySelectorAll(
      '.main-nav button'
    )
    .forEach(
      btn =>
        btn.classList.remove('active')
    );


  button.classList.add('active');


  buildSubcategoryNav();

  updateSectionTitle();

  applyFilters();

}


/* =========================================================
   SUBCATEGORY
   ========================================================= */

function selectSubcategory(
  category,
  button
) {

  currentSubcategory =
    category === 'All Topics'
      ? 'All'
      : category;


  document
    .querySelectorAll(
      '.subnav button'
    )
    .forEach(
      btn =>
        btn.classList.remove('active')
    );


  button.classList.add('active');


  updateSectionTitle();

  applyFilters();

}


/* =========================================================
   BUILD SUBNAV
   ========================================================= */

function buildSubcategoryNav() {

  const nav =
    document.getElementById(
      'subcategoryNav'
    );


  const categories =
    SUBCATEGORIES[
      currentMainCategory
    ] ||
    SUBCATEGORIES.All;


  nav.innerHTML =
    categories
      .map(
        category => {

          const value =
            category === 'All Topics'
              ? 'All'
              : category;


          const active =
            currentSubcategory === value;


          return `
            <button
              class="${active ? 'active' : ''}"
              data-subcategory="${escapeHtml(value)}"
            >
              ${escapeHtml(category)}
            </button>
          `;

        }
      )
      .join('');


  nav
    .querySelectorAll(
      '[data-subcategory]'
    )
    .forEach(
      button => {

        button.addEventListener(
          'click',
          () => {

            selectSubcategory(
              button.dataset.subcategory,
              button
            );

          }
        );

      }
    );

}


/* =========================================================
   FILTER
   ========================================================= */

function applyFilters() {

  const search =
    document
      .getElementById('search')
      .value
      .toLowerCase()
      .trim();


  const filtered =
    allArticles.filter(
      article => {

        const mainMatch =
          currentMainCategory === 'All' ||
          article.mainCategory ===
            currentMainCategory;


        const subMatch =
          currentSubcategory === 'All' ||
          article.category ===
            currentSubcategory;


        const searchable =
          [
            article.title,
            article.description,
            article.category,
            article.mainCategory,
            article.source
          ]
          .join(' ')
          .toLowerCase();


        const searchMatch =
          !search ||
          searchable.includes(search);


        return (
          mainMatch &&
          subMatch &&
          searchMatch
        );

      }
    );


  renderNews(filtered);

}


/* =========================================================
   RENDER NEWS
   ========================================================= */

function renderNews(articles) {

  const container =
    document.getElementById(
      'newsContainer'
    );


  document.getElementById(
    'articleCount'
  ).textContent =
    `${articles.length} ${
      articles.length === 1
        ? 'article'
        : 'articles'
    }`;


  if (!articles.length) {

    container.innerHTML = `
      <div class="empty">
        <div class="empty-icon">🔎</div>

        <h3>No stories found</h3>

        <p>
          Try another category or search term.
        </p>
      </div>
    `;

    return;

  }


  container.innerHTML = `
    <div class="news-grid">
      ${articles
        .map(createArticleCard)
        .join('')}
    </div>
  `;

}


/* =========================================================
   ARTICLE CARD
   ========================================================= */

function createArticleCard(article) {

  const date =
    new Date(article.published);


  const isNew =
    !isNaN(date) &&
    Date.now() - date.getTime()
      <
    2 * 60 * 60 * 1000;


  const icon =
    article.mainCategory === 'Gaming'
      ? '🎮'
      : '⚡';


  let image =
    `
      <div class="image-placeholder">
        ${icon}
      </div>
    `;


  if (
    article.image &&
    /^https?:\/\//i.test(article.image)
  ) {

    image =
      `
        <img
          class="article-image"
          src="${escapeHtml(article.image)}"
          alt=""
          loading="lazy"
          referrerpolicy="no-referrer"
          onerror="this.style.display='none';this.nextElementSibling.style.display='flex';"
        >

        <div
          class="image-placeholder"
          style="display:none;"
        >
          ${icon}
        </div>
      `;

  }


  const safeUrl =
    /^https?:\/\//i.test(article.url)
      ? article.url
      : '#';


  return `
    <article class="article">

      <div class="article-image-wrap">

        ${image}

        ${
          isNew
            ? '<span class="new-badge">NEW</span>'
            : ''
        }

      </div>


      <div class="article-body">

        <div class="article-category">

          <span class="category-badge">
            ${escapeHtml(article.category)}
          </span>

        </div>


        <h3 class="article-title">

          <a
            href="${escapeHtml(safeUrl)}"
            target="_blank"
            rel="noopener noreferrer"
          >
            ${escapeHtml(article.title)}
          </a>

        </h3>


        <p class="article-description">
          ${escapeHtml(article.description)}
        </p>


        <div class="article-footer">

          <span class="source-name">
            ${escapeHtml(article.source)}
          </span>

          <span
            class="article-time"
            data-time="${escapeHtml(article.published)}"
          >
            ${formatRelativeTime(article.published)}
          </span>

        </div>

      </div>

    </article>
  `;

}


/* =========================================================
   HERO
   ========================================================= */

function renderHero() {

  if (!allArticles.length) {
    return;
  }


  const latest =
    allArticles[0];


  const technology =
    allArticles.find(
      article =>
        article.mainCategory ===
        'Technology'
    );


  const gaming =
    allArticles.find(
      article =>
        article.mainCategory ===
        'Gaming'
    );


  const hero =
    document.getElementById(
      'heroMain'
    );


  hero.innerHTML = `
    <div class="hero-label">
      Fresh Story
    </div>

    <div class="hero-title">
      ${escapeHtml(latest.title)}
    </div>

    <div class="hero-meta">
      ${escapeHtml(latest.category)}
      •
      ${escapeHtml(latest.source)}
      •
      ${formatRelativeTime(latest.published)}
    </div>
  `;


  hero.onclick =
    () => openArticle(latest.url);


  document.getElementById(
    'heroSide'
  ).innerHTML = `

    ${createQuickHeroCard(
      'Technology',
      technology
    )}

    ${createQuickHeroCard(
      'Gaming',
      gaming
    )}

  `;

}


/* =========================================================
   QUICK CARD
   ========================================================= */

function createQuickHeroCard(
  label,
  article
) {

  if (!article) {

    return `
      <div class="quick-card">

        <div class="quick-label">
          ${escapeHtml(label)}
        </div>

        <div class="quick-title">
          No current story available.
        </div>

      </div>
    `;

  }


  return `
    <div
      class="quick-card"
      data-url="${escapeHtml(article.url)}"
    >

      <div class="quick-label">
        ${escapeHtml(label)}
      </div>

      <div class="quick-title">
        ${escapeHtml(article.title)}
      </div>

    </div>
  `;

}


/* =========================================================
   QUICK CARD CLICK
   ========================================================= */

document.addEventListener(
  'click',
  event => {

    const card =
      event.target.closest(
        '.quick-card[data-url]'
      );


    if (card) {

      openArticle(
        card.dataset.url
      );

    }

  }
);


/* =========================================================
   SECTION TITLE
   ========================================================= */

function updateSectionTitle() {

  let title =
    'Latest News';


  if (
    currentMainCategory !==
    'All'
  ) {

    title =
      currentMainCategory;

  }


  if (
    currentSubcategory !==
    'All'
  ) {

    title =
      currentSubcategory;

  }


  document.getElementById(
    'sectionTitle'
  ).textContent =
    title;


  document.getElementById(
    'sectionSubtitle'
  ).textContent =
    'Fresh stories updated automatically';

}


/* =========================================================
   MANUAL REFRESH
   ========================================================= */

async function manualRefresh() {

  const button =
    document.getElementById(
      'refreshButton'
    );


  button.disabled = true;

  button.textContent =
    'Refreshing...';


  await loadNews(true);


  button.disabled = false;

  button.textContent =
    '↻ Refresh';

}


/* =========================================================
   RELATIVE TIME
   ========================================================= */

function formatRelativeTime(value) {

  const date =
    new Date(value);


  if (isNaN(date)) {
    return 'Recently';
  }


  const seconds =
    Math.floor(
      (Date.now() - date.getTime()) /
      1000
    );


  if (seconds < 60) {
    return 'Just now';
  }


  const minutes =
    Math.floor(seconds / 60);


  if (minutes < 60) {
    return `${minutes} min ago`;
  }


  const hours =
    Math.floor(minutes / 60);


  if (hours < 24) {
    return `${hours} hr ago`;
  }


  const days =
    Math.floor(hours / 24);


  if (days === 1) {
    return 'Yesterday';
  }


  return `${days} days ago`;

}


/* =========================================================
   TIME
   ========================================================= */

function formatTime(value) {

  const date =
    new Date(value);


  if (isNaN(date)) {
    return 'recently';
  }


  return date.toLocaleTimeString(
    undefined,
    {
      hour: 'numeric',
      minute: '2-digit'
    }
  );

}


/* =========================================================
   UPDATE VISIBLE TIMES
   ========================================================= */

function refreshVisibleTimes() {

  document
    .querySelectorAll(
      '.article-time'
    )
    .forEach(
      element => {

        const value =
          element.dataset.time;


        if (value) {

          element.textContent =
            formatRelativeTime(value);

        }

      }
    );


  renderHero();

}


/* =========================================================
   ERROR
   ========================================================= */

function showError(message) {

  document.getElementById(
    'statusText'
  ).textContent =
    'News service temporarily unavailable';


  document.getElementById(
    'newsContainer'
  ).innerHTML = `

    <div class="empty">

      <div class="empty-icon">
        ⚠️
      </div>

      <h3>
        Unable to load news
      </h3>

      <p>
        ${escapeHtml(
          message ||
          'Please try again.'
        )}
      </p>

      <br>

      <button
        class="refresh-btn"
        onclick="manualRefresh()"
      >
        Try Again
      </button>

    </div>

  `;

}


/* =========================================================
   OPEN ARTICLE
   ========================================================= */

function openArticle(url) {

  if (
    /^https?:\/\//i.test(url)
  ) {

    window.open(
      url,
      '_blank',
      'noopener,noreferrer'
    );

  }

}


/* =========================================================
   DARK MODE
   ========================================================= */

function toggleTheme() {

  document.body.classList.toggle('dark');


  const dark =
    document.body.classList.contains('dark');


  try {

    localStorage.setItem(
      'techpulse-theme',
      dark ? 'dark' : 'light'
    );

  } catch (error) {
    console.warn(error);
  }


  document.getElementById(
    'themeButton'
  ).textContent =
    dark ? '☀' : '☾';

}


function loadSavedTheme() {

  try {

    const saved =
      localStorage.getItem(
        'techpulse-theme'
      );


    if (saved === 'dark') {

      document.body.classList.add(
        'dark'
      );

      document.getElementById(
        'themeButton'
      ).textContent =
        '☀';

    }

  } catch (error) {
    console.warn(error);
  }

}


/* =========================================================
   CLEAN TEXT
   ========================================================= */

function cleanText(value) {

  const element =
    document.createElement('div');


  element.innerHTML =
    String(value || '');


  return (
    element.textContent ||
    element.innerText ||
    ''
  )
    .replace(/\s+/g, ' ')
    .trim();

}


/* =========================================================
   ARTICLE ID
   ========================================================= */

function createArticleId(
  title,
  url,
  published,
  index
) {

  const raw =
    `${title}|${url}|${published}|${index}`;


  let hash = 0;


  for (
    let i = 0;
    i < raw.length;
    i++
  ) {

    hash =
      (
        (hash << 5) -
        hash +
        raw.charCodeAt(i)
      ) |
      0;

  }


  return `article-${Math.abs(hash)}`;

}


/* =========================================================
   ESCAPE HTML
   ========================================================= */

function escapeHtml(value) {

  return String(
    value == null
      ? ''
      : value
  )
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');

}
