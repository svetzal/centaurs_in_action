const status = document.querySelector('.copy-status');
for (const button of document.querySelectorAll('[data-copy]')) {
  button.hidden = false;
  button.addEventListener('click', async () => {
    const prompt = document.getElementById(button.dataset.copy);
    try {
      await navigator.clipboard.writeText(prompt.textContent);
      status.textContent = 'Image prompt copied. Attach the character reference sheet when you use it.';
      button.textContent = 'Copied';
      window.setTimeout(() => { button.textContent = 'Copy image prompt'; }, 2000);
    } catch {
      const selection = window.getSelection();
      const range = document.createRange();
      range.selectNodeContents(prompt);
      selection.removeAllRanges();
      selection.addRange(range);
      status.textContent = 'Clipboard access is unavailable. The prompt is selected; use your browser’s Copy command.';
      button.textContent = 'Prompt selected — copy manually';
    }
  });
}

const expressionGrid = document.querySelector('[data-expression-grid]');
const formToggle = document.querySelector('.form-toggle');
if (expressionGrid && formToggle) {
  formToggle.hidden = false;
  for (const button of formToggle.querySelectorAll('[data-form]')) {
    button.addEventListener('click', () => {
      const form = button.dataset.form;
      expressionGrid.dataset.form = form;
      for (const other of formToggle.querySelectorAll('[data-form]')) {
        const active = other === button;
        other.classList.toggle('is-active', active);
        other.setAttribute('aria-pressed', String(active));
      }
      for (const image of expressionGrid.querySelectorAll('[data-expression]')) {
        image.src = `assets/${form}-${image.dataset.expression}.png`;
        image.alt = `${expressionGrid.dataset.character} ${image.dataset.emotion} in ${form === 'human' ? 'centaur' : 'reverse-centaur'} form`;
      }
    });
  }
}
