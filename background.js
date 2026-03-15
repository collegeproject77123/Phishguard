// background.js (MV3 service worker, "type": "module")

const DEBUG = true; // Enable for debugging ML API calls
const log = (...args) => DEBUG && console.log('[PG]', ...args);

// ML API configuration
const ML_API_URL = 'https://phishguard-production-f818.up.railway.app/predict';
const ML_ENABLED = true; // Set to false to disable ML predictions

// Backend dataset API configuration
const DATASETS_API_URL = 'https://phishguard-production-f818.up.railway.app/api/datasets';

// Draw circular icon with OffscreenCanvas. We return 16/32/48 for DPI variants.
async function drawIcon(hex, size) {
  const c = new OffscreenCanvas(size, size);
  const ctx = c.getContext('2d');

  ctx.clearRect(0, 0, size, size);

  // drop shadow
  ctx.beginPath();
  ctx.arc(size / 2, size / 2 + size * 0.08, size * 0.42, 0, Math.PI * 2);
  ctx.fillStyle = 'rgba(0,0,0,0.20)';
  ctx.fill();

  // white ring for contrast on dark toolbars
  ctx.beginPath();
  ctx.arc(size / 2, size / 2, size * 0.44, 0, Math.PI * 2);
  ctx.fillStyle = '#ffffff';
  ctx.fill();

  // main disc
  ctx.beginPath();
  ctx.arc(size / 2, size / 2, size * 0.38, 0, Math.PI * 2);
  ctx.fillStyle = hex;
  ctx.fill();

  return ctx.getImageData(0, 0, size, size);
}

const ICON_CACHE = new Map();
async function getIconImageData(hex) {
  if (ICON_CACHE.has(hex)) return ICON_CACHE.get(hex);
  const img16 = await drawIcon(hex, 16);
  const img32 = await drawIcon(hex, 32);
  const img48 = await drawIcon(hex, 48);
  const set = { 16: img16, 32: img32, 48: img48 };
  ICON_CACHE.set(hex, set);
  return set;
}

async function setIconFor(tabId, label) {
  // Guard: ignore if tab no longer exists
  try {
    const t = await chrome.tabs.get(tabId);
    if (!t || t.id !== tabId) return;
  } catch {
    return;
  }
  const color =
    label === 'safe' ? '#2ecc71' :        // green
      label === 'suspicious' ? '#ff9800' :        // yellow
        label === 'malicious' ? '#e74c3c' :        // red
          '#95a5a6';         // unknown → gray

  const imageData = await getIconImageData(color);
  chrome.action.setIcon({ tabId, imageData }, () => {
    if (chrome.runtime.lastError) log('setIcon error:', chrome.runtime.lastError.message);
  });
  chrome.action.setBadgeText({ tabId, text: '' });

  // Set tooltip so you can verify what the worker classified
  chrome.action.setTitle({ tabId, title: `PhishGuard: ${label}` });
}

// Datasets
let SAFE_DATASET = [];
let MALICIOUS_DATASET = ['phishy-demo.test', 'fraud-demo.test', 'secure-verify.test']; // Fallbacks

async function syncDatasets() {
  try {
    const data = await chrome.storage.local.get(['safe_dataset', 'malicious_dataset']);
    if (data.safe_dataset) SAFE_DATASET = data.safe_dataset;
    if (data.malicious_dataset) MALICIOUS_DATASET = data.malicious_dataset;

    const res = await fetch(DATASETS_API_URL);
    if (res.ok) {
      const json = await res.json();
      SAFE_DATASET = json.safe_dataset || SAFE_DATASET;
      MALICIOUS_DATASET = json.malicious_dataset || MALICIOUS_DATASET;
      await chrome.storage.local.set({ 
        safe_dataset: SAFE_DATASET, 
        malicious_dataset: MALICIOUS_DATASET 
      });
      log('Synced datasets from backend.');
    }
  } catch (e) {
    log('Failed to sync datasets from backend, using cache.', e);
  }
}

syncDatasets();
chrome.alarms.create('syncDatasets', { periodInMinutes: 60 });
chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === 'syncDatasets') syncDatasets();
});

// Removed old bindings

function matchesDomain(hostname, domain) {
  if (!hostname || !domain) return false;
  if (hostname === domain) return true;
  return hostname.endsWith('.' + domain);
}

function collectReasons(u) {
  const host = u.hostname || '';
  const reasons = [];
  // Domain/hostname checks
  if (/^\d+\.\d+\.\d+\.\d+$/.test(host)) reasons.push('IP address used instead of domain');
  // Removed 'Many subdomains' check as it causes false positives

  if (/\bxn--/i.test(host)) reasons.push('Punycode domain detected');
  // Additional URL signals to align with popup
  if (u.protocol !== 'https:') reasons.push('No HTTPS detected');
  if (u.href.includes('@')) reasons.push('`@` symbol in URL');
  if (/login|verify|update|secure|account/i.test(host + u.pathname)) reasons.push('Suspicious keywords detected');
  return reasons;
}

async function queryMLAPI(url) {
  /**
   * Query the ML API for a prediction.
   * Returns: { suspicious: boolean, probability: number } or null on error
   */
  if (!ML_ENABLED) {
    log('ML API disabled');
    return null;
  }

  log('Querying ML API for:', url);

  try {
    const response = await fetch(ML_API_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url })
    });

    log('ML API response status:', response.status);

    if (!response.ok) {
      const errorText = await response.text();
      log('ML API error:', response.status, errorText);
      return null;
    }

    const data = await response.json();
    log('ML API result:', data);

    return {
      suspicious: data.suspicious || false,
      probability: data.probability || 0
    };
  } catch (error) {
    log('ML API request failed:', error.message, error.stack);
    return null; // Fail gracefully - fall back to URL heuristics
  }
}

function classifyQuick(url) {
  try {
    const u = new URL(url);
    const host = u.hostname || '';

    // Check safe dataset first - safe sites override suspicious patterns
    const isSafe = SAFE_DATASET.some(d => matchesDomain(host, d));
    if (isSafe) return { label: 'safe' };

    // Check malicious dataset second - known malicious sites are always flagged
    const inMaliciousDataset = MALICIOUS_DATASET.some(d => matchesDomain(host, d));
    if (inMaliciousDataset) {
      return { label: 'malicious' };
    }

    // If not safe and not explicitly malicious, then check for suspicious URL characteristics
    const reasons = collectReasons(u);
    const suspicious = reasons.length > 0;
    if (suspicious) {
      return { label: 'suspicious' };
    }

    return { label: 'unknown' };
  } catch {
    return { label: 'suspicious' };
  }
}

async function classifyWithML(url) {
  /**
   * Hybrid classification: URL heuristics + ML prediction.
   * For suspicious/unknown sites, we query ML API to get webpage-based prediction.
   */
  const quickResult = classifyQuick(url);

  log('Quick classification result:', quickResult.label);

  // Skip ML for browser internal URLs (edge://, chrome://, etc.) - can't fetch them
  if (url.startsWith('edge://') || url.startsWith('chrome://') || url.startsWith('about:')) {
    log('Browser internal URL, skipping ML');
    return quickResult;
  }

  // If URL heuristics say it's safe or malicious, trust that (no ML needed)
  if (quickResult.label === 'safe' || quickResult.label === 'malicious') {
    log('Trusting URL heuristic result (safe/malicious), skipping ML');
    return quickResult;
  }

  // For suspicious or unknown, check ML API to add webpage content analysis
  if (quickResult.label === 'suspicious' || quickResult.label === 'unknown') {
    const mlResult = await queryMLAPI(url);

    if (mlResult) {
      log('ML result received:', mlResult);

      // ML alone can trigger suspicious flag - if ML says suspicious (probability >= 0.8), mark as suspicious
      // This allows ML to upgrade unknown -> suspicious OR keep suspicious -> suspicious
      // Both URL heuristics OR ML can mark as suspicious (either or both)
      if (mlResult.suspicious && mlResult.probability >= 0.8) {
        log('ML confirms suspicious (probability >= 0.8), marking as suspicious');
        return { label: 'suspicious', mlProbability: mlResult.probability };
      }

      // ML says it's safe with low probability (< 0.3)
      // Only downgrade from 'suspicious' to 'unknown' if ML strongly says safe
      // Don't downgrade from 'unknown' since that would require explicit safe detection
      if (!mlResult.suspicious && mlResult.probability < 0.3) {
        if (quickResult.label === 'suspicious') {
          log('ML says safe with low probability, downgrading suspicious -> unknown');
          return { label: 'unknown', mlProbability: mlResult.probability };
        }
        // If already 'unknown', ML confirms it's likely safe, but keep as 'unknown'
      }

      log('ML result in uncertain zone, keeping original classification');
    } else {
      log('ML API unavailable or failed, using URL heuristics only');
    }
  }

  return quickResult;
}

const lastLabelByTab = new Map();

async function updateTab(tabId, url, force = false) {
  if (!tabId || !url) return;

  // Use hybrid classification (URL heuristics + ML)
  const { label: quickLabel } = await classifyWithML(url);

  // Whitelist or SAFE_DATASET override (blacklist removed per new rules)
  let effectiveLabel = quickLabel;
  try {
    const u = new URL(url);
    const host = u.hostname || '';

    const { whitelist = [] } = await chrome.storage.local.get(['whitelist']);
    const matchesDomain = (hostname, domain) => {
      if (!hostname || !domain) return false;
      if (hostname === domain) return true;
      return hostname.endsWith('.' + domain);
    };
    let isWhite = whitelist.some(d => matchesDomain(host, d));
    // Also check SAFE_DATASET (from classifier.js, should be global)
    if (!isWhite && typeof self !== 'undefined' && self.SAFE_DATASET) {
      isWhite = self.SAFE_DATASET.some(d => matchesDomain(host, d));
    }
    if (isWhite) effectiveLabel = 'safe';
  } catch { }
  // Verify tab still exists before attempting updates
  try {
    const t = await chrome.tabs.get(tabId);
    if (!t) return;
  } catch {
    return;
  }
  if (force || lastLabelByTab.get(tabId) !== effectiveLabel) {
    log('update tab', tabId, effectiveLabel, url);
    await setIconFor(tabId, effectiveLabel);
    lastLabelByTab.set(tabId, effectiveLabel);
  }
  // Inject in-page UI for http/https pages
  if (/^https?:/i.test(url)) {
    try {
      const t2 = await chrome.tabs.get(tabId);
      if (!t2) return;
      if (effectiveLabel === 'malicious') {
        await chrome.scripting.executeScript({ target: { tabId }, files: ['content.js'] });
      } else if (effectiveLabel === 'suspicious') {
        await chrome.scripting.executeScript({ target: { tabId }, files: ['content_suspicious.js'] });
      }
    } catch { }
  }
}

// Initialize all open tabs at startup / reload
async function initAll() {
  const tabs = await chrome.tabs.query({});
  for (const t of tabs) await updateTab(t.id, t.url || '', true);
  log('init complete');
}
initAll();
chrome.runtime.onInstalled.addListener(initAll);
chrome.runtime.onStartup.addListener(initAll);

// Cover ALL navigation modes:
chrome.tabs.onCreated.addListener(t => updateTab(t.id, t.url || '', true));
chrome.tabs.onActivated.addListener(async ({ tabId }) => {
  const t = await chrome.tabs.get(tabId); updateTab(tabId, t?.url || '', true);
});
chrome.tabs.onUpdated.addListener((tabId, info, tab) => {
  if (info.url) updateTab(tabId, info.url);                         // URL changed
  if (info.status === 'loading') updateTab(tabId, tab?.url || '', true);  // refresh started
  if (info.status === 'complete') updateTab(tabId, tab?.url || '', true); // refresh finished
});
// Removed webNavigation listeners due to compatibility issues; tabs.* events above cover updates

// Allow popup to force an icon
chrome.runtime.onMessage.addListener((msg, sender) => {
  if (msg.type === 'setIconByLabel' && msg.label) {
    const tabId = msg.tabId || sender?.tab?.id;
    if (!tabId) return;
    // Validate tab before attempting to set icon
    chrome.tabs.get(tabId, (t) => {
      if (chrome.runtime.lastError || !t) return;
      setIconFor(tabId, msg.label);
    });
  } else if (msg.type === 'pg_close_tab') {
    const tabId = sender?.tab?.id;
    if (!tabId) return;
    try { chrome.tabs.remove(tabId); } catch { }
  } else if (msg.type === 'pg_force_update_tab' && msg.tabId) {
    chrome.tabs.get(msg.tabId, (t) => {
      if (chrome.runtime.lastError || !t) return;
      updateTab(msg.tabId, t.url || '', true);
    });
  }
});
