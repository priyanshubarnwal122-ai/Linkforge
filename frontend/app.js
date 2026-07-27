/* ==========================================================================
   LinkForge Enterprise App JS
   ========================================================================== */

const API_BASE = '/api/v1';
let userToken = localStorage.getItem('access_token');
let userLinks = [];

let recommendDebounceTimer = null;

document.addEventListener('DOMContentLoaded', () => {
  // Handle OAuth hash callback token
  if (window.location.hash && window.location.hash.includes('access_token=')) {
    const params = new URLSearchParams(window.location.hash.substring(1));
    const token = params.get('access_token');
    if (token) {
      localStorage.setItem('access_token', token);
      userToken = token;
      window.location.hash = '';
      alert('Logged in via Google OAuth successfully!');
    }
  }

  checkAuth();
  loadUserLinks();
  setupUrlInputListener();
  
  if (window.location.search.includes('oauth_notice=1')) {
    alert('Google OAuth requires a real GOOGLE_CLIENT_ID in your .env file. Please use the Email & Password Sign In tab for instant login!');
    openAuthModal('login');
  }
});

function setupUrlInputListener() {
  const targetUrlInput = document.getElementById('targetUrl');
  if (!targetUrlInput) return;

  targetUrlInput.addEventListener('input', (e) => {
    clearTimeout(recommendDebounceTimer);
    const url = e.target.value.trim();
    if (url.length < 8 || (!url.includes('.') && !url.includes('http'))) {
      document.getElementById('aiRecommendationBar').style.display = 'none';
      return;
    }

    recommendDebounceTimer = setTimeout(() => {
      fetchAliasRecommendations(url);
    }, 400);
  });
}

async function fetchAliasRecommendations(url) {
  try {
    const res = await fetch(`${API_BASE}/links/recommend-alias`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url })
    });

    if (!res.ok) return;
    const data = await res.json();
    renderAIRecommendations(data);
  } catch (err) {
    console.error('Failed to fetch recommendations:', err);
  }
}

function renderAIRecommendations(data) {
  const bar = document.getElementById('aiRecommendationBar');
  const badge = document.getElementById('domainTrustBadge');
  const chipsContainer = document.getElementById('suggestionChips');

  if (!data || !data.recommendations || data.recommendations.length === 0) {
    bar.style.display = 'none';
    return;
  }

  badge.textContent = `🛡️ ${data.trust_score}% Trust • ${data.category}`;
  
  chipsContainer.innerHTML = data.recommendations.map(opt => `
    <button type="button" class="chip ${opt.available ? '' : 'disabled'}" onclick="selectSuggestedAlias('${opt.alias}', this)">
      <span>✨ /${opt.alias}</span>
      ${opt.available ? '' : '<small style="opacity:0.6;">(taken)</small>'}
    </button>
  `).join('');

  bar.style.display = 'flex';
}

function selectSuggestedAlias(alias, chipElement) {
  document.getElementById('customAlias').value = alias;
  
  document.querySelectorAll('.chip').forEach(c => c.classList.remove('selected'));
  chipElement.classList.add('selected');

  const panel = document.getElementById('advancedPanel');
  if (!panel.classList.contains('open')) {
    panel.classList.add('open');
  }

  document.getElementById('customAlias').focus();
}

function checkAuth() {
  const userControls = document.getElementById('userControls');
  if (userToken) {
    userControls.innerHTML = `
      <span class="security-badge" style="background:#e8f0fe; color:#1a73e8; border-color:#aecbfa;">
        Logged In
      </span>
      <button class="btn-secondary" onclick="handleLogout()">Logout</button>
    `;
  }
}

function openAuthModal(tab = 'login') {
  switchAuthTab(tab);
  document.getElementById('authModal').classList.add('open');
}

function switchAuthTab(tab) {
  const tabLogin = document.getElementById('tabLogin');
  const tabRegister = document.getElementById('tabRegister');
  const loginForm = document.getElementById('loginForm');
  const registerForm = document.getElementById('registerForm');
  const authModalTitle = document.getElementById('authModalTitle');

  if (tab === 'login') {
    tabLogin.classList.add('active');
    tabRegister.classList.remove('active');
    loginForm.style.display = 'block';
    registerForm.style.display = 'none';
    authModalTitle.textContent = 'Sign In to LinkForge';
  } else {
    tabRegister.classList.add('active');
    tabLogin.classList.remove('active');
    registerForm.style.display = 'block';
    loginForm.style.display = 'none';
    authModalTitle.textContent = 'Create LinkForge Account';
  }
}

function fillDemoAccount() {
  document.getElementById('loginEmail').value = 'testuser@example.com';
  document.getElementById('loginPassword').value = 'Password123!';
}

async function handleLoginSubmit(event) {
  event.preventDefault();
  const email = document.getElementById('loginEmail').value.trim();
  const password = document.getElementById('loginPassword').value.trim();

  try {
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });

    if (!res.ok) {
      const err = await res.json();
      const msg = err.error?.message || err.detail || 'Incorrect email or password.';
      alert(`Login failed: ${msg}\n\nFirst time here? Click the "Register" tab to create your account!`);
      return;
    }

    const data = await res.json();
    localStorage.setItem('access_token', data.access_token);
    userToken = data.access_token;
    closeModal('authModal');
    checkAuth();
    loadUserLinks();
  } catch (err) {
    alert(`Connection error: ${err.message}`);
  }
}

async function handleRegisterSubmit(event) {
  event.preventDefault();
  const username = document.getElementById('regUsername').value.trim();
  const email = document.getElementById('regEmail').value.trim();
  const password = document.getElementById('regPassword').value.trim();

  try {
    const res = await fetch(`${API_BASE}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, email, password })
    });

    if (!res.ok) {
      const err = await res.json();
      const msg = err.error?.message || err.detail || 'Failed to create account.';
      alert(`Registration failed: ${msg}`);
      return;
    }

    alert('Account created successfully! Signing in...');
    // Auto-login after registration
    const loginRes = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });
    if (loginRes.ok) {
      const data = await loginRes.json();
      localStorage.setItem('access_token', data.access_token);
      userToken = data.access_token;
      closeModal('authModal');
      checkAuth();
      loadUserLinks();
    }
  } catch (err) {
    alert(`Connection error: ${err.message}`);
  }
}

function handleGoogleLogin() {
  window.location.href = `${API_BASE}/auth/google/login`;
}

function handleLogout() {
  localStorage.removeItem('access_token');
  location.reload();
}

function toggleAdvanced() {
  const panel = document.getElementById('advancedPanel');
  panel.classList.toggle('open');
}

async function handleShorten(event) {
  event.preventDefault();
  
  if (!userToken) {
    alert('Please sign in or create an account first to shorten links!');
    openAuthModal('login');
    return;
  }

  let targetUrl = document.getElementById('targetUrl').value.trim();
  if (targetUrl && !targetUrl.startsWith('http://') && !targetUrl.startsWith('https://')) {
    targetUrl = 'https://' + targetUrl;
  }
  let customAlias = document.getElementById('customAlias').value.trim() || null;
  if (customAlias) {
    customAlias = customAlias.replace(/^\/+/, '').trim();
    if (!customAlias) customAlias = null;
  }
  const linkPassword = document.getElementById('linkPassword').value.trim() || null;
  const iosUrl = document.getElementById('iosUrl').value.trim() || null;
  const androidUrl = document.getElementById('androidUrl').value.trim() || null;
  const isOneTime = document.getElementById('isOneTime').checked;

  const payload = {
    original_url: targetUrl,
    custom_alias: customAlias,
    password: linkPassword,
    ios_url: iosUrl,
    android_url: androidUrl,
    is_one_time: isOneTime
  };

  try {
    const res = await fetch(`${API_BASE}/links/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${userToken}`
      },
      body: JSON.stringify(payload)
    });

    if (!res.ok) {
      const err = await res.json();
      const msg = err.error?.message || err.detail || 'Failed to create short link';
      alert(`Error: ${msg}`);
      return;
    }

    const data = await res.json();
    document.getElementById('shortenForm').reset();
    document.getElementById('advancedPanel').classList.remove('open');
    
    userLinks.unshift(data);
    renderTable();
  } catch (err) {
    alert(`Connection error: ${err.message}`);
  }
}

async function loadUserLinks() {
  if (!userToken) return;
  try {
    const res = await fetch(`${API_BASE}/links/`, {
      headers: { 'Authorization': `Bearer ${userToken}` }
    });
    if (res.ok) {
      userLinks = await res.json();
      renderTable();
    }
  } catch (err) {
    console.error('Failed to load links:', err);
  }
}

function renderTable() {
  const tbody = document.getElementById('linksTableBody');
  const countBadge = document.getElementById('linkCountBadge');
  
  countBadge.textContent = `${userLinks.length} Link${userLinks.length === 1 ? '' : 's'}`;

  if (userLinks.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="5" style="text-align: center; color: var(--text-subtle); padding: 2rem;">
          No links created yet. Paste a URL above to create your first short link!
        </td>
      </tr>
    `;
    return;
  }

  tbody.innerHTML = userLinks.map(link => {
    const displayAlias = link.custom_alias ? link.custom_alias : link.short_code;
    const shortUrl = link.short_url || `${window.location.origin}/s/${displayAlias}`;
    
    let featuresHTML = '';
    if (link.is_password_protected) featuresHTML += `<span class="badge badge-feature">🔒 Password</span>`;
    if (link.is_one_time) featuresHTML += `<span class="badge badge-feature">💣 One-Time</span>`;
    if (link.ios_url || link.android_url) featuresHTML += `<span class="badge badge-feature">📱 Device Route</span>`;
    if (!featuresHTML) featuresHTML = `<span style="color:var(--text-subtle);">-</span>`;

    return `
      <tr>
        <td>
          <a href="${shortUrl}" target="_blank" class="link-code">${displayAlias}</a>
        </td>
        <td>
          <div class="link-original" title="${link.original_url}">${link.original_url}</div>
        </td>
        <td>${featuresHTML}</td>
        <td><strong>${link.click_count || 0}</strong></td>
        <td>
          <div class="action-buttons">
            <button class="btn-secondary" onclick="copyToClipboard('${shortUrl}', this)">Copy</button>
            <button class="btn-secondary" onclick="showQR('${link.id}')">QR Code</button>
            <button class="btn-secondary" onclick="showAnalytics('${link.id}')">Stats</button>
          </div>
        </td>
      </tr>
    `;
  }).join('');
}

function copyToClipboard(text, btnElement) {
  navigator.clipboard.writeText(text).then(() => {
    const origText = btnElement.textContent;
    btnElement.textContent = 'Copied!';
    btnElement.style.borderColor = '#10b981';
    btnElement.style.color = '#10b981';
    setTimeout(() => {
      btnElement.textContent = origText;
      btnElement.style.borderColor = '';
      btnElement.style.color = '';
    }, 2000);
  });
}

function showQR(linkId) {
  const qrUrl = `${API_BASE}/links/${linkId}/qr`;
  document.getElementById('qrImage').src = qrUrl;
  document.getElementById('qrDownloadBtn').href = qrUrl;
  document.getElementById('qrModal').classList.add('open');
}

async function showAnalytics(linkId) {
  document.getElementById('totalClicks').textContent = '...';
  document.getElementById('analyticsDetails').textContent = 'Loading click insights...';
  document.getElementById('analyticsModal').classList.add('open');

  try {
    const res = await fetch(`${API_BASE}/links/${linkId}/stats`);
    if (res.ok) {
      const data = await res.json();
      document.getElementById('totalClicks').textContent = data.total_clicks || 0;
      
      const topDevice = data.top_devices && data.top_devices.length > 0 ? data.top_devices[0].device : 'Desktop';
      document.getElementById('topDevice').textContent = topDevice;

      document.getElementById('analyticsDetails').innerHTML = `
        <p><strong>Browser Distribution:</strong> ${data.top_browsers && data.top_browsers.length > 0 ? data.top_browsers.map(b => `${b.browser} (${b.clicks})`).join(', ') : 'No click data yet'}</p>
        <p style="margin-top:0.35rem;"><strong>Daily Breakdowns:</strong> ${data.daily_clicks ? data.daily_clicks.length : 0} active days recorded.</p>
      `;
    }
  } catch (err) {
    document.getElementById('analyticsDetails').textContent = 'Failed to load stats.';
  }
}

function closeModal(modalId) {
  document.getElementById(modalId).classList.remove('open');
}
