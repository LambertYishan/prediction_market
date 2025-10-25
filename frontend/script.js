// Common JavaScript functions for the prediction market frontend

// The base URL for API requests. By default this is an empty string,
// meaning that API calls will be relative to the current origin. If you
// deploy your backend on a different domain (e.g. Render), update this
// constant accordingly, e.g. 'https://your-backend.onrender.com'.
const apiBase = 'https://prediction-market-wy1h.onrender.com';

/**
 * Update the user greeting in the navigation bar.
 * If a user is logged in (their ID and username are stored in localStorage),
 * display a greeting and hide the login link. Otherwise show the login link.
 */
function updateUserGreeting() {
  const username = localStorage.getItem('username');
  const balance = localStorage.getItem('balance');
  const greetingEl = document.getElementById('user-greeting');
  const loginLink = document.getElementById('login-link');
  if (username) {
    greetingEl.textContent = `Hello, ${username} (Balance: ${parseFloat(balance).toFixed(2)})`;
    greetingEl.classList.remove('hidden');
    if (loginLink) loginLink.classList.add('hidden');
  } else {
    greetingEl.classList.add('hidden');
    if (loginLink) loginLink.classList.remove('hidden');
  }
}

/**
 * Fetch all markets from the API and render them on the index page.
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
      card.innerHTML = `
        <h3>${market.title}</h3>
        <p>${market.description || ''}</p>
        <p><strong>Price YES:</strong> ${market.price_yes.toFixed(2)} &nbsp;|&nbsp; <strong>Price NO:</strong> ${market.price_no.toFixed(2)}</p>
        <p><strong>YES shares:</strong> ${market.yes_shares.toFixed(2)} &nbsp;|&nbsp; <strong>NO shares:</strong> ${market.no_shares.toFixed(2)}</p>
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
 * Extract a query parameter by name from the current URL.
 * @param {string} name The name of the query parameter
 * @returns {string|null} The value or null if not present
 */
function getQueryParam(name) {
  const params = new URLSearchParams(window.location.search);
  return params.get(name);
}

/**
 * Load the details for a single market and render them on the page.
 * Also sets up the bet form submission handler if the market is not resolved.
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
    container.innerHTML = `
      <h2>${market.title}</h2>
      <p>${market.description || ''}</p>
      <p><strong>Price YES:</strong> ${market.price_yes.toFixed(2)} &nbsp;|&nbsp; <strong>Price NO:</strong> ${market.price_no.toFixed(2)}</p>
      <p><strong>YES shares:</strong> ${market.yes_shares.toFixed(2)} &nbsp;|&nbsp; <strong>NO shares:</strong> ${market.no_shares.toFixed(2)}</p>
      ${market.resolved ? `<p><strong>Outcome:</strong> ${market.outcome}</p>` : ''}
    `;
    // Show bet form if market is unresolved
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
            body: JSON.stringify({ user_id: parseInt(userId), market_id: parseInt(marketId), side, amount })
          });
          if (!res.ok) {
            const err = await res.json();
            betMessage.textContent = err.detail || 'Bet failed';
            return;
          }
          const bet = await res.json();
          betMessage.textContent = `Bet placed: ${bet.amount} shares @ price ${bet.price.toFixed(2)} (total cost: ${bet.total_cost.toFixed(2)})`;
          // Update balance in localStorage by requesting updated user info
          const userRes = await fetch(apiBase + `/user/${userId}`);
          if (userRes.ok) {
            const userInfo = await userRes.json();
            localStorage.setItem('balance', userInfo.balance);
            updateUserGreeting();
          }
          // Reload market details to reflect updated shares and prices
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

// Export functions to the global scope so inline scripts can call them if necessary
window.updateUserGreeting = updateUserGreeting;
window.loadMarkets = loadMarkets;
window.loadMarketDetails = loadMarketDetails;