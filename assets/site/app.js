/* Navigation, a timed opening illustration, and a separate full-width demo view. */
(() => {
  const root = document.documentElement;
  const header = document.querySelector('.site-header');
  const links = [...document.querySelectorAll('.site-nav a')];
  const sections = links.map(link => document.querySelector(link.getAttribute('href'))).filter(Boolean);
  const figure = document.querySelector('.hero-chart');
  const curve = document.getElementById('progress-curve');
  const reveal = document.getElementById('progress-reveal');
  const cursor = document.getElementById('progress-cursor');
  const dot = document.getElementById('progress-dot');
  const halo = document.getElementById('progress-halo');
  const demoSection = document.getElementById('demo');
  const demoView = document.getElementById('demo-view');
  const demo = document.getElementById('run-demo');
  const precedingContent = [...document.querySelectorAll('#top > :not(#demo), .site-footer')];
  const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)');
  const length = curve.getTotalLength();
  const clamp = value => Math.max(0, Math.min(1, value));
  const targetOrigin = location.origin === 'null' ? '*' : location.origin;
  let frame = 0;
  let curveFrame = 0;
  let curveStarted = false;
  let curveObserver;
  let demoOpen = false;

  root.classList.add('demo-view-enabled');
  demoView.inert = true;

  const drawCurve = progress => {
    const point = curve.getPointAtLength(length * progress);
    curve.style.strokeDasharray = `${length * progress} ${length}`;
    reveal.setAttribute('width', String(point.x - 30));
    cursor.setAttribute('d', `M${point.x} ${point.y}V318`);
    for (const node of [dot, halo]) {
      node.setAttribute('cx', String(point.x));
      node.setAttribute('cy', String(point.y));
    }
  };
  const startCurve = () => {
    if (curveStarted) return;
    curveStarted = true;
    if (reducedMotion.matches) { drawCurve(1); return; }
    drawCurve(0);
    let startedAt;
    const animate = now => {
      startedAt ??= now;
      const progress = clamp((now - startedAt) / 5000);
      drawCurve(progress);
      curveFrame = progress < 1 ? requestAnimationFrame(animate) : 0;
    };
    curveFrame = requestAnimationFrame(animate);
  };
  const resetCurve = () => {
    cancelAnimationFrame(curveFrame);
    curveFrame = 0;
    curveStarted = false;
    drawCurve(reducedMotion.matches ? 1 : 0);
  };
  const observeCurve = () => {
    curveObserver?.disconnect();
    const headerInset = getComputedStyle(header).position === 'sticky' ? header.offsetHeight : 0;
    curveObserver = new IntersectionObserver(entries => {
      for (const entry of entries) {
        if (!entry.isIntersecting || entry.intersectionRatio === 0) resetCurve();
        else if (entry.intersectionRatio >= .15 && !document.hidden) startCurve();
      }
    }, {threshold: [0,.15], rootMargin: `-${headerInset}px 0px 0px 0px`});
    curveObserver.observe(figure);
  };
  resetCurve();
  observeCurve();

  const syncDemoPlayback = () => {
    demo.contentWindow?.postMessage({type: demoOpen ? 'arex-demo:play' : 'arex-demo:pause'}, targetOrigin);
  };
  const sizeDemo = () => {
    root.style.setProperty('--demo-top', `${header.offsetHeight}px`);
    const height = Math.max(580, innerHeight - 32);
    demo.contentWindow?.postMessage({type: 'arex-demo:viewport', height}, targetOrigin);
  };
  const setDemoOpen = open => {
    if (open === demoOpen) return;
    demoOpen = open;
    root.classList.toggle('demo-is-open', open);
    header.inert = open;
    demoView.inert = !open;
    precedingContent.forEach(section => { section.inert = open; });
    if (open) demoView.scrollTop = 0;
    syncDemoPlayback();
  };

  const update = () => {
    frame = 0;
    const headerHeight = header.offsetHeight;
    const threshold = Math.max(headerHeight, parseFloat(getComputedStyle(root).scrollPaddingTop)) + 20;
    const demoTop = demoSection.getBoundingClientRect().top;
    const demoOffset = Math.max(0, demoTop - headerHeight);
    const demoProgress = clamp(1 - demoOffset / Math.max(1, innerHeight));
    root.style.setProperty('--demo-offset', `${demoOffset}px`);
    root.style.setProperty('--demo-progress', String(demoProgress));
    root.style.setProperty('--page-opacity', String(1 - demoProgress));
    root.classList.toggle('demo-is-visible', demoProgress > 0);
    setDemoOpen(demoOffset < 1);
    let active = demoOpen ? demoSection : undefined;
    if (!demoOpen) {
      for (const section of sections) {
        if (section.getBoundingClientRect().top <= threshold) active = section;
      }
    }
    links.forEach(link => {
      if (active && link.getAttribute('href') === `#${active.id}`) link.setAttribute('aria-current', 'location');
      else link.removeAttribute('aria-current');
    });

  };
  const schedule = () => { if (!frame) frame = requestAnimationFrame(update); };
  window.addEventListener('scroll', schedule, {passive: true});
  window.addEventListener('resize', () => {
    sizeDemo();
    observeCurve();
    if (demoOpen) scrollTo({top: demoSection.getBoundingClientRect().top + scrollY - header.offsetHeight, behavior: 'instant'});
    schedule();
  });
  reducedMotion.addEventListener('change', () => {
    resetCurve();
    observeCurve();
  });
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) resetCurve();
    else observeCurve();
  });
  window.addEventListener('load', schedule);
  demo.addEventListener('load', () => { sizeDemo(); syncDemoPlayback(); });

  window.addEventListener('hashchange', schedule);
  window.addEventListener('message', event => {
    if (event.source !== demo.contentWindow || event.origin !== location.origin) return;
    if (event.data?.type === 'arex-demo:size' && Number.isFinite(event.data.height)) {
      const embeddedHeight = Math.max(320, Math.min(2400, event.data.height));
      demo.style.height = `${embeddedHeight}px`;
      schedule();
    }
  });
  sizeDemo();
  update();
})();
