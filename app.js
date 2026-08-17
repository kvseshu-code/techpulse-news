/************************************************************
 * TECHPULSE FRONTEND
 * Version 2.0
 *
 * API:
 * Google Apps Script → Google Sheet → JSON → TechPulse
 ************************************************************/


/* ==========================================================
   CONFIGURATION
   ========================================================== */

const API_URL =
  'https://script.google.com/macros/s/AKfycbxcG1zxiqjZ8N1tYlF6kpLVbn597imA2n8W6Zruglk4QF6mbgXrUgTx2msHktYcL-TRwg/exec';


/*
 * Automatic frontend refresh.
 *
 * This does NOT collect news.
 * It only asks the API for the latest available data.
 */

const REFRESH_INTERVAL =
  5 * 60 * 1000;


/* ==========================================================
   APPLICATION STATE
   ========================================================== */

let allArticles = [];

let previousArticleIds = new Set();

let currentCategory = 'All';

let isLoading = false;

let selectedLanguage =
  localStorage.getItem(
    'techpulse-language'
  ) || 'en';


/*
 * Speech synthesis state.
 */

let speechQueue = [];

let speechIndex = 0;

let currentSpeechArticle = null;

let speechPaused = false;


/* ==========================================================
   TRANSLATIONS
   ========================================================== */

const translations = {

  en: {

    all: 'All',

    technology: 'Technology',

    ai: 'AI',

    cybersecurity: 'Cybersecurity',

    gaming: 'Gaming',

    space: 'Space',

    liveNews: 'LIVE NEWS',

    heroDescription:
      'Technology, AI, cybersecurity, gaming and space news — gathered from trusted publishers and updated automatically.',

    feedStatus:
      'FEED STATUS',

    refreshFeed:
      'Refresh Feed',

    refresh:
      'Refresh',

    searchPlaceholder:
      'Search technology news...',

    latest:
      'THE LATEST',

    latestNews:
      'Latest News',

    topStories:
      'TOP STORIES',

    loadingStory:
      'Loading the latest story...',

    loadingNews:
      'Loading the latest news...',

    noStories:
      'No stories found',

    tryAnother:
      'Try another search or category.',

    unableLoad:
      'Unable to load the news',

    tryAgain:
      'Try Again',

    explore:
      'EXPLORE',

    topics:
      'Topics',

    artificialIntelligence:
      'Artificial Intelligence',

    footerTagline:
      'Technology news, simplified.',

    footerDescription:
      'TechPulse provides news discovery and summaries. Full stories remain with their respective publishers.',

    readStory:
      'Read Full Story',

    read:
      'Read',

    listen:
      'Listen',

    stop:
      'Stop',

    pause:
      'Pause',

    resume:
      'Resume',

    ready:
      'Ready',

    speaking:
      'Speaking',

    paused:
      'Paused',

    narrationStopped:
      'Narration stopped',

    newStories:
      'New stories available',

    stories:
      'stories',

    story:
      'story',

    live:
      'Live',

    offline:
      'Offline',

    updating:
      'Updating...',

    recently:
      'Recently',

    justNow:
      'Just now'

  },


  hi: {

    all: 'सभी',

    technology: 'प्रौद्योगिकी',

    ai: 'एआई',

    cybersecurity: 'साइबर सुरक्षा',

    gaming: 'गेमिंग',

    space: 'अंतरिक्ष',

    liveNews: 'लाइव न्यूज़',

    heroDescription:
      'प्रौद्योगिकी, एआई, साइबर सुरक्षा, गेमिंग और अंतरिक्ष की खबरें — विश्वसनीय प्रकाशकों से एकत्रित और स्वचालित रूप से अपडेट।',

    feedStatus: 'फीड स्थिति',

    refreshFeed: 'फीड रीफ्रेश करें',

    refresh: 'रीफ्रेश',

    searchPlaceholder:
      'टेक्नोलॉजी न्यूज़ खोजें...',

    latest: 'नवीनतम',

    latestNews: 'नवीनतम समाचार',

    topStories: 'प्रमुख समाचार',

    loadingStory:
      'नवीनतम समाचार लोड हो रहा है...',

    loadingNews:
      'नवीनतम समाचार लोड हो रहे हैं...',

    noStories:
      'कोई समाचार नहीं मिला',

    tryAnother:
      'दूसरी खोज या श्रेणी आज़माएं।',

    unableLoad:
      'समाचार लोड नहीं हो सके',

    tryAgain:
      'फिर कोशिश करें',

    explore: 'एक्सप्लोर करें',

    topics: 'विषय',

    artificialIntelligence:
      'कृत्रिम बुद्धिमत्ता',

    footerTagline:
      'टेक्नोलॉजी समाचार, सरल रूप में।',

    footerDescription:
      'TechPulse समाचार खोज और सारांश प्रदान करता है। पूरी खबरें संबंधित प्रकाशकों के पास रहती हैं।',

    readStory:
      'पूरी खबर पढ़ें',

    read: 'पढ़ें',

    listen: 'सुनें',

    stop: 'रोकें',

    pause: 'रोकें',

    resume: 'जारी रखें',

    ready: 'तैयार',

    speaking: 'पढ़ा जा रहा है',

    paused: 'रुका हुआ',

    narrationStopped:
      'नरेशन रोक दिया गया',

    newStories:
      'नई खबरें उपलब्ध हैं',

    stories: 'खबरें',

    story: 'खबर',

    live: 'लाइव',

    offline: 'ऑफलाइन',

    updating: 'अपडेट हो रहा है...',

    recently: 'हाल ही में',

    justNow: 'अभी'
  },


  te: {

    all: 'అన్ని',

    technology: 'టెక్నాలజీ',

    ai: 'AI',

    cybersecurity: 'సైబర్ సెక్యూరిటీ',

    gaming: 'గేమింగ్',

    space: 'అంతరిక్షం',

    liveNews: 'లైవ్ న్యూస్',

    heroDescription:
      'టెక్నాలజీ, AI, సైబర్ సెక్యూరిటీ, గేమింగ్ మరియు అంతరిక్ష వార్తలు — విశ్వసనీయ ప్రచురణకర్తల నుండి సేకరించి ఆటోమేటిక్‌గా అప్‌డేట్ అవుతాయి.',

    feedStatus: 'ఫీడ్ స్థితి',

    refreshFeed: 'ఫీడ్ రిఫ్రెష్',

    refresh: 'రిఫ్రెష్',

    searchPlaceholder:
      'టెక్నాలజీ వార్తలను శోధించండి...',

    latest: 'తాజా',

    latestNews: 'తాజా వార్తలు',

    topStories: 'ముఖ్య వార్తలు',

    loadingStory:
      'తాజా వార్త లోడ్ అవుతోంది...',

    loadingNews:
      'తాజా వార్తలు లోడ్ అవుతున్నాయి...',

    noStories:
      'వార్తలు కనుగొనబడలేదు',

    tryAnother:
      'మరొక శోధన లేదా వర్గాన్ని ప్రయత్నించండి.',

    unableLoad:
      'వార్తలను లోడ్ చేయలేకపోయాము',

    tryAgain: 'మళ్లీ ప్రయత్నించండి',

    explore: 'అన్వేషించండి',

    topics: 'విషయాలు',

    artificialIntelligence:
      'కృత్రిమ మేధస్సు',

    footerTagline:
      'టెక్నాలజీ వార్తలు, సరళంగా.',

    footerDescription:
      'TechPulse వార్తల అన్వేషణ మరియు సారాంశాలను అందిస్తుంది. పూర్తి కథనాలు వాటి సంబంధిత ప్రచురణకర్తల వద్ద ఉంటాయి.',

    readStory:
      'పూర్తి వార్త చదవండి',

    read: 'చదవండి',

    listen: 'వినండి',

    stop: 'ఆపండి',

    pause: 'పాజ్',

    resume: 'కొనసాగించండి',

    ready: 'సిద్ధంగా ఉంది',

    speaking: 'చదువుతోంది',

    paused: 'పాజ్ చేయబడింది',

    narrationStopped:
      'నరేషన్ ఆపబడింది',

    newStories:
      'కొత్త వార్తలు అందుబాటులో ఉన్నాయి',

    stories: 'వార్తలు',

    story: 'వార్త',

    live: 'లైవ్',

    offline: 'ఆఫ్‌లైన్',

    updating: 'అప్‌డేట్ అవుతోంది...',

    recently: 'ఇటీవల',

    justNow: 'ఇప్పుడే'
  },


  ta: {

    all: 'அனைத்தும்',

    technology: 'தொழில்நுட்பம்',

    ai: 'AI',

    cybersecurity: 'சைபர் பாதுகாப்பு',

    gaming: 'கேமிங்',

    space: 'விண்வெளி',

    liveNews: 'நேரலை செய்திகள்',

    heroDescription:
      'தொழில்நுட்பம், AI, சைபர் பாதுகாப்பு, கேமிங் மற்றும் விண்வெளி செய்திகள் — நம்பகமான வெளியீட்டாளர்களிடமிருந்து சேகரிக்கப்பட்டு தானாக புதுப்பிக்கப்படும்.',

    feedStatus: 'ஃபீட் நிலை',

    refreshFeed: 'ஃபீட்டை புதுப்பிக்கவும்',

    refresh: 'புதுப்பி',

    searchPlaceholder:
      'தொழில்நுட்ப செய்திகளைத் தேடுங்கள்...',

    latest: 'சமீபத்திய',

    latestNews: 'சமீபத்திய செய்திகள்',

    topStories: 'முக்கிய செய்திகள்',

    loadingStory:
      'சமீபத்திய செய்தி ஏற்றப்படுகிறது...',

    loadingNews:
      'சமீபத்திய செய்திகள் ஏற்றப்படுகின்றன...',

    noStories:
      'செய்திகள் எதுவும் கிடைக்கவில்லை',

    tryAnother:
      'மற்றொரு தேடல் அல்லது வகையை முயற்சிக்கவும்.',

    unableLoad:
      'செய்திகளை ஏற்ற முடியவில்லை',

    tryAgain: 'மீண்டும் முயற்சிக்கவும்',

    explore: 'ஆராயுங்கள்',

    topics: 'தலைப்புகள்',

    artificialIntelligence:
      'செயற்கை நுண்ணறிவு',

    footerTagline:
      'தொழில்நுட்ப செய்திகள், எளிமையாக.',

    footerDescription:
      'TechPulse செய்தி கண்டுபிடிப்பு மற்றும் சுருக்கங்களை வழங்குகிறது. முழு செய்திகள் அவற்றின் வெளியீட்டாளர்களிடமே இருக்கும்.',

    readStory:
      'முழு செய்தியைப் படிக்கவும்',

    read: 'படிக்க',

    listen: 'கேட்க',

    stop: 'நிறுத்து',

    pause: 'இடைநிறுத்து',

    resume: 'தொடரவும்',

    ready: 'தயார்',

    speaking: 'வாசிக்கிறது',

    paused: 'இடைநிறுத்தப்பட்டது',

    narrationStopped:
      'வாசிப்பு நிறுத்தப்பட்டது',

    newStories:
      'புதிய செய்திகள் உள்ளன',

    stories: 'செய்திகள்',

    story: 'செய்தி',

    live: 'நேரலை',

    offline: 'ஆஃப்லைன்',

    updating: 'புதுப்பிக்கிறது...',

    recently: 'சமீபத்தில்',

    justNow: 'இப்போது'
  },


  kn: {

    all: 'ಎಲ್ಲಾ',

    technology: 'ತಂತ್ರಜ್ಞಾನ',

    ai: 'AI',

    cybersecurity: 'ಸೈಬರ್ ಭದ್ರತೆ',

    gaming: 'ಗೇಮಿಂಗ್',

    space: 'ಬಾಹ್ಯಾಕಾಶ',

    liveNews: 'ಲೈವ್ ಸುದ್ದಿ',

    heroDescription:
      'ತಂತ್ರಜ್ಞಾನ, AI, ಸೈಬರ್ ಭದ್ರತೆ, ಗೇಮಿಂಗ್ ಮತ್ತು ಬಾಹ್ಯಾಕಾಶ ಸುದ್ದಿಗಳು — ವಿಶ್ವಾಸಾರ್ಹ ಪ್ರಕಾಶಕರಿಂದ ಸಂಗ್ರಹಿಸಿ ಸ್ವಯಂಚಾಲಿತವಾಗಿ ನವೀಕರಿಸಲಾಗುತ್ತದೆ.',

    feedStatus: 'ಫೀಡ್ ಸ್ಥಿತಿ',

    refreshFeed: 'ಫೀಡ್ ರಿಫ್ರೆಶ್',

    refresh: 'ರಿಫ್ರೆಶ್',

    searchPlaceholder:
      'ತಂತ್ರಜ್ಞಾನ ಸುದ್ದಿಗಳನ್ನು ಹುಡುಕಿ...',

    latest: 'ಇತ್ತೀಚಿನ',

    latestNews: 'ಇತ್ತೀಚಿನ ಸುದ್ದಿಗಳು',

    topStories: 'ಪ್ರಮುಖ ಸುದ್ದಿಗಳು',

    loadingStory:
      'ಇತ್ತೀಚಿನ ಸುದ್ದಿ ಲೋಡ್ ಆಗುತ್ತಿದೆ...',

    loadingNews:
      'ಇತ್ತೀಚಿನ ಸುದ್ದಿಗಳು ಲೋಡ್ ಆಗುತ್ತಿವೆ...',

    noStories:
      'ಯಾವುದೇ ಸುದ್ದಿಗಳು ಕಂಡುಬಂದಿಲ್ಲ',

    tryAnother:
      'ಬೇರೆ ಹುಡುಕಾಟ ಅಥವಾ ವರ್ಗವನ್ನು ಪ್ರಯತ್ನಿಸಿ.',

    unableLoad:
      'ಸುದ್ದಿಗಳನ್ನು ಲೋಡ್ ಮಾಡಲು ಸಾಧ್ಯವಾಗಲಿಲ್ಲ',

    tryAgain: 'ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ',

    explore: 'ಅನ್ವೇಷಿಸಿ',

    topics: 'ವಿಷಯಗಳು',

    artificialIntelligence:
      'ಕೃತಕ ಬುದ್ಧಿಮತ್ತೆ',

    footerTagline:
      'ತಂತ್ರಜ್ಞಾನ ಸುದ್ದಿ, ಸರಳವಾಗಿ.',

    footerDescription:
      'TechPulse ಸುದ್ದಿ ಅನ್ವೇಷಣೆ ಮತ್ತು ಸಾರಾಂಶಗಳನ್ನು ಒದಗಿಸುತ್ತದೆ. ಸಂಪೂರ್ಣ ಸುದ್ದಿಗಳು ಸಂಬಂಧಿತ ಪ್ರಕಾಶಕರಲ್ಲೇ ಇರುತ್ತವೆ.',

    readStory:
      'ಸಂಪೂರ್ಣ ಸುದ್ದಿ ಓದಿ',

    read: 'ಓದಿ',

    listen: 'ಕೇಳಿ',

    stop: 'ನಿಲ್ಲಿಸಿ',

    pause: 'ವಿರಾಮ',

    resume: 'ಮುಂದುವರಿಸಿ',

    ready: 'ಸಿದ್ಧವಾಗಿದೆ',

    speaking: 'ಓದುತ್ತಿದೆ',

    paused: 'ವಿರಾಮಗೊಂಡಿದೆ',

    narrationStopped:
      'ನರೇಶನ್ ನಿಲ್ಲಿಸಲಾಗಿದೆ',

    newStories:
      'ಹೊಸ ಸುದ್ದಿಗಳು ಲಭ್ಯವಿವೆ',

    stories: 'ಸುದ್ದಿಗಳು',

    story: 'ಸುದ್ದಿ',

    live: 'ಲೈವ್',

    offline: 'ಆಫ್‌ಲೈನ್',

    updating: 'ನವೀಕರಿಸಲಾಗುತ್ತಿದೆ...',

    recently: 'ಇತ್ತೀಚೆಗೆ',

    justNow: 'ಈಗ'
  }

};


/* ==========================================================
   DOM ELEMENTS
   ========================================================== */

const elements = {

  newsGrid:
    document.getElementById('newsGrid'),

  featuredStory:
    document.getElementById('featuredStory'),

  articleCount:
    document.getElementById('articleCount'),

  feedStatus:
    document.getElementById('feedStatus'),

  lastUpdated:
    document.getElementById('lastUpdated'),

  searchInput:
    document.getElementById('searchInput'),

  refreshButton:
    document.getElementById('refreshButton'),

  refreshIcon:
    document.getElementById('refreshIcon'),

  retryButton:
    document.getElementById('retryButton'),

  errorState:
    document.getElementById('errorState'),

  errorMessage:
    document.getElementById('errorMessage'),

  emptyState:
    document.getElementById('emptyState'),

  themeToggle:
    document.getElementById('themeToggle'),

  languageSelect:
    document.getElementById('languageSelect'),

  currentYear:
    document.getElementById('currentYear'),

  audioBar:
    document.getElementById('audioBar'),

  audioTitle:
    document.getElementById('audioTitle'),

  audioStatus:
    document.getElementById('audioStatus'),

  audioPlay:
    document.getElementById('audioPlay'),

  audioPause:
    document.getElementById('audioPause'),

  audioStop:
    document.getElementById('audioStop'),

  heroRefreshButton:
    document.getElementById('heroRefreshButton'),

  newStoriesBadge:
    document.getElementById('newStoriesBadge')

};


/* ==========================================================
   INITIALIZATION
   ========================================================== */

document.addEventListener(
  'DOMContentLoaded',
  function() {

    initializeTheme();

    initializeLanguage();

    setupEventListeners();

    updateYear();

    loadNews();

    /*
     * Check the API every five minutes.
     *
     * This does not reload the browser.
     */

    setInterval(
      function() {

        loadNews(false);

      },
      REFRESH_INTERVAL
    );

  }
);


/* ==========================================================
   EVENT LISTENERS
   ========================================================== */

function setupEventListeners() {

  /*
   * All category controls.
   */

  document
    .querySelectorAll('[data-category]')
    .forEach(
      function(button) {

        button.addEventListener(
          'click',
          function() {

            setCategory(
              button.dataset.category
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

        loadNews(true);

      }
    );


  /*
   * Hero refresh.
   */

  elements.heroRefreshButton
    .addEventListener(
      'click',
      function() {

        loadNews(true);

      }
    );


  /*
   * Retry.
   */

  elements.retryButton
    .addEventListener(
      'click',
      function() {

        loadNews(true);

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


  /*
   * Language.
   */

  elements.languageSelect
    .addEventListener(
      'change',
      function() {

        setLanguage(
          this.value
        );

      }
    );


  /*
   * Audio controls.
   */

  elements.audioPlay
    .addEventListener(
      'click',
      resumeSpeech
    );


  elements.audioPause
    .addEventListener(
      'click',
      pauseSpeech
    );


  elements.audioStop
    .addEventListener(
      'click',
      stopSpeech
    );


  /*
   * Browser speech ended.
   */

  if (
    'speechSynthesis' in window
  ) {

    window.speechSynthesis.addEventListener(
      'end',
      handleSpeechEnd
    );

  }

}


/* ==========================================================
   LOAD NEWS
   ========================================================== */

async function loadNews(
  manualRefresh = false
) {

  if (isLoading) {
    return;
  }


  if (
    !API_URL ||
    API_URL.includes('PASTE_YOUR')
  ) {

    showError(
      'Please add your Apps Script Web App URL to app.js.'
    );

    return;

  }


  isLoading = true;


  if (manualRefresh) {

    setRefreshLoading(true);

  }


  setFeedStatus(
    t('updating')
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


    if (!response.ok) {

      throw new Error(
        'API returned HTTP ' +
        response.status
      );

    }


    const data =
      await response.json();


    if (!data.success) {

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


    const incomingArticles =
      normalizeArticles(
        data.articles
      );


    /*
     * Detect new stories.
     */

    detectNewStories(
      incomingArticles
    );


    allArticles =
      incomingArticles;


    setFeedStatus(
      t('live')
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
      t('offline')
    );


    showError(
      error.message ||
      'Unable to load the latest news.'
    );


  } finally {

    isLoading = false;


    if (manualRefresh) {

      setRefreshLoading(false);

    }

  }

}


/* ==========================================================
   DETECT NEW STORIES
   ========================================================== */

function detectNewStories(
  articles
) {

  if (
    previousArticleIds.size === 0
  ) {

    previousArticleIds =
      new Set(
        articles.map(
          article => article.id
        )
      );

    return;

  }


  const newArticles =
    articles.filter(
      article =>
        article.id &&
        !previousArticleIds.has(
          article.id
        )
    );


  if (
    newArticles.length > 0
  ) {

    showNewStories(
      newArticles.length
    );

  }


  previousArticleIds =
    new Set(
      articles.map(
        article => article.id
      )
    );

}


/* ==========================================================
   NEW STORIES INDICATOR
   ========================================================== */

function showNewStories(
  count
) {

  if (
    !elements.newStoriesBadge
  ) {

    return;

  }


  elements.newStoriesBadge
    .textContent =
      count +
      ' ' +
      (
        count === 1
          ? t('story')
          : t('stories')
      ) +
      ' ' +
      t('newStories');


  elements.newStoriesBadge
    .classList.remove(
      'hidden'
    );


  setTimeout(
    function() {

      elements.newStoriesBadge
        .classList.add(
          'hidden'
        );

    },
    10000
  );

}


/* ==========================================================
   NORMALIZE ARTICLES
   ========================================================== */

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
            String(
              article.id || ''
            ),

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


/* ==========================================================
   FILTER + RENDER
   ========================================================== */

function renderFilteredNews() {

  const search =
    elements.searchInput
      .value
      .trim()
      .toLowerCase();


  const filtered =
    allArticles.filter(
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


        const searchable = (

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


/* ==========================================================
   FEATURED ARTICLE
   ========================================================== */

function renderFeatured(
  article
) {

  const image =
    getImage(article);


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


          <div class="article-actions">

            <button
              class="listen-button"
              data-speak-id="${escapeAttribute(
                article.id
              )}"
              onclick="startNarrationById(this.dataset.speakId)"
            >
              🔊
              ${escapeHTML(
                t('listen')
              )}
            </button>


            <a
              class="read-link"
              href="${escapeAttribute(
                article.article_url
              )}"
              target="_blank"
              rel="noopener noreferrer"
            >
              ${escapeHTML(
                t('readStory')
              )}
              →
            </a>

          </div>

        </div>

      </article>

  `;

}


/* ==========================================================
   NEWS GRID
   ========================================================== */

function renderNewsGrid(
  articles
) {

  if (
    articles.length === 0
  ) {

    elements.newsGrid.innerHTML =
      '';

    return;

  }


  elements.newsGrid.innerHTML =
    articles
      .map(
        createArticleCard
      )
      .join('');

}


/* ==========================================================
   ARTICLE CARD
   ========================================================== */

function createArticleCard(
  article
) {

  const image =
    getImage(article);


  return `

    <article class="news-card">

      <div class="card-image">

        <img
          src="${escapeAttribute(image)}"
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


          <div class="card-actions">

            <button
              class="listen-button"
              data-speak-id="${escapeAttribute(
                article.id
              )}"
              onclick="startNarrationById(this.dataset.speakId)"
              title="${escapeAttribute(
                t('listen')
              )}"
            >
              🔊
            </button>


            <a
              class="card-link"
              href="${escapeAttribute(
                article.article_url
              )}"
              target="_blank"
              rel="noopener noreferrer"
            >
              ${escapeHTML(
                t('read')
              )}
              →
            </a>

          </div>

        </div>

      </div>

    </article>

  `;

}


/* ==========================================================
   CATEGORY
   ========================================================== */

function setCategory(
  category
) {

  currentCategory =
    category;


  document
    .querySelectorAll(
      '[data-category]'
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


  /*
   * Smoothly return to the news section
   * when a topic is selected.
   */

  const newsSection =
    document.querySelector(
      '.news-section'
    );


  if (
    newsSection &&
    window.innerWidth < 1000
  ) {

    newsSection.scrollIntoView({
      behavior: 'smooth',
      block: 'start'
    });

  }

}


/* ==========================================================
   CATEGORY COUNTS
   ========================================================== */

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


/* ==========================================================
   ARTICLE COUNT
   ========================================================== */

function updateArticleCount(
  count
) {

  elements.articleCount
    .textContent =
      count +
      ' ' +
      (
        count === 1
          ? t('story')
          : t('stories')
      );

}


/* ==========================================================
   IMAGE
   ========================================================== */

function getImage(
  article
) {

  if (
    article.image_url &&
    isValidImageURL(
      article.image_url
    )
  ) {

    return article.image_url;

  }


  return createPlaceholder(
    article.category
  );

}


/* ==========================================================
   IMAGE VALIDATION
   ========================================================== */

function isValidImageURL(
  url
) {

  try {

    const parsed =
      new URL(url);


    return (
      parsed.protocol === 'https:' ||
      parsed.protocol === 'http:'
    );

  } catch {

    return false;

  }

}


/* ==========================================================
   PLACEHOLDER IMAGE
   ========================================================== */

function createPlaceholder(
  category = 'TechPulse'
) {

  const safeCategory =
    escapeHTML(
      category
    );


  return (
    'data:image/svg+xml;charset=UTF-8,' +
    encodeURIComponent(`

      <svg
        xmlns="http://www.w3.org/2000/svg"
        width="800"
        height="450"
        viewBox="0 0 800 450"
      >

        <defs>

          <linearGradient
            id="g"
            x1="0"
            y1="0"
            x2="1"
            y2="1"
          >

            <stop
              offset="0%"
              stop-color="#101828"
            />

            <stop
              offset="100%"
              stop-color="#252f70"
            />

          </linearGradient>

        </defs>


        <rect
          width="800"
          height="450"
          fill="url(#g)"
        />


        <text
          x="400"
          y="205"
          text-anchor="middle"
          fill="#ffffff"
          font-family="Arial"
          font-size="42"
          font-weight="700"
        >
          TECHPULSE
        </text>


        <text
          x="400"
          y="255"
          text-anchor="middle"
          fill="#c7ccef"
          font-family="Arial"
          font-size="20"
        >
          ${safeCategory}
        </text>

      </svg>

    `)
  );

}


/* ==========================================================
   RELATIVE TIME
   ========================================================== */

function formatRelativeTime(
  dateValue
) {

  if (!dateValue) {

    return t('recently');

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

    return t('recently');

  }


  const now =
    new Date();


  const difference =
    now.getTime() -
    date.getTime();


  if (
    difference < 0
  ) {

    return t('justNow');

  }


  const minutes =
    Math.floor(
      difference / 60000
    );


  if (
    minutes < 1
  ) {

    return t('justNow');

  }


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


/* ==========================================================
   API UPDATED TIME
   ========================================================== */

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


/* ==========================================================
   FEED STATUS
   ========================================================== */

function setFeedStatus(
  status
) {

  elements.feedStatus
    .textContent =
      status;

}


/* ==========================================================
   REFRESH BUTTON
   ========================================================== */

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


/* ==========================================================
   ERROR
   ========================================================== */

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


/* ==========================================================
   THEME
   ========================================================== */

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


/* ==========================================================
   LANGUAGE
   ========================================================== */

function initializeLanguage() {

  if (
    !translations[
      selectedLanguage
    ]
  ) {

    selectedLanguage =
      'en';

  }


  elements.languageSelect
    .value =
      selectedLanguage;


  applyTranslations();

}


function setLanguage(
  language
) {

  if (
    !translations[language]
  ) {

    language =
      'en';

  }


  selectedLanguage =
    language;


  localStorage.setItem(
    'techpulse-language',
    language
  );


  applyTranslations();


  /*
   * Re-render dynamic article controls.
   */

  renderFilteredNews();

  updateCategoryCounts();

}


function applyTranslations() {

  const dictionary =
    translations[
      selectedLanguage
    ] || translations.en;


  /*
   * Regular text.
   */

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


  /*
   * Input placeholders.
   */

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


  document.documentElement.lang =
    selectedLanguage;

}


/* ==========================================================
   TRANSLATION HELPER
   ========================================================== */

function t(
  key
) {

  return (
    translations[
      selectedLanguage
    ]?.[key] ||
    translations.en[key] ||
    key
  );

}


/* ==========================================================
   SPEECH / NARRATION
   ========================================================== */

function startNarrationById(
  articleId
) {

  const article =
    allArticles.find(
      item =>
        item.id ===
        articleId
    );


  if (!article) {

    return;

  }


  startNarration(
    article
  );

}


function startNarration(
  article
) {

  if (
    !('speechSynthesis' in window)
  ) {

    alert(
      'Speech narration is not supported by this browser.'
    );

    return;

  }


  stopSpeech();


  currentSpeechArticle =
    article;


  speechQueue = [];


  /*
   * Narrate title first.
   */

  speechQueue.push(
    article.title
  );


  /*
   * Then summary.
   */

  if (
    article.summary
  ) {

    speechQueue.push(
      article.summary
    );

  }


  speechIndex =
    0;

  speechPaused =
    false;


  elements.audioBar
    .classList.remove(
      'hidden'
    );


  elements.audioTitle
    .textContent =
      article.title;


  speakCurrentSegment();

}


function speakCurrentSegment() {

  if (
    speechIndex >=
    speechQueue.length
  ) {

    finishSpeech();

    return;

  }


  const text =
    speechQueue[
      speechIndex
    ];


  const utterance =
    new SpeechSynthesisUtterance(
      text
    );


  utterance.lang =
    getSpeechLanguage(
      selectedLanguage
    );


  utterance.rate =
    0.95;


  utterance.pitch =
    1;


  utterance.volume =
    1;


  /*
   * Prefer a matching voice when
   * the browser provides one.
   */

  const voices =
    window.speechSynthesis
      .getVoices();


  const preferredVoice =
    voices.find(
      voice =>
        voice.lang
          .toLowerCase()
          .startsWith(
            utterance.lang
              .split('-')[0]
          )
    );


  if (
    preferredVoice
  ) {

    utterance.voice =
      preferredVoice;

  }


  utterance.onstart =
    function() {

      elements.audioStatus
        .textContent =
          t('speaking');

    };


  utterance.onend =
    function() {

      speechIndex++;

      speakCurrentSegment();

    };


  utterance.onerror =
    function(event) {

      console.warn(
        'Speech synthesis error:',
        event
      );

      finishSpeech();

    };


  window.speechSynthesis
    .speak(
      utterance
    );

}


function pauseSpeech() {

  if (
    !('speechSynthesis' in window)
  ) {

    return;

  }


  if (
    window.speechSynthesis
      .speaking
  ) {

    window.speechSynthesis
      .pause();

    speechPaused =
      true;


    elements.audioStatus
      .textContent =
        t('paused');

  }

}


function resumeSpeech() {

  if (
    !('speechSynthesis' in window)
  ) {

    return;

  }


  if (
    window.speechSynthesis
      .paused
  ) {

    window.speechSynthesis
      .resume();

    speechPaused =
      false;


    elements.audioStatus
      .textContent =
        t('speaking');

    return;

  }


  if (
    currentSpeechArticle
  ) {

    startNarration(
      currentSpeechArticle
    );

  }

}


function stopSpeech() {

  if (
    'speechSynthesis' in window
  ) {

    window.speechSynthesis
      .cancel();

  }


  speechQueue = [];

  speechIndex = 0;

  speechPaused = false;


  if (
    elements.audioBar
  ) {

    elements.audioBar
      .classList.add(
        'hidden'
      );

  }


  document
    .querySelectorAll(
      '.listen-button'
    )
    .forEach(
      function(button) {

        button.classList.remove(
          'playing'
        );

      }
    );

}


function finishSpeech() {

  elements.audioStatus
    .textContent =
      t('ready');


  document
    .querySelectorAll(
      '.listen-button'
    )
    .forEach(
      function(button) {

        button.classList.remove(
          'playing'
        );

      }
    );

}


function handleSpeechEnd() {

  /*
   * Individual utterance handlers
   * control the queue.
   */

}


/* ==========================================================
   SPEECH LANGUAGE
   ========================================================== */

function getSpeechLanguage(
  language
) {

  const languages = {

    en: 'en-US',

    hi: 'hi-IN',

    te: 'te-IN',

    ta: 'ta-IN',

    kn: 'kn-IN'

  };


  return (
    languages[language] ||
    'en-US'
  );

}


/* ==========================================================
   YEAR
   ========================================================== */

function updateYear() {

  elements.currentYear
    .textContent =
      new Date()
        .getFullYear();

}


/* ==========================================================
   HTML SAFETY
   ========================================================== */

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


/* ==========================================================
   ATTRIBUTE SAFETY
   ========================================================== */

function escapeAttribute(
  value
) {

  return escapeHTML(
    value
  );

}
