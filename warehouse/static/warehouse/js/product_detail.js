(function () {
  const tbody = document.getElementById('history-body');
  if (!tbody) return;

  const productId = tbody.dataset.historyFor;
  const moreBtn = document.getElementById('history-more');

  if (moreBtn) {
    moreBtn.addEventListener('click', async () => {
      moreBtn.disabled = true;
      
      try {
        const data = await App.api(`/api/products/${productId}/movements/?offset=${moreBtn.dataset.offset}`);
        
        tbody.insertAdjacentHTML('beforeend', data.html);
        moreBtn.dataset.offset = data.next_offset;
        
        if (!data.has_more) {
          moreBtn.closest('.card-footer').remove();
        }
      } catch (err) {
        App.toast(err.message, 'danger');
      } finally {
        moreBtn.disabled = false;
      }
    });
  }

  document.addEventListener('stock:moved', (e) => {
    const data = e.detail;
    
    if (String(data.product.id) !== productId) return;

    const emptyRow = tbody.querySelector('.empty-row');
    if (emptyRow) emptyRow.remove();

    tbody.insertAdjacentHTML('afterbegin', data.movement_html);
    tbody.firstElementChild.classList.add('flash');

    if (moreBtn) {
      moreBtn.dataset.offset = Number(moreBtn.dataset.offset) + 1;
    }
  });
})();