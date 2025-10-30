// =============================================================
// Common JavaScript functions for the prediction market frontend
// =============================================================

// The base URL for API requests. Update if your backend is on another domain.
const apiBase = 'https://prediction-market-wy1h.onrender.com';

/**
 * Update the user greeting in the navigation bar.
 * Shows username and balance if logged in.
 */
async function updateUserGreeting() {
  const username = localStorage.getItem('username');
  const userId = localStorage.getItem('user_id');
  const greetingEl = document.getElementById('user-greeting');
  const loginLink = document.getElementById('login-link');
  const logoutLink = document.getElementById('logout-link');
  const portalLink = document.getElementById('portal-link'); // ✅ new line

  if (username && userId) {
    try {
      const res = await fetch(`${apiBase}/user/${userId}`);
      if (res.ok) {
        const userInfo = await res.json();
        localStorage.setItem('balance', userInfo.balance);
      }
    } catch (err) {
      console.warn("Failed to refresh user balance:", err);
    }

    const balance = localStorage.getItem('balance');
    greetingEl.textContent = `Hello, ${username} (Balance: $${parseFloat(balance).toFixed(2)})`;
    greetingEl.classList.remove('hidden');
    if (loginLink) loginLink.classList.add('hidden');
    if (logoutLink) logoutLink.classList.remove('hidden');
    if (portalLink) portalLink.classList.remove('hidden');
  } else {
    greetingEl.classList.add('hidden');
    if (loginLink) loginLink.classList.remove('hidden');
    if (logoutLink) logoutLink.classList.add('hidden');
    if (portalLink) portalLink.classList.add('hidden');
  }
}

// --- Utility to safely parse timestamps as UTC ---
const parseUtc = (ts) => {
  if (!ts) return null;
  return new Date(ts.endsWith("Z") ? ts : ts + "Z");
};


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
 * Fetch and render all markets, grouped as Active and Inactive.
 */
async function loadMarkets() {
  const activeList = document.getElementById('active-market-list');
  const inactiveList = document.getElementById('inactive-market-list');

  if (!activeList || !inactiveList) return;

  activeList.innerHTML = 'Loading markets...';
  inactiveList.innerHTML = '';

  try {
    const res = await fetch(apiBase + '/markets');
    if (!res.ok) {
      activeList.textContent = 'Failed to load markets';
      return;
    }

    const markets = await res.json();
    if (!Array.isArray(markets) || markets.length === 0) {
      activeList.textContent = 'No markets found.';
      return;
    }

    // Separate active/inactive
    const now = new Date();
    const active = [];
    const inactive = [];

    markets.forEach(m => {
      const expiry = m.expires_at ? new Date(m.expires_at) : null;
      const isExpired = expiry && expiry < now;
      const status = m.resolved ? 'resolved' : isExpired ? 'expired' : 'active';
      if (status === 'active') active.push({ ...m, status });
      else inactive.push({ ...m, status });
    });

    // Render helper
    function renderMarketCard(m) {
      const expiryLine = m.expires_at
        ? `<p><strong>Expires:</strong> ${new Date(m.expires_at).toLocaleString()}</p>`
        : '';
      const statusLabel =
        m.status === 'resolved'
          ? `<p><strong>Status:</strong> ✅ Resolved (${m.outcome})</p>`
          : m.status === 'expired'
            ? `<p><strong>Status:</strong> ⚠️ Expired — Awaiting Resolution</p>`
            : `<p><strong>Status:</strong> ⏳ Active</p>`;

      const card = document.createElement('div');
      card.className = 'market-card';
      card.innerHTML = `
        <h3>${m.title}</h3>
        <p>${m.description || ''}</p>
        ${expiryLine}
        ${statusLabel}
        <p><strong>YES Price:</strong> ${m.price_yes.toFixed(2)} |
           <strong>NO Price:</strong> ${m.price_no.toFixed(2)}</p>
        <p><strong>YES Shares:</strong> ${m.yes_shares.toFixed(2)} |
           <strong>NO Shares:</strong> ${m.no_shares.toFixed(2)}</p>
        <a href="market.html?id=${m.id}">View Market</a>
      `;
      return card;
    }

    // Clear and populate sections
    activeList.innerHTML = '';
    inactiveList.innerHTML = '';

    if (active.length === 0)
      activeList.innerHTML = '<p>No active markets currently.</p>';
    else active.forEach(m => activeList.appendChild(renderMarketCard(m)));

    if (inactive.length === 0)
      inactiveList.innerHTML = '<p>No inactive markets yet.</p>';
    else inactive.forEach(m => inactiveList.appendChild(renderMarketCard(m)));

  } catch (err) {
    console.error("Error loading markets:", err);
    activeList.textContent = 'Error loading markets.';
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
 * Also sets up the bet form handler if the market is unresolved and active.
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

    // Compute status locally (in case backend hasn’t yet added it)
    const now = new Date();
    const expiry = market.expires_at ? new Date(market.expires_at) : null;
    let status = "active";
    if (market.resolved) status = "resolved";
    else if (expiry && expiry < now) status = "expired";

    // Render market details
    const localTz = Intl.DateTimeFormat().resolvedOptions().timeZone;
    const expiryLine = market.expires_at
      ? `<p><strong>Expires (${localTz}):</strong> ${new Date(market.expires_at).toLocaleString('en-US', {
        timeZone: localTz,
        dateStyle: 'medium',
        timeStyle: 'short'
      })}</p>`
      : '';

    const statusLabel = status === "resolved"
      ? `<p><strong>Status:</strong> ✅ Resolved (${market.outcome})</p>`
      : status === "expired"
        ? `<p><strong>Status:</strong> ⚠️ Expired — Awaiting Resolution</p>`
        : `<p><strong>Status:</strong> ⏳ Active</p>`;

    container.innerHTML = `
      <h2>${market.title}</h2>
      <p>${market.description || ''}</p>
      ${expiryLine}
      ${statusLabel}
      <p><strong>Price YES:</strong> ${market.price_yes.toFixed(2)} &nbsp;|&nbsp;
         <strong>Price NO:</strong> ${market.price_no.toFixed(2)}</p>
      <p><strong>YES Shares:</strong> ${market.yes_shares.toFixed(2)} &nbsp;|&nbsp;
         <strong>NO Shares:</strong> ${market.no_shares.toFixed(2)}</p>
      ${market.resolved ? `<p><strong>Outcome:</strong> ${market.outcome}</p>` : ''}
    `;

    // 🟡 Disable betting if inactive
    if (status !== "active" || market.resolved) {
      betContainer.classList.add('hidden');
      const lockMsg = document.createElement('p');
      lockMsg.style.color = status === "resolved" ? "green" : "orange";
      lockMsg.style.fontWeight = "bold";
      lockMsg.style.marginTop = "10px";
      lockMsg.textContent =
        status === "resolved"
          ? `✅ This market has been resolved (${market.outcome}).`
          : `⚠️ This market has expired. Waiting for admin to resolve.`;
      container.appendChild(lockMsg);
    } else {
      // 🟢 Active: show betting form
      betContainer.classList.remove('hidden');
      const betForm = document.getElementById('bet-form');
      const betMessage = document.getElementById('bet-message');

      betForm.addEventListener('submit', async function (e) {
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
          betMessage.textContent =
            `✅ Bet placed: ${bet.amount} shares @ ${bet.price.toFixed(2)} (cost: ${bet.total_cost.toFixed(2)})`;
          // Refresh balance
          const userRes = await fetch(apiBase + `/user/${userId}`);
          if (userRes.ok) {
            const userInfo = await userRes.json();
            localStorage.setItem('balance', userInfo.balance);
            updateUserGreeting();
          }
          loadMarketDetails(); // reload page to refresh prices
        } catch (err) {
          betMessage.textContent = 'Request failed';
        }
      }, { once: true });
    }

    // ✅ Return the market for chart and leaderboard
    return market;

  } catch (err) {
    console.error(err);
    container.textContent = 'Error loading market';
    return null;
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

function renderMembershipStats(user) {
  const created = new Date(user.created_at || Date.now());
  const lastLogin = new Date(user.last_login || Date.now());
  const now = new Date();

  const daysMember = Math.floor((now - created) / (1000 * 60 * 60 * 24));
  const daysSinceLogin = Math.floor((now - lastLogin) / (1000 * 60 * 60 * 24));

  document.getElementById("days-member").textContent =
    `👤 Member for ${daysMember} day${daysMember !== 1 ? "s" : ""}`;
  document.getElementById("days-since-login").textContent =
    `⏱️ Last login ${daysSinceLogin} day${daysSinceLogin !== 1 ? "s" : ""} ago`;
}

function renderTransactions(user) {
  const txBody = document.getElementById("transaction-body");
  if (!user.transactions || user.transactions.length === 0) {
    txBody.innerHTML = "<tr><td colspan='7'>No transactions yet.</td></tr>";
  } else {
    txBody.innerHTML = user.transactions
      .map((t) => {
        const side = t.side || t.outcome || "-";
        const shares = t.shares ? t.shares.toFixed(2) : "-";
        const total = t.total_spent || t.payout || t.refund || 0;
        const avg = t.avg_price ? t.avg_price.toFixed(3) : "-";

        const localTz = Intl.DateTimeFormat().resolvedOptions().timeZone;
        const formattedTime = new Date(t.timestamp).toLocaleString("en-US", {
          timeZone: localTz,
          dateStyle: "medium",
          timeStyle: "short",
        });

        return `
          <tr>
            <td>${t.type.replace(/_/g, " ")}</td>
            <td>${t.market_title}</td>
            <td>${side}</td>
            <td>${shares}</td>
            <td>${total.toFixed(2)}</td>
            <td>${avg}</td>
            <td>${formattedTime}</td>
          </tr>`;
      })
      .join("");
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
