(() => {
  'use strict';
  document.querySelector('[data-print-report]')?.addEventListener('click', () => window.print());
  const model = JSON.parse(document.getElementById('report-data').textContent);
  const tooltip = document.getElementById('citation-popover');
  let preview = null;
  function hideCitation() {
    tooltip.hidden = true;
    preview?.removeAttribute('aria-describedby');
    preview = null;
  }
  function showCitation(link) {
    const entry = (model.evidence || []).find(item => item.id === link.dataset.evidence);
    if (!entry) return;
    const parent = link.closest('dialog') || document.body;
    if (tooltip.parentElement !== parent) parent.append(tooltip);
    const heading = document.createElement('strong'), summary = document.createElement('p'), source = document.createElement('small');
    heading.textContent = '来源 ' + link.textContent;
    const shorten = (value, limit) => value.length > limit ? value.slice(0,limit) + '…' : value;
    summary.textContent = shorten(entry.summary,180);
    source.textContent = shorten(entry.source,110) + (entry.limitation ? ' · 限制：' + shorten(entry.limitation,100) : '') + ' · 点击查看完整来源';
    link.removeAttribute('title'); // Native title remains available without JavaScript.
    tooltip.replaceChildren(heading, summary, source);
    preview?.removeAttribute('aria-describedby');
    preview = link;
    link.setAttribute('aria-describedby', 'citation-popover');
    tooltip.hidden = false;
    const rect = link.getBoundingClientRect(), box = tooltip.getBoundingClientRect();
    tooltip.style.left = Math.max(12, Math.min(innerWidth - box.width - 12, rect.left)) + 'px';
    tooltip.style.top = Math.max(8, Math.min(innerHeight - box.height - 8, rect.bottom + 10)) + 'px';
  }
  for (const type of ['mouseover', 'focusin']) document.addEventListener(type, event => { const link = event.target.closest?.('.evidence-ref'); if (link) showCitation(link); });
  for (const type of ['mouseout', 'focusout']) document.addEventListener(type, event => { if (event.target.closest?.('.evidence-ref')) hideCitation(); });
  document.addEventListener('keydown', event => { if (event.key === 'Escape') hideCitation(); });
  document.addEventListener('report-panelchange', hideCitation);
  addEventListener('resize', hideCitation);
  addEventListener('scroll', hideCitation, true);
  document.addEventListener('click', event => { if (event.target.closest?.('.evidence-ref')) hideCitation(); });
  if (model.readingMode === 'continuous') return;

  function positionHeadingNote(note) {
    const button = note.querySelector('.heading-help'), tip = note.querySelector('.heading-tooltip');
    button.removeAttribute('title'); // Keep the native title only as the no-script fallback.
    const rect = button.getBoundingClientRect(), box = tip.getBoundingClientRect();
    const mobile = matchMedia('(max-width:760px)').matches;
    const left = mobile ? rect.left : rect.right + 10;
    const top = mobile ? rect.bottom + 8 : rect.top + (rect.height - box.height) / 2;
    tip.style.left = Math.max(12, Math.min(innerWidth - box.width - 12, left)) + 'px';
    tip.style.top = Math.max(8, Math.min(innerHeight - box.height - 8, top)) + 'px';
    button.setAttribute('aria-expanded', 'true');
  }
  function dismissHeadingNotes(except=null) {
    document.querySelectorAll('.heading-note').forEach(note => {
      if (note !== except) {
        note.classList.remove('is-open'); note.classList.add('is-dismissed');
        note.querySelector('.heading-help').setAttribute('aria-expanded', 'false');
      }
    });
  }
  document.addEventListener('click', event => {
    const button = event.target.closest?.('.heading-help');
    if (!button) { dismissHeadingNotes(); return; }
    const note = button.closest('.heading-note');
    const opening = !note.classList.contains('is-open');
    dismissHeadingNotes(note);
    note.classList.toggle('is-open', opening);
    note.classList.toggle('is-dismissed', !opening);
    if (opening) positionHeadingNote(note);
    else button.setAttribute('aria-expanded', 'false');
  });
  for (const type of ['mouseover','focusin']) document.addEventListener(type,event => {
    const note=event.target.closest?.('.heading-note');
    if (note && !note.contains(event.relatedTarget)) {
      dismissHeadingNotes(note);
      note.classList.remove('is-dismissed');
      positionHeadingNote(note);
    }
  });
  for (const type of ['mouseout','focusout']) document.addEventListener(type,event => {
    const note=event.target.closest?.('.heading-note');
    if (note && !note.contains(event.relatedTarget) && !note.classList.contains('is-open')) note.querySelector('.heading-help').setAttribute('aria-expanded', 'false');
  });
  document.addEventListener('keydown',event => { if (event.key==='Escape') dismissHeadingNotes(); });
  document.addEventListener('report-panelchange',()=>dismissHeadingNotes());
  addEventListener('resize',()=>dismissHeadingNotes());
  addEventListener('scroll',()=>dismissHeadingNotes(),true);

  const outline = document.getElementById('report-outline');
  const panels = [...document.querySelectorAll('.shell > [data-chapter]')];
  const links = [...outline.querySelectorAll('nav a')];
  const decode = hash => { try { return decodeURIComponent(hash.slice(1)); } catch { return ''; } };
  function measureNavigation() {
    document.documentElement.style.setProperty('--focus-nav-height', matchMedia('(max-width:760px)').matches ? outline.offsetHeight + 'px' : '0px');
  }
  function activate(hash, { push = false, focus = false, scroll = true } = {}) {
    const target = document.getElementById(decode(hash)) || panels[0];
    const panel = target.closest('.shell > [data-chapter]');
    if (!panel) return false;
    hideCitation();
    document.dispatchEvent(new Event('report-panelchange'));
    for (const item of panels) item.classList.toggle('is-active', item === panel);
    for (const link of links) {
      if (link.getAttribute('href') === '#' + panel.id) link.setAttribute('aria-current', 'page');
      else link.removeAttribute('aria-current');
    }
    const activeLink = links.find(link => link.hasAttribute('aria-current'));
    document.getElementById('reading-position').textContent = `${panel.dataset.chapter} / ${panels.length} · ${activeLink?.querySelector('span:last-child')?.textContent || ''}`;
    if (target.tagName === 'DETAILS') target.open = true;
    for (let parent = target.parentElement; parent && parent !== panel; parent = parent.parentElement) if (parent.tagName === 'DETAILS') parent.open = true;
    panel.querySelector(':scope > .section-content > details[data-primary]')?.setAttribute('open', '');
    const destination = target === panel ? panel.querySelector('h2') : target;
    if (push && location.hash !== hash) history.pushState(null, '', hash);
    requestAnimationFrame(() => {
      measureNavigation();
      if (scroll) {
        if (target === panel && !matchMedia('(max-width:760px)').matches) window.scrollTo({ top: 0, behavior: 'instant' });
        else target.scrollIntoView({ block: 'start', behavior: 'instant' });
      }
      if (focus) {
        if (!destination.hasAttribute('tabindex')) destination.setAttribute('tabindex', '-1');
        destination.focus({ preventScroll: true });
      }
    });
    return true;
  }
  document.addEventListener('click', event => {
    const link = event.target.closest?.('a[href^="#"]');
    if (!link || link.classList.contains('term') || event.defaultPrevented || event.ctrlKey || event.metaKey || event.altKey || event.shiftKey || event.button !== 0) return;
    const hash = link.getAttribute('href');
    if (!document.getElementById(decode(hash))?.closest('.shell > [data-chapter]')) return;
    event.preventDefault();
    link.closest('dialog[open]')?.close();
    activate(hash, { push: true, focus: true });
  });
  outline.addEventListener('keydown', event => {
    const index = links.indexOf(document.activeElement);
    if (index < 0 || !['ArrowUp','ArrowDown','Home','End'].includes(event.key)) return;
    event.preventDefault();
    const next = event.key === 'Home' ? 0 : event.key === 'End' ? links.length - 1 : (index + (event.key === 'ArrowDown' ? 1 : -1) + links.length) % links.length;
    links[next].focus();
  });
  const restore = () => activate(location.hash || '#overview', { focus: true });
  addEventListener('popstate', restore);
  addEventListener('hashchange', restore);
  addEventListener('resize', measureNavigation);
  activate(location.hash || '#overview', { scroll: !!location.hash });
  document.documentElement.classList.add('focus-ready');
  measureNavigation();
})();
