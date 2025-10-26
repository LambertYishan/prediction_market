// =============================================================
// Common JavaScript functions for the prediction market frontend
// =============================================================

// The base URL for API requests. Update if your backend is on another domain.
const apiBase = 'https://prediction-market-wy1h.onrender.com';

/**
 * Update the user greeting in the navigation bar.
 * Shows username and balance if logged in.
 */
function updateUserGreeting() {
  const username = localStorage.getItem('username');
  const balance = localStorage.getItem('balance');
  const greetingEl = document.getElementById('user-greeting');
  const loginLink = document.getElementById('login-link');
  const logoutLink = document.getElementById('logout-link');

  if (username) {
    greetingEl.textContent = `Hello, ${username} (Balance: ${parseFloat(balance).toFixed(2)})`;
    greetingEl.classList.remove('hidden');
    if (loginLink) loginLink.classList.add('hidden');
    if (logoutLink) logoutLink.classList.remove('hidden');
  } else {
    greetingEl.classList.add('hidden');
    if (loginLink) loginLink.classList.remove('hidden');
    if (logoutLink) logoutLink.classList.add('hidden'); 
  }
}

/**
 * Handle logout behavior.
 */
document.addEventListener('DOMContentLoaded', () => {
  const logoutLink = document.getElementById('logout-link');
  if (logoutLink) {
    logoutLink.addEventListener('click', (e) => {
      e.preventDefault();
      localStorage.removeItem('username');
      localStorage.removeItem('balance');
      localStorage.removeItem('user_id');
      updateUserGreeting();
      alert('You have logged out.');
      window.location.href = 'index.html';
    });
  }
});

/**
 * Fetch and render all markets on the index page.
 */
async function loadMarkets() {
  const listEl = document.getElementById('market-list');
  if (!listEl) return;
  listEl.innerHTML = 'Loading markets...';
  try {
    const res = await fetch(apiBase + '/markets');
    if (!res.ok) {
      listEl.textContent = 'Failed to load markets';
      return;
    }
    const markets = await res.json();
    if (!Array.isArray(markets) || markets.length === 0) {
      listEl.textContent = 'No markets found.';
      return;
    }

    listEl.innerHTML = '';
    markets.forEach(market => {
      const card = document.createElement('div');
      card.className = 'market-card';
      const expiryInfo = market.expires_at
        ? `<p><strong>Expires:</strong> ${new Date(market.expires_at).toLocaleString()}</p>`
        : '';
      card.innerHTML = `
        <h3>${market.title}</h3>
        <p>${market.description || ''}</p>
        <p><strong>Price YES:</strong> ${market.price_yes.toFixed(2)} &nbsp;|&nbsp;
           <strong>Price NO:</strong> ${market.price_no.toFixed(2)}</p>
        <p><strong>YES shares:</strong> ${market.yes_shares.toFixed(2)} &nbsp;|&nbsp;
           <strong>NO shares:</strong> ${market.no_shares.toFixed(2)}</p>
        ${expiryInfo}
        ${market.resolved ? `<p><strong>Outcome:</strong> ${market.outcome}</p>` : ''}
        <a href="market.html?id=${market.id}">View Market</a>
      `;
      listEl.appendChild(card);
    });
  } catch (err) {
    listEl.textContent = 'Error loading markets';
  }
}

/**
 * Extract a query parameter by name.
 */
function getQueryParam(name) {
  const params = new URLSearchParams(window.location.search);
  return params.get(name);
}

/**
 * Load details for a single market and render them on the page.
 * Also sets up the bet form handler if the market is unresolved.
 */
async function loadMarketDetails() {
  const marketId = getQueryParam('id');
  const container = document.getElementById('market-container');
  const betContainer = document.getElementById('bet-container');
  if (!marketId || !container) return;
  container.innerHTML = 'Loading market...';
  try {
    const res = await fetch(apiBase + '/markets');
    if (!res.ok) {
      container.textContent = 'Failed to load market';
      return;
    }
    const markets = await res.json();
    const market = markets.find(m => String(m.id) === String(marketId));
    if (!market) {
      container.textContent = 'Market not found';
      return;
    }

    // Render details
    const expiryLine = market.expires_at
      ? `<p><strong>Expires:</strong> ${new Date(market.expires_at).toLocaleString()}</p>`
      : '';
    container.innerHTML = `
      <h2>${market.title}</h2>
      <p>${market.description || ''}</p>
      <p><strong>Price YES:</strong> ${market.price_yes.toFixed(2)} &nbsp;|&nbsp;
         <strong>Price NO:</strong> ${market.price_no.toFixed(2)}</p>
      <p><strong>YES shares:</strong> ${market.yes_shares.toFixed(2)} &nbsp;|&nbsp;
         <strong>NO shares:</strong> ${market.no_shares.toFixed(2)}</p>
      ${expiryLine}
      ${market.resolved ? `<p><strong>Outcome:</strong> ${market.outcome}</p>` : ''}
    `;

    // Betting section
    if (!market.resolved) {
      betContainer.classList.remove('hidden');
      const betForm = document.getElementById('bet-form');
      const betMessage = document.getElementById('bet-message');
      betForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        const userId = localStorage.getItem('user_id');
        if (!userId) {
          betMessage.textContent = 'Please log in to place a bet.';
          return;
        }
        const amount = parseFloat(document.getElementById('bet-amount').value);
        const side = betForm.elements['side'].value;
        try {
          const res = await fetch(apiBase + '/bet', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              user_id: parseInt(userId),
              market_id: parseInt(marketId),
              side,
              amount
            })
          });
          if (!res.ok) {
            const err = await res.json();
            betMessage.textContent = err.detail || 'Bet failed';
            return;
          }
          const bet = await res.json();
          betMessage.textContent = `✅ Bet placed: ${bet.amount} shares @ ${bet.price.toFixed(2)} (cost: ${bet.total_cost.toFixed(2)})`;
          // Update balance in localStorage
          const userRes = await fetch(apiBase + `/user/${userId}`);
          if (userRes.ok) {
            const userInfo = await userRes.json();
            localStorage.setItem('balance', userInfo.balance);
            updateUserGreeting();
          }
          loadMarketDetails();
        } catch (err) {
          betMessage.textContent = 'Request failed';
        }
      });
    } else {
      betContainer.classList.add('hidden');
    }
  } catch (err) {
    container.textContent = 'Error loading market';
  }
}

// =============================================================
// Admin utility functions
// =============================================================

/**
 * Create a new market (for admin.html)
 */
async function createMarket(title, description, liquidity, admin_username, admin_password, expires_at) {
  try {
    const res = await fetch(apiBase + '/markets', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        title,
        description,
        liquidity,
        admin_username,
        admin_password,
        expires_at
      })
    });
    return await res.json();
  } catch (err) {
    console.error('Error creating market:', err);
    return { detail: 'Request failed' };
  }
}

/**
 * Delete a market (for admin.html)
 */
async function deleteMarket(marketId, username, password) {
  try {
    const url = `${apiBase}/markets/${marketId}?username=${encodeURIComponent(username)}&password=${encodeURIComponent(password)}`;
    const res = await fetch(url, { method: 'DELETE' });
    if (res.ok) return { detail: `Market ${marketId} deleted successfully` };
    return await res.json();
  } catch (err) {
    console.error('Error deleting market:', err);
    return { detail: 'Request failed' };
  }
}

// =============================================================
// Expose functions globally (for inline scripts)
// =============================================================
window.updateUserGreeting = updateUserGreeting;
window.loadMarkets = loadMarkets;
window.loadMarketDetails = loadMarketDetails;
window.createMarket = createMarket;
window.deleteMarket = deleteMarket;
