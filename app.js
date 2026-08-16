/* =========================================================
   TECHPULSE NEWS ENGINE
   GitHub JSON Frontend
   ========================================================= */

const NEWS_JSON_URL =
  "https://raw.githubusercontent.com/kvseshu-code/techpulse-news/main/news.json";


const AUTO_REFRESH_INTERVAL =
  5 * 60 * 1000; // 5 minutes


let allArticles = [];

let currentCategory = "All";

let lastUpdated = null;


/* =========================================================
   INITIAL LOAD
   ========================================================= */

document.addEventListener(
  "DOMContentLoaded",
  function () {

    loadNews();

    startAutomaticRefresh();

  }
);


/* =========================================================
   LOAD NEWS FROM GITHUB
   ========================================================= */

async function loadNews() {

  setStatus(
    "Fetching latest news..."
  );


  try {

    /*
     * Cache-busting parameter.
     *
     * This prevents the browser from
     * showing an older cached JSON file.
     */

    const url =
      NEWS_JSON_URL +
      "?t=" +
      Date.now();


    const response =
      await fetch(
        url,
        {
          cache: "no-store"
        }
      );


    if (!response.ok) {

      throw new Error(
        "HTTP " +
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
        "Invalid news.json format"
      );

    }


    allArticles =
      data.articles;


    lastUpdated =
      data.updatedAt ||
      null;


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


    setStatus(
      "News updated " +
      formatRelativeTime(
        lastUpdated
      )
    );


    applyFilters();


  } catch (error) {

    console.error(
      "News loading error:",
      error
    );


    setStatus(
      "Unable to load latest news"
    );


    showError(
      error.message ||
      "Unable to load news."
    );

  }

}


/* =========================================================
   AUTOMATIC REFRESH
   ========================================================= */

function startAutomaticRefresh() {

  setInterval(
    function () {

      loadNews();

    },
    AUTO_REFRESH_INTERVAL
  );

}


/* =========================================================
   MANUAL REFRESH
   ========================================================= */

function manualRefresh() {

  const button =
    document.querySelector(
      ".refresh"
    );


  if (button) {

    button.disabled =
      true;

    button.textContent =
      "Refreshing...";

  }


  loadNews()
    .finally(
      function () {

        setTimeout(
          function () {

            if (button) {

              button.disabled =
                false;

              button.textContent =
                "↻ Refresh";

            }

          },
          500
        );

      }
    );

}


/* =========================================================
   CATEGORY
   ========================================================= */

function setCategory(
  category,
  button
) {

  currentCategory =
    category;


  document
    .querySelectorAll(
      "nav button"
    )
    .forEach(
      function (btn) {

        btn.classList.remove(
          "active"
        );

      }
    );


  if (button) {

    button.classList.add(
      "active"
    );

  }


  applyFilters();

}


/* =========================================================
   SEARCH + CATEGORY FILTER
   ========================================================= */

function applyFilters() {

  const searchElement =
    document.getElementById(
      "search"
    );


  const search =
    searchElement
      ? searchElement.value
          .toLowerCase()
          .trim()
      : "";


  const filtered =
    allArticles.filter(
      function (article) {

        const categoryMatch =
          currentCategory === "All" ||
          article.mainCategory ===
            currentCategory ||
          article.category ===
            currentCategory;


        const searchableText =
          (
            (article.title || "") +
            " " +
            (article.description || "") +
            " " +
            (article.source || "") +
            " " +
            (article.category || "")
          )
          .toLowerCase();


        const searchMatch =
          !search ||
          searchableText.includes(
            search
          );


        return (
          categoryMatch &&
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
      "newsContainer"
    );


  const count =
    document.getElementById(
      "articleCount"
    );


  if (count) {

    count.textContent =
      articles.length +
      (
        articles.length === 1
          ? " article"
          : " articles"
      );

  }


  if (!articles.length) {

    if (container) {

      container.innerHTML = `

        <div class="message">

          <h3>
            No news found
          </h3>

          <p>
            Try another category or search term.
          </p>

        </div>

      `;

    }

    return;

  }


  if (container) {

    container.innerHTML = `

      <div class="news-grid">

        ${articles
          .map(
            createArticleCard
          )
          .join("")}

      </div>

    `;

  }

}


/* =========================================================
   CREATE ARTICLE CARD
   ========================================================= */

function createArticleCard(
  article
) {

  const category =
    article.category ||
    article.mainCategory ||
    "Technology";


  const icon =
    category
      .toLowerCase()
      .includes("gaming")
      ? "🎮"
      : "⚡";


  let imageHTML;


  if (article.image) {

    imageHTML = `

      <img
        class="article-image"
        src="${escapeHtml(article.image)}"
        alt=""
        loading="lazy"
        onerror="
          this.style.display='none';
          this.nextElementSibling.style.display='flex';
        "
      >

      <div
        class="image-placeholder"
        style="display:none;"
      >
        ${icon}
      </div>

    `;

  } else {

    imageHTML = `

      <div class="image-placeholder">
        ${icon}
      </div>

    `;

  }


  return `

    <article class="article">

      ${imageHTML}

      <div class="article-content">

        <div class="category">

          ${escapeHtml(category)}

        </div>


        <h2 class="article-title">

          <a
            href="${escapeHtml(article.url || "#")}"
            target="_blank"
            rel="noopener noreferrer"
          >

            ${escapeHtml(
              article.title ||
              "Untitled news"
            )}

          </a>

        </h2>


        <p class="description">

          ${escapeHtml(
            article.description ||
            "Read the latest technology and gaming news."
          )}

        </p>


        <div class="article-footer">

          <span class="source">

            ${escapeHtml(
              article.source ||
              "TechPulse"
            )}

          </span>


          <span class="date">

            ${formatDate(
              article.published
            )}

          </span>

        </div>

      </div>

    </article>

  `;

}


/* =========================================================
   STATUS
   ========================================================= */

function setStatus(
  message
) {

  const status =
    document.getElementById(
      "statusText"
    );


  if (status) {

    status.textContent =
      message;

  }

}


/* =========================================================
   ERROR
   ========================================================= */

function showError(
  message
) {

  const container =
    document.getElementById(
      "newsContainer"
    );


  if (!container) {

    return;

  }


  container.innerHTML = `

    <div class="message">

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
        class="refresh"
        onclick="manualRefresh()"
      >
        Try Again
      </button>

    </div>

  `;

}


/* =========================================================
   DATE FORMAT
   ========================================================= */

function formatDate(
  value
) {

  if (!value) {

    return "";

  }


  const date =
    new Date(value);


  if (
    isNaN(
      date.getTime()
    )
  ) {

    return "";

  }


  return date.toLocaleString(
    undefined,
    {
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit"
    }
  );

}


/* =========================================================
   RELATIVE / UPDATE TIME
   ========================================================= */

function formatRelativeTime(
  value
) {

  if (!value) {

    return "recently";

  }


  const date =
    new Date(value);


  if (
    isNaN(
      date.getTime()
    )
  ) {

    return "recently";

  }


  const diff =
    Date.now() -
    date.getTime();


  if (diff < 60000) {

    return "just now";

  }


  if (
    diff <
    60 * 60000
  ) {

    const minutes =
      Math.floor(
        diff /
        60000
      );

    return (
      minutes +
      (
        minutes === 1
          ? " minute ago"
          : " minutes ago"
      )
    );

  }


  if (
    diff <
    24 * 60 * 60000
  ) {

    const hours =
      Math.floor(
        diff /
        (
          60 *
          60000
        )
      );

    return (
      hours +
      (
        hours === 1
          ? " hour ago"
          : " hours ago"
      )
    );

  }


  return date.toLocaleString(
    undefined,
    {
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit"
    }
  );

}


/* =========================================================
   ESCAPE HTML
   ========================================================= */

function escapeHtml(
  value
) {

  return String(
    value || ""
  )
    .replace(
      /&/g,
      "&amp;"
    )
    .replace(
      /</g,
      "&lt;"
    )
    .replace(
      />/g,
      "&gt;"
    )
    .replace(
      /"/g,
      "&quot;"
    )
    .replace(
      /'/g,
      "&#039;"
    );

}
