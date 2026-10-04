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
