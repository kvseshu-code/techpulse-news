/*
 * ============================================================
 * TECHPULSE
 * Frontend News Application
 *
 * GitHub Pages version
 *
 * Data source:
 *     news.json
 *
 * No Google Apps Script
 * No google.script.run
 * No traditional database
 * ============================================================
 */

'use strict';


/* ============================================================
   CONFIGURATION
   ============================================================ */

const CONFIG = {

    NEWS_FILE: './news.json',

    // Check for a new news.json every 2 minutes.
    REFRESH_INTERVAL: 2 * 60 * 1000,

    // Cache-busting parameter.
    CACHE_BUST: true

};


/* ============================================================
   APPLICATION STATE
   ============================================================ */

let allArticles = [];

let currentCategory = 'All';

let lastUpdated = null;

let refreshTimer = null;

let isLoading = false;


/* ============================================================
   INITIALIZATION
   ============================================================ */

document.addEventListener(
    'DOMContentLoaded',
    function () {

        initializeApplication();

    }
);


/* ============================================================
   INITIALIZE APPLICATION
   ============================================================ */

function initializeApplication() {

    loadNews();

    startAutomaticRefresh();

    setupVisibilityRefresh();

}


/* ============================================================
   LOAD NEWS
   ============================================================ */

async function loadNews() {

    if (isLoading) {

        return;

    }


    isLoading = true;


    setStatus(
        'Checking for the latest news...',
        false
    );


    try {

        const newsUrl =
            buildNewsUrl();


        const response =
            await fetch(
                newsUrl,
                {
                    method: 'GET',

                    cache: 'no-store',

                    headers: {
                        'Cache-Control':
                            'no-cache'
                    }
                }
            );


        if (!response.ok) {

            throw new Error(
                'News file returned HTTP ' +
                response.status
            );

        }


        const data =
            await response.json();


        validateNewsResponse(
            data
        );


        allArticles =
            Array.isArray(
                data.articles
            )
                ? data.articles
                : [];


        lastUpdated =
            data.updatedAt ||
            null;


        sortArticles();


        applyFilters();


        updateStatus(
            data
        );


    } catch (error) {

        console.error(
            'News loading error:',
            error
        );


        showError(
            error.message ||
            'Unable to load the latest news.'
        );

    } finally {

        isLoading = false;

    }

}


/* ============================================================
   BUILD NEWS URL
   ============================================================ */

function buildNewsUrl() {

    let url =
        CONFIG.NEWS_FILE;


    if (
        CONFIG.CACHE_BUST
    ) {

        const separator =
            url.indexOf('?') === -1
                ? '?'
                : '&';


        url +=
            separator +
            '_=' +
            Date.now();

    }


    return url;

}


/* ============================================================
   VALIDATE RESPONSE
   ============================================================ */

function validateNewsResponse(
    data
) {

    if (
        !data ||
        typeof data !== 'object'
    ) {

        throw new Error(
            'Invalid news data.'
        );

    }


    if (
        data.success === false
    ) {

        throw new Error(
            data.error ||
            'News engine returned an error.'
        );

    }


    if (
        !Array.isArray(
            data.articles
        )
    ) {

        throw new Error(
            'No article list found.'
        );

    }

}


/* ============================================================
   SORT ARTICLES
   ============================================================ */

function sortArticles() {

    allArticles.sort(
        function (
            first,
            second
        ) {

            const firstTime =
                new Date(
                    first.published ||
                    0
                ).getTime();


            const secondTime =
                new Date(
                    second.published ||
                    0
                ).getTime();


            return (
                secondTime -
                firstTime
            );

        }
    );

}


/* ============================================================
   AUTOMATIC REFRESH
   ============================================================ */

function startAutomaticRefresh() {

    if (
        refreshTimer
    ) {

        clearInterval(
            refreshTimer
        );

    }


    refreshTimer =
        setInterval(
            function () {

                loadNews();

            },
            CONFIG.REFRESH_INTERVAL
        );

}


/* ============================================================
   REFRESH WHEN USER RETURNS
   ============================================================ */

function setupVisibilityRefresh() {

    document.addEventListener(
        'visibilitychange',
        function () {

            if (
                document.visibilityState ===
                'visible'
            ) {

                loadNews();

            }

        }
    );

}


/* ============================================================
   MANUAL REFRESH
   ============================================================ */

function manualRefresh() {

    const button =
        document.querySelector(
            '.refresh'
        );


    if (button) {

        button.disabled =
            true;

        button.textContent =
            'Refreshing...';

    }


    loadNews()
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


/* ============================================================
   CATEGORY
   ============================================================ */

function setCategory(
    category,
    button
) {

    currentCategory =
        category;


    document
        .querySelectorAll(
            'nav button'
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


    applyFilters();

}


/* ============================================================
   FILTER ARTICLES
   ============================================================ */

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

                const articleCategory =
                    article.category ||
                    article.mainCategory ||
                    'Technology';


                const categoryMatch =
                    currentCategory ===
                    'All' ||
                    articleCategory ===
                    currentCategory ||
                    article.mainCategory ===
                    currentCategory;


                const searchableText =
                    (
                        (article.title ||
                            '') +
                        ' ' +
                        (article.description ||
                            '') +
                        ' ' +
                        (article.source ||
                            '') +
                        ' ' +
                        (article.category ||
                            '')
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


/* ============================================================
   RENDER NEWS
   ============================================================ */

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


    updateArticleCount(
        articles.length
    );


    if (
        !articles.length
    ) {

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

        return;

    }


    container.innerHTML = `

        <div class="news-grid">

            ${articles
                .map(
                    createArticleCard
                )
                .join('')}

        </div>

    `;

}


/* ============================================================
   CREATE ARTICLE CARD
   ============================================================ */

function createArticleCard(
    article
) {

    const category =
        article.category ||
        article.mainCategory ||
        'Technology';


    const image =
        article.image ||
        '';


    const title =
        article.title ||
        'Untitled article';


    const description =
        article.description ||
        'Read the latest story.';


    const source =
        article.source ||
        'News Source';


    const url =
        article.url ||
        '#';


    const published =
        article.published ||
        '';


    const icon =
        category === 'Gaming'
            ? '🎮'
            : '⚡';


    let imageHtml = '';


    if (image) {

        imageHtml = `

            <img
                class="article-image"
                src="${escapeHtml(image)}"
                alt=""
                loading="lazy"
                referrerpolicy="no-referrer"
                onerror="handleImageError(this)"
            >

            <div
                class="image-placeholder"
                style="display:none;"
            >
                ${icon}
            </div>

        `;

    } else {

        imageHtml = `

            <div class="image-placeholder">

                ${icon}

            </div>

        `;

    }


    return `

        <article
            class="article"
            data-id="${escapeHtml(
                article.id || ''
            )}"
        >

            ${imageHtml}


            <div class="article-content">

                <div class="category">

                    ${escapeHtml(
                        category
                    )}

                </div>


                <h2 class="article-title">

                    <a
                        href="${escapeHtml(url)}"
                        target="_blank"
                        rel="noopener noreferrer"
                    >

                        ${escapeHtml(title)}

                    </a>

                </h2>


                <p class="description">

                    ${escapeHtml(
                        description
                    )}

                </p>


                <div class="article-footer">

                    <span class="source">

                        ${escapeHtml(source)}

                    </span>


                    <span class="date">

                        ${formatDate(
                            published
                        )}

                    </span>

                </div>

            </div>

        </article>

    `;

}


/* ============================================================
   IMAGE ERROR
   ============================================================ */

function handleImageError(
    image
) {

    if (!image) {

        return;

    }


    image.style.display =
        'none';


    const placeholder =
        image.nextElementSibling;


    if (
        placeholder
    ) {

        placeholder.style.display =
            'flex';

    }

}


/* ============================================================
   STATUS
   ============================================================ */

function updateStatus(
    data
) {

    const updated =
        data.updatedAt ||
        lastUpdated;


    const articleTotal =
        Array.isArray(
            data.articles
        )
            ? data.articles.length
            : 0;


    const statusText =
        document.getElementById(
            'statusText'
        );


    if (
        statusText
    ) {

        statusText.textContent =
            'News updated ' +
            formatRelativeTime(
                updated
            );

    }


    updateArticleCount(
        articleTotal
    );

}


/* ============================================================
   STATUS MESSAGE
   ============================================================ */

function setStatus(
    message,
    error
) {

    const statusText =
        document.getElementById(
            'statusText'
        );


    if (
        statusText
    ) {

        statusText.textContent =
            message;

    }


    const dot =
        document.querySelector(
            '.status-dot'
        );


    if (
        dot
    ) {

        dot.style.background =
            error
                ? '#ef4444'
                : '#22c55e';

    }

}


/* ============================================================
   ARTICLE COUNT
   ============================================================ */

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


/* ============================================================
   ERROR
   ============================================================ */

function showError(
    message
) {

    setStatus(
        'Unable to update news',
        true
    );


    const container =
        document.getElementById(
            'newsContainer'
        );


    if (!container) {

        return;

    }


    // Do not destroy existing news if
    // a background refresh fails.

    if (
        allArticles.length > 0
    ) {

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


/* ============================================================
   DATE FORMAT
   ============================================================ */

function formatDate(
    value
) {

    const date =
        new Date(value);


    if (
        isNaN(
            date.getTime()
        )
    ) {

        return '';

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


/* ============================================================
   RELATIVE / UPDATED TIME
   ============================================================ */

function formatRelativeTime(
    value
) {

    if (!value) {

        return 'recently';

    }


    const date =
        new Date(value);


    if (
        isNaN(
            date.getTime()
        )
    ) {

        return 'recently';

    }


    const now =
        Date.now();


    const difference =
        Math.max(
            0,
            now -
            date.getTime()
        );


    const minutes =
        Math.floor(
            difference /
            60000
        );


    if (
        minutes < 1
    ) {

        return 'just now';

    }


    if (
        minutes < 60
    ) {

        return (
            minutes +
            (
                minutes === 1
                    ? ' minute ago'
                    : ' minutes ago'
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


/* ============================================================
   ESCAPE HTML
   ============================================================ */

function escapeHtml(
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
