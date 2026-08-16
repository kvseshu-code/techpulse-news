'use strict';

/*
=========================================================
 TECHPULSE FRONTEND
 --------------------------------------------------------
 Data source:
   ./news.json

 No Google Apps Script.
 No Google Sheets.
 No database.

 GitHub Actions updates news.json automatically.
 This frontend reads the latest news.json periodically.
=========================================================
*/


/* =====================================================
   CONFIGURATION
   ===================================================== */

const NEWS_FILE = './news.json';

/*
 * Check GitHub Pages for new news every 2 minutes.
 *
 * GitHub Actions is responsible for generating the
 * actual news.json every 15 minutes.
 */
const AUTO_REFRESH_INTERVAL = 2 * 60 * 1000;

/*
 * Articles newer than this are marked NEW.
 */
const NEW_ARTICLE_WINDOW = 2 * 60 * 60 * 1000;


/* =====================================================
   STATE
   ===================================================== */

let allArticles = [];

let currentMainCategory = 'All';

let currentSubcategory = 'All';

let lastUpdatedAt = null;

let previousArticleIds = new Set();

let firstLoad = true;


/* =====================================================
   SUBCATEGORIES
   ===================================================== */

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


/* =====================================================
   INITIALIZATION
   ===================================================== */

document.addEventListener(
  'DOMContentLoaded',
  function () {

    initializePage();

  }
);


/* =====================================================
   INITIALIZE PAGE
   ===================================================== */

function initializePage() {

  const year =
    document.getElementById('year');

  if (year) {

    year.textContent =
      new Date().getFullYear();

  }


  loadSavedTheme();

  buildSubcategoryNav();

  buildTopicChips();

  setupEventListeners();

  loadNews(true);


  /*
   * Frontend automatically checks news.json
   * every 2 minutes.
   */
  setInterval(
    function () {

      loadNews(false);

    },
    AUTO_REFRESH_INTERVAL
  );


  /*
   * Refresh relative article times.
   */
  setInterval(
    function () {

      refreshVisibleTimes();

    },
    60 * 1000
  );

}


/* =====================================================
   EVENT LISTENERS
   ===================================================== */

function setupEventListeners() {

  const refreshButton =
    document.getElementById(
      'refreshButton'
    );

  if (refreshButton) {

    refreshButton.addEventListener(
      'click',
      manualRefresh
    );

  }


  const themeButton =
    document.getElementById(
      'themeButton'
    );

  if (themeButton) {

    themeButton.addEventListener(
      'click',
      toggleTheme
    );

  }


  const search =
    document.getElementById(
      'search'
    );

  if (search) {

    search.addEventListener(
      'input',
      function () {

        applyFilters();

      }
    );

  }


  document
    .querySelectorAll(
      '[data-main-category]'
    )
    .forEach(
      function (button) {

        button.addEventListener(
          'click',
          function () {

            selectMainCategory(
              button.dataset.mainCategory,
              button
            );

          }
        );

      }
    );

}


/* =====================================================
   LOAD NEWS
   ===================================================== */

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
        ? 'Loading latest stories...'
        : 'Checking for new stories...';

  }


  try {

    /*
     * Cache-busting is important on GitHub Pages.
     *
     * Without this, a browser/CDN may temporarily
     * return an older news.json.
     */
    const cacheBust =
      '?t=' +
      Date.now();


    const response =
      await fetch(
        NEWS_FILE + cacheBust,
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


    /*
     * Preserve IDs from the previous load.
     */
    const oldIds =
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


    /*
     * Remove duplicate articles.
     */
    allArticles =
      removeDuplicates(
        allArticles
      );


    /*
     * Sort newest first.
     */
    allArticles.sort(
      function (a, b) {

        return (
          getDateValue(
            b.published
          ) -
          getDateValue(
            a.published
          )
        );

      }
    );


    lastUpdatedAt =
      data.updatedAt ||
      new Date().toISOString();


    /*
     * Detect newly added stories.
     */
    let newCount = 0;


    if (!firstLoad) {

      newCount =
        allArticles.filter(
          function (article) {

            return !oldIds.has(
              article.id
            );

          }
        ).length;

    }


    previousArticleIds =
      new Set(
        allArticles.map(
          function (article) {

            return article.id;

          }
        )
      );


    firstLoad = false;


    /*
     * Render everything.
     */
    renderHero();

    buildTopicChips();

    applyFilters();

    renderTrending();

    updateStatus(
      newCount
    );


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


/* =====================================================
   NORMALIZE ARTICLES
   ===================================================== */

function normalizeArticles(
  articles
) {

  return articles
    .map(
      function (article, index) {

        const title =
          cleanText(
            article.title ||
            'Untitled story'
          );


        const description =
          cleanText(
            article.description ||
            'Read the latest story from the original publisher.'
          );


        const url =
          String(
            article.url ||
            article.link ||
            ''
          ).trim();


        const published =
          article.published ||
          article.pubDate ||
          new Date().toISOString();


        const category =
          cleanText(
            article.category ||
            'Technology'
          );


        const mainCategory =
          cleanText(
            article.mainCategory ||
            detectMainCategory(
              category
            )
          );


        const source =
          cleanText(
            article.source ||
            'TechPulse'
          );


        const image =
          String(
            article.image ||
            ''
          ).trim();


        const id =
          article.id ||
          createArticleId(
            title,
            url,
            published,
            index
          );


        return {

          id:
            String(id),

          title,

          description,

          url,

          image,

          category,

          mainCategory,

          source,

          published

        };

      }
    );

}


/* =====================================================
   REMOVE DUPLICATES
   ===================================================== */

function removeDuplicates(
  articles
) {

  const seenIds =
    new Set();

  const seenUrls =
    new Set();

  const seenTitles =
    new Set();


  return articles.filter(
    function (article) {

      const id =
        article.id;

      const url =
        normalizeUrl(
          article.url
        );

      const title =
        normalizeTitle(
          article.title
        );


      /*
       * Same ID.
       */
      if (
        seenIds.has(id)
      ) {

        return false;

      }


      /*
       * Same URL.
       */
      if (
        url &&
        seenUrls.has(url)
      ) {

        return false;

      }


      /*
       * Same normalized title.
       */
      if (
        title &&
        seenTitles.has(title)
      ) {

        return false;

      }


      seenIds.add(id);

      if (url) {
        seenUrls.add(url);
      }

      if (title) {
        seenTitles.add(title);
      }


      return true;

    }
  );

}


/* =====================================================
   CREATE ARTICLE ID
   ===================================================== */

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


/* =====================================================
   DETECT MAIN CATEGORY
   ===================================================== */

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
    'console',
    'pc gaming',
    'mobile gaming'

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


/* =====================================================
   MAIN CATEGORY
   ===================================================== */

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

  buildTopicChips();

  updateSectionTitle();

  applyFilters();

}


/* =====================================================
   SUBCATEGORY
   ===================================================== */

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


/* =====================================================
   BUILD SUBCATEGORY NAV
   ===================================================== */

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
      function (button) {

        button.addEventListener(
          'click',
          function () {

            selectSubcategory(
              button.dataset.subcategory,
              button
            );

          }
        );

      }
    );

}


/* =====================================================
   TOPIC CHIPS
   ===================================================== */

function buildTopicChips() {

  const container =
    document.getElementById(
      'topicChips'
    );


  if (!container) {

    return;

  }


  let categories;


  if (
    currentMainCategory ===
    'All'
  ) {

    categories = [

      'All Topics',

      'Artificial Intelligence',

      'Cybersecurity',

      'Cloud & Infrastructure',

      'Smartphones & Mobile',

      'Software & Applications',

      'Hardware & Devices',

      'PC Gaming',

      'Console Gaming',

      'Mobile Gaming',

      'Game Releases',

      'Gaming Hardware',

      'Esports'

    ];

  } else {

    categories =
      SUBCATEGORIES[
        currentMainCategory
      ] ||
      [];

  }


  container.innerHTML =
    categories
      .map(
        function (category) {

          const value =
            category === 'All Topics'
              ? 'All'
              : category;


          const active =
            currentSubcategory ===
            value;


          return `

            <button
              class="topic-chip ${active ? 'active' : ''}"
              data-topic="${escapeHtml(value)}"
            >
              ${escapeHtml(category)}
            </button>

          `;

        }
      )
      .join('');


  container
    .querySelectorAll(
      '[data-topic]'
    )
    .forEach(
      function (button) {

        button.addEventListener(
          'click',
          function () {

            currentSubcategory =
              button.dataset.topic;


            buildSubcategoryNav();

            buildTopicChips();

            updateSectionTitle();

            applyFilters();

          }
        );

      }
    );

}


/* =====================================================
   FILTER
   ===================================================== */

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


  updateArticleCount(
    filtered.length
  );

}


/* =====================================================
   RENDER NEWS
   ===================================================== */

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
          Try another category or search term.
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


/* =====================================================
   ARTICLE CARD
   ===================================================== */

function createArticleCard(
  article
) {

  const isNew =
    isRecentlyPublished(
      article.published
    );


  const placeholder =
    article.mainCategory ===
    'Gaming'
      ? '🎮'
      : '⚡';


  let imageHtml = `

    <div class="image-placeholder">

      <div class="placeholder-icon">
        ${placeholder}
      </div>

      <div class="placeholder-text">
        TechPulse
      </div>

    </div>

  `;


  if (
    isValidHttpUrl(
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

        <div class="placeholder-icon">
          ${placeholder}
        </div>

        <div class="placeholder-text">
          TechPulse
        </div>

      </div>

    `;

  }


  const safeUrl =
    isValidHttpUrl(
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


        <a
          class="read-link"
          href="${escapeHtml(safeUrl)}"
          target="_blank"
          rel="noopener noreferrer"
        >
          Read Story →
        </a>


        <div class="article-footer">

          <span class="article-source">

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


/* =====================================================
   HERO
   ===================================================== */

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

    const heroUrl =
      isValidHttpUrl(
        latest.url
      )
        ? latest.url
        : '';


    hero.innerHTML = `

      <div class="hero-content">

        <div class="hero-label">

          ${
            isRecentlyPublished(
              latest.published
            )
              ? 'Breaking / Fresh'
              : 'Latest Story'
          }

        </div>

        <div class="hero-title">

          ${escapeHtml(
            latest.title
          )}

        </div>

        <div class="hero-description">

          ${escapeHtml(
            latest.description
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

      </div>

      ${
        heroUrl
          ? `
            <a
              class="hero-link"
              href="${escapeHtml(heroUrl)}"
              target="_blank"
              rel="noopener noreferrer"
              aria-label="Read latest story"
            >
              Read story
            </a>
          `
          : ''
      }

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


/* =====================================================
   QUICK HERO CARD
   ===================================================== */

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


  const safeUrl =
    isValidHttpUrl(
      article.url
    )
      ? article.url
      : '';


  return `

    <div class="quick-card">

      <div class="quick-label">

        ${escapeHtml(label)}

      </div>

      <div class="quick-title">

        ${escapeHtml(
          article.title
        )}

      </div>

      <div class="quick-meta">

        ${escapeHtml(
          article.source
        )}

        •

        ${formatRelativeTime(
          article.published
        )}

      </div>

      ${
        safeUrl
          ? `
            <a
              href="${escapeHtml(safeUrl)}"
              target="_blank"
              rel="noopener noreferrer"
              style="position:absolute;inset:0;z-index:5;text-indent:-9999px;"
              aria-label="Read story"
            >
              Read story
            </a>
          `
          : ''
      }

    </div>

  `;

}


/* =====================================================
   TRENDING
   ===================================================== */

function renderTrending() {

  const container =
    document.getElementById(
      'trendingGrid'
    );


  if (!container) {

    return;

  }


  const trending =
    allArticles
      .slice()
      .sort(
        function (a, b) {

          const scoreA =
            getTrendingScore(
              a
            );

          const scoreB =
            getTrendingScore(
              b
            );

          return scoreB - scoreA;

        }
      )
      .slice(
        0,
        6
      );


  if (!trending.length) {

    container.innerHTML = '';

    return;

  }


  container.innerHTML =
    trending
      .map(
        function (
          article,
          index
        ) {

          return `

            <div class="trend-card">

              <div class="trend-number">

                ${index + 1}

              </div>

              <div>

                <div class="trend-title">

                  ${escapeHtml(
                    article.title
                  )}

                </div>

                <div class="trend-meta">

                  ${escapeHtml(
                    article.category
                  )}

                  •

                  ${formatRelativeTime(
                    article.published
                  )}

                </div>

              </div>

            </div>

          `;

        }
      )
      .join('');

}


/* =====================================================
   TRENDING SCORE
   ===================================================== */

function getTrendingScore(
  article
) {

  const published =
    getDateValue(
      article.published
    );


  if (!published) {

    return 0;

  }


  const ageHours =
    Math.max(
      0,
      (
        Date.now() -
        published
      ) /
      3600000
    );


  /*
   * Newer articles receive higher scores.
   */
  let score =
    Math.max(
      0,
      100 -
      (
        ageHours * 4
      )
    );


  /*
   * Slight preference for major categories.
   */
  if (
    article.mainCategory ===
    'Technology'
  ) {

    score += 3;

  }

  if (
    article.mainCategory ===
    'Gaming'
  ) {

    score += 3;

  }


  return score;

}


/* =====================================================
   SECTION TITLE
   ===================================================== */

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
      currentMainCategory === 'All'
        ? 'Fresh technology and gaming stories'
        : 'Fresh stories from this section';

  }

}


/* =====================================================
   ARTICLE COUNT
   ===================================================== */

function updateArticleCount(
  count
) {

  const element =
    document.getElementById(
      'articleCount'
    );


  if (!element) {

    return;

  }


  element.textContent =
    count +
    (
      count === 1
        ? ' article'
        : ' articles'
    );

}


/* =====================================================
   STATUS
   ===================================================== */

function updateStatus(
  newCount
) {

  const status =
    document.getElementById(
      'statusText'
    );


  const updated =
    document.getElementById(
      'lastUpdated'
    );


  if (status) {

    if (
      newCount > 0
    ) {

      status.textContent =
        newCount +
        (
          newCount === 1
            ? ' new story'
            : ' new stories'
        ) +
        ' detected';

    } else {

      status.textContent =
        'News feed is active';

    }

  }


  if (updated) {

    updated.textContent =
      'Updated ' +
      formatFullTime(
        lastUpdatedAt
      );

  }

}


/* =====================================================
   RELATIVE TIME
   ===================================================== */

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
      ) /
      1000
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


/* =====================================================
   FULL TIME
   ===================================================== */

function formatFullTime(
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


  return date.toLocaleString(
    undefined,
    {
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit'
    }
  );

}


/* =====================================================
   REFRESH VISIBLE TIMES
   ===================================================== */

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


  if (
    allArticles.length
  ) {

    renderHero();

    renderTrending();

  }

}


/* =====================================================
   MANUAL REFRESH
   ===================================================== */

async function manualRefresh() {

  const button =
    document.getElementById(
      'refreshButton'
    );


  if (button) {

    button.disabled = true;

    button.textContent =
      'Refreshing...';

  }


  try {

    await loadNews(true);

  } finally {

    if (button) {

      button.disabled = false;

      button.textContent =
        '↻ Refresh News';

    }

  }

}


/* =====================================================
   DARK MODE
   ===================================================== */

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


  updateThemeButton();

}


/* =====================================================
   LOAD THEME
   ===================================================== */

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

  }


  updateThemeButton();

}


/* =====================================================
   THEME BUTTON
   ===================================================== */

function updateThemeButton() {

  const button =
    document.getElementById(
      'themeButton'
    );


  if (!button) {

    return;

  }


  const dark =
    document.body.classList.contains(
      'dark'
    );


  button.textContent =
    dark
      ? '☀'
      : '☾';


  button.setAttribute(
    'aria-label',
    dark
      ? 'Switch to light mode'
      : 'Switch to dark mode'
  );

}


/* =====================================================
   ERROR
   ===================================================== */

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


  const updated =
    document.getElementById(
      'lastUpdated'
    );


  if (updated) {

    updated.textContent =
      'Retrying automatically...';

  }


  const container =
    document.getElementById(
      'newsContainer'
    );


  if (!container) {

    return;

  }


  /*
   * If old articles already exist, don't destroy
   * the working news page just because one refresh
   * temporarily failed.
   */
  if (
    allArticles.length
  ) {

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
        ${escapeHtml(
          message
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


/* =====================================================
   HELPERS
   ===================================================== */

function isValidHttpUrl(
  value
) {

  return /^https?:\/\//i.test(
    String(
      value || ''
    ).trim()
  );

}


function getDateValue(
  value
) {

  const time =
    new Date(
      value
    ).getTime();


  return isNaN(time)
    ? 0
    : time;

}


function isRecentlyPublished(
  value
) {

  const time =
    getDateValue(
      value
    );


  if (!time) {

    return false;

  }


  const age =
    Date.now() -
    time;


  return (
    age >= 0 &&
    age <=
    NEW_ARTICLE_WINDOW
  );

}


function normalizeUrl(
  value
) {

  try {

    const url =
      new URL(
        value
      );


    url.hash = '';


    return (
      url.href
        .replace(
          /\/$/,
          ''
        )
        .toLowerCase()
    );

  } catch (error) {

    return String(
      value || ''
    )
      .trim()
      .toLowerCase();

  }

}


function normalizeTitle(
  value
) {

  return String(
    value || ''
  )
    .toLowerCase()
    .replace(
      /[^a-z0-9\s]/g,
      ''
    )
    .replace(
      /\s+/g,
      ' '
    )
    .trim();

}


function cleanText(
  value
) {

  return String(
    value == null
      ? ''
      : value
  )
    .replace(
      /<[^>]*>/g,
      ' '
    )
    .replace(
      /\s+/g,
      ' '
    )
    .trim();

}


/* =====================================================
   ESCAPE HTML
   ===================================================== */

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
