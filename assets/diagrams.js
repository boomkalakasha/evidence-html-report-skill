(() => {
  'use strict';
  function measure(diagram) {
    const selected = diagram.querySelector('.diagram-scene.is-selected .change-diagram-canvas');
    if (selected && selected.clientWidth) diagram.classList.toggle('diagram-has-overflow', selected.scrollWidth > selected.clientWidth + 2);
  }
  function select(diagram, state) {
    const buttons = [...diagram.querySelectorAll('[data-diagram-view]')];
    const scenes = [...diagram.querySelectorAll('[data-diagram-state]')];
    for (const button of buttons) button.setAttribute('aria-pressed', String(button.dataset.diagramView === state));
    for (const scene of scenes) scene.classList.toggle('is-selected', scene.dataset.diagramState === state);
    measure(diagram);
  }
  // Delegation also serves chapter copies in the optional continuous reader.
  document.addEventListener('click', event => {
    const button = event.target.closest?.('[data-diagram-view]');
    if (button) select(button.closest('[data-change-diagram]'), button.dataset.diagramView);
  });
  document.querySelectorAll('[data-change-diagram]').forEach(diagram => {
    const scenes = [...diagram.querySelectorAll('[data-diagram-state]')];
    if (!scenes.length) return;
    diagram.classList.add('diagrams-ready');
    select(diagram, scenes.length === 1 ? scenes[0].dataset.diagramState : 'change');
    if ('ResizeObserver' in window) new ResizeObserver(() => measure(diagram)).observe(diagram);
  });
  window.addEventListener('resize', () => document.querySelectorAll('[data-change-diagram]').forEach(measure));
})();
