const MONTH_ORDER = [
  "jan","feb","mar","apr","may","jun","jul","aug","sep","oct","nov","dec"
];

document.addEventListener("DOMContentLoaded", () => {
  const config = window.dashboardConfig || {};
  const regionSelect = document.getElementById("regionSelect");
  const parameterSelect = document.getElementById("parameterSelect");
  const periodTypeSelect = document.getElementById("periodTypeSelect");
  const startYearInput = document.getElementById("startYearInput");
  const endYearInput = document.getElementById("endYearInput");
  const refreshButton = document.getElementById("refreshButton");
  const tableBody = document.getElementById("recordsTableBody");
  const tableMeta = document.getElementById("tableMeta");
  const chartMeta = document.getElementById("chartMeta");
  const summaryCount = document.getElementById("summaryCount");
  const summaryMin = document.getElementById("summaryMin");
  const summaryMax = document.getElementById("summaryMax");
  const summaryAvg = document.getElementById("summaryAvg");
  const groupButtons = Array.from(document.querySelectorAll(".chart-group-btn"));

  if (config.defaultRegion) regionSelect.value = config.defaultRegion;
  if (config.defaultParameter) parameterSelect.value = config.defaultParameter;

  let chartInstance;

  function formatValue(value) {
    if (value === null || value === undefined) return "-";
    const num = Number(value);
    if (Number.isNaN(num)) return "-";
    return num.toFixed(2);
  }

  function buildQuery() {
    const params = new URLSearchParams();
    params.set("region", regionSelect.value);
    params.set("parameter", parameterSelect.value);
    params.set("period_type", periodTypeSelect.value);
    params.set("ordering", "year,period");
    params.set("limit", "5000");
    if (startYearInput.value) params.set("start_year", startYearInput.value);
    if (endYearInput.value) params.set("end_year", endYearInput.value);
    return params;
  }

  function updateTable(records, total) {
    if (!records.length) {
      tableBody.innerHTML = `<tr><td colspan="3">No data available.</td></tr>`;
      tableMeta.textContent = "0 rows";
      return;
    }

    tableBody.innerHTML = records
      .map(
        (record) => `
      <tr>
        <td>${record.year}</td>
        <td>${record.period.toUpperCase()}</td>
        <td>${formatValue(record.value)}</td>
      </tr>`
      )
      .join("");

    tableMeta.textContent = `${records.length} of ${total} rows`;
  }

  function periodToOrder(record) {
    if (record.period_type === "month") {
      return MONTH_ORDER.indexOf(record.period.toLowerCase());
    }
    const order = { win: 0, spr: 1, sum: 2, aut: 3, ann: 4 };
    return order[record.period.toLowerCase()] ?? 0;
  }

  function updateChart(records) {
    const sorted = [...records].sort((a, b) => {
      if (a.year === b.year) {
        return periodToOrder(a) - periodToOrder(b);
      }
      return a.year - b.year;
    });

    const labels = sorted.map(
      (record) => `${record.year}-${record.period.toUpperCase()}`
    );
    const values = sorted.map((record) => Number(record.value));

    const ctx = document.getElementById("climateChart").getContext("2d");
    if (chartInstance) {
      chartInstance.data.labels = labels;
      chartInstance.data.datasets[0].data = values;
      chartInstance.update();
    } else {
      chartInstance = new Chart(ctx, {
        type: "line",
        data: {
          labels,
          datasets: [
            {
              label: "Value",
              data: values,
              fill: false,
              tension: 0.2,
              borderColor: "#2563eb",
              backgroundColor: "rgba(37, 99, 235, 0.3)",
              pointRadius: 0,
            },
          ],
        },
        options: {
          responsive: true,
          scales: {
            x: {
              ticks: { maxRotation: 0, autoSkip: true },
            },
            y: {
              beginAtZero: false,
            },
          },
          plugins: {
            legend: { display: false },
          },
        },
      });
    }

    const periodLabel = periodTypeSelect.options[
      periodTypeSelect.selectedIndex
    ].text;
    chartMeta.textContent = `${periodLabel} values (${records.length} points)`;
  }

  function updateSummary(summary) {
    summaryCount.textContent = summary.count ?? "-";
    summaryMin.textContent = formatValue(summary.min_value);
    summaryMax.textContent = formatValue(summary.max_value);
    summaryAvg.textContent = formatValue(summary.avg_value);
  }

  function setActiveGroup() {
    groupButtons.forEach((button) => {
      button.classList.toggle("active", button.dataset.group === periodTypeSelect.value);
    });
  }

  async function refreshData() {
    const params = buildQuery();
    const recordsUrl = `${config.endpoints.records}?${params.toString()}`;
    const summaryUrl = `${config.endpoints.summary}?${params.toString()}`;

    tableBody.innerHTML = `<tr><td colspan="3">Loading...</td></tr>`;

    try {
      const [recordsResponse, summaryResponse] = await Promise.all([
        fetch(recordsUrl),
        fetch(summaryUrl),
      ]);

      if (!recordsResponse.ok) {
        throw new Error("Failed to fetch records");
      }

      const recordsPayload = await recordsResponse.json();
      const summaryPayload = summaryResponse.ok
        ? await summaryResponse.json()
        : { count: 0 };

      const records = recordsPayload.results ?? recordsPayload;
      const total = recordsPayload.count ?? records.length;

      updateTable(records, total);
      updateChart(records);
      updateSummary(summaryPayload);
    } catch (error) {
      console.error(error);
      tableBody.innerHTML = `<tr><td colspan="3">Error loading data.</td></tr>`;
      updateSummary({ count: "-", min_value: null, max_value: null, avg_value: null });
    }
  }

  refreshButton.addEventListener("click", () => {
    refreshData();
  });

  [regionSelect, parameterSelect, periodTypeSelect].forEach((element) => {
    element.addEventListener("change", () => {
      if (element === periodTypeSelect) {
        setActiveGroup();
      }
      refreshData();
    });
  });

  groupButtons.forEach((button) => {
    button.addEventListener("click", () => {
      periodTypeSelect.value = button.dataset.group;
      setActiveGroup();
      refreshData();
    });
  });

  setActiveGroup();
  refreshData();
});

