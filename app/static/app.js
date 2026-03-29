const state = {
  companies: [],
  selectedSymbol: null,
  compareSymbol: null,
  days: 30,
  topMovers: null,
  priceChart: null,
  comparisonChart: null,
  activeRequests: 0,
};

const currencyFormatter = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  maximumFractionDigits: 2,
});

const compactCurrencyFormatter = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  notation: "compact",
  maximumFractionDigits: 1,
});

const percentFormatter = new Intl.NumberFormat("en-IN", {
  style: "percent",
  maximumFractionDigits: 2,
});

const axisDateFormatter = new Intl.DateTimeFormat("en-US", {
  month: "short",
  day: "numeric",
});

function showLoader() {
  state.activeRequests += 1;
  document.getElementById("global-loader").classList.remove("hidden");
}

function hideLoader() {
  state.activeRequests = Math.max(0, state.activeRequests - 1);
  if (state.activeRequests === 0) {
    document.getElementById("global-loader").classList.add("hidden");
  }
}

async function fetchJson(url) {
  showLoader();
  try {
    const response = await fetch(url);
    if (!response.ok) {
      const error = await response.json().catch(() => ({
        error: "Could not load data. Please try again.",
      }));
      throw new Error(error.error || "Could not load data. Please try again.");
    }
    return response.json();
  } finally {
    hideLoader();
  }
}

async function initializeDashboard() {
  try {
    const companyResponse = await fetchJson("/companies");
    state.companies = companyResponse.companies;
    state.selectedSymbol = state.companies[0];
    state.compareSymbol = state.companies[1] || state.companies[0];

    renderCompanyList();
    renderCompareOptions();
    bindFilters();
    await loadTopMovers();
    await refreshDashboard();
  } catch (error) {
    renderBannerError(error.message);
    document.getElementById("selected-symbol").textContent = "Dashboard failed to load";
  }
}

function bindFilters() {
  document.querySelectorAll(".filter-button").forEach((button) => {
    button.addEventListener("click", async () => {
      document.querySelectorAll(".filter-button").forEach((node) => node.classList.remove("active"));
      button.classList.add("active");
      state.days = Number(button.dataset.days);
      await refreshDashboard();
    });
  });

  document.getElementById("compare-symbol").addEventListener("change", async (event) => {
    state.compareSymbol = event.target.value;
    await renderComparisonChart();
  });
}

function renderCompanyList() {
  const container = document.getElementById("company-list");
  container.innerHTML = "";

  state.companies.forEach((symbol) => {
    const button = document.createElement("button");
    button.className = `symbol-button ${symbol === state.selectedSymbol ? "active" : ""}`;
    button.textContent = symbol;
    button.addEventListener("click", async () => {
      state.selectedSymbol = symbol;
      if (state.compareSymbol === symbol) {
        state.compareSymbol = state.companies.find((item) => item !== symbol) || symbol;
        renderCompareOptions();
      }
      renderCompanyList();
      await refreshDashboard();
    });
    container.appendChild(button);
  });
}

function renderTopMovers() {
  const errorNode = document.getElementById("top-movers-error");
  hideError(errorNode);

  if (!state.topMovers) {
    showError(errorNode, "Could not load data. Please try again.");
    return;
  }

  renderMoverColumn("top-gainers", state.topMovers.gainers, "gain");
  renderMoverColumn("top-losers", state.topMovers.losers, "loss");
}

async function loadTopMovers() {
  try {
    state.topMovers = await fetchJson("/top-movers");
    renderTopMovers();
  } catch (error) {
    state.topMovers = null;
    renderTopMovers();
  }
}

function renderMoverColumn(containerId, movers, type) {
  const container = document.getElementById(containerId);
  container.innerHTML = "";

  movers.forEach((mover) => {
    const card = document.createElement("article");
    card.className = `mover-card ${type}`;
    card.innerHTML = `
      <p>${mover.symbol}</p>
      <h4>${percentFormatter.format(mover.return)}</h4>
    `;
    container.appendChild(card);
  });
}

function renderCompareOptions() {
  const select = document.getElementById("compare-symbol");
  select.innerHTML = "";

  state.companies
    .filter((symbol) => symbol !== state.selectedSymbol)
    .forEach((symbol) => {
      const option = document.createElement("option");
      option.value = symbol;
      option.textContent = symbol;
      option.selected = symbol === state.compareSymbol;
      select.appendChild(option);
    });

  if (!select.value) {
    state.compareSymbol = state.companies.find((symbol) => symbol !== state.selectedSymbol) || state.selectedSymbol;
    select.value = state.compareSymbol;
  }
}

async function refreshDashboard() {
  renderCompareOptions();
  clearDashboardErrors();

  try {
    const [summary, stockData] = await Promise.all([
      fetchJson(`/summary/${state.selectedSymbol}`),
      fetchJson(`/data/${state.selectedSymbol}?days=${state.days}`),
    ]);
    const predictions =
      state.days === 7
        ? []
        : await fetchJson(`/predict/${state.selectedSymbol}`)
            .then((response) => response.predictions)
            .catch(() => {
              showError(document.getElementById("price-chart-error"), "Prediction line unavailable for this symbol right now.");
              return [];
            });

    document.getElementById("selected-symbol").textContent = `${state.selectedSymbol} · Last ${state.days} Days`;
    renderSummary(summary);
    renderPriceChart(stockData.records, predictions);
    await renderComparisonChart();
  } catch (error) {
    renderBannerError(error.message);
    showError(document.getElementById("price-chart-error"), "Could not load data. Please try again.");
  }
}

function renderSummary(summary) {
  const grid = document.getElementById("summary-grid");
  const tiles = [
    ["52-Week High", currencyFormatter.format(summary.high_52_week)],
    ["52-Week Low", currencyFormatter.format(summary.low_52_week)],
    ["Average Close", currencyFormatter.format(summary.average_closing_price)],
    [
      summary.custom_metric_name || "Volatility",
      summary.latest_custom_metric_value === null ? "N/A" : percentFormatter.format(summary.latest_custom_metric_value),
    ],
  ];

  const markup = tiles
    .map(
      ([label, value]) => `
        <article class="summary-tile">
          <p>${label}</p>
          <h4>${value}</h4>
        </article>
      `
    )
    .join("");

  grid.innerHTML =
    markup ||
    `
      <article class="summary-tile">
        <p>Overview</p>
        <h4>Data unavailable</h4>
      </article>
    `;
}

function renderPriceChart(records, predictions) {
  const context = document.getElementById("price-chart").getContext("2d");
  const labels = records.map((record) => record.date);
  const rawLabels = [...labels, ...predictions.map((record) => record.date)];
  const closingPrices = records.map((record) => record.close);
  const movingAverage = records.map((record) => record.moving_average_7);
  const predictionLabels = predictions.map((record) => record.date);
  const formattedLabels = rawLabels.map((label) => formatDateLabel(label));
  const predictedPrices = [
    ...new Array(labels.length).fill(null),
    ...predictions.map((record) => record.predicted_price),
  ];

  if (state.priceChart) {
    state.priceChart.destroy();
  }

  state.priceChart = new Chart(context, {
    type: "line",
    data: {
      labels: formattedLabels,
      datasets: [
        {
          label: "Closing Price",
          data: [...closingPrices, ...new Array(predictionLabels.length).fill(null)],
          borderColor: "#0f766e",
          backgroundColor: "rgba(15, 118, 110, 0.12)",
          borderWidth: 2.25,
          pointRadius: 0,
          pointHoverRadius: 4,
          pointHoverBackgroundColor: "#0f766e",
          pointHoverBorderColor: "#fffaf1",
          pointHoverBorderWidth: 2,
          tension: 0.25,
          fill: true,
        },
        {
          label: "7-Day Moving Average",
          data: [...movingAverage, ...new Array(predictionLabels.length).fill(null)],
          borderColor: "#ef8354",
          backgroundColor: "transparent",
          borderWidth: 2,
          pointRadius: 0,
          pointHoverRadius: 3,
          pointHoverBackgroundColor: "#ef8354",
          pointHoverBorderColor: "#fffaf1",
          pointHoverBorderWidth: 2,
          tension: 0.25,
        },
        ...(state.days === 7
          ? []
          : [
              {
                label: "Predicted (Linear Regression)",
                data: predictedPrices,
                borderColor: "#f97316",
                backgroundColor: "transparent",
                borderWidth: 2,
                pointRadius: 0,
                pointHoverRadius: 3,
                pointHoverBackgroundColor: "#f97316",
                pointHoverBorderColor: "#fffaf1",
                pointHoverBorderWidth: 2,
                tension: 0.25,
                borderDash: [6, 6],
              },
            ]),
      ],
    },
    options: buildChartOptions({
      title: `${state.selectedSymbol} Closing Price · Last ${state.days} Days`,
      formatPrice: true,
      rawLabels,
    }),
  });
}

async function renderComparisonChart() {
  if (!state.compareSymbol) {
    return;
  }

  try {
    const data = await fetchJson(
      `/compare?symbol1=${state.selectedSymbol}&symbol2=${state.compareSymbol}&days=${state.days}`
    );

    const context = document.getElementById("comparison-chart").getContext("2d");

    if (state.comparisonChart) {
      state.comparisonChart.destroy();
    }

    hideError(document.getElementById("comparison-chart-error"));
    const comparisonRawLabels = data.records.map((record) => record.date);
    state.comparisonChart = new Chart(context, {
      type: "line",
      data: {
        labels: comparisonRawLabels.map((record) => formatDateLabel(record)),
        datasets: [
          {
            label: `${data.symbol1} Normalized`,
            data: data.records.map((record) => record.normalized_close_symbol1),
            borderColor: "#264653",
            borderWidth: 2.25,
            pointRadius: 0,
            pointHoverRadius: 4,
            pointHoverBackgroundColor: "#264653",
            pointHoverBorderColor: "#fffaf1",
            pointHoverBorderWidth: 2,
            tension: 0.25,
          },
          {
            label: `${data.symbol2} Normalized`,
            data: data.records.map((record) => record.normalized_close_symbol2),
            borderColor: "#e76f51",
            borderWidth: 2.25,
            pointRadius: 0,
            pointHoverRadius: 4,
            pointHoverBackgroundColor: "#e76f51",
            pointHoverBorderColor: "#fffaf1",
            pointHoverBorderWidth: 2,
            tension: 0.25,
          },
        ],
      },
      options: buildChartOptions({
        title: `${data.symbol1} vs ${data.symbol2} · Last ${state.days} Days`,
        formatPrice: false,
        rawLabels: comparisonRawLabels,
      }),
    });
  } catch (error) {
    showError(document.getElementById("comparison-chart-error"), "Could not load comparison data. Please try again.");
  }
}

function buildChartOptions({ title, formatPrice, rawLabels }) {
  return {
    responsive: true,
    maintainAspectRatio: false,
    interaction: { mode: "index", intersect: false },
    plugins: {
      title: {
        display: true,
        text: title,
        color: "#122620",
        font: { size: 14, weight: "600" },
        padding: { bottom: 14 },
      },
      legend: {
        labels: {
          usePointStyle: true,
          color: "#30433c",
          padding: 14,
          font: { size: 12, weight: "500" },
        },
      },
      tooltip: {
        backgroundColor: "rgba(18, 38, 32, 0.92)",
        borderColor: "rgba(255, 250, 241, 0.12)",
        borderWidth: 1,
        titleColor: "#fffaf1",
        bodyColor: "#fffaf1",
        displayColors: true,
        padding: 10,
        callbacks: {
          title: (items) => formatTooltipDate(rawLabels[items[0].dataIndex]),
          label: (context) => {
            const value = context.parsed.y;
            if (value === null || value === undefined) {
              return `${context.dataset.label}: N/A`;
            }
            return formatPrice
              ? `${context.dataset.label}: ${currencyFormatter.format(value)}`
              : `${context.dataset.label}: ${value.toFixed(2)}`;
          },
        },
      },
    },
    scales: {
      x: {
        grid: {
          display: false,
        },
        title: {
          display: true,
          text: "Trading Date",
          color: "#5f6f65",
          font: { size: 12, weight: "600" },
          padding: { top: 10 },
        },
        ticks: {
          color: "#5f6f65",
          maxRotation: 0,
          autoSkip: true,
          maxTicksLimit: 8,
          padding: 8,
        },
        border: {
          display: false,
        },
      },
      y: {
        ticks: {
          callback: (value) => (formatPrice ? formatAxisPrice(value) : formatAxisIndex(value)),
          color: "#5f6f65",
          padding: 10,
          maxTicksLimit: 6,
        },
        title: {
          display: true,
          text: formatPrice ? "Price (₹)" : "Normalized Index",
          color: "#5f6f65",
          font: { size: 12, weight: "600" },
          padding: { bottom: 10 },
        },
        grid: {
          color: "rgba(18, 38, 32, 0.07)",
        },
        border: {
          display: false,
        },
      },
    },
  };
}

function formatAxisPrice(value) {
  if (Math.abs(value) >= 1000) {
    return compactCurrencyFormatter.format(value).replace(".0", "");
  }

  return `₹${Math.round(value)}`;
}

function formatAxisIndex(value) {
  return Number(value).toFixed(1);
}

function formatTooltipDate(rawDate) {
  if (!rawDate) {
    return "";
  }

  const parsedDate = new Date(`${rawDate}T00:00:00`);
  if (Number.isNaN(parsedDate.getTime())) {
    return String(rawDate);
  }

  return parsedDate.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function formatDateLabel(rawDate) {
  if (!rawDate) {
    return "";
  }

  const parsedDate = new Date(`${rawDate}T00:00:00`);
  if (Number.isNaN(parsedDate.getTime())) {
    return String(rawDate);
  }

  return axisDateFormatter.format(parsedDate);
}

function showError(element, message) {
  element.textContent = message;
  element.classList.remove("hidden");
}

function hideError(element) {
  element.textContent = "";
  element.classList.add("hidden");
}

function clearDashboardErrors() {
  hideError(document.getElementById("dashboard-error"));
  hideError(document.getElementById("price-chart-error"));
  hideError(document.getElementById("comparison-chart-error"));
}

function renderBannerError(message) {
  showError(document.getElementById("dashboard-error"), message || "Could not load data. Please try again.");
}

initializeDashboard().catch((error) => {
  renderBannerError(error.message || "Could not load data. Please try again.");
  document.getElementById("selected-symbol").textContent = "Dashboard failed to load";
  document.getElementById("summary-grid").innerHTML =
    '<article class="summary-tile"><p>Error</p><h4>Could not load data. Please try again.</h4></article>';
});
