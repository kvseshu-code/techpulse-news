/* =========================================================
   TECHPULSE — GitHub Pages Frontend
   Loads news from news.json
   No Google Apps Script dependency
   ========================================================= */

'use strict';


/* =========================================================
   STATE
   ========================================================= */

let allArticles = [];

let currentMainCategory = 'All';

let currentSubcategory = 'All';

let lastUpdatedAt = null;

let knownArticleIds = new Set();


const NEWS_FILE = './news.json';

const AUTO_REFRESH_INTERVAL = 2 * 60 * 1000;


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
   INITIALIZATION
   ========================================================= */

document.addEventListener(
  'DOMContentLoaded',
  function () {

    const year =
      document.getElementById('year');

    if (year) {

      year.textContent =
        new Date().getFullYear();

    }


    loadSavedTheme();

    buildSubcategoryNav();

    loadNews(true);


    /*
     * Check for updated news every 2 minutes.
     */

    setInterval(
      function () {

        loadNews(false);

      },
      AUTO_REFRESH_INTERVAL
    );


    /*
     * Update relative article times every minute.
     */

    setInterval(
      function () {

        refreshVisibleTimes();

      },
      60 * 1000
    );

  }
);


/* =========================================================
   LOAD NEWS
   ========================================================= */

async function loadNews(
  forceRefresh = false
) {

  const status =
    document.getElementById(
      'statusText'
    );


  if (status) {

    status.textContent =
      forceRefresh
        ? 'Loading latest news...'
        : 'Checking for latest news...';

  }


  try {

    /*
     * Cache busting is used during refresh.
     *
     * This prevents the browser from
     * continuously displaying an old
     * cached news.json.
     */

    const cacheParameter =
      '?t=' + Date.now();


    const response =
      await fetch(
        NEWS_FILE + cacheParameter,
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
        'Unable to load news.json. HTTP ' +
        response.status
      );

    }


    const data =
      await response.json();


    if (
      !data ||
      !Array.isArray(
        data.articles
      )
    ) {

      throw new Error(
        'Invalid news.json format.'
      );

    }


    const previousIds =
      new Set(
        allArticles.map(
          function (article) {

            return article.id;

          }
        )
      );


    allArticles =
      normalizeArticles(
        data.articles
      );


    lastUpdatedAt =
      data.updatedAt ||
      new Date().toISOString();


    allArticles.forEach(
      function (article) {

        knownArticleIds.add(
          article.id
        );

      }
    );


    /*
     * Sort newest first.
     */

    allArticles.sort(
      function (a, b) {

        return (
          new Date(
            b.published
          ).getTime()
          -
          new Date(
            a.published
          ).getTime()
        );

      }
    );


    renderHero();

    applyFilters();


    const newCount =
      allArticles.filter(
        function (article) {

          return !previousIds.has(
            article.id
          );

        }
      ).length;


    if (status) {

      if (
        previousIds.size > 0 &&
        newCount > 0
      ) {

        status.textContent =
          newCount +
          (
            newCount === 1
              ? ' new story'
              : ' new stories'
          ) +
          ' found • Updated ' +
          formatTime(
            lastUpdatedAt
          );

      } else {

        status.textContent =
          'News updated ' +
          formatTime(
            lastUpdatedAt
          );

      }

    }

  } catch (error) {

    console.error(
      'TechPulse news error:',
      error
    );


    showError(
      error.message ||
      'Unable to load the latest news.'
    );

  }

}


/* =========================================================
   NORMALIZE ARTICLES
   ========================================================= */

function normalizeArticles(
  articles
) {

  return articles
    .map(
      function (article, index) {

        const published =
          article.published ||
          article.pubDate ||
          new Date().toISOString();


        const title =
          article.title ||
          'Untitled story';


        const url =
          article.url ||
          article.link ||
          '#';


        const id =
          article.id ||
          createArticleId(
            title,
            url,
            published,
            index
          );


        return {

          id: String(id),

          title:
            String(title),

          description:
            String(
              article.description ||
              'Read the latest story from the original publisher.'
            ),

          url:
            String(url),

          image:
            String(
              article.image ||
              ''
            ),

          category:
            String(
              article.category ||
              'General'
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
              'TechPulse'
            ),

          published:
            published

        };

      }
    );

}


/* =========================================================
   CREATE ARTICLE ID
   ========================================================= */

function createArticleId(
  title,
  url,
  published,
  index
) {

  const raw =
    title +
    '|' +
    url +
    '|' +
    published +
    '|' +
    index;


  let hash = 0;


  for (
    let i = 0;
    i < raw.length;
    i++
  ) {

    hash =
      (
        (
          hash << 5
        ) -
        hash
      ) +
      raw.charCodeAt(i);

    hash |= 0;

  }


  return (
    'article-' +
    Math.abs(hash)
  );

}


/* =========================================================
   DETECT MAIN CATEGORY
   ========================================================= */

function detectMainCategory(
  category
) {

  const value =
    String(
      category || ''
    )
    .toLowerCase();


  const gamingKeywords = [

    'gaming',
    'game',
    'games',
    'esports',
    'playstation',
    'xbox',
    'nintendo',
    'steam',
    'pc gaming'

  ];


  for (
    const keyword of gamingKeywords
  ) {

    if (
      value.includes(keyword)
    ) {

      return 'Gaming';

    }

  }


  return 'Technology';

}


/* =========================================================
   MANUAL REFRESH
   ========================================================= */

function manualRefresh() {

  const button =
    document.getElementById(
      'refreshButton'
    );


  if (button) {

    button.disabled = true;

    button.textContent =
      'Refreshing...';

  }


  loadNews(true)
    .finally(
      function () {

        if (button) {

          button.disabled =
            false;

          button.textContent =
            '↻ Refresh';

        }

      }
    );

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
      function (btn) {

        btn.classList.remove(
          'active'
        );

      }
    );


  if (button) {

    button.classList.add(
      'active'
    );

  }


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
      function (btn) {

        btn.classList.remove(
          'active'
        );

      }
    );


  if (button) {

    button.classList.add(
      'active'
    );

  }


  updateSectionTitle();

  applyFilters();

}


/* =========================================================
   BUILD SUBCATEGORY NAV
   ========================================================= */

function buildSubcategoryNav() {

  const nav =
    document.getElementById(
      'subcategoryNav'
    );


  if (!nav) {

    return;

  }


  const categories =
    SUBCATEGORIES[
      currentMainCategory
    ] ||
    SUBCATEGORIES.All;


  nav.innerHTML =
    categories
      .map(
        function (
          category,
          index
        ) {

          const value =
            category === 'All Topics'
              ? 'All'
              : category;


          const active =
            (
              (
                index === 0 &&
                currentSubcategory === 'All'
              ) ||
              currentSubcategory === value
            );


          return `

            <button
              class="${active ? 'active' : ''}"
              onclick="selectSubcategory(
                '${escapeJs(value)}',
                this
              )"
            >
              ${escapeHtml(category)}
            </button>

          `;

        }
      )
      .join('');

}


/* =========================================================
   FILTER
   ========================================================= */

function applyFilters() {

  const searchElement =
    document.getElementById(
      'search'
    );


  const search =
    searchElement
      ? searchElement.value
          .toLowerCase()
          .trim()
      : '';


  const filtered =
    allArticles.filter(
      function (article) {

        const mainMatch =
          currentMainCategory ===
          'All' ||
          article.mainCategory ===
          currentMainCategory;


        const subMatch =
          currentSubcategory ===
          'All' ||
          article.category ===
          currentSubcategory;


        const searchText = (

          article.title +
          ' ' +
          article.description +
          ' ' +
          article.category +
          ' ' +
          article.mainCategory +
          ' ' +
          article.source

        ).toLowerCase();


        const searchMatch =
          !search ||
          searchText.includes(
            search
          );


        return (
          mainMatch &&
          subMatch &&
          searchMatch
        );

      }
    );


  renderNews(
    filtered
  );

}


/* =========================================================
   RENDER NEWS
   ========================================================= */

function renderNews(
  articles
) {

  const container =
    document.getElementById(
      'newsContainer'
    );


  if (!container) {

    return;

  }


  const countElement =
    document.getElementById(
      'articleCount'
    );


  if (countElement) {

    countElement.textContent =
      articles.length +
      (
        articles.length === 1
          ? ' article'
          : ' articles'
      );

  }


  if (!articles.length) {

    container.innerHTML = `

      <div class="empty">

        <div class="empty-icon">
          🔎
        </div>

        <h3>
          No stories found
        </h3>

        <p>
          Try another topic or search term.
        </p>

      </div>

    `;

    return;

  }


  container.innerHTML = `

    <div class="news-grid">

      ${
        articles
          .map(
            createArticleCard
          )
          .join('')
      }

    </div>

  `;

}


/* =========================================================
   ARTICLE CARD
   ========================================================= */

function createArticleCard(
  article
) {

  const publishedTime =
    new Date(
      article.published
    ).getTime();


  const isNew =
    !isNaN(publishedTime) &&
    (
      Date.now() -
      publishedTime
    ) <
    2 * 60 * 60 * 1000;


  const placeholder =
    article.mainCategory ===
    'Gaming'
      ? '🎮'
      : '⚡';


  let imageHtml = `

    <div class="image-placeholder">

      ${placeholder}

    </div>

  `;


  if (
    article.image &&
    /^https?:\/\//i.test(
      article.image
    )
  ) {

    imageHtml = `

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
        ${placeholder}
      </div>

    `;

  }


  const safeUrl =
    /^https?:\/\//i.test(
      article.url
    )
      ? article.url
      : '#';


  return `

    <article class="article">

      <div class="article-image-wrap">

        ${imageHtml}

        ${
          isNew
            ? `
              <span class="new-badge">
                NEW
              </span>
            `
            : ''
        }

      </div>


      <div class="article-body">

        <div class="article-category">

          <span class="category-badge">

            ${escapeHtml(
              article.category
            )}

          </span>

        </div>


        <h3 class="article-title">

          <a
            href="${escapeHtml(safeUrl)}"
            target="_blank"
            rel="noopener noreferrer"
          >

            ${escapeHtml(
              article.title
            )}

          </a>

        </h3>


        <p class="article-description">

          ${escapeHtml(
            article.description
          )}

        </p>


        <div class="article-footer">

          <span class="source-name">

            ${escapeHtml(
              article.source
            )}

          </span>


          <span
            class="article-time"
            data-time="${escapeHtml(
              article.published
            )}"
          >

            ${formatRelativeTime(
              article.published
            )}

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

  if (
    !allArticles.length
  ) {

    return;

  }


  const latest =
    allArticles[0];


  const technology =
    allArticles.find(
      function (article) {

        return (
          article.mainCategory ===
          'Technology'
        );

      }
    );


  const gaming =
    allArticles.find(
      function (article) {

        return (
          article.mainCategory ===
          'Gaming'
        );

      }
    );


  const hero =
    document.getElementById(
      'heroMain'
    );


  if (hero) {

    hero.innerHTML = `

      <div class="hero-label">
        Fresh Story
      </div>

      <div class="hero-title">

        ${escapeHtml(
          latest.title
        )}

      </div>

      <div class="hero-meta">

        ${escapeHtml(
          latest.category
        )}

        •

        ${escapeHtml(
          latest.source
        )}

        •

        ${formatRelativeTime(
          latest.published
        )}

      </div>

    `;

  }


  const side =
    document.getElementById(
      'heroSide'
    );


  if (side) {

    side.innerHTML = `

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

}


/* =========================================================
   QUICK HERO CARD
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
      onclick="openArticle('${escapeJs(
        article.url
      )}')"
    >

      <div class="quick-label">
        ${escapeHtml(label)}
      </div>

      <div class="quick-title">

        ${escapeHtml(
          article.title
        )}

      </div>

    </div>

  `;

}


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


  const titleElement =
    document.getElementById(
      'sectionTitle'
    );


  const subtitleElement =
    document.getElementById(
      'sectionSubtitle'
    );


  if (titleElement) {

    titleElement.textContent =
      title;

  }


  if (subtitleElement) {

    subtitleElement.textContent =
      'Fresh stories updated automatically';

  }

}


/* =========================================================
   RELATIVE TIME
   ========================================================= */

function formatRelativeTime(
  value
) {

  const date =
    new Date(value);


  if (
    isNaN(
      date.getTime()
    )
  ) {

    return 'Recently';

  }


  const seconds =
    Math.floor(
      (
        Date.now() -
        date.getTime()
      ) / 1000
    );


  if (
    seconds < 0
  ) {

    return 'Just now';

  }


  if (
    seconds < 60
  ) {

    return 'Just now';

  }


  const minutes =
    Math.floor(
      seconds / 60
    );


  if (
    minutes < 60
  ) {

    return (
      minutes +
      ' min ago'
    );

  }


  const hours =
    Math.floor(
      minutes / 60
    );


  if (
    hours < 24
  ) {

    return (
      hours +
      ' hr ago'
    );

  }


  const days =
    Math.floor(
      hours / 24
    );


  if (
    days === 1
  ) {

    return 'Yesterday';

  }


  return (
    days +
    ' days ago'
  );

}


/* =========================================================
   SERVER / JSON UPDATE TIME
   ========================================================= */

function formatTime(
  value
) {

  const date =
    new Date(value);


  if (
    isNaN(
      date.getTime()
    )
  ) {

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
   REFRESH VISIBLE TIMES
   ========================================================= */

function refreshVisibleTimes() {

  document
    .querySelectorAll(
      '.article-time'
    )
    .forEach(
      function (element) {

        const value =
          element.dataset.time;


        if (value) {

          element.textContent =
            formatRelativeTime(
              value
            );

        }

      }
    );


  if (allArticles.length) {

    renderHero();

  }

}


/* =========================================================
   ERROR
   ========================================================= */

function showError(
  message
) {

  const status =
    document.getElementById(
      'statusText'
    );


  if (status) {

    status.textContent =
      'News service temporarily unavailable';

  }


  const container =
    document.getElementById(
      'newsContainer'
    );


  if (!container) {

    return;

  }


  container.innerHTML = `

    <div class="empty">

      <div class="empty-icon">
        ⚠️
      </div>

      <h3>
        Unable to load news
      </h3>

      <p>
        ${escapeHtml(message)}
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

function openArticle(
  url
) {

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

  document.body.classList.toggle(
    'dark'
  );


  const dark =
    document.body.classList.contains(
      'dark'
    );


  try {

    localStorage.setItem(
      'techpulse-theme',
      dark
        ? 'dark'
        : 'light'
    );

  } catch (error) {

    console.warn(
      'Unable to save theme preference.'
    );

  }


  const button =
    document.getElementById(
      'themeButton'
    );


  if (button) {

    button.textContent =
      dark
        ? '☀'
        : '☾';

  }

}


/* =========================================================
   LOAD SAVED THEME
   ========================================================= */

function loadSavedTheme() {

  let saved = null;


  try {

    saved =
      localStorage.getItem(
        'techpulse-theme'
      );

  } catch (error) {

    saved = null;

  }


  if (
    saved === 'dark'
  ) {

    document.body.classList.add(
      'dark'
    );


    const button =
      document.getElementById(
        'themeButton'
      );


    if (button) {

      button.textContent =
        '☀';

    }

  }

}


/* =========================================================
   ESCAPE HTML
   ========================================================= */

function escapeHtml(
  value
) {

  return String(
    value == null
      ? ''
      : value
  )
    .replace(
      /&/g,
      '&amp;'
    )
    .replace(
      /</g,
      '&lt;'
    )
    .replace(
      />/g,
      '&gt;'
    )
    .replace(
      /"/g,
      '&quot;'
    )
    .replace(
      /'/g,
      '&#039;'
    );

}


/* =========================================================
   ESCAPE JAVASCRIPT
   ========================================================= */

function escapeJs(
  value
) {

  return String(
    value == null
      ? ''
      : value
  )
    .replace(
      /\\/g,
      '\\\\'
    )
    .replace(
      /'/g,
      "\\'"
    )
    .replace(
      /\r/g,
      '\\r'
    )
    .replace(
      /\n/g,
      '\\n'
    );

}
