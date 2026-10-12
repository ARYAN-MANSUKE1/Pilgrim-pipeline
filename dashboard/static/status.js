// Shared on every page: warns when the job queue is paused (a provider ran out of
// credit, or several temples in a row failed), when WordPress can't be reached, or
// when the dashboard itself stopped answering. Polls /api/stats and hands the result
// to the page as a "pp-stats" event, so the Home page draws from the same call.
(function () {
  const PROVIDER_LINK = {
    Gemini: ['Google AI Studio billing', 'https://aistudio.google.com/'],
    Sarvam: ['Sarvam dashboard', 'https://dashboard.sarvam.ai/'],
  };
  const bar = document.createElement('div');
  bar.id = 'ppbanner';
  bar.setAttribute('role', 'alert');
  document.body.prepend(bar);
  let misses = 0;

  const esc = s => String(s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));

  function resumeButton() {
    document.getElementById('ppresume').onclick = async () => {
      const r = await (await fetch('/api/resume', {method: 'POST'})).json();
      bar.className = '';
      alert(`Queue resumed — ${r.waiting} temple(s) will continue.\nIf the problem is still there it will pause again by itself.`);
      poll();
    };
  }

  // Which website this dashboard changes -- shown next to the name on every page.
  function showSite(url) {
    const brand = document.querySelector('.nav .brand');
    if (!brand || document.getElementById('ppsite')) return;
    const s = document.createElement('span');
    s.id = 'ppsite'; s.className = 'pill'; s.style.marginRight = '10px';
    s.title = 'The website this dashboard reads from and writes to';
    s.textContent = String(url).replace(/^https?:\/\//, '').replace(/\/$/, '');
    brand.after(s);
  }

  function draw(s) {
    if (s.site) showSite(s.site);
    if (s.paused && s.paused.provider) {
      const p = s.paused, link = PROVIDER_LINK[p.provider];
      bar.className = 'show danger';
      bar.innerHTML = `<b>${esc(p.provider)} has run out of credit — the queue is paused.</b>
        ${s.queue_depth} temple(s) are waiting; nothing already done has been lost.
        ${link ? `Top up at <a href="${link[1]}" target="_blank" rel="noopener">${link[0]}</a>, then` : 'Top up, then'}
        <button class="btn" id="ppresume">Resume the queue</button>`;
      resumeButton();
    } else if (s.paused) {
      bar.className = 'show danger';
      bar.innerHTML = `<b>The queue is paused — ${s.paused.streak} temples in a row failed.</b>
        ${s.queue_depth} temple(s) are still waiting and have not been touched.
        Reason: <i>${esc(s.paused.reason || 'unknown')}</i>.
        Once that is fixed, <button class="btn" id="ppresume">Resume the queue</button>`;
      resumeButton();
    } else if (!s.wp_ok) {
      bar.className = 'show warn';
      bar.innerHTML = '<b>Can’t reach the website right now.</b> Temple lists and saving will fail until it responds — check that the website is up, then reload this page.';
    } else {
      bar.className = '';
    }
  }

  async function poll() {
    try {
      const s = await (await fetch('/api/stats')).json();
      misses = 0;
      window.ppStats = s;
      draw(s);
      window.dispatchEvent(new CustomEvent('pp-stats', {detail: s}));
    } catch (e) {
      // One miss is a blip or a restart; two in a row means the dashboard is not running.
      if (++misses >= 2) {
        bar.className = 'show warn';
        bar.innerHTML = '<b>Lost connection to the dashboard.</b> It may have been closed or is restarting. Jobs already queued are saved and continue when it is back — this page reconnects by itself.';
      }
    }
  }
  window.ppRefreshStats = poll;
  poll();
  setInterval(poll, 5000);
})();
