/* AREX 2.0. Vanilla JavaScript. Each enhancement fails independently. */
(() => {
  'use strict';
  const root = document.documentElement;
  const $ = (selector, within = document) => within.querySelector(selector);
  const $$ = (selector, within = document) => [...within.querySelectorAll(selector)];
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  const safeInit = (name, init) => { try { init(); } catch (error) { console.warn(`AREX ${name}:`, error); } };
  let paused = reducedMotion.matches;
  let toastTimer;
  const toast = message => {
    const el = $('#toast');
    el.textContent = message;
    el.classList.add('visible');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => el.classList.remove('visible'), 3800);
  };
  const setMotion = value => {
    paused = Boolean(value);
    root.classList.toggle('motion-off', paused);
    const button = $('#motion-toggle');
    button.setAttribute('aria-pressed', String(paused));
    button.setAttribute('aria-label', paused ? 'Play animation' : 'Pause animation');
    button.title = paused ? 'Play animation' : 'Pause animation';
    if (paused && document.getAnimations) document.getAnimations().forEach(a => { try { a.finish(); } catch (_) {} });
    document.dispatchEvent(new CustomEvent('arex:motion', { detail: { paused } }));
  };
  safeInit('motion control', () => {
    setMotion(paused);
    $('#motion-toggle').addEventListener('click', () => setMotion(!paused));
    reducedMotion.addEventListener('change', e => setMotion(e.matches));
  });

  safeInit('reveals', () => {
    if (!('IntersectionObserver' in window)) return;
    const observer = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (!entry.isIntersecting) return;
        entry.target.classList.remove('waiting');
        entry.target.classList.add('in-view');
        observer.unobserve(entry.target);
      });
    }, { threshold: 0.08, rootMargin: '0px 0px -25px 0px' });
    $$('.reveal').forEach(el => { if (!paused) el.classList.add('waiting'); observer.observe(el); });
  });

  safeInit('navigation', () => {
    const menu = $('#main-nav');
    const toggle = $('#menu-toggle');
    const closeMenu = () => {
      menu.classList.remove('open');
      toggle.setAttribute('aria-expanded', 'false');
      toggle.setAttribute('aria-label', 'Open navigation');
    };
    toggle.addEventListener('click', () => {
      const open = toggle.getAttribute('aria-expanded') !== 'true';
      menu.classList.toggle('open', open);
      toggle.setAttribute('aria-expanded', String(open));
      toggle.setAttribute('aria-label', open ? 'Close navigation' : 'Open navigation');
    });
    $$('a', menu).forEach(link => link.addEventListener('click', closeMenu));
    document.addEventListener('keydown', e => {
      if (e.key === 'Escape' && menu.classList.contains('open')) { closeMenu(); toggle.focus(); }
    });
    document.addEventListener('pointerdown', e => {
      if (!e.target.closest('#site-header')) closeMenu();
    });
    window.addEventListener('resize', () => { if (window.innerWidth > 700) closeMenu(); }, { passive: true });
    $$('[data-open-appendix]').forEach(link => link.addEventListener('click', () => { $('#appendix').open = true; }));
    if (location.hash === '#full-results') $('#appendix').open = true;
    window.addEventListener('hashchange', () => { if (location.hash === '#full-results') $('#appendix').open = true; });
    const sections = ['research', 'method', 'results'].map(id => document.getElementById(id));
    const steps = $$('.method-step');
    const phases = ['01 / Build', '02 / Iterate', '03 / Select', '04 / Train'];
    let activeStep = -1, ticking = false;
    const update = () => {
      const y = window.scrollY;
      const scrollable = document.documentElement.scrollHeight - window.innerHeight;
      $('#reading-progress').style.transform = `scaleX(${scrollable > 0 ? Math.min(1, y / scrollable) : 0})`;
      $('#site-header').classList.toggle('scrolled', y > 12);
      let current = '';
      for (const section of sections) if (section.getBoundingClientRect().top <= 170) current = section.id;
      $$('[data-nav]').forEach(link => {
        if (link.dataset.nav === current) link.setAttribute('aria-current', 'location');
        else link.removeAttribute('aria-current');
      });
      let closest = 0, distance = Infinity;
      steps.forEach((step, i) => {
        const rect = step.getBoundingClientRect();
        const d = Math.abs(rect.top + rect.height * .45 - window.innerHeight * .5);
        if (d < distance) { distance = d; closest = i; }
      });
      if (closest !== activeStep) {
        activeStep = closest;
        steps.forEach((step, i) => step.classList.toggle('is-active', i === closest));
        $$('[data-flow-stage]').forEach((stage, i) => stage.classList.toggle('stage-active', i === closest));
        $$('.method-step-meter i').forEach((segment, i) => segment.classList.toggle('active', i === closest));
        $('#method-phase-label').textContent = phases[closest];
      }
      ticking = false;
    };
    const queueUpdate = () => { if (!ticking) { ticking = true; requestAnimationFrame(update); } };
    window.addEventListener('scroll', queueUpdate, { passive: true });
    window.addEventListener('resize', queueUpdate, { passive: true });
    $('#appendix').addEventListener('toggle', queueUpdate);
    update();
  });

  safeInit('iteration sculpture', () => {
    const canvas = $('#iteration-canvas');
    const visual = $('#study-visual');
    const ctx = canvas.getContext('2d', { alpha: true });
    if (!ctx) return; // The inline SVG remains visible.
    const samples = 170, strands = 49;
    const curves = [];
    for (let j = 0; j < strands; j++) {
      const curve = new Float32Array((samples + 1) * 3);
      const w = j / (strands - 1) - .5;
      for (let i = 0; i <= samples; i++) {
        const t = i / samples, a = t * Math.PI * 2.8 - .7, r = 1.05 - .25 * t;
        curve[i * 3] = r * Math.cos(a) + w * .65 * Math.cos(a * .58);
        curve[i * 3 + 1] = (t - .5) * 2.95 + w * .8 * Math.sin(a * .58);
        curve[i * 3 + 2] = r * Math.sin(a) + w * .4 * Math.cos(a * .7);
      }
      curves.push(curve);
    }
    let width = 0, height = 0, ratio = 1, frame = 0, previous = 0, time = 0;
    let onScreen = true, pointerX = 0, pointerY = 0, targetX = 0, targetY = 0;
    const draw = () => {
      if (!width || !height) return;
      const scale = Math.min(width / 620, height / 644);
      ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
      ctx.clearRect(0, 0, width, height);
      const ry = -.58 + Math.sin(time * .33) * .18 + pointerX * .28;
      const rz = -.36 + Math.sin(time * .22) * .035 + pointerY * .04;
      const cy = Math.cos(ry), sy = Math.sin(ry), cz = Math.cos(rz), sz = Math.sin(rz);
      ctx.lineWidth = .91 * scale;
      ctx.lineJoin = 'round';
      ctx.globalAlpha = .80;
      for (let j = 0; j < curves.length; j++) {
        const curve = curves[j];
        ctx.beginPath();
        for (let i = 0; i <= samples; i++) {
          const x0 = curve[i * 3], y0 = curve[i * 3 + 1], z0 = curve[i * 3 + 2];
          const x1 = x0 * cy + z0 * sy, z = -x0 * sy + z0 * cy;
          const x = x1 * cz - y0 * sz, y = x1 * sz + y0 * cz;
          const perspective = 5 / (5 + z);
          const px = width / 2 + x * perspective * 151 * scale;
          const py = height / 2 - 10 * scale - y * perspective * 151 * scale;
          if (i === 0) ctx.moveTo(px, py); else ctx.lineTo(px, py);
        }
        ctx.strokeStyle = j > 41 ? '#be472d' : '#252823';
        ctx.stroke();
      }
      ctx.globalAlpha = 1;
    };
    const resize = () => {
      const box = visual.getBoundingClientRect();
      width = box.width; height = box.height;
      ratio = Math.min(window.devicePixelRatio || 1, 1.8);
      canvas.width = Math.max(1, Math.round(width * ratio));
      canvas.height = Math.max(1, Math.round(height * ratio));
      draw();
    };
    const tick = stamp => {
      frame = 0;
      if (paused || !onScreen || document.hidden) { previous = 0; return; }
      const dt = previous ? Math.min((stamp - previous) / 1000, .05) : 0;
      // Cap raster work at roughly 30 fps. Stop entirely when offscreen/hidden/paused.
      if (!previous || stamp - previous >= 30) {
        time += dt; previous = stamp;
        pointerX += (targetX - pointerX) * .1;
        pointerY += (targetY - pointerY) * .1;
        draw();
      }
      frame = requestAnimationFrame(tick);
    };
    const resume = () => {
      if (!paused && onScreen && !document.hidden && !frame) { previous = 0; frame = requestAnimationFrame(tick); }
    };
    const stop = () => { cancelAnimationFrame(frame); frame = 0; previous = 0; };
    new ResizeObserver(resize).observe(visual);
    if ('IntersectionObserver' in window) new IntersectionObserver(entries => {
      onScreen = entries[0].isIntersecting;
      if (onScreen) resume(); else stop();
    }, { rootMargin: '60px' }).observe(visual);
    document.addEventListener('visibilitychange', () => { if (document.hidden) stop(); else resume(); });
    document.addEventListener('arex:motion', () => { if (paused) stop(); else resume(); });
    visual.addEventListener('pointermove', e => {
      if (e.pointerType !== 'mouse' || paused) return;
      const rect = visual.getBoundingClientRect();
      targetX = (e.clientX - rect.left) / rect.width - .5;
      targetY = (e.clientY - rect.top) / rect.height - .5;
    }, { passive: true });
    visual.addEventListener('pointerleave', () => { targetX = 0; targetY = 0; }, { passive: true });
    $('#study-reset').addEventListener('click', () => { time = 0; targetX = pointerX = targetY = pointerY = 0; draw(); });
    resize(); visual.classList.add('canvas-ready'); resume();
  });

  safeInit('reflection explorer', () => {
    const reflection = $('#reflection-control'), horizon = $('#horizon-control');
    const presets = { none: [0, 24], short: [6, 6], both: [6, 24] };
    const formatGain = value => `${Number(value).toFixed(1).replace('.0', '')}%`;
    const update = (preset = '') => {
      const r = Number(reflection.value) / 100, T = Number(horizon.value);
      const final = Math.pow(1 + r, T);
      const xEnd = 46 + T / 24 * 493;
      const yEnd = 230 - (final - 1) / 3.25 * 192;
      const points = [];
      for (let i = 0; i <= 120; i++) {
        const t = i / 5, value = Math.pow(1 + r, Math.min(t, T));
        points.push(`${(46 + t / 24 * 493).toFixed(1)},${(230 - (value - 1) / 3.25 * 192).toFixed(1)}`);
      }
      $('#curve-path').setAttribute('points', points.join(' '));
      $('#curve-horizon').setAttribute('x1', xEnd);
      $('#curve-horizon').setAttribute('x2', xEnd);
      $('#curve-dot').setAttribute('cx', xEnd);
      $('#curve-dot').setAttribute('cy', yEnd);
      $('#curve-t-label').setAttribute('x', Math.min(531, xEnd));
      $('#curve-t-label').textContent = `T = ${T}`;
      $('#curve-value').setAttribute('y', yEnd - 12);
      $('#curve-value').textContent = `${final.toFixed(2)}×`;
      $('#reflection-output').textContent = formatGain(reflection.value);
      $('#horizon-output').textContent = `${T} rounds`;
      reflection.setAttribute('aria-valuetext', `${reflection.value} percent expected gain per round`);
      horizon.setAttribute('aria-valuetext', `${T} effective rounds`);
      $('#curve-description').textContent = `Illustration, not measured results. ${reflection.value} percent expected relative gain over ${T} effective rounds gives ${final.toFixed(2)} times initial quality. No further gain is assumed after the effective horizon.`;
      $$('[data-preset]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.preset === preset)));
    };
    [reflection, horizon].forEach(input => input.addEventListener('input', () => update()));
    $$('[data-preset]').forEach(button => button.addEventListener('click', () => {
      const [r, T] = presets[button.dataset.preset]; reflection.value = r; horizon.value = T; update(button.dataset.preset);
    }));
    update();
  });

  let benchmarkSource;
  safeInit('benchmark explorer', () => {
    benchmarkSource = JSON.parse($('#benchmark-source').textContent);
    const configs = {
      mle: {
        title: 'MLE-bench Lite', group: 'coding_and_mle',
        tagline: 'The highest Medal Average in the manuscript’s comparison set.',
        protocol: 'Medal Average · higher is better\nOpenMLE protocol · up to 12 hours per task',
        scope: 'Selected open- and closed-weight systems',
        note: '‡ Results reproduced and reported by OpenMLE. Selected comparisons; all bars start at zero.',
        models: ['AREX 2.0', 'GPT-5.6 Sol', 'Kimi-K3', 'Frontis-MA1-35B', 'GPT-5.5', 'Kimi-K2.6', 'Claude Opus 4.8']
      },
      fcs: {
        title: 'Frontier-CS', group: 'coding_and_mle',
        tagline: 'Above every listed open-weight baseline. 5.7 points behind the highest reported score.',
        protocol: '188-task Agent Track · higher is better\nMaximum execution budget: 5 hours per task',
        scope: 'Selected open- and closed-weight systems',
        note: '* Results reproduced by the authors. † Default pi-agent evaluation for those Frontier-CS results. All bars start at zero.',
        models: ['GPT-5.6 Sol', 'Claude Opus 4.8', 'GPT-5.5', 'AREX 2.0', 'Gemini-3.1-Pro', 'Kimi-K2.7-Code', 'GLM-5.3-Flash']
      },
      bc: {
        title: 'BrowseComp', group: 'deep_research',
        tagline: 'The highest listed score among models with at most 40B parameters.',
        protocol: 'Accuracy · higher is better\nAREX protocol: 300 inner / 1,500 overall turns',
        scope: 'Selected models with ≤40B parameters',
        note: 'Total parameter counts define the size group. The complete table includes larger and frontier models. All bars start at zero.',
        models: ['AREX 2.0', 'Iris-mini', 'Agents-A1', 'Nex-N2-mini', 'Apodex-1.0-mini', 'AREX-Turbo', 'MiroThinker-1.7-mini']
      },
      hle: {
        title: 'HLE', group: 'deep_research',
        tagline: 'The highest listed text-only score among models with at most 40B parameters.',
        protocol: 'Text-only accuracy · higher is better\nAREX protocol: 300 inner / 1,500 overall turns',
        scope: 'Selected ≤40B models · text-only HLE',
        note: 'Text-only subset throughout this chart. Full-set HLE scores appear separately marked in the complete table and are not directly comparable.',
        models: ['AREX 2.0', 'Iris-mini', 'Agents-A1', 'Qwen3.5-35B', 'Apodex-1.0-mini', 'AREX-Turbo', 'Quest-35B']
      },
      gaia: {
        title: 'GAIA', group: 'deep_research',
        tagline: '92.2 accuracy. Below Agents-A1, above every other listed small model with a reported result.',
        protocol: 'Accuracy · higher is better\nAREX protocol: 300 inner / 1,500 overall turns',
        scope: 'Selected models with ≤40B parameters',
        note: 'Agents-A1 reports 96.0 on GAIA. AREX 2.0 is not the highest-scoring small model on this benchmark. All bars start at zero.',
        models: ['Agents-A1', 'AREX 2.0', 'Nex-N2-mini', 'AREX-Turbo', 'Quest-35B', 'MiroThinker-1.7-mini', 'Qwen3.5-35B']
      },
      dsqa: {
        title: 'DeepSearchQA', group: 'deep_research',
        tagline: 'The highest listed F1 among models with at most 40B parameters.',
        protocol: 'F1 · higher is better\nAREX protocol: 300 inner / 1,500 overall turns',
        scope: 'Selected models with ≤40B parameters',
        note: 'DeepSearchQA reports F1, not accuracy. The complete table also includes larger and frontier models. All bars start at zero.',
        models: ['AREX 2.0', 'Nex-N2-mini', 'Iris-mini', 'Apodex-1.0-mini', 'AREX-Turbo', 'Qwen3.5-35B', 'MiroThinker-1.7-mini']
      }
    };
    let selected = 'mle';
    const tabs = $$('[data-tab]');
    const animations = new Set();
    const select = (key, announce = true, animate = true) => {
      const config = configs[key]; if (!config) return;
      selected = key;
      const rows = config.models.map(name => benchmarkSource[config.group].find(model => model.model === name));
      if (rows.some(row => !row || typeof row[key] !== 'number')) throw new Error(`Missing data for ${key}`);
      const our = rows.find(row => row.model === 'AREX 2.0');
      tabs.forEach(tab => {
        const active = tab.dataset.tab === key;
        tab.setAttribute('aria-selected', String(active)); tab.tabIndex = active ? 0 : -1;
      });
      $('#benchmark-panel').setAttribute('aria-labelledby', `tab-${key}`);
      $('#benchmark-score').textContent = our[key].toFixed(1);
      $('#benchmark-big-label').textContent = config.title;
      $('#benchmark-tagline').textContent = config.tagline;
      $('#benchmark-protocol').replaceChildren(...config.protocol.split('\n').flatMap((line, i) => i ? [document.createElement('br'), document.createTextNode(line)] : [document.createTextNode(line)]));
      $('#chart-scope').textContent = config.scope;
      $('#chart-note').textContent = config.note;
      const fragment = document.createDocumentFragment();
      for (const model of rows) {
        const row = document.createElement('div'); row.className = `chart-row${model.model === 'AREX 2.0' ? ' ours' : ''}`;
        const label = document.createElement('span'); label.className = 'chart-model'; label.textContent = model.model;
        const marker = [model[`${key}_mark`] || '', key === 'fcs' ? (model.model_mark || '') : ''].join('');
        if (marker) { const sup = document.createElement('sup'); sup.textContent = marker; label.append(sup); }
        const track = document.createElement('span'); track.className = 'chart-track'; track.setAttribute('aria-hidden', 'true');
        const bar = document.createElement('span'); bar.className = 'chart-bar'; bar.style.setProperty('--value', `${model[key]}%`); track.append(bar);
        const score = document.createElement('span'); score.className = 'chart-value'; score.textContent = model[key].toFixed(1);
        row.append(label, track, score); fragment.append(row);
      }
      animations.forEach(a => a.cancel()); animations.clear();
      $('#chart-rows').replaceChildren(fragment);
      if (!paused && animate && Element.prototype.animate) $$('.chart-bar').forEach((bar, i) => {
        const a = bar.animate([{ transform: 'scaleX(.04)' }, { transform: 'scaleX(1)' }], { duration: 660, delay: i * 30, easing: 'cubic-bezier(.2,.7,.2,1)', fill: 'backwards' });
        animations.add(a); a.onfinish = () => animations.delete(a);
      });
      if (announce) $('#benchmark-announcement').textContent = `${config.title}: AREX 2.0 scores ${our[key].toFixed(1)}. ${config.tagline}`;
    };
    tabs.forEach((tab, i) => {
      tab.addEventListener('click', () => { select(tab.dataset.tab); });
      tab.addEventListener('keydown', e => {
        let index = i;
        if (e.key === 'ArrowRight') index = (i + 1) % tabs.length;
        else if (e.key === 'ArrowLeft') index = (i - 1 + tabs.length) % tabs.length;
        else if (e.key === 'Home') index = 0;
        else if (e.key === 'End') index = tabs.length - 1;
        else return;
        e.preventDefault(); tabs[index].focus(); select(tabs[index].dataset.tab);
      });
    });
    $$('[data-benchmark]').forEach(link => link.addEventListener('click', () => {
      select(link.dataset.benchmark);
      const tab = $(`#tab-${link.dataset.benchmark}`);
      const strip = $('.benchmark-tabs');
      // Only scroll the tab strip; do not change the page's native anchor scroll.
      strip.scrollLeft = Math.max(0, tab.offsetLeft - strip.offsetLeft - 15);
    }));
    select('mle', false, false);
    if ('IntersectionObserver' in window) {
      const observer = new IntersectionObserver(entries => {
        if (entries.some(entry => entry.isIntersecting)) { select(selected, false, true); observer.disconnect(); }
      }, { threshold: .15 });
      observer.observe($('#benchmark-panel'));
    }
  });

  safeInit('resources', () => {
    // Optional standalone builds inject the existing PDF as base64. The deployed
    // edition uses a normal same-directory PDF link and no base64 overhead.
    const embeddedPDF = $('#embedded-pdf');
    if (embeddedPDF) {
      const bin = atob(embeddedPDF.textContent.trim());
      const bytes = new Uint8Array(bin.length);
      for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
      const url = URL.createObjectURL(new Blob([bytes], { type: 'application/pdf' }));
      $$('[data-pdf]').forEach(link => { link.href = url; });
      window.addEventListener('pagehide', e => { if (!e.persisted) URL.revokeObjectURL(url); }, { once: true });
    }
    $('#download-data').addEventListener('click', () => {
      const source = benchmarkSource || JSON.parse($('#benchmark-source').textContent);
      const blob = new Blob([JSON.stringify(source, null, 2) + '\n'], { type: 'application/json' });
      const url = URL.createObjectURL(blob), anchor = document.createElement('a');
      anchor.href = url; anchor.download = 'AREX-2.0-benchmarks.json'; document.body.append(anchor); anchor.click(); anchor.remove();
      setTimeout(() => URL.revokeObjectURL(url), 5000);
      toast('Benchmark data downloaded.');
    });
    const copy = async text => {
      if (navigator.clipboard && window.isSecureContext) {
        try { await navigator.clipboard.writeText(text); return true; } catch (_) {}
      }
      const field = document.createElement('textarea'); field.value = text;
      field.style.cssText = 'position:fixed;top:-9999px;left:-9999px;'; document.body.append(field); field.select();
      let success = false; try { success = document.execCommand('copy'); } catch (_) {}
      field.remove(); return success;
    };
    $('#share-research').addEventListener('click', async () => {
      const local = location.protocol === 'file:' || ['localhost', '127.0.0.1', '[::1]'].includes(location.hostname);
      const title = 'AREX 2.0 — Advancing Self-Improving Agents through Long-Horizon Reflective Tasks';
      const summary = `${title}\nA 27B agent trained for reflection and long-horizon execution. Reported results: MLE-bench Lite 81.8; Frontier-CS 70.7; BrowseComp 84.0; HLE (text-only) 52.6.`;
      const url = local ? '' : location.origin + location.pathname;
      if (!local && navigator.share) {
        try { await navigator.share({ title, text: summary, url }); return; }
        catch (error) { if (error.name === 'AbortError') return; }
      }
      const success = await copy(local ? summary : `${summary}\n${url}`);
      toast(success ? (local ? 'Research summary copied. Local file paths are not shared.' : 'Research summary and link copied.') : 'Copy is unavailable in this browser. Use the address bar to share the page.');
    });
    let appendixWasOpen = false;
    window.addEventListener('beforeprint', () => { appendixWasOpen = $('#appendix').open; $('#appendix').open = true; });
    window.addEventListener('afterprint', () => { $('#appendix').open = appendixWasOpen; });
  });
})();
