const command = `python3 -m arex_v2 research BrowseComp \\\n  --n 5 --save-path runs/smoke`;
const copyButton = document.querySelector('#copy-command');
const copyStatus = document.querySelector('#copy-status');
if (copyButton) {
  copyButton.addEventListener('click', async () => {
    try {
      await navigator.clipboard.writeText(command);
      copyStatus.textContent = 'copied to clipboard';
      copyButton.textContent = 'copied';
      setTimeout(() => { copyStatus.textContent = ''; copyButton.textContent = 'copy'; }, 1800);
    } catch (_) {
      copyStatus.textContent = 'select the command manually';
    }
  });
}
const links = [...document.querySelectorAll('.nav a[data-section]')];
const sections = links.map(link => document.getElementById(link.dataset.section)).filter(Boolean);
const observer = new IntersectionObserver(entries => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      links.forEach(link => link.classList.toggle('active', link.dataset.section === entry.target.id));
    }
  });
}, { rootMargin: '-30% 0px -58% 0px', threshold: 0 });
sections.forEach(section => observer.observe(section));
