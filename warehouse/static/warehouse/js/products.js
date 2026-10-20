(function () {
  const list = document.getElementById('product-list');
  const form = document.getElementById('filter-form');
  const counter = document.getElementById('products-count');
  
  if (!list || !form) return;

  const VIEW_KEY = 'inv-products-view';
  const viewButtons = document.querySelectorAll('[data-view]');

  function setView(view) {
    if (view !== 'table' && view !== 'cards') view = 'table';
    
    list.classList.toggle('view-table', view === 'table');
    list.classList.toggle('view-cards', view === 'cards');
    
    viewButtons.forEach((b) =>
      b.classList.toggle('active', b.dataset.view === view)
    );
    
    App.storage.set(VIEW_KEY, view);
  }

  viewButtons.forEach((b) =>
    b.addEventListener('click', () => setView(b.dataset.view))
  );
  
  setView(App.storage.get(VIEW_KEY, 'table'));


  let timer = null;
  let lastRequest = 0;

  async function refresh() {
    const params = new URLSearchParams(new FormData(form));
    
    for (const [key, value] of [...params]) {
      if (value === '') params.delete(key);
    }
    
    const query = params.toString();
    
    history.replaceState(null, '', query ? `?${query}` : location.pathname);
    
    const requestId = ++lastRequest;
    list.classList.add('is-loading');
    
    try {
      const data = await App.api(`/api/products/search/?${query}`);
      
      if (requestId !== lastRequest) return;
      
      list.innerHTML = data.html;
      counter.textContent = data.count;
      
    } catch (err) {
      App.toast(err.message, 'danger');
    } finally {
      if (requestId === lastRequest) {
        list.classList.remove('is-loading');
      }
    }
  }

  form.addEventListener('input', (e) => {
    clearTimeout(timer);
    timer = setTimeout(refresh, e.target.name === 'q' ? 300 : 0);
  });

  form.addEventListener('submit', (e) => {
    e.preventDefault();
    refresh();
  });


  list.addEventListener('click', async (e) => {
    const btn = e.target.closest('[data-action="archive"]');
    if (!btn) return;
    
    const id = btn.closest('[data-product-id]').dataset.productId;
    
    if (!confirm(`Переместить «${btn.dataset.name}» в архив?`)) return;
    
    try {
      await App.api(`/api/products/${id}/archive/`, {});
      
      list.querySelectorAll(`[data-product-id="${id}"]`).forEach((el) => {
        el.classList.add('fade-out');
        setTimeout(() => el.remove(), 300);
      });
      
      counter.textContent = Math.max(0, Number(counter.textContent) - 1);
      App.toast('Товар перемещён в архив');
      
    } catch (err) {
      App.toast(err.message, 'danger');
    }
  });
})();