// TECHPULSE ADMIN FRONTEND AUTHENTICATION
const ADMIN_USERNAME = 'admin';
const ADMIN_PASSWORD = 'TempTass_2026!';
const ADMIN_SESSION_KEY = 'techpulse_admin_logged_in_v1';
let adminInitialized = false;

function isLoggedIn() {
    return sessionStorage.getItem(ADMIN_SESSION_KEY) === 'true';
}

function showAdminConsole() {
    const login = document.getElementById('adminLogin');
    if (login) login.style.display = 'none';
}

function hideAdminConsole() {
    const login = document.getElementById('adminLogin');
    if (login) login.style.display = 'flex';
}

function showLoginError(message) {
    const element = document.getElementById('loginError');
    if (element) element.textContent = message;
}

function handleLogin() {
    const username = document.getElementById('adminUsername').value.trim();
    const password = document.getElementById('adminPassword').value;

    if (username === ADMIN_USERNAME && password === ADMIN_PASSWORD) {
        sessionStorage.setItem(ADMIN_SESSION_KEY, 'true');
        showAdminConsole();
        showLoginError('');
        initializeAdminConsole();
        return;
    }

    showLoginError('Invalid username or password.');
}

function refreshAdminNews() {
    window.location.reload();
}

function logoutAdmin() {
    sessionStorage.removeItem(ADMIN_SESSION_KEY);
    hideAdminConsole();
    window.scrollTo(0, 0);
    const username = document.getElementById('adminUsername');
    const password = document.getElementById('adminPassword');
    if (username) username.value = '';
    if (password) password.value = '';
}

function initializeAdminConsole() {
    if (adminInitialized) return;
    adminInitialized = true;

    document.getElementById('search').addEventListener('input', applyFilters);
    const themeToggle=document.getElementById('themeToggle');const themeIcon=document.getElementById('themeIcon');const themeText=document.getElementById('themeText');function applyAdminTheme(t){document.documentElement.setAttribute('data-theme',t);localStorage.setItem('techpulse_admin_theme',t);if(themeIcon)themeIcon.textContent=t==='dark'?'☀':'☾';if(themeText)themeText.textContent=t==='dark'?'Light':'Dark';}function initializeAdminTheme(){var t=localStorage.getItem('techpulse_admin_theme')||'light';applyAdminTheme(t);}if(themeToggle)themeToggle.addEventListener('click',function(){var t=document.documentElement.getAttribute('data-theme')=== 'dark'?'light':'dark';applyAdminTheme(t);});initializeAdminTheme();const refreshButton = document.getElementById('refreshNews');
    if (refreshButton) refreshButton.addEventListener('click', refreshAdminNews);
    const logoutButton = document.getElementById('logoutAdmin');
    if (logoutButton) logoutButton.addEventListener('click', logoutAdmin);
    document.getElementById('category').addEventListener('change', applyFilters);
    document.getElementById('source').addEventListener('change', applyFilters);
    document.getElementById('status').addEventListener('change', applyFilters);
    document.getElementById('relevance').addEventListener('change', applyFilters);

    document.getElementById('pageSize').addEventListener('change', event => {
        state.pageSize = Number(event.target.value);
        state.page = 1;
        render();
    });

    load();
    addPublishModerationButton();
}

function setupAdminLogin() {
    const button = document.getElementById('adminLoginButton');
    const password = document.getElementById('adminPassword');

    if (button) button.addEventListener('click', handleLogin);

    if (password) {
        password.addEventListener('keyup', event => {
            if (event.key === 'Enter') {
                event.preventDefault();
                handleLogin();
            }
        });
    }

    if (isLoggedIn()) {
        showAdminConsole();
        initializeAdminConsole();
    } else {
        hideAdminConsole();
    }
}

document.addEventListener('DOMContentLoaded', setupAdminLogin);
const state = {
    articles: [],
    filtered: [],
    page: 1,
    pageSize: 50,
    decisions: {}
};

const STORAGE_KEY = 'techpulse_admin_moderation_v1';

function load() {
    loadDecisions();

    fetch('../news.json')
        .then(response => {
            if (!response.ok) {
                throw new Error('Unable to load news.json');
            }

            return response.json();
        })
        .then(data => {
            state.articles = Array.isArray(data.articles)
                ? data.articles
                : [];

            populateFilters();
            applyFilters();
        })
        .catch(error => {
            document.getElementById('articles').innerHTML =
                '<div class="card error-card">' +
                '<h2>Unable to load news</h2>' +
                '<p>' + escapeHtml(error.message) + '</p>' +
                '</div>';
        });
}

function loadDecisions() {
    try {
        const saved = localStorage.getItem(STORAGE_KEY);

        if (saved) {
            const parsed = JSON.parse(saved);

            state.decisions =
                parsed && typeof parsed === 'object'
                    ? parsed
                    : {};
        }
    } catch (error) {
        console.warn('Unable to load moderation data:', error);
        state.decisions = {};
    }
}

function saveDecisions() {
    localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify(state.decisions)
    );
}

function getDecision(id) {
    return state.decisions[id] || null;
}

function setDecision(id, action, reason = '') {
    state.decisions[id] = {
        action: action,
        reason: reason,
        updated_at: new Date().toISOString()
    };

    saveDecisions();
}

function clearDecision(id) {
    delete state.decisions[id];
    saveDecisions();
}

function populateFilters() {
    populateSelect(
        'category',
        state.articles.map(article => article.category)
    );

    populateSelect(
        'source',
        state.articles.map(article => article.source)
    );

    populateSelect(
        'status',
        state.articles.map(article => article.status)
    );

    populateSelect(
        'relevance',
        state.articles.map(article => article.relevance)
    );
}

function populateSelect(id, values) {
    const select = document.getElementById(id);

    const uniqueValues = [...new Set(
        values
            .filter(Boolean)
            .map(value => String(value).trim())
    )].sort((a, b) => a.localeCompare(b));

    uniqueValues.forEach(value => {
        const option = document.createElement('option');

        option.value = value;
        option.textContent = value;

        select.appendChild(option);
    });
}

function applyFilters() {
    const search = document
        .getElementById('search')
        .value
        .trim()
        .toLowerCase();

    const category =
        document.getElementById('category').value;

    const source =
        document.getElementById('source').value;

    const status =
        document.getElementById('status').value;

    const relevance =
        document.getElementById('relevance').value;

    state.filtered = state.articles.filter(article => {

        if (category && article.category !== category) {
            return false;
        }

        if (source && article.source !== source) {
            return false;
        }

        if (status && article.status !== status) {
            return false;
        }

        if (relevance && article.relevance !== relevance) {
            return false;
        }

        if (search) {
            const searchable = [
                article.title,
                article.source,
                article.category,
                article.subcategory,
                article.summary,
                article.why_it_matters,
                article.what_changes,
                article.whats_next,
                ...(article.tags || []),
                ...(article.secondary_topics || [])
            ]
                .filter(Boolean)
                .join(' ')
                .toLowerCase();

            if (!searchable.includes(search)) {
                return false;
            }
        }

        return true;
    });

    state.page = 1;

    render();
}

function render() {
    renderStats();
    renderArticles();
    renderPagination();
}

function renderStats() {
    const stats = document.getElementById('stats');

    const total = state.articles.length;
    const visible = state.filtered.length;

    const start = visible === 0
        ? 0
        : ((state.page - 1) * state.pageSize) + 1;

    const end = Math.min(
        state.page * state.pageSize,
        visible
    );

    const hiddenCount = Object.values(state.decisions)
        .filter(item => item.action === 'hide')
        .length;

    const reviewCount = Object.values(state.decisions)
        .filter(item => item.action === 'review')
        .length;

    stats.textContent =
        'Showing ' +
        start +
        '–' +
        end +
        ' of ' +
        visible +
        ' articles · ' +
        total +
        ' total · ' +
        reviewCount +
        ' review · ' +
        hiddenCount +
        ' hidden';
}

function renderArticles() {
    const box = document.getElementById('articles');

    if (state.filtered.length === 0) {
        box.innerHTML =
            '<div class="empty card">' +
            '<h2>No articles found</h2>' +
            '<p>Try changing your search or filters.</p>' +
            '</div>';

        return;
    }

    const start =
        (state.page - 1) * state.pageSize;

    const end =
        start + state.pageSize;

    const pageArticles =
        state.filtered.slice(start, end);

    box.innerHTML =
        pageArticles
            .map(renderArticle)
            .join('');
}

function renderArticle(article) {
    const decision = getDecision(article.id);

    const title = escapeHtml(
        article.title || 'Untitled'
    );

    const summary = escapeHtml(
        article.summary ||
        article.why_it_matters ||
        'No summary available.'
    );

    const category = escapeHtml(
        article.category || 'Technology'
    );

    const source = escapeHtml(
        article.source || 'Unknown source'
    );

    const status = escapeHtml(
        article.status ||
        article.verification_status ||
        'UNKNOWN'
    );

    const relevance = escapeHtml(
        article.relevance || 'UNKNOWN'
    );

    const confidence =
        article.confidence ?? '—';

    const importance =
        article.importance ?? '—';

    const classification = escapeHtml(
        article.classification_confidence || '—'
    );

    const visualMap = {
        AI: 'AI',
        Cloud: 'CL',
        Cybersecurity: 'CY',
        Enterprise: 'EN',
        Gaming: 'GM',
        Hardware: 'HW',
        Linux: 'LX',
        Quantum: 'QN',
        Robotics: 'RB',
        Space: 'SP',
        Technology: 'TP'
    };

    const visualLabel = escapeHtml(
        visualMap[article.category] || 'TP'
    );

    const published =
        formatDate(article.published_at);

    const qualityFlags =
        Array.isArray(article.quality_flags)
            ? article.quality_flags
            : [];

    const flagsHtml =
        qualityFlags.length
            ? '<div class="flags">' +
              qualityFlags.map(flag =>
                  '<span class="flag">' +
                  escapeHtml(flag) +
                  '</span>'
              ).join('') +
              '</div>'
            : '';

    const decisionHtml =
        decision
            ? `
                <div class="editorial-decision ${escapeHtml(decision.action)}">
                    <strong>Editorial:</strong>
                    ${escapeHtml(decision.action.toUpperCase())}
                    ${
                        decision.reason
                            ? ' · ' + escapeHtml(decision.reason)
                            : ''
                    }
                </div>
              `
            : '';

    const safeUrl =
        safeArticleUrl(article.url);

    return `
        <article class="card article-card">

            <div class="article-visual" aria-hidden="true">
                <span>${visualLabel}</span>
                <i></i>
                <b></b>
            </div>

            <div class="article-content">

            <div class="article-top">

                <div class="meta">
                    <span>${category}</span>
                    <span>·</span>
                    <span>${source}</span>

                    ${
                        published
                            ? '<span>·</span><span>' +
                              published +
                              '</span>'
                            : ''
                    }
                </div>

                <div class="badges">
                    <span class="badge status">
                        ${status}
                    </span>

                    <span class="badge relevance">
                        ${relevance}
                    </span>
                </div>

            </div>

            <h2>${title}</h2>

            <p class="summary">
                ${summary}
            </p>

            <div class="metrics">

                <div>
                    <span>Confidence</span>
                    <strong>${confidence}</strong>
                </div>

                <div>
                    <span>Importance</span>
                    <strong>${importance}</strong>
                </div>

                <div>
                    <span>Classification</span>
                    <strong>${classification}</strong>
                </div>

            </div>

            ${flagsHtml}

            ${decisionHtml}

            <div class="actions">

                ${
                    safeUrl
                        ? `
                            <a
                                class="button primary"
                                href="${safeUrl}"
                                target="_blank"
                                rel="noopener noreferrer"
                            >
                                Open Article
                            </a>
                          `
                        : ''
                }

                <button
                    class="button"
                    type="button"
                    onclick="reviewArticle('${escapeJs(article.id)}')"
                >
                    Review
                </button>

                ${
                    decision && decision.action === 'hide'
                        ? `
                            <button
                                class="button restore"
                                type="button"
                                onclick="restoreArticle('${escapeJs(article.id)}')"
                            >
                                Restore
                            </button>
                          `
                        : `
                            <button
                                class="button danger"
                                type="button"
                                onclick="hideArticle('${escapeJs(article.id)}')"
                            >
                                Hide
                            </button>
                          `
                }

            </div>

            </div>

        </article>
    `;
}

function reviewArticle(id) {
    const article =
        state.articles.find(item => item.id === id);

    if (!article) {
        return;
    }

    const current =
        getDecision(id);

    const reason =
        window.prompt(
            'Enter an editorial review reason:',
            current?.reason || ''
        );

    if (reason === null) {
        return;
    }

    setDecision(
        id,
        'review',
        reason.trim()
    );

    render();
}

function hideArticle(id) {
    const article =
        state.articles.find(item => item.id === id);

    if (!article) {
        return;
    }

    const confirmed =
        window.confirm(
            'Hide this article from the Admin editorial view?\n\n' +
            (article.title || 'Untitled') +
            '\n\n' +
            'This does NOT modify news.json or the public site.'
        );

    if (!confirmed) {
        return;
    }

    const reason =
        window.prompt(
            'Reason for hiding this article:',
            ''
        );

    if (reason === null) {
        return;
    }

    setDecision(
        id,
        'hide',
        reason.trim()
    );

    render();
}

function restoreArticle(id) {
    const confirmed =
        window.confirm(
            'Restore this article to the normal editorial view?'
        );

    if (!confirmed) {
        return;
    }

    clearDecision(id);

    render();
}

function exportModeration() {
    const payload = {
        version: 1,
        updated_at: new Date().toISOString(),
        decisions: state.decisions
    };

    const blob = new Blob(
        [
            JSON.stringify(
                payload,
                null,
                2
            )
        ],
        {
            type: 'application/json'
        }
    );

    const url =
        URL.createObjectURL(blob);

    const link =
        document.createElement('a');

    link.href = url;
    link.download = 'moderation.json';

    document.body.appendChild(link);

    link.click();

    link.remove();

    URL.revokeObjectURL(url);
}

function clearAllModeration() {
    const confirmed =
        window.confirm(
            'Clear ALL editorial decisions from this browser?\n\n' +
            'This cannot be undone.'
        );

    if (!confirmed) {
        return;
    }

    state.decisions = {};

    localStorage.removeItem(STORAGE_KEY);

    render();
}

function renderPagination() {
    const box =
        document.getElementById('pagination');

    const totalPages =
        Math.ceil(
            state.filtered.length /
            state.pageSize
        );

    if (totalPages <= 1) {
        box.innerHTML = '';
        return;
    }

    let html = '';

    html += `
        <button
            class="page-button"
            ${state.page === 1 ? 'disabled' : ''}
            onclick="goToPage(${state.page - 1})"
        >
            ← Previous
        </button>
    `;

    const maxButtons = 7;

    let start =
        Math.max(
            1,
            state.page -
            Math.floor(maxButtons / 2)
        );

    let end =
        Math.min(
            totalPages,
            start + maxButtons - 1
        );

    if (end - start + 1 < maxButtons) {
        start =
            Math.max(
                1,
                end - maxButtons + 1
            );
    }

    for (
        let page = start;
        page <= end;
        page++
    ) {
        html += `
            <button
                class="page-button ${
                    page === state.page
                        ? 'active'
                        : ''
                }"
                onclick="goToPage(${page})"
            >
                ${page}
            </button>
        `;
    }

    html += `
        <button
            class="page-button"
            ${
                state.page === totalPages
                    ? 'disabled'
                    : ''
            }
            onclick="goToPage(${state.page + 1})"
        >
            Next →
        </button>
    `;

    box.innerHTML = html;
}

function goToPage(page) {
    const totalPages =
        Math.ceil(
            state.filtered.length /
            state.pageSize
        );

    if (
        page < 1 ||
        page > totalPages
    ) {
        return;
    }

    state.page = page;

    render();

    window.scrollTo({
        top: 0,
        behavior: 'smooth'
    });
}

function formatDate(value) {
    if (!value) {
        return '';
    }

    const date =
        new Date(value);

    if (Number.isNaN(date.getTime())) {
        return '';
    }

    return date.toLocaleString();
}

function safeArticleUrl(value) {
    if (!value) {
        return '';
    }

    try {
        const url =
            new URL(value);

        if (
            url.protocol !== 'http:' &&
            url.protocol !== 'https:'
        ) {
            return '';
        }

        return escapeHtml(
            url.href
        );
    } catch {
        return '';
    }
}

function escapeHtml(value) {
    return String(value)
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#039;');
}

function escapeJs(value) {
    return String(value)
        .replaceAll('\\', '\\\\')
        .replaceAll("'", "\\'");
}

document.addEventListener(
    'DOMContentLoaded',
    () => {

        document
            .getElementById('search')
            .addEventListener(
                'input',
                applyFilters
            );

        document
            .getElementById('category')
            .addEventListener(
                'change',
                applyFilters
            );

        document
            .getElementById('source')
            .addEventListener(
                'change',
                applyFilters
            );

        document
            .getElementById('status')
            .addEventListener(
                'change',
                applyFilters
            );

        document
            .getElementById('relevance')
            .addEventListener(
                'change',
                applyFilters
            );

        document
            .getElementById('pageSize')
            .addEventListener(
                'change',
                event => {
                    state.pageSize =
                        Number(event.target.value);

                    state.page = 1;

                    render();
                }
            );

        load();
    }
);
function showPublishPanel() {
    const existing = document.getElementById('tp-publish-panel');
    if (existing) { existing.scrollIntoView({ behavior: 'smooth', block: 'center' }); return; }
    const panel = document.createElement('section');
    panel.id = 'tp-publish-panel';
    panel.style.cssText = 'margin:24px 0;padding:20px;border:1px solid rgba(127,127,127,.35);border-radius:12px;background:rgba(127,127,127,.06)';
    panel.innerHTML = `
        <h2 style="margin:0 0 8px">Publish Moderation Changes</h2>
        <p style="margin:0 0 14px">Hide, Review, and Restore decisions are currently saved in this browser. Export the moderation file, replace <code>admin\\moderation.json</code> in your local TechPulse repository, then run the commands below.</p>
        <ol style="margin:0 0 14px;padding-left:22px">
            <li>Click <strong>Export Moderation</strong> above.</li>
            <li>Replace <code>admin\\moderation.json</code> with the downloaded file.</li>
            <li>Open Command Prompt in the TechPulse repository.</li>
            <li>Run the commands below.</li>
        </ol>
        <pre style="padding:12px;overflow:auto;border-radius:8px;background:rgba(0,0,0,.08)">git add admin/moderation.json
git diff --cached --check
git commit -m "Apply editorial moderation"
git push origin main</pre>
        <p style="margin:12px 0 0;font-size:.92em">The public site applies the moderation decision after <code>admin/moderation.json</code> is pushed to GitHub.</p>
    `;
    const anchor = document.querySelector('main') || document.body.firstElementChild;
    if (anchor && anchor.parentNode) anchor.parentNode.insertBefore(panel, anchor); else document.body.appendChild(panel);
    panel.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

function addPublishModerationButton() {
    if (document.getElementById('tp-publish-button')) return;
    const button = document.createElement('button');
    button.id = 'tp-publish-button';
    button.type = 'button';
    button.textContent = 'Publish Moderation Changes';
    button.onclick = showPublishPanel;
    button.style.cssText = 'margin-left:8px;padding:10px 14px;border:1px solid currentColor;border-radius:8px;cursor:pointer;font:inherit';
    const exportButton = document.querySelector('button[onclick*=\"exportModeration\"]');
    if (exportButton && exportButton.parentNode) exportButton.parentNode.insertBefore(button, exportButton.nextSibling);
}

document.addEventListener('DOMContentLoaded', addPublishModerationButton);
