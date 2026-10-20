(function () {
  const el = document.getElementById('movements-chart');
  if (!el) return;

  const PERIOD_KEY = 'inv-chart-days';
  const PERIODS = ['7', '14', '30'];
  const buttons = document.querySelectorAll('[data-chart-days]');

  const cssVar = (name) =>
    getComputedStyle(document.documentElement).getPropertyValue(name).trim();

  const chart = new ApexCharts(el, {
    chart: {
      type: 'bar',
      height: 300,
      toolbar: { show: false },
      fontFamily: 'inherit',
      background: 'transparent',
    },
    theme: { mode: App.currentTheme() },
    series: [
      { name: 'Приход', data: [] },
      { name: 'Расход', data: [] },
    ],
    colors: [
      cssVar('--tblr-green') || '#2fb344',
      cssVar('--tblr-red') || '#d63939',
    ],
    plotOptions: {
      bar: { columnWidth: '60%', borderRadius: 3 },
    },
    dataLabels: { enabled: false },
    legend: { position: 'top' },
    grid: { strokeDashArray: 4 },
    xaxis: {
      categories: [],
      labels: { hideOverlappingLabels: true },
    },
    noData: { text: 'Загрузка…' },
    responsive: [
      {
        breakpoint: 576,
        options: {
          chart: { height: 220 },
          legend: { position: 'bottom' },
        },
      },
    ],
  });

  chart.render();

  async function load(days) {
    if (!PERIODS.includes(days)) days = '14';
    buttons.forEach((b) =>
      b.classList.toggle('active', b.dataset.chartDays === days)
    );
    App.storage.set(PERIOD_KEY, days);

    try {
      const data = await App.api(`/api/stats/movements/?days=${days}`);
      chart.updateOptions({ xaxis: { categories: data.labels } });
      chart.updateSeries([
        { name: 'Приход', data: data.income },
        { name: 'Расход', data: data.outcome },
      ]);
    } catch (err) {
      App.toast(err.message, 'danger');
    }
  }

  buttons.forEach((b) =>
    b.addEventListener('click', () => load(b.dataset.chartDays))
  );

  document.addEventListener('theme:changed', (e) =>
    chart.updateOptions({ theme: { mode: e.detail.theme } })
  );

  load(App.storage.get(PERIOD_KEY, '14'));
})();