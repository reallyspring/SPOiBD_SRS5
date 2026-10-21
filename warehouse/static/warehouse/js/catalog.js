(function () {
  const form = document.getElementById('catalog-form');
  if (!form) return;

  const listEl = document.getElementById('catalog-list');
  const statusEl = document.getElementById('catalog-status');
  const detailEl = document.getElementById('catalog-detail');
  const countEl = document.getElementById('catalog-count');
  const pageLabel = document.getElementById('catalog-page-label');
  const prevBtn = document.getElementById('catalog-prev');
  const nextBtn = document.getElementById('catalog-next');

  const ORDERING_KEY = 'inv-catalog-ordering';
  const DETAIL_HINT = detailEl.innerHTML;
  const money = new Intl.NumberFormat('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

  const params = new URLSearchParams(location.search);
  const state = {
    search: params.get('search') || '',
    category: params.get('category') || '',
    status: params.get('status') || '',
    ordering: params.get('ordering') || App.storage.get(ORDERING_KEY, 'name'),
    page: Number(params.get('page')) || 1,
    selected: params.get('selected') || '',
  };

  for (const name of ['search', 'category', 'status', 'ordering']) {
    form.elements[name].value = state[name];
    state[name] = form.elements[name].value;
  }
  if (!state.ordering) state.ordering = form.elements.ordering.value = 'name';

  function saveState() {
    const query = new URLSearchParams();
    for (const [key, value] of Object.entries(state)) {
      if (value && !(key === 'page' && value === 1) && !(key === 'ordering' && value === 'name')) {
        query.set(key, value);
      }
    }
    history.replaceState(null, '', query.toString() ? `?${query}` : location.pathname);
    App.storage.set(ORDERING_KEY, state.ordering);
  }

  async function getJSON(url, signal) {
    let response;
    try {
      response = await fetch(url, { headers: { Accept: 'application/json' }, signal });
    } catch (err) {
      if (err.name === 'AbortError') throw err;
      throw new Error('Сервер недоступен. Проверьте подключение и повторите попытку.');
    }
    let data = null;
    try {
      data = await response.json();
    } catch (err) {
      if (err.name === 'AbortError') throw err;
    }
    if (!response.ok || !data || data.ok === false) {
      throw new Error((data && data.error) || `Ошибка сервера (${response.status})`);
    }
    return data;
  }

  function showStatus(kind, message) {
    listEl.classList.toggle('is-loading', kind === 'loading');
    if (kind === 'loading') {
      statusEl.innerHTML = `
        <div class="d-flex align-items-center gap-2 text-secondary px-3 py-2">
          <span class="spinner-border spinner-border-sm"></span>Загрузка…
        </div>`;
    } else if (kind === 'empty') {
      statusEl.innerHTML = `
        <div class="empty py-4">
          <div class="empty-icon"><i class="ti ti-mood-empty fs-1"></i></div>
          <p class="empty-title">Ничего не найдено</p>
          <p class="empty-subtitle text-secondary">Измените запрос или сбросьте фильтры</p>
          <button type="button" class="btn btn-sm" data-action="reset">Сбросить фильтры</button>
        </div>`;
    } else if (kind === 'error') {
      statusEl.innerHTML = `
        <div class="alert alert-danger m-3" role="alert">
          <div class="d-flex justify-content-between align-items-center gap-2">
            <div data-role="text"></div>
            <button type="button" class="btn btn-sm" data-action="retry">Повторить</button>
          </div>
        </div>`;
      statusEl.querySelector('[data-role="text"]').textContent = message;
    } else {
      statusEl.innerHTML = '';
    }
  }

  let listController = null;
  let listRequestId = 0;

  async function loadList() {
    if (listController) listController.abort();
    listController = new AbortController();
    const requestId = ++listRequestId;
    saveState();
    showStatus('loading');

    const query = new URLSearchParams({
      search: state.search,
      category: state.category,
      status: state.status,
      ordering: state.ordering,
      page: state.page,
    });

    try {
      const data = await getJSON(`/api/catalog/?${query}`, listController.signal);
      if (requestId !== listRequestId) return;
      renderList(data);
    } catch (err) {
      if (err.name === 'AbortError' || requestId !== listRequestId) return;
      listEl.replaceChildren();
      countEl.textContent = '—';
      pageLabel.textContent = '';
      prevBtn.disabled = nextBtn.disabled = true;
      showStatus('error', err.message);
    }
  }

  function renderList(data) {
    state.page = data.page;
    countEl.textContent = data.count;
    pageLabel.textContent = `Страница ${data.page} из ${data.pages}`;
    prevBtn.disabled = data.page <= 1;
    nextBtn.disabled = data.page >= data.pages;
    listEl.replaceChildren(...data.results.map(renderItem));
    showStatus(data.count === 0 ? 'empty' : 'ok');
    saveState();
  }

  function renderItem(p) {
    const item = document.createElement('button');
    item.type = 'button';
    item.className = 'list-group-item list-group-item-action catalog-item';
    item.dataset.id = p.id;
    item.classList.toggle('active', String(p.id) === state.selected);
    item.innerHTML = `
      <div class="d-flex justify-content-between align-items-start gap-2">
        <div class="catalog-item-text">
          <div class="fw-medium" data-role="name"></div>
          <div class="text-secondary small" data-role="meta"></div>
        </div>
        <div class="text-end text-nowrap">
          <div class="fw-medium" data-role="price"></div>
          <span data-role="status"></span>
        </div>
      </div>`;
    item.querySelector('[data-role="name"]').textContent = p.name;
    item.querySelector('[data-role="meta"]').textContent = `${p.sku} · ${p.category} · ${p.quantity} ${p.unit}`;
    item.querySelector('[data-role="price"]').textContent = `${money.format(Number(p.price))} ₽`;
    const badge = item.querySelector('[data-role="status"]');
    badge.className = `badge bg-${p.status_color}-lt`;
    badge.textContent = p.status_label;
    return item;
  }

  let detailController = null;
  let detailRequestId = 0;

  async function loadDetail() {
    if (detailController) detailController.abort();
    const requestId = ++detailRequestId;
    if (!state.selected) {
      detailEl.innerHTML = DETAIL_HINT;
      return;
    }
    detailController = new AbortController();
    detailEl.innerHTML = `
      <div class="card-body text-center text-secondary py-5">
        <span class="spinner-border mb-2"></span>
        <div>Загрузка карточки…</div>
      </div>`;
    try {
      const data = await getJSON(`/api/catalog/${state.selected}/`, detailController.signal);
      if (requestId !== detailRequestId) return;
      renderDetail(data.product);
    } catch (err) {
      if (err.name === 'AbortError' || requestId !== detailRequestId) return;
      detailEl.innerHTML = `
        <div class="card-body">
          <div class="alert alert-danger mb-0" role="alert" data-role="text"></div>
        </div>`;
      detailEl.querySelector('[data-role="text"]').textContent = err.message;
    }
  }

  function renderDetail(p) {
    detailEl.innerHTML = `
      <div class="card-header">
        <h3 class="card-title" data-role="name"></h3>
        <div class="card-actions"><span data-role="status"></span></div>
      </div>
      <div class="card-body">
        <dl class="row mb-3" data-role="fields"></dl>
        <h4 class="mb-2">Последние операции</h4>
        <div class="list-group list-group-flush" data-role="movements"></div>
      </div>
      <div class="card-footer text-end">
        <a class="btn btn-primary" data-role="link">
          <i class="ti ti-external-link me-1"></i>Открыть страницу товара
        </a>
      </div>`;
    detailEl.querySelector('[data-role="name"]').textContent = p.name;
    const badge = detailEl.querySelector('[data-role="status"]');
    badge.className = `badge bg-${p.status_color}-lt`;
    badge.textContent = p.status_label;
    detailEl.querySelector('[data-role="link"]').href = p.url;

    const fields = [
      ['Артикул', p.sku],
      ['Категория', p.category],
      ['Поставщик', p.supplier],
      ['Цена', `${money.format(Number(p.price))} ₽`],
      ['Остаток', `${p.quantity} ${p.unit} (мин. ${p.min_quantity})`],
      ['Стоимость остатка', `${money.format(Number(p.stock_value))} ₽`],
      ['Пришло / ушло', `+${p.total_in} / −${p.total_out}`],
    ];
    detailEl.querySelector('[data-role="fields"]').replaceChildren(
      ...fields.flatMap(([label, value]) => {
        const dt = document.createElement('dt');
        dt.className = 'col-6 fw-normal text-secondary';
        dt.textContent = label;
        const dd = document.createElement('dd');
        dd.className = 'col-6 text-end';
        dd.textContent = value;
        return [dt, dd];
      })
    );

    const movesEl = detailEl.querySelector('[data-role="movements"]');
    if (!p.movements.length) {
      movesEl.textContent = 'Операций ещё не было';
      return;
    }
    movesEl.replaceChildren(...p.movements.map((m) => {
      const row = document.createElement('div');
      row.className = 'list-group-item px-0 d-flex justify-content-between gap-2';
      row.innerHTML = `
        <div>
          <div class="small text-secondary" data-role="date"></div>
          <div data-role="comment"></div>
        </div>
        <div class="fw-medium text-nowrap" data-role="qty"></div>`;
      row.querySelector('[data-role="date"]').textContent = m.date;
      row.querySelector('[data-role="comment"]').textContent = m.comment || (m.type === 'in' ? 'Приход' : 'Расход');
      const qty = row.querySelector('[data-role="qty"]');
      qty.className = `fw-medium text-nowrap ${m.type === 'in' ? 'text-green' : 'text-red'}`;
      qty.textContent = `${m.type === 'in' ? '+' : '−'}${m.quantity} ${p.unit}`;
      return row;
    }));
  }

  let timer = null;

  form.addEventListener('input', (e) => {
    state[e.target.name] = e.target.value;
    state.page = 1;
    clearTimeout(timer);
    timer = setTimeout(loadList, e.target.name === 'search' ? 300 : 0);
  });
  form.addEventListener('submit', (e) => e.preventDefault());

  prevBtn.addEventListener('click', () => { state.page -= 1; loadList(); });
  nextBtn.addEventListener('click', () => { state.page += 1; loadList(); });

  listEl.addEventListener('click', (e) => {
    const item = e.target.closest('.catalog-item');
    if (!item) return;
    state.selected = item.dataset.id;
    listEl.querySelectorAll('.catalog-item').forEach((el) => el.classList.toggle('active', el === item));
    saveState();
    loadDetail();
    if (window.innerWidth < 768) detailEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
  });

  statusEl.addEventListener('click', (e) => {
    const button = e.target.closest('[data-action]');
    if (!button) return;
    if (button.dataset.action === 'reset') {
      Object.assign(state, { search: '', category: '', status: '', page: 1 });
      form.elements.search.value = form.elements.category.value = form.elements.status.value = '';
    }
    loadList();
  });

  loadList();
  loadDetail();
})();