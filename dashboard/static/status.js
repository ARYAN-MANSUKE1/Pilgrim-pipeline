// Shared on every page: warns when the job queue is paused because a provider ran
// out of credit, or when WordPress can't be reached. Polls /api/stats and hands the
// result to the page as a "pp-stats" event, so the Home page draws from the same call.
(function () {
  const PROVIDER_LINK = {
    Gemini: ['Google AI Studio billing', 'https://aistudio.google.com/'],
    Sarvam: ['Sarvam dashboard', 'https://dashboard.sarvam.ai/'],
  };
  const bar = document.createElement('div');
  bar.id = 'ppbanner';
  bar.setAttribute('role', 'alert');
  document.body.prepend(bar);

  const esc = s => String(s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));

  function draw(s) {
    if (s.paused) {
      const p = s.paused, link = PROVIDER_LINK[p.provider];
      bar.className = 'show danger';
      bar.innerHTML = `<b>${esc(p.provider)} has run out of credit — the queue is paused.</b>
        ${s.queue_depth} temple(s) are waiting; nothing already done has been lost.
        ${link ? `Top up at <a href="${link[1]}" target="_blank" rel="noopener">${link[0]}</a>, then` : 'Top up, then'}
        <button class="btn" id="ppresume">Resume the queue</button>`;
      document.getElementById('ppresume').onclick = async () => {
        const r = await (await fetch('/api/resume', {method: 'POST'})).json();
        bar.className = '';
        alert(`Queue resumed — ${r.waiting} temple(s) will continue.\nIf the credit is still empty it will pause again after the next temple.`);
        poll();
      };
    } else if (!s.wp_ok) {
      bar.className = 'show warn';
      bar.innerHTML = '<b>Can’t reach WordPress right now.</b> Temple lists and saving will fail until the site responds — check that the website is up.';
    } else {
      bar.className = '';
    }
  }

  async function poll() {
    try {
      const s = await (await fetch('/api/stats')).json();
      draw(s);
      window.dispatchEvent(new CustomEvent('pp-stats', {detail: s}));
    } catch (e) { /* server restarting: try again next tick */ }
  }
  window.ppRefreshStats = poll;
  poll();
  setInterval(poll, 5000);
})();
