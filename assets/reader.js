(() => {
  const model = JSON.parse(document.getElementById('report-data').textContent);
  const chapter = document.getElementById('chapter-dialog');
  const nodeDialog = document.getElementById('component-dialog');
  const figure = document.getElementById('figure-dialog');
  const returnTargets = new WeakMap();
  let cloneSequence = 0;
  function open(dialog, trigger) {
    returnTargets.set(dialog, trigger);
    if (!dialog.open) dialog.showModal();
    dialog.querySelector('[data-close-dialog]').focus();
  }
  for (const dialog of [chapter, nodeDialog, figure]) {
    dialog.querySelector('[data-close-dialog]').addEventListener('click', () => dialog.close());
    dialog.addEventListener('click', event => { if (event.target === dialog) { const r = dialog.getBoundingClientRect(); if (event.clientX < r.left || event.clientX > r.right || event.clientY < r.top || event.clientY > r.bottom) dialog.close(); } });
    dialog.addEventListener('close', () => { returnTargets.get(dialog)?.focus({ preventScroll: true }); if (dialog === chapter) { document.getElementById('chapter-body').replaceChildren(); updateReadingPosition(); } });
  }
  function cloneChapter(source) {
    const copy = source.cloneNode(true), prefix = 'chapter-copy-' + (++cloneSequence) + '-';
    const ids = new Map();
    for (const element of [copy, ...copy.querySelectorAll('[id]')]) {
      if (element.id) { ids.set(element.id, prefix + element.id); element.dataset.originalId = element.id; element.id = prefix + element.id; }
    }
    copy.querySelectorAll('a[href^="#"]').forEach(a => { const old = a.getAttribute('href').slice(1); if (ids.has(old)) a.setAttribute('href', '#' + ids.get(old)); });
    copy.querySelectorAll('[aria-labelledby],[aria-describedby],[aria-controls]').forEach(el => { for (const attr of ['aria-labelledby', 'aria-describedby', 'aria-controls']) if (el.hasAttribute(attr)) el.setAttribute(attr, el.getAttribute(attr).split(' ').map(id => ids.get(id) || id).join(' ')); });
    copy.querySelectorAll('[marker-end],[fill],[clip-path]').forEach(el => { for (const attr of ['marker-end', 'fill', 'clip-path']) if (el.hasAttribute(attr)) el.setAttribute(attr, el.getAttribute(attr).replace(/url\(#([^)]+)\)/g, (all,id) => ids.has(id) ? 'url(#'+ids.get(id)+')' : all)); });
    copy.querySelectorAll('.print-only,noscript').forEach(el => el.remove());
    if (copy.tagName === 'DETAILS') copy.open = true;
    copy.querySelector('details[data-primary]')?.setAttribute('open', '');
    initExplorers(copy);
    const search = copy.querySelector('[data-original-id="search"]');
    if (search) {
      let status = '';
      const rows = [...copy.querySelectorAll('tbody tr')];
      const filter = () => { let count = 0; rows.forEach(row => { row.hidden = (!!status && row.dataset.status !== status) || (!!search.value && !row.dataset.search.toLocaleLowerCase().includes(search.value.toLocaleLowerCase())); if (!row.hidden) count++; }); copy.querySelector('[data-original-id="count"]').textContent = `显示 ${count} / ${rows.length} 项`; copy.querySelector('[data-original-id="empty"]').hidden = count > 0; copy.querySelectorAll('[data-status-filter]').forEach(b => { b.setAttribute('aria-pressed', String(b.dataset.statusFilter === status)); }); };
      search.addEventListener('input', filter);
      copy.querySelectorAll('[data-status-filter]').forEach(b => b.addEventListener('click', () => { status = b.dataset.statusFilter; filter(); }));
      copy.querySelector('[data-original-id="reset"]').addEventListener('click', () => { status = ''; search.value = ''; filter(); });
      filter();
    }
    return copy;
  }
  document.addEventListener('click', event => {
    const link = event.target.closest?.('#report-outline a[href^="#"]');
    if (model.readingMode === 'continuous' && link && !event.ctrlKey && !event.metaKey && !event.shiftKey && !event.altKey) {
      const source = document.getElementById(link.getAttribute('href').slice(1));
      if (!source) return;
      event.preventDefault(); event.stopImmediatePropagation();
      document.getElementById('chapter-title').textContent = link.textContent;
      document.getElementById('chapter-body').replaceChildren(cloneChapter(source));
      const primary = source.closest('section[data-chapter]');
      if (primary) {
        const count = document.querySelectorAll('.shell>section[data-chapter]').length;
        document.getElementById('reading-position').textContent = `阅读位置 ${primary.dataset.chapter} / ${count} · ${primary.querySelector('h2')?.textContent || link.textContent}`;
        document.querySelectorAll('#report-outline a').forEach(a => { if (a.getAttribute('href') === '#'+primary.id) a.setAttribute('aria-current','location'); else a.removeAttribute('aria-current'); });
      }
      open(chapter, link);
      return;
    }
    const anchor = event.target.closest?.('#chapter-dialog a[href^="#"],#component-dialog a[href^="#"]');
    if (anchor && !anchor.classList.contains('term') && !anchor.getAttribute('href').startsWith('#chapter-copy-')) {
      if (nodeDialog.open) nodeDialog.close();
      if (chapter.open) chapter.close();
    }
  }, true);
  function setView(view) {
    document.body.dataset.view = view;
    document.querySelectorAll('[data-report-view]').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.reportView === view)));
  }
  setView(model.readingMode === 'continuous' ? (model.defaultView || (model.schemaVersion === 2 ? 'brief' : 'full')) : 'full');
  document.querySelectorAll('[data-report-view]').forEach(button => button.addEventListener('click', () => setView(button.dataset.reportView)));
  function initExplorers(root) {
    root.querySelectorAll('.scenario-explorer').forEach(explorer => {
      const select = explorer.querySelector('[data-scenario-select]');
      const articles = [...explorer.querySelectorAll(':scope > [data-scenario]')];
      const show = () => articles.forEach(article => { article.hidden = article.dataset.scenario !== select.value; article.dataset.trace = '-1'; article.querySelectorAll('[aria-current=step]').forEach(x => x.removeAttribute('aria-current')); article.querySelectorAll('.executing').forEach(x => x.classList.remove('executing')); const status = article.querySelector('.trace-state'); if (status) status.textContent = '这是说明演示，不发送业务请求。'; });
      select.addEventListener('change', show); show();
    });
  }
  initExplorers(document);
  document.addEventListener('click', event => {
    const button = event.target.closest?.('[data-trace-next]');
    if (button) {
      const article = button.closest('[data-scenario]'), steps = [...article.querySelectorAll('.trace-list li')];
      if (!steps.length) return;
      const current = ((Number(article.dataset.trace ?? -1)) + 1) % steps.length; article.dataset.trace = String(current);
      steps.forEach((step, i) => { if (i === current) step.setAttribute('aria-current', 'step'); else step.removeAttribute('aria-current'); });
      article.querySelectorAll('[data-node]').forEach(node => node.classList.toggle('executing', node.dataset.node === steps[current].dataset.traceNode));
      article.querySelector('.trace-state').textContent = `第${current+1}/${steps.length}步：${steps[current].textContent}`;
    }
    const node = event.target.closest?.('[data-component]');
    if (node) {
      const definition = (model.components || []).find(c => c.id === node.dataset.component);
      if (!definition) return;
      const body = nodeDialog.querySelector('.reader-dialog-body');
      body.replaceChildren();
      for (const [key, label] of [['title','组件'],['body','职责'],['artifact','引入形式'],['owner','责任方'],['scope','范围'],['acceptance','验收']]) {
        if (definition[key]) { const p = document.createElement('p'), strong = document.createElement('strong'); strong.textContent = label + '：'; p.append(strong, document.createTextNode(definition[key])); body.append(p); }
      }
      for (const id of definition.evidence || []) {
        const evidence = (model.evidence || []).find(e => e.id === id); if (!evidence) continue;
        const p = document.createElement('p'); p.textContent = `依据 ${id}：${evidence.summary}；来源：${evidence.source}；定位：${evidence.locator || '未提供'}；限制：${evidence.limitation || '未说明'}`; body.append(p);
      }
      open(nodeDialog, node);
    }
  });
  let zoom = 1, fit = 1;
  const preview = figure.querySelector('img'), stage = figure.querySelector('.figure-stage');
  function sizeFigure() { if (preview.naturalWidth) { fit = Math.min((stage.clientWidth-28)/preview.naturalWidth, (stage.clientHeight-28)/preview.naturalHeight, 1); preview.style.width = Math.max(1, preview.naturalWidth*fit*zoom) + 'px'; } }
  preview.addEventListener('load', sizeFigure);
  figure.querySelectorAll('[data-zoom]').forEach(button => button.addEventListener('click', () => { zoom = button.dataset.zoom === 'in' ? Math.min(8,zoom*1.5) : Math.max(.5,zoom/1.5); sizeFigure(); }));
  preview.addEventListener('click', () => figure.close());
  function openFigure(trigger, src) { zoom = 1; preview.alt = trigger.alt || trigger.textContent || '架构图'; preview.src = src; open(figure, trigger); if (preview.complete) sizeFigure(); }
  document.addEventListener('click', event => {
    if (event.target.closest?.('#figure-dialog')) return;
    const image = event.target.closest?.('.report-figure img'), button = event.target.closest?.('[data-image-src]');
    if (image) openFigure(image, image.src);
    else if (button) openFigure(button, button.dataset.imageSrc);
  });
  document.addEventListener('keydown', event => {
    const target = event.target.closest?.('[data-component],.report-figure img');
    if (target && (event.key === 'Enter' || event.key === ' ')) { event.preventDefault(); target.dispatchEvent(new MouseEvent('click', { bubbles: true })); }
  });
  addEventListener('resize', () => { if (figure.open) sizeFigure(); });
})();
