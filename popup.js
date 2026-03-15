// popup.js

// ML API configuration (for popup to query ML predictions)
const ML_API_URL = 'http://127.0.0.1:5000/predict';
const REPORT_API_URL = 'http://127.0.0.1:5000/report';
const ML_ENABLED = true; // Set to false to disable ML predictions

async function queryMLAPI(url) {
  /**
   * Query the ML API for a prediction.
   * Returns: { suspicious: boolean, probability: number } or null on error
   */
  if (!ML_ENABLED) {
    return null;
  }
  
  try {
    const response = await fetch(ML_API_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url })
    });
    
    if (!response.ok) {
      return null;
    }
    
    const data = await response.json();
    
    return {
      suspicious: data.suspicious || false,
      probability: data.probability || 0
    };
  } catch (error) {
    // Fail gracefully - fall back to URL heuristics only
    return null;
  }
}

async function getActiveTab() {
  const [tab] = await chrome.tabs.query({ active: true, lastFocusedWindow: true });
  return tab;
}

function setUI(state) {
  const app = document.getElementById('app');
  app.classList.remove('state-trusted', 'state-susp', 'state-mal', 'state-neutral');

  const badge = document.getElementById('badge');
  const message = document.getElementById('message');
  const reasonsUl = document.getElementById('reasons');
  reasonsUl.innerHTML = '';

  switch (state.label) {
    case 'safe':
      app.classList.add('state-trusted');
      badge.textContent = 'Safe Site';
      message.textContent = 'This website is known to be safe.';
      break;
    case 'suspicious':
      app.classList.add('state-susp');
      badge.textContent = 'Suspicious Site';
      if (state.mlConfirmed && state.mlProbability) {
        const confidence = Math.round(state.mlProbability * 100);
        message.textContent = `Proceed with caution — Machine Learning analysis indicates this site is suspicious (${confidence}% confidence).`;
      } else {
        message.textContent = 'Proceed with caution — unusual patterns found.';
      }
      break;
    case 'malicious':
      app.classList.add('state-mal');
      badge.textContent = 'Malicious Site';
      message.textContent = 'Warning! This site is a known phishing site.';
      break;
    case 'unknown':
      app.classList.add('state-neutral');
      badge.textContent = 'Unknown';
      message.textContent = 'No issues detected, but not on the known-safe list.';
      break;
    default:
      app.classList.add('state-neutral');
      badge.textContent = 'Unknown';
      message.textContent = 'Unable to classify.';
  }

  (state.reasons || []).forEach(r => {
    const li = document.createElement('li');
    li.textContent = r;
    reasonsUl.appendChild(li);
  });

  const danger = state.label === 'suspicious' || state.label === 'malicious';
  document.getElementById('proceed').style.display = danger ? 'inline-block' : 'none';
  document.getElementById('goback').style.display  = danger ? 'inline-block' : 'none';
  document.getElementById('close').style.display   = state.label === 'malicious' ? 'inline-block' : 'none';
  document.getElementById('report').style.display = state.label === 'malicious' ? 'none' : 'inline-block';
  document.getElementById('trust').style.display = (state.label === 'malicious' || state.label === 'safe') ? 'none' : 'inline-block';
}

function nudgeBackgroundToSetIcon(label, tabId) {
  // Background listens for this and paints the per-tab icon color
  chrome.runtime.sendMessage({ type: 'setIconByLabel', label, tabId });
}

document.addEventListener('DOMContentLoaded', async () => {
  const tab = await getActiveTab();
  const urlText = tab?.url || '';
  document.getElementById('url').textContent = urlText;

  // Theme setup
  const root = document.documentElement;
  const { theme = 'light' } = await chrome.storage.local.get(['theme']);
  root.setAttribute('data-theme', theme);
  const themeBtn = document.getElementById('themeToggle');
  if (themeBtn) {
    themeBtn.textContent = theme === 'dark' ? 'Light Mode' : 'Dark Mode';
    themeBtn.onclick = async () => {
      const next = (root.getAttribute('data-theme') === 'dark') ? 'light' : 'dark';
      root.setAttribute('data-theme', next);
      themeBtn.textContent = next === 'dark' ? 'Light Mode' : 'Dark Mode';
      await chrome.storage.local.set({ theme: next });
      // Broadcast so content scripts can adopt theme on next inject
      chrome.runtime.sendMessage({ type: 'pg_theme_changed', theme: next });
    };
  }

  if (!tab || !urlText) {
    setUI({ label: 'unknown', reasons: ['No active tab URL detected'] });
    return;
  }

  // Instant local classification (from classifier.js) with whitelist override
  let currentState;
  let isWhite = false;
  try {
    const u = new URL(urlText);
    const host = u.hostname || '';
    const storageData = await chrome.storage.local.get(['whitelist', 'safe_dataset', 'malicious_dataset']);
    const whitelist = storageData.whitelist || [];
    const safeDataset = storageData.safe_dataset || [];
    const maliciousDataset = storageData.malicious_dataset || [];

    // Instant local classification with injected datasets
    currentState = window.classifyUrlQuick(urlText, safeDataset, maliciousDataset);

    const matchesDomain = (hostname, domain) => {
      if (!hostname || !domain) return false;
      if (hostname === domain) return true;
      return hostname.endsWith('.' + domain);
    };
    isWhite = whitelist.some(d => matchesDomain(host, d));
    // Also check SAFE_DATASET from classifier.js
    if (!isWhite && safeDataset) {
      isWhite = safeDataset.some(d => matchesDomain(host, d));
    }
    if (isWhite) {
      // Remove any duplicate or old reason
      let reasons = (currentState.reasons || []).filter(r => !/Domain is whitelisted or in SAFE_DATASET|Domain is whitelisted or in safe dataset/i.test(r));
      reasons.push('Domain is whitelisted or in safe dataset');
      currentState = { ...currentState, label: 'safe', reasons };
    }
  } catch {}

  // If whitelisted or in SAFE_DATASET, always force safe (even if ML runs first)
  if (isWhite) {
    // Remove any duplicate or old reason
    let reasons = (currentState.reasons || []).filter(r => !/Domain is whitelisted or in SAFE_DATASET|Domain is whitelisted or in safe dataset/i.test(r));
    reasons.push('Domain is whitelisted or in safe dataset');
    currentState = { ...currentState, label: 'safe', reasons };
  } else if (currentState.label === 'suspicious' || currentState.label === 'unknown') {
    // Skip ML for browser internal URLs
    if (!urlText.startsWith('edge://') && !urlText.startsWith('chrome://') && !urlText.startsWith('about:')) {
      const mlResult = await queryMLAPI(urlText);
      if (mlResult && mlResult.suspicious && mlResult.probability >= 0.8) {
        // ML confirms suspicious - upgrade to suspicious and add to reasons
        const mlConfidence = Math.round(mlResult.probability * 100);
        const mlReason = `Machine Learning model detected suspicious characteristics (${mlConfidence}% confidence)`;
        currentState = {
          ...currentState,
          label: 'suspicious',
          reasons: [...(currentState.reasons || []), mlReason],
          mlProbability: mlResult.probability,
          mlConfirmed: true
        };
      }
    }
  }

  setUI(currentState);
  nudgeBackgroundToSetIcon(currentState.label, tab.id);

  // Backend prediction
  // try {
  //   const res = await fetch('https://your-ml-api/predict', {
  //     method: 'POST',
  //     headers: { 'Content-Type': 'application/json' },
  //     body: JSON.stringify({ url: urlText })
  //   });
  //   if (res.ok) {
  //     const data = await res.json(); // { label, score, reasons: [] }
  //     currentState = data;
  //     setUI(currentState);
  //     nudgeBackgroundToSetIcon(currentState.label, tab.id);
  //   }
  // } catch (e) {
  //   console.warn('Backend prediction failed; using quick result only.', e);
  // }

  // Buttons
  document.getElementById('goback').onclick = () => chrome.tabs.goBack(tab.id);
  document.getElementById('proceed').onclick = () => window.close();
  document.getElementById('close').onclick = async () => {
    try { await chrome.tabs.remove(tab.id); } catch {}
    window.close();
  };
  document.getElementById('report').onclick = async () => {
    const report = { 
      url: urlText, 
      label: currentState.label, 
      reasons: currentState.reasons || [] 
    };
    // Store in browser storage (backup)
    const prev = (await chrome.storage.local.get('reports')).reports || [];
    prev.push({ ...report, ts: Date.now() });
    await chrome.storage.local.set({ reports: prev });
    // Send to backend to save in reports.md file
    try {
      const response = await fetch(REPORT_API_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(report)
      });
      if (response.ok) {
        const result = await response.json();
        alert('Thanks! Your report was saved to reports.md file.');
      } else {
        alert('Thanks! Your report was recorded locally. (Backend not available - reports.md not updated)');
      }
    } catch (error) {
      console.warn('Failed to send report to backend:', error);
      alert('Thanks! Your report was recorded locally. (Backend not available - reports.md not updated)');
    }
  };

  // Trust Site button: add to whitelist and update UI/icon immediately
  document.getElementById('trust').onclick = async () => {
    try {
      const u = new URL(urlText);
      const host = u.hostname || '';
      let { whitelist = [] } = await chrome.storage.local.get(['whitelist']);
      if (!whitelist.includes(host)) {
        whitelist.push(host);
        await chrome.storage.local.set({ whitelist });
      }
      // Update UI and icon immediately
      currentState = { ...currentState, label: 'safe', reasons: [...(currentState.reasons||[]), 'Domain is whitelisted'] };
      setUI(currentState);
      nudgeBackgroundToSetIcon('safe', tab.id);
      // Also trigger background to re-run updateTab for this tab (ensures icon stays in sync after navigation)
      chrome.runtime.sendMessage({ type: 'pg_force_update_tab', tabId: tab.id });
    } catch (e) {
      alert('Could not trust this site.');
    }
  };

  // Optional tiny debug helper (only wires up if you added a button with this id in popup.html)
  const dbg = document.getElementById('debugYellow');
  if (dbg) {
    dbg.onclick = () => nudgeBackgroundToSetIcon('suspicious', tab.id);
  }
});
