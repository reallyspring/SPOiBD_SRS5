(function () {
  'use strict';

  const storage = {
    get(key, fallback) {
      try {
        const value = localStorage.getItem(key);
        return value === null ? fallback : value;
      } catch (e) {
        return fallback;
      }
    },
    set(key, value) {
      try {
        localStorage.setItem(key, value);
      } catch (e) {
      }
    },
  };

  const csrfToken = document.querySelector('meta[name="csrf-token"]').content;

  async function api(url, body) {
    const options = { headers: { Accept: 'application/json' } };
    if (body !== undefined) {
      options.method = 'POST';
      options.headers['Content-Type'] = 'application/json';
      options.headers['X-CSRFToken'] = csrfToken;
      options.body = JSON.stringify(body);
    }
    
    const response = await fetch(url, options);
    let data;
    try {
      data = await response.json();
    } catch (e) {
      throw new Error(`Сервер вернул ошибку ${response.status}`);
    }
    
    if (!response.ok || data.ok === false) {
      throw new Error(data.error || `Ошибка ${response.status}`);
    }
    return data;
  }

  const TOAST_ICONS = { success: 'circle-check', danger: 'alert-circle', info: 'info-circle' };

  function toast(message, type = 'success') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const el = document.createElement('div');
    el.className = 'toast show';
    el.setAttribute('role', 'status');
    el.innerHTML = `
      <div class="toast-body d-flex align-items-center gap-2">
        <i class="ti ti-${TOAST_ICONS[type] || 'info-circle'} fs-2 text-${type}"></i>
        <div class="flex-fill" data-role="text"></div>
        <button type="button" class="btn-close" aria-label="Закрыть"></button>
      </div>`;
    
    el.querySelector('[data-role="text"]').textContent = message;
    el.querySelector('.btn-close').addEventListener('click', () => el.remove());
    container.appendChild(el);
    
    setTimeout(() => {
      el.classList.add('fade-out');
      setTimeout(() => el.remove(), 300);
    }, 3500);
  }

  const money = new Intl.NumberFormat('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

  function updateProductEverywhere(p) {
    document.querySelectorAll(`[data-product-id="${p.id}"]`).forEach((holder) => {
      holder.querySelectorAll('[data-field="quantity"]').forEach((el) => {
        el.textContent = p.quantity;
      });
      holder.querySelectorAll('[data-field="price"]').forEach((el) => {
        el.dataset.value = p.price;
        el.textContent = `${money.format(Number(p.price))} ₽`;
      });
      holder.querySelectorAll('[data-field="stock_value"]').forEach((el) => {
        el.textContent = `${money.format(Number(p.stock_value))} ₽`;
      });
      holder.querySelectorAll('[data-field="status"]').forEach((el) => {
        el.className = `badge bg-${p.status_color}-lt`;
        el.textContent = p.status_label;
      });
      
      holder.classList.add('flash');
      setTimeout(() => holder.classList.remove('flash'), 1000);
    });
  }

  function currentTheme() {
    return document.documentElement.getAttribute('data-bs-theme') === 'dark' ? 'dark' : 'light';
  }

  document.addEventListener('click', (e) => {
    if (!e.target.closest('[data-action="toggle-theme"]')) return;
    const theme = currentTheme() === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-bs-theme', theme);
    storage.set('inv-theme', theme);
    
    document.dispatchEvent(new CustomEvent('theme:changed', { detail: { theme } }));
  });

  document.addEventListener('click', (e) => {
    const el = e.target.closest('[data-action="edit-price"]');
    if (!el || el.querySelector('input')) return;

    const id = el.closest('[data-product-id]').dataset.productId;
    const oldValue = el.dataset.value;
    const oldText = el.textContent;

    const input = document.createElement('input');
    input.type = 'number';
    input.step = '0.01';
    input.min = '0';
    input.value = oldValue;
    input.className = 'form-control form-control-sm price-input';
    el.textContent = '';
    el.appendChild(input);
    input.focus();
    input.select();

    let finished = false;
    async function finish(save) {
      if (finished) return;
      finished = true;
      
      if (!save || input.value === '' || input.value === oldValue) {
        el.textContent = oldText;
        return;
      }
      
      try {
        const data = await api(`/api/products/${id}/price/`, { price: input.value });
        updateProductEverywhere(data.product);
        toast('Цена обновлена');
      } catch (err) {
        el.textContent = oldText;
        toast(err.message, 'danger');
      }
    }

    input.addEventListener('keydown', (ev) => {
      if (ev.key === 'Enter') finish(true);
      if (ev.key === 'Escape') finish(false);
    });
    input.addEventListener('blur', () => finish(true));
  });

  const modal = document.getElementById('movement-modal');
  if (modal) {
    const form = modal.querySelector('form');
    const errorBox = modal.querySelector('[data-role="error"]');
    const submitBtn = form.querySelector('[type="submit"]');

    modal.addEventListener('show.bs.modal', (e) => {
      const btn = e.relatedTarget;
      form.reset();
      errorBox.classList.add('d-none');
      form.elements.product_id.value = btn.dataset.moveId;
      form.elements.movement_type.value = btn.dataset.moveType;
      modal.querySelector('[data-role="product-name"]').textContent = btn.dataset.moveName;
      modal.querySelector('[data-role="unit"]').textContent = btn.dataset.moveUnit;
    });

    modal.addEventListener('shown.bs.modal', () => form.elements.quantity.focus());

    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      errorBox.classList.add('d-none');
      submitBtn.disabled = true;

      try {
        const data = await api(`/api/products/${form.elements.product_id.value}/move/`, {
          movement_type: form.elements.movement_type.value,
          quantity: form.elements.quantity.value,
          comment: form.elements.comment.value,
        });

        updateProductEverywhere(data.product);
        
        document.dispatchEvent(new CustomEvent('stock:moved', { detail: data }));
        
        modal.querySelector('[data-bs-dismiss="modal"]').click();
        toast(data.message);
        
      } catch (err) {
        errorBox.textContent = err.message;
        errorBox.classList.remove('d-none');
      } finally {
        submitBtn.disabled = false;
      }
    });
  }

  window.App = { api, toast, storage, updateProductEverywhere, currentTheme };
})();