/* =========================================================
   TECHPULSE NEXUS
   FRONTEND ENGINE
   ========================================================= */


/* =========================================================
   CONFIGURATION
   ========================================================= */

const API_URL =
  'https://script.google.com/macros/s/AKfycbxcG1zxiqjZ8N1tYlF6kpLVbn597imA2n8W6Zruglk4QF6mbgXrUgTx2msHktYcL-TRwg/exec';


const REFRESH_INTERVAL =
  5 * 60 * 1000;


/* =========================================================
   APPLICATION STATE
   ========================================================= */

let allArticles = [];

let currentCategory = 'All';

let currentLanguage =
  localStorage.getItem(
    'techpulse-language'
  ) || 'en';

let isLoading = false;

let speaking = false;

let currentSpeech = null;


/* =========================================================
   DOM
   ========================================================= */

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

  heroStoryCount:
    document.getElementById(
      'heroStoryCount'
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

  heroRefresh:
    document.getElementById(
      'heroRefresh'
    ),

  heroAudio:
    document.getElementById(
      'heroAudio'
    ),

  audioButton:
    document.getElementById(
      'audioButton'
    ),

  audioPlayer:
    document.getElementById(
      'audioPlayer'
    ),

  audioTitle:
    document.getElementById(
      'audioTitle'
    ),

  audioStop:
    document.getElementById(
      'audioStop'
    ),

  voiceSpeed:
    document.getElementById(
      'voiceSpeed'
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

  languageSelect:
    document.getElementById(
      'languageSelect'
    ),

  mobileMenuButton:
    document.getElementById(
      'mobileMenuButton'
    ),

  mobileNav:
    document.getElementById(
      'mobileNav'
    ),

  currentYear:
    document.getElementById(
      'currentYear'
    )

};


/* =========================================================
   TRANSLATIONS
   ========================================================= */

const translations = {

  en: {

    nav_all:
      'All',

    nav_technology:
      'Technology',

    nav_ai:
      'AI',

    nav_security:
      'Cybersecurity',

    nav_gaming:
      'Gaming',

    nav_space:
      'Space',

    live_signal:
      'LIVE INTELLIGENCE',

    hero_description:
      'Technology, AI, cybersecurity, gaming and space intelligence — continuously gathered and refreshed from trusted publishers.',

    refresh_feed:
      'Refresh feed',

    listen:
      'Listen',

    network_status:
      'NETWORK STATUS',

    feed:
      'FEED',

    stories:
      'STORIES',

    updated:
      'UPDATED',

    narrate:
      'Narrate',

    refresh:
      'Refresh',

    search_placeholder:
      'Search the intelligence feed...',

    latest_intelligence:
      'Latest intelligence',

    latest_description:
      'The newest stories entering the TechPulse feed.',

    no_results:
      'No intelligence found',

    no_results_description:
      'Try another category or search term.',

    feed_error:
      'Feed connection interrupted',

    explore_domains:
      'Explore domains',

    footer_description:
      'Technology intelligence, simplified.',

    footer_note:
      'TechPulse provides news discovery and summaries. Full stories remain with their respective publishers.'

  },


  hi: {

    nav_all:
      'सभी',

    nav_technology:
      'टेक्नोलॉजी',

    nav_ai:
      'AI',

    nav_security:
      'साइबर सुरक्षा',

    nav_gaming:
      'गेमिंग',

    nav_space:
      'अंतरिक्ष',

    live_signal:
      'लाइव इंटेलिजेंस',

    hero_description:
      'टेक्नोलॉजी, AI, साइबर सुरक्षा, गेमिंग और अंतरिक्ष की खबरें — विश्वसनीय प्रकाशकों से लगातार एकत्र और अपडेट की जाती हैं।',

    refresh_feed:
      'फीड अपडेट करें',

    listen:
      'सुनें',

    network_status:
      'नेटवर्क स्थिति',

    feed:
      'फीड',

    stories:
      'समाचार',

    updated:
      'अपडेट',

    narrate:
      'सुनाएं',

    refresh:
      'रीफ्रेश',

    search_placeholder:
      'टेक्नोलॉजी समाचार खोजें...',

    latest_intelligence:
      'नवीनतम जानकारी',

    latest_description:
      'TechPulse फीड में आने वाली नवीनतम खबरें।',

    no_results:
      'कोई परिणाम नहीं मिला',

    no_results_description:
      'दूसरी श्रेणी या खोज शब्द आज़माएं।',

    feed_error:
      'फीड कनेक्शन बाधित है',

    explore_domains:
      'क्षेत्र खोजें',

    footer_description:
      'टेक्नोलॉजी जानकारी, सरल रूप में।',

    footer_note:
      'TechPulse समाचार खोज और सारांश प्रदान करता है। पूरी खबरें संबंधित प्रकाशकों की हैं।'

  },


  te: {

    nav_all:
      'అన్నీ',

    nav_technology:
      'టెక్నాలజీ',

    nav_ai:
      'AI',

    nav_security:
      'సైబర్ సెక్యూరిటీ',

    nav_gaming:
      'గేమింగ్',

    nav_space:
      'అంతరిక్షం',

    live_signal:
      'లైవ్ ఇంటెలిజెన్స్',

    hero_description:
      'టెక్నాలజీ, AI, సైబర్ సెక్యూరిటీ, గేమింగ్ మరియు అంతరిక్ష వార్తలు — విశ్వసనీయ ప్రచురణకర్తల నుండి నిరంతరం సేకరించబడతాయి మరియు నవీకరించబడతాయి.',

    refresh_feed:
      'ఫీడ్ రిఫ్రెష్',

    listen:
      'వినండి',

    network_status:
      'నెట్‌వర్క్ స్థితి',

    feed:
      'ఫీడ్',

    stories:
      'వార్తలు',

    updated:
      'నవీకరణ',

    narrate:
      'వినిపించు',

    refresh:
      'రిఫ్రెష్',

    search_placeholder:
      'టెక్నాలజీ వార్తలను వెతకండి...',

    latest_intelligence:
      'తాజా సమాచారం',

    latest_description:
      'TechPulse ఫీడ్‌లోకి వచ్చిన తాజా వార్తలు.',

    no_results:
      'వార్తలు కనుగొనబడలేదు',

    no_results_description:
      'మరొక కేటగిరీ లేదా సెర్చ్ పదాన్ని ప్రయత్నించండి.',

    feed_error:
      'ఫీడ్ కనెక్షన్ అంతరాయం',

    explore_domains:
      'విభాగాలను అన్వేషించండి',

    footer_description:
      'టెక్నాలజీ సమాచారం, సులభంగా.',

    footer_note:
      'TechPulse వార్తల శోధన మరియు సారాంశాలను అందిస్తుంది. పూర్తి కథనాలు సంబంధిత ప్రచురణకర్తలకు చెందినవి.'

  }

};


/* =========================================================
   INITIALIZATION
   ========================================================= */

document.addEventListener(
  'DOMContentLoaded',
  function() {

    initializeTheme();

    initializeLanguage();

    setupEventListeners();

    updateYear();

    loadNews();

    setInterval(
      function() {

        loadNews();

      },
      REFRESH_INTERVAL
    );

  }
);


/* =========================================================
   EVENT LISTENERS
   ========================================================= */

function setupEventListeners() {


  document
    .querySelectorAll(
      '[data-category]'
    )
    .forEach(
      function(button) {

        button.addEventListener(
          'click',
          function() {

            setCategory(
              button.dataset.category
            );

            closeMobileMenu();

          }
        );

      }
    );


  elements.searchInput
    .addEventListener(
      'input',
      renderFilteredNews
    );


  elements.refreshButton
    .addEventListener(
      'click',
      function() {

        loadNews(true);

      }
    );


  elements.heroRefresh
    .addEventListener(
      'click',
      function() {

        loadNews(true);

      }
    );


  elements.retryButton
    .addEventListener(
      'click',
      function() {

        loadNews(true);

      }
    );


  elements.themeToggle
    .addEventListener(
      'click',
      toggleTheme
    );


  elements.languageSelect
    .addEventListener(
      'change',
      function() {

        changeLanguage(
          this.value
        );

      }
    );


  elements.audioButton
    .addEventListener(
      'click',
      function() {

        narrateFeatured();

      }
    );


  elements.heroAudio
    .addEventListener(
      'click',
      function() {

        narrateFeatured();

      }
    );


  elements.audioStop
    .addEventListener(
      'click',
      stopNarration
    );


  elements.mobileMenuButton
    .addEventListener(
      'click',
      toggleMobileMenu
    );


  document.addEventListener(
    'keydown',
    function(event) {

      if (
        event.key === '/' &&
        document.activeElement !==
        elements.searchInput
      ) {

        event.preventDefault();

        elements.searchInput.focus();

      }

    }
  );

}


/* =========================================================
   LOAD NEWS
   ========================================================= */

async function loadNews(
  manualRefresh = false
) {

  if (isLoading) {
    return;
  }


  isLoading = true;


  setFeedStatus(
    'UPDATING'
  );


  if (manualRefresh) {

    setRefreshLoading(true);

  }


  hideError();


  try {

    const response =
      await fetch(
        API_URL +
        (
          API_URL.includes('?')
            ? '&'
            : '?'
        ) +
        '_=' +
        Date.now(),
        {
          method: 'GET',
          cache: 'no-store'
        }
      );


    if (!response.ok) {

      throw new Error(
        'HTTP ' +
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
        'API returned an error.'
      );

    }


    if (
      !Array.isArray(
        data.articles
      )
    ) {

      throw new Error(
        'Invalid article data.'
      );

    }


    allArticles =
      normalizeArticles(
        data.articles
      );


    setFeedStatus(
      'ONLINE'
    );


    setLastUpdated(
      data.updated_at
    );


    updateHeroStoryCount();

    updateCategoryCounts();

    renderFilteredNews();


  } catch (error) {

    console.error(
      'TechPulse feed error:',
      error
    );


    setFeedStatus(
      'OFFLINE'
    );


    showError(
      error.message ||
      'Unable to connect to the TechPulse feed.'
    );


  } finally {

    isLoading = false;


    if (manualRefresh) {

      setRefreshLoading(false);

    }

  }

}


/* =========================================================
   NORMALIZE
   ========================================================= */

function normalizeArticles(
  articles
) {

  return articles

    .filter(
      function(article) {

        return (
          article &&
          article.title &&
          article.article_url &&
          (
            article.status ===
            'active' ||
            !article.status
          )
        );

      }
    )

    .map(
      function(article) {

        return {

          id:
            String(
              article.id || ''
            ),

          title:
            String(
              article.title || ''
            ),

          summary:
            String(
              article.summary || ''
            ),

          category:
            normalizeCategory(
              article.category
            ),

          source:
            String(
              article.source ||
              'News Source'
            ),

          published_at:
            article.published_at,

          article_url:
            String(
              article.article_url
            ),

          image_url:
            String(
              article.image_url || ''
            ),

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
      function(a,b) {

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


/* =========================================================
   CATEGORY NORMALIZATION
   ========================================================= */

function normalizeCategory(
  category
) {

  const value =
    String(
      category || ''
    ).trim();


  const map = {

    technology:
      'Technology',

    tech:
      'Technology',

    ai:
      'AI',

    'artificial intelligence':
      'AI',

    cybersecurity:
      'Cybersecurity',

    'cyber security':
      'Cybersecurity',

    gaming:
      'Gaming',

    games:
      'Gaming',

    space:
      'Space'

  };


  return (
    map[
      value.toLowerCase()
    ] ||
    value ||
    'Technology'
  );

}


/* =========================================================
   FILTER
   ========================================================= */

function getFilteredArticles() {

  const search =
    elements.searchInput
      .value
      .trim()
      .toLowerCase();


  return allArticles.filter(
    function(article) {

      const categoryMatch =
        currentCategory === 'All' ||
        article.category ===
        currentCategory;


      if (!categoryMatch) {
        return false;
      }


      if (!search) {
        return true;
      }


      const searchable =
        (
          article.title +
          ' ' +
          article.summary +
          ' ' +
          article.source +
          ' ' +
          article.category
        ).toLowerCase();


      return searchable.includes(
        search
      );

    }
  );

}


/* =========================================================
   RENDER
   ========================================================= */

function renderFilteredNews() {

  const filtered =
    getFilteredArticles();


  updateArticleCount(
    filtered.length
  );


  if (
    filtered.length === 0
  ) {

    elements.featuredStory.innerHTML =
      '';

    elements.newsGrid.innerHTML =
      '';

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


/* =========================================================
   FEATURED
   ========================================================= */

function renderFeatured(
  article
) {

  const image =
    getImage(
      article
    );


  elements.featuredStory.innerHTML = `

    <article
      class="featured-card"
      data-article-id="${escapeAttribute(article.id)}"
    >

      <div class="featured-image">

        <img
          src="${escapeAttribute(image)}"
          alt=""
          loading="eager"
          onerror="this.src='${escapeAttribute(createPlaceholder())}'"
        >

      </div>


      <div class="featured-content">

        <div class="featured-kicker">
          FEATURED SIGNAL
        </div>


        <div class="article-meta">

          <span class="category-badge">
            ${escapeHTML(article.category)}
          </span>

          <span>
            ${escapeHTML(article.source)}
          </span>

          <span>
            ${formatRelativeTime(article.published_at)}
          </span>

        </div>


        <h3>
          ${escapeHTML(article.title)}
        </h3>


        <p>
          ${escapeHTML(
            article.summary ||
            'Read the latest story from the original publisher.'
          )}
        </p>


        <div class="featured-actions">

          <a
            class="read-link"
            href="${escapeAttribute(article.article_url)}"
            target="_blank"
            rel="noopener noreferrer"
          >
            Read story →
          </a>


          <button
            class="listen-link"
            type="button"
            data-narrate-id="${escapeAttribute(article.id)}"
          >
            🔊 Listen
          </button>

        </div>

      </div>

    </article>

  `;


  const listenButton =
    elements.featuredStory
      .querySelector(
        '[data-narrate-id]'
      );


  if (listenButton) {

    listenButton.addEventListener(
      'click',
      function() {

        narrateArticle(
          article
        );

      }
    );

  }

}


/* =========================================================
   GRID
   ========================================================= */

function renderNewsGrid(
  articles
) {

  elements.newsGrid.innerHTML =
    articles
      .map(
        createArticleCard
      )
      .join('');


  elements.newsGrid
    .querySelectorAll(
      '[data-narrate-id]'
    )
    .forEach(
      function(button) {

        button.addEventListener(
          'click',
          function() {

            const article =
              allArticles.find(
                function(item) {

                  return (
                    item.id ===
                    button.dataset.narrateId
                  );

                }
              );


            if (article) {

              narrateArticle(
                article
              );

            }

          }
        );

      }
    );

}


/* =========================================================
   ARTICLE CARD
   ========================================================= */

function createArticleCard(
  article,
  index
) {

  const image =
    getImage(
      article
    );


  return `

    <article
      class="news-card"
      style="animation-delay:${Math.min(index * 35, 350)}ms"
    >

      <div class="card-image">

        <img
          src="${escapeAttribute(image)}"
          alt=""
          loading="lazy"
          onerror="this.src='${escapeAttribute(createPlaceholder())}'"
        >

      </div>


      <div class="card-content">

        <div class="article-meta">

          <span class="category-badge">
            ${escapeHTML(article.category)}
          </span>

          <span>
            ${formatRelativeTime(article.published_at)}
          </span>

        </div>


        <h3 class="card-title">

          ${escapeHTML(article.title)}

        </h3>


        <p class="card-summary">

          ${escapeHTML(
            article.summary ||
            'Read the full story from the original publisher.'
          )}

        </p>


        <div class="card-footer">

          <span class="source-name">

            ${escapeHTML(article.source)}

          </span>


          <div class="card-actions">

            <button
              class="card-listen"
              type="button"
              data-narrate-id="${escapeAttribute(article.id)}"
            >
              🔊
            </button>


            <a
              class="card-link"
              href="${escapeAttribute(article.article_url)}"
              target="_blank"
              rel="noopener noreferrer"
            >
              Read →
            </a>

          </div>

        </div>

      </div>

    </article>

  `;

}


/* =========================================================
   CATEGORY
   ========================================================= */

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


/* =========================================================
   COUNTS
   ========================================================= */

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
          'count' + category
        );


      if (element) {

        element.textContent =
          count;

      }

    }
  );

}


/* =========================================================
   COUNTERS
   ========================================================= */

function updateArticleCount(
  count
) {

  elements.articleCount
    .textContent =
      count +
      (
        count === 1
          ? ' STORY'
          : ' STORIES'
      );

}


function updateHeroStoryCount() {

  elements.heroStoryCount
    .textContent =
      allArticles.length;

}


/* =========================================================
   IMAGE
   ========================================================= */

function getImage(
  article
) {

  if (
    article.image_url &&
    isSafeImageURL(
      article.image_url
    )
  ) {

    return article.image_url;

  }


  return createPlaceholder();

}


function isSafeImageURL(
  value
) {

  try {

    const url =
      new URL(
        value,
        window.location.href
      );


    return (
      url.protocol ===
      'https:' ||
      url.protocol ===
      'http:'
    );

  } catch {

    return false;

  }

}


/* =========================================================
   PLACEHOLDER
   ========================================================= */

function createPlaceholder() {

  return (
    'data:image/svg+xml;charset=UTF-8,' +
    encodeURIComponent(`

      <svg
        xmlns="http://www.w3.org/2000/svg"
        width="1000"
        height="600"
      >

        <defs>

          <linearGradient
            id="g"
            x1="0"
            x2="1"
          >

            <stop
              offset="0"
              stop-color="#0b1724"
            />

            <stop
              offset=".5"
              stop-color="#15102d"
            />

            <stop
              offset="1"
              stop-color="#210d20"
            />

          </linearGradient>

        </defs>


        <rect
          width="1000"
          height="600"
          fill="url(#g)"
        />


        <circle
          cx="500"
          cy="300"
          r="120"
          fill="none"
          stroke="#29d9ff"
          stroke-opacity=".3"
        />


        <circle
          cx="500"
          cy="300"
          r="55"
          fill="#29d9ff"
          fill-opacity=".8"
        />


        <text
          x="500"
          y="450"
          text-anchor="middle"
          fill="#ffffff"
          font-family="Arial"
          font-size="34"
          font-weight="800"
        >
          TECHPULSE
        </text>

      </svg>

    `)
  );

}


/* =========================================================
   TIME
   ========================================================= */

function formatRelativeTime(
  value
) {

  if (!value) {
    return 'Recently';
  }


  const date =
    new Date(value);


  if (
    isNaN(
      date.getTime()
    )
  ) {

    return 'Recently';

  }


  const diff =
    Date.now() -
    date.getTime();


  if (diff < 0) {

    return 'Just now';

  }


  const minutes =
    Math.floor(
      diff / 60000
    );


  if (minutes < 1) {
    return 'Just now';
  }


  if (minutes < 60) {

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


  if (hours < 24) {

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


  if (days < 7) {

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
      month: 'short',
      day: 'numeric',
      year: 'numeric'
    }
  );

}


/* =========================================================
   UPDATED
   ========================================================= */

function setLastUpdated(
  timestamp
) {

  if (!timestamp) {

    elements.lastUpdated
      .textContent =
      'AVAILABLE';

    return;

  }


  const date =
    new Date(timestamp);


  if (
    isNaN(
      date.getTime()
    )
  ) {

    elements.lastUpdated
      .textContent =
      'AVAILABLE';

    return;

  }


  elements.lastUpdated
    .textContent =
    date.toLocaleTimeString(
      undefined,
      {
        hour: '2-digit',
        minute: '2-digit'
      }
    );

}


/* =========================================================
   FEED STATUS
   ========================================================= */

function setFeedStatus(
  status
) {

  elements.feedStatus
    .textContent =
    status;

}


/* =========================================================
   REFRESH
   ========================================================= */

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


/* =========================================================
   ERROR
   ========================================================= */

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


/* =========================================================
   THEME
   ========================================================= */

function initializeTheme() {

  const saved =
    localStorage.getItem(
      'techpulse-theme'
    );


  if (
    saved === 'light'
  ) {

    document.body
      .classList.add(
        'light'
      );

    elements.themeToggle
      .textContent =
      '☀';

  } else {

    elements.themeToggle
      .textContent =
      '☾';

  }

}


function toggleTheme() {

  const light =
    document.body
      .classList.toggle(
        'light'
      );


  localStorage.setItem(
    'techpulse-theme',
    light
      ? 'light'
      : 'dark'
  );


  elements.themeToggle
    .textContent =
    light
      ? '☀'
      : '☾';

}


/* =========================================================
   LANGUAGE
   ========================================================= */

function initializeLanguage() {

  elements.languageSelect.value =
    currentLanguage;


  applyTranslations();

}


function changeLanguage(
  language
) {

  if (
    !translations[language]
  ) {

    language = 'en';

  }


  currentLanguage =
    language;


  localStorage.setItem(
    'techpulse-language',
    language
  );


  applyTranslations();

}


function applyTranslations() {

  const dictionary =
    translations[currentLanguage] ||
    translations.en;


  document
    .querySelectorAll(
      '[data-i18n]'
    )
    .forEach(
      function(element) {

        const key =
          element.dataset.i18n;


        if (
          dictionary[key]
        ) {

          element.textContent =
            dictionary[key];

        }

      }
    );


  document
    .querySelectorAll(
      '[data-i18n-placeholder]'
    )
    .forEach(
      function(element) {

        const key =
          element.dataset.i18nPlaceholder;


        if (
          dictionary[key]
        ) {

          element.placeholder =
            dictionary[key];

        }

      }
    );

}


/* =========================================================
   AUDIO / SPEECH SYNTHESIS
   ========================================================= */

function narrateFeatured() {

  const filtered =
    getFilteredArticles();


  if (
    filtered.length === 0
  ) {

    return;

  }


  narrateArticle(
    filtered[0]
  );

}


function narrateArticle(
  article
) {

  if (
    !('speechSynthesis' in window)
  ) {

    alert(
      'Audio narration is not supported by this browser.'
    );

    return;

  }


  if (
    speaking
  ) {

    stopNarration();

    return;

  }


  const title =
    article.title;


  const summary =
    article.summary ||
    'Read the complete story from the original publisher.';


  const source =
    article.source;


  const text =
    title +
    '. ' +
    summary +
    '. Source: ' +
    source;


  currentSpeech =
    new SpeechSynthesisUtterance(
      text
    );


  currentSpeech.rate =
    parseFloat(
      elements.voiceSpeed.value
    );


  currentSpeech.pitch =
    1;


  currentSpeech.volume =
    1;


  currentSpeech.lang =
    getSpeechLanguage();


  currentSpeech.onstart =
    function() {

      speaking = true;

      showAudioPlayer(
        article.title
      );

    };


  currentSpeech.onend =
    function() {

      speaking = false;

      hideAudioPlayer();

    };


  currentSpeech.onerror =
    function() {

      speaking = false;

      hideAudioPlayer();

    };


  window.speechSynthesis.cancel();


  window.speechSynthesis.speak(
    currentSpeech
  );

}


function getSpeechLanguage() {

  const map = {

    en:
      'en-US',

    hi:
      'hi-IN',

    te:
      'te-IN'

  };


  return (
    map[currentLanguage] ||
    'en-US'
  );

}


function stopNarration() {

  if (
    'speechSynthesis' in window
  ) {

    window.speechSynthesis.cancel();

  }


  speaking = false;

  hideAudioPlayer();

}


function showAudioPlayer(
  title
) {

  elements.audioTitle
    .textContent =
    title;


  elements.audioPlayer
    .classList.remove(
      'hidden'
    );


  elements.audioPlayer
    .classList.add(
      'playing'
    );


  elements.audioButton
    .innerHTML =
    '⏹ <span>Stop</span>';

}


function hideAudioPlayer() {

  elements.audioPlayer
    .classList.add(
      'hidden'
    );


  elements.audioPlayer
    .classList.remove(
      'playing'
    );


  elements.audioButton
    .innerHTML =
    '🔊 <span data-i18n="narrate">Narrate</span>';


  applyTranslations();

}


/* =========================================================
   MOBILE NAV
   ========================================================= */

function toggleMobileMenu() {

  const open =
    elements.mobileNav
      .classList.toggle(
        'open'
      );


  elements.mobileMenuButton
    .setAttribute(
      'aria-expanded',
      String(open)
    );

}


function closeMobileMenu() {

  elements.mobileNav
    .classList.remove(
      'open'
    );


  elements.mobileMenuButton
    .setAttribute(
      'aria-expanded',
      'false'
    );

}


/* =========================================================
   YEAR
   ========================================================= */

function updateYear() {

  elements.currentYear
    .textContent =
    new Date()
      .getFullYear();

}


/* =========================================================
   SECURITY
   ========================================================= */

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


function escapeAttribute(
  value
) {

  return escapeHTML(
    value
  );

}
