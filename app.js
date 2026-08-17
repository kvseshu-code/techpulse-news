/************************************************************
 * TECHPULSE FRONTEND
 ************************************************************/


/*
 * ==========================================================
 * CONFIGURATION
 * ==========================================================
 */

const API_URL =
  'https://script.google.com/macros/s/AKfycbxcG1zxiqjZ8N1tYlF6kpLVbn597imA2n8W6Zruglk4QF6mbgXrUgTx2msHktYcL-TRwg/exec';


const REFRESH_INTERVAL =
  5 * 60 * 1000;


/*
 * ==========================================================
 * APPLICATION STATE
 * ==========================================================
 */

let allArticles = [];

let currentCategory = 'All';

let isLoading = false;


/*
 * ==========================================================
 * DOM ELEMENTS
 * ==========================================================
 */

const elements = {

  newsGrid:
    document.getElementById(
      'newsGrid'
    ),

  featuredStory:
    document.getElementById(
      'featuredStory'
    ),

  articleCount:
    document.getElementById(
      'articleCount'
    ),

  feedStatus:
    document.getElementById(
      'feedStatus'
    ),

  lastUpdated:
    document.getElementById(
      'lastUpdated'
    ),

  searchInput:
    document.getElementById(
      'searchInput'
    ),

  refreshButton:
    document.getElementById(
      'refreshButton'
    ),

  refreshIcon:
    document.getElementById(
      'refreshIcon'
    ),

  emptyState:
    document.getElementById(
      'emptyState'
    ),

  errorState:
    document.getElementById(
      'errorState'
    ),

  errorMessage:
    document.getElementById(
      'errorMessage'
    ),

  retryButton:
    document.getElementById(
      'retryButton'
    ),

  themeToggle:
    document.getElementById(
      'themeToggle'
    ),

  currentYear:
    document.getElementById(
      'currentYear'
    )

};


/*
 * ==========================================================
 * INITIALIZATION
 * ==========================================================
 */

document.addEventListener(
  'DOMContentLoaded',
  function() {

    initializeTheme();

    setupEventListeners();

    updateYear();

    loadNews();

    /*
     * Background refresh.
     */

    setInterval(
      loadNews,
      REFRESH_INTERVAL
    );

  }
);


/*
 * ==========================================================
 * EVENT LISTENERS
 * ==========================================================
 */

function setupEventListeners() {

  /*
   * Category navigation.
   */

  document
    .querySelectorAll(
      '[data-category]'
    )
    .forEach(
      function(button) {

        button.addEventListener(
          'click',
          function() {

            const category =
              button.dataset.category;

            setCategory(
              category
            );

          }
        );

      }
    );


  /*
   * Search.
   */

  elements.searchInput
    .addEventListener(
      'input',
      renderFilteredNews
    );


  /*
   * Refresh.
   */

  elements.refreshButton
    .addEventListener(
      'click',
      function() {

        loadNews(
          true
        );

      }
    );


  /*
   * Retry.
   */

  elements.retryButton
    .addEventListener(
      'click',
      function() {

        loadNews(
          true
        );

      }
    );


  /*
   * Theme.
   */

  elements.themeToggle
    .addEventListener(
      'click',
      toggleTheme
    );

}


/*
 * ==========================================================
 * LOAD NEWS
 * ==========================================================
 */

async function loadNews(
  manualRefresh = false
) {

  if (
    isLoading
  ) {

    return;

  }


  if (
    !API_URL ||
    API_URL.indexOf(
      'PASTE_YOUR'
    ) !== -1
  ) {

    showError(
      'Please add your Apps Script Web App URL to app.js.'
    );

    return;

  }


  isLoading = true;


  if (
    manualRefresh
  ) {

    setRefreshLoading(
      true
    );

  }


  setFeedStatus(
    'Updating...'
  );


  hideError();


  try {

    const response =
      await fetch(
        API_URL,
        {
          method: 'GET',

          cache: 'no-store',

          headers: {
            'Accept':
              'application/json'
          }
        }
      );


    if (
      !response.ok
    ) {

      throw new Error(
        'API returned HTTP ' +
        response.status
      );

    }


    const data =
      await response.json();


    if (
      !data.success
    ) {

      throw new Error(
        data.error ||
        'News API returned an error.'
      );

    }


    if (
      !Array.isArray(
        data.articles
      )
    ) {

      throw new Error(
        'Invalid news data received.'
      );

    }


    allArticles =
      normalizeArticles(
        data.articles
      );


    setFeedStatus(
      'Live'
    );


    setLastUpdated(
      data.updated_at
    );


    renderFilteredNews();

    updateCategoryCounts();


  } catch (error) {

    console.error(
      'TechPulse API error:',
      error
    );


    setFeedStatus(
      'Offline'
    );


    showError(
      error.message ||
      'Unable to load the latest news.'
    );


  } finally {

    isLoading = false;


    if (
      manualRefresh
    ) {

      setRefreshLoading(
        false
      );

    }

  }

}


/*
 * ==========================================================
 * NORMALIZE ARTICLES
 * ==========================================================
 */

function normalizeArticles(
  articles
) {

  return articles

    .filter(
      function(article) {

        return (
          article &&
          article.title &&
          article.article_url
        );

      }
    )

    .map(
      function(article) {

        return {

          id:
            article.id || '',

          title:
            String(
              article.title
            ),

          summary:
            String(
              article.summary || ''
            ),

          category:
            article.category ||
            'Technology',

          source:
            article.source ||
            'News Source',

          published_at:
            article.published_at,

          article_url:
            article.article_url,

          image_url:
            article.image_url ||
            '',

          language:
            article.language ||
            'en',

          collected_at:
            article.collected_at,

          status:
            article.status ||
            'active'

        };

      }
    )

    .sort(
      function(a, b) {

        return (
          new Date(
            b.published_at
          ) -
          new Date(
            a.published_at
          )
        );

      }
    );

}


/*
 * ==========================================================
 * FILTER + RENDER
 * ==========================================================
 */

function renderFilteredNews() {

  const search =
    elements.searchInput
      .value
      .trim()
      .toLowerCase();


  let filtered =
    allArticles.filter(
      function(article) {

        const categoryMatch =
          currentCategory ===
          'All' ||
          article.category ===
          currentCategory;


        if (
          !categoryMatch
        ) {

          return false;

        }


        if (!search) {

          return true;

        }


        const searchable = (

          article.title +
          ' ' +
          article.summary +
          ' ' +
          article.source +
          ' ' +
          article.category

        ).toLowerCase();


        return searchable
          .includes(
            search
          );

      }
    );


  updateArticleCount(
    filtered.length
  );


  if (
    filtered.length === 0
  ) {

    elements.featuredStory
      .innerHTML = '';

    elements.newsGrid
      .innerHTML = '';

    elements.emptyState
      .classList.remove(
        'hidden'
      );

    return;

  }


  elements.emptyState
    .classList.add(
      'hidden'
    );


  renderFeatured(
    filtered[0]
  );


  renderNewsGrid(
    filtered.slice(1)
  );

}


/*
 * ==========================================================
 * FEATURED ARTICLE
 * ==========================================================
 */

function renderFeatured(
  article
) {

  const image =
    getImage(
      article
    );


  elements.featuredStory
    .innerHTML = `

      <article class="featured-card">

        <div class="featured-image">

          <img
            src="${escapeAttribute(image)}"
            alt=""
            loading="eager"
            onerror="this.src='${escapeAttribute(
              createPlaceholder()
            )}'"
          >

        </div>


        <div class="featured-content">

          <div class="article-meta">

            <span class="category-badge">
              ${escapeHTML(
                article.category
              )}
            </span>

            <span>
              ${escapeHTML(
                article.source
              )}
            </span>

            <span>
              ${formatRelativeTime(
                article.published_at
              )}
            </span>

          </div>


          <h3>
            ${escapeHTML(
              article.title
            )}
          </h3>


          <p>
            ${escapeHTML(
              article.summary ||
              'Read the latest story from the original publisher.'
            )}
          </p>


          <a
            class="read-link"
            href="${escapeAttribute(
              article.article_url
            )}"
            target="_blank"
            rel="noopener noreferrer"
          >
            Read Full Story →
          </a>

        </div>

      </article>

  `;

}


/*
 * ==========================================================
 * NEWS GRID
 * ==========================================================
 */

function renderNewsGrid(
  articles
) {

  if (
    articles.length === 0
  ) {

    elements.newsGrid
      .innerHTML = '';

    return;

  }


  elements.newsGrid
    .innerHTML =
      articles
        .map(
          createArticleCard
        )
        .join('');

}


/*
 * ==========================================================
 * ARTICLE CARD
 * ==========================================================
 */

function createArticleCard(
  article
) {

  const image =
    getImage(
      article
    );


  return `

    <article class="news-card">

      <div class="card-image">

        <img
          src="${escapeAttribute(
            image
          )}"
          alt=""
          loading="lazy"
          onerror="this.src='${escapeAttribute(
            createPlaceholder()
          )}'"
        >

      </div>


      <div class="card-content">

        <div class="article-meta">

          <span class="category-badge">
            ${escapeHTML(
              article.category
            )}
          </span>

          <span>
            ${formatRelativeTime(
              article.published_at
            )}
          </span>

        </div>


        <h3 class="card-title">

          ${escapeHTML(
            article.title
          )}

        </h3>


        <p class="card-summary">

          ${escapeHTML(
            article.summary ||
            'Read the full story from the original publisher.'
          )}

        </p>


        <div class="card-footer">

          <span class="source-name">

            ${escapeHTML(
              article.source
            )}

          </span>


          <a
            class="card-link"
            href="${escapeAttribute(
              article.article_url
            )}"
            target="_blank"
            rel="noopener noreferrer"
          >
            Read →
          </a>

        </div>

      </div>

    </article>

  `;

}


/*
 * ==========================================================
 * CATEGORY
 * ==========================================================
 */

function setCategory(
  category
) {

  currentCategory =
    category;


  document
    .querySelectorAll(
      '.nav-link'
    )
    .forEach(
      function(button) {

        button.classList.toggle(
          'active',
          button.dataset.category ===
          category
        );

      }
    );


  renderFilteredNews();

}


/*
 * ==========================================================
 * CATEGORY COUNTS
 * ==========================================================
 */

function updateCategoryCounts() {

  const categories = [
    'Technology',
    'AI',
    'Cybersecurity',
    'Gaming',
    'Space'
  ];


  categories.forEach(
    function(category) {

      const count =
        allArticles.filter(
          function(article) {

            return (
              article.category ===
              category
            );

          }
        ).length;


      const element =
        document.getElementById(
          'count' +
          category
        );


      if (element) {

        element.textContent =
          count;

      }

    }
  );

}


/*
 * ==========================================================
 * ARTICLE COUNT
 * ==========================================================
 */

function updateArticleCount(
  count
) {

  elements.articleCount
    .textContent =
      count +
      (
        count === 1
          ? ' story'
          : ' stories'
      );

}


/*
 * ==========================================================
 * IMAGE
 * ==========================================================
 */

function getImage(
  article
) {

  if (
    article.image_url
  ) {

    return article.image_url;

  }


  return createPlaceholder();

}


/*
 * ==========================================================
 * PLACEHOLDER IMAGE
 * ==========================================================
 */

function createPlaceholder() {

  return (
    'data:image/svg+xml;charset=UTF-8,' +
    encodeURIComponent(`

      <svg
        xmlns="http://www.w3.org/2000/svg"
        width="800"
        height="450"
        viewBox="0 0 800 450"
      >

        <rect
          width="800"
          height="450"
          fill="#eef0f5"
        />

        <text
          x="400"
          y="225"
          text-anchor="middle"
          dominant-baseline="middle"
          fill="#8b95a7"
          font-family="Arial"
          font-size="28"
          font-weight="700"
        >
          TECHPULSE
        </text>

      </svg>

    `)
  );

}


/*
 * ==========================================================
 * RELATIVE TIME
 * ==========================================================
 */

function formatRelativeTime(
  dateValue
) {

  if (!dateValue) {

    return 'Recently';

  }


  const date =
    new Date(
      dateValue
    );


  if (
    isNaN(
      date.getTime()
    )
  ) {

    return 'Recently';

  }


  const now =
    new Date();


  const difference =
    now.getTime() -
    date.getTime();


  const minutes =
    Math.floor(
      difference /
      60000
    );


  if (
    minutes < 1
  ) {

    return 'Just now';

  }


  if (
    minutes < 60
  ) {

    return (
      minutes +
      (
        minutes === 1
          ? ' min ago'
          : ' mins ago'
      )
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
      (
        hours === 1
          ? ' hour ago'
          : ' hours ago'
      )
    );

  }


  const days =
    Math.floor(
      hours / 24
    );


  if (
    days < 7
  ) {

    return (
      days +
      (
        days === 1
          ? ' day ago'
          : ' days ago'
      )
    );

  }


  return date.toLocaleDateString(
    undefined,
    {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    }
  );

}


/*
 * ==========================================================
 * API UPDATED TIME
 * ==========================================================
 */

function setLastUpdated(
  timestamp
) {

  if (!timestamp) {

    elements.lastUpdated
      .textContent =
        'Latest feed available';

    return;

  }


  const date =
    new Date(
      timestamp
    );


  if (
    isNaN(
      date.getTime()
    )
  ) {

    elements.lastUpdated
      .textContent =
        'Latest feed available';

    return;

  }


  elements.lastUpdated
    .textContent =
      'Updated ' +
      date.toLocaleTimeString(
        undefined,
        {
          hour: 'numeric',
          minute: '2-digit'
        }
      );

}


/*
 * ==========================================================
 * FEED STATUS
 * ==========================================================
 */

function setFeedStatus(
  status
) {

  elements.feedStatus
    .textContent =
      status;

}


/*
 * ==========================================================
 * REFRESH BUTTON
 * ==========================================================
 */

function setRefreshLoading(
  loading
) {

  elements.refreshButton
    .classList.toggle(
      'loading',
      loading
    );


  elements.refreshIcon
    .textContent =
      loading
        ? '⟳'
        : '↻';

}


/*
 * ==========================================================
 * ERROR
 * ==========================================================
 */

function showError(
  message
) {

  elements.errorMessage
    .textContent =
      message;


  elements.errorState
    .classList.remove(
      'hidden'
    );

}


function hideError() {

  elements.errorState
    .classList.add(
      'hidden'
    );

}


/*
 * ==========================================================
 * THEME
 * ==========================================================
 */

function initializeTheme() {

  const saved =
    localStorage.getItem(
      'techpulse-theme'
    );


  if (
    saved === 'dark'
  ) {

    document.body
      .classList.add(
        'dark'
      );

    elements.themeToggle
      .textContent =
        '☀';

  }

}


function toggleTheme() {

  const dark =
    document.body
      .classList.toggle(
        'dark'
      );


  localStorage.setItem(
    'techpulse-theme',
    dark
      ? 'dark'
      : 'light'
  );


  elements.themeToggle
    .textContent =
      dark
        ? '☀'
        : '☾';

}


/*
 * ==========================================================
 * YEAR
 * ==========================================================
 */

function updateYear() {

  elements.currentYear
    .textContent =
      new Date()
        .getFullYear();

}


/*
 * ==========================================================
 * HTML SAFETY
 * ==========================================================
 */

function escapeHTML(
  value
) {

  return String(
    value || ''
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


/*
 * ==========================================================
 * ATTRIBUTE SAFETY
 * ==========================================================
 */

function escapeAttribute(
  value
) {

  return escapeHTML(
    value
  );

}
