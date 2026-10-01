(() => {
  const menuButton = document.querySelector('.menu-button');
  const nav = document.querySelector('.site-nav');
  if (menuButton && nav) {
    menuButton.addEventListener('click', () => {
      const opened = nav.classList.toggle('is-open');
      menuButton.classList.toggle('is-open', opened);
      menuButton.setAttribute('aria-expanded', String(opened));
    });
    nav.querySelectorAll('a').forEach((link) => link.addEventListener('click', () => {
      nav.classList.remove('is-open');
      menuButton.classList.remove('is-open');
      menuButton.setAttribute('aria-expanded', 'false');
    }));
  }

  const dialog = document.querySelector('#photo-dialog');
  const dialogImage = document.querySelector('#dialog-image');
  const dialogCaption = document.querySelector('#dialog-caption');
  const closeButton = document.querySelector('.lightbox-close');
  document.querySelectorAll('.talk-photo').forEach((button) => {
    button.addEventListener('click', () => {
      dialogImage.src = button.dataset.full;
      dialogImage.alt = button.querySelector('img').alt;
      dialogCaption.textContent = button.dataset.caption;
      dialog.showModal();
    });
  });
  closeButton?.addEventListener('click', () => dialog.close());
  dialog?.addEventListener('click', (event) => {
    if (event.target === dialog) dialog.close();
  });
})();
