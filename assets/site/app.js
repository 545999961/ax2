/* Small progressive enhancements for the static AREX-2 homepage. */
(() => {
  const header = document.querySelector('.site-header');
  const links = [...document.querySelectorAll('.site-nav a')];
  const sections = links.map(link => document.querySelector(link.getAttribute('href'))).filter(Boolean);
  const update = () => {
    header.classList.toggle('is-scrolled', window.scrollY > 8);
    let active = sections[0];
    for (const section of sections) {
      if (section.getBoundingClientRect().top <= 120) active = section;
    }
    links.forEach(link => link.toggleAttribute('aria-current', link.getAttribute('href') === `#${active.id}`));
  };
  window.addEventListener('scroll', update, { passive: true });
  update();
})();
