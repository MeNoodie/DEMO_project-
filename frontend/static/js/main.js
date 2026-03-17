const inputView = document.getElementById("inputView");
const reportView = document.getElementById("reportView");
const form = document.getElementById("analysisForm");
const analyzeBtn = document.getElementById("analyzeBtn");
const formMessage = document.getElementById("formMessage");
const backBtn = document.getElementById("backBtn");
const downloadPdfBtn = document.getElementById("downloadPdfBtn");

const reportPaper = document.getElementById("reportPaper");
const reportMeta = document.getElementById("reportMeta");
const topRecommendation = document.getElementById("topRecommendation");
const projectSnapshot = document.getElementById("projectSnapshot");
const engineeringHighlights = document.getElementById("engineeringHighlights");
const materialsTable = document.getElementById("materialsTable");
const reportContent = document.getElementById("reportContent");

let scoreChart;
let radarChart;

function switchToReport() {
  inputView.classList.remove("active");
  reportView.classList.add("active");
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function switchToInput() {
  reportView.classList.remove("active");
  inputView.classList.add("active");
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function toPayload(formData) {
  return {
    requirement: (formData.get("requirement") || "").trim() || null,
    building_type: (formData.get("building_type") || "").trim() || null,
    floors: Number(formData.get("floors") || 1),
    location: (formData.get("location") || "").trim() || null,
    budget_level: (formData.get("budget_level") || "moderate").trim(),
    priority: (formData.get("priority") || "cooling").trim(),
    rainfall: (formData.get("rainfall") || "medium").trim(),
    material_tone: (formData.get("material_tone") || "balanced").trim(),
    timeline: (formData.get("timeline") || "standard").trim(),
    cost_preference: (formData.get("cost_preference") || "balanced").trim(),
    notes: (formData.get("notes") || "").trim() || null,
  };
}

function renderTopRecommendation(materials = []) {
  if (!materials.length) {
    topRecommendation.innerHTML = "<p>No recommendation available.</p>";
    return;
  }

  const best = materials[0];
  topRecommendation.innerHTML = `
    <p><strong>${best.name || "Recommended Material"}</strong> is the best-fit option for your current project profile.</p>
    <p>Overall fit score: <strong>${Math.round(Number(best.score || 0))}/100</strong>.</p>
  `;
}

function renderSnapshot(userInput = {}) {
  const chips = [
    `Building: ${userInput.building_type || "-"}`,
    `Floors: ${userInput.floors ?? "-"}`,
    `Location: ${userInput.location || "-"}`,
    `Budget: ${userInput.budget_level || "-"}`,
    `Priority: ${userInput.priority || "-"}`,
    `Rainfall: ${userInput.rainfall || "-"}`,
    `Timeline: ${userInput.timeline || "-"}`,
  ];

  projectSnapshot.innerHTML = chips.map((item) => `<span>${item}</span>`).join("");
}

function renderEngineering(engineering = {}) {
  const idx = engineering.engineering_indices || {};
  const chips = [
    `Structural Req: ${engineering.structural_requirement ?? "-"}`,
    `Thermal Index: ${idx.thermal_performance_index ?? "-"}`,
    `Budget Pressure: ${idx.budget_pressure_index ?? "-"}`,
    `Eco Priority: ${idx.eco_priority_index ?? "-"}`,
    `Constructability: ${idx.constructability_index ?? "-"}`,
    `Climate: ${engineering.climate || "-"}`,
  ];

  engineeringHighlights.innerHTML = chips.map((item) => `<span>${item}</span>`).join("");
}

function renderMaterialsTable(materials = []) {
  if (!materials.length) {
    materialsTable.innerHTML = "<p>No material comparison available.</p>";
    return;
  }

  const rows = materials
    .map(
      (m) => `
      <tr>
        <td>${m.name || "-"}</td>
        <td>${Math.round(m.score || 0)}</td>
        <td>${Math.round(m.strength || 0)}</td>
        <td>${Math.round(m.thermal || 0)}</td>
        <td>${Math.round(m.sustainability || 0)}</td>
        <td>${Math.round(m.cost || 0)}</td>
        <td>${Math.round(m.risk || 0)}</td>
      </tr>`
    )
    .join("");

  materialsTable.innerHTML = `
    <table class="table">
      <thead>
        <tr>
          <th>Material</th>
          <th>Fit</th>
          <th>Strength</th>
          <th>Thermal</th>
          <th>Sustainability</th>
          <th>Cost</th>
          <th>Risk</th>
        </tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>`;
}

function renderCharts(visualData = {}) {
  const materials = visualData.material_scores || [];

  const scoreCtx = document.getElementById("scoreChart");
  const radarCtx = document.getElementById("radarChart");

  if (scoreChart) scoreChart.destroy();
  if (radarChart) radarChart.destroy();

  if (!window.Chart || !materials.length) {
    return;
  }

  scoreChart = new Chart(scoreCtx, {
    type: "bar",
    data: {
      labels: materials.map((m) => m.name || "Material"),
      datasets: [
        {
          label: "Decision Score",
          data: materials.map((m) => Number(m.score || 0)),
          backgroundColor: ["#147d68", "#2f8fdd", "#d96c2f"],
          borderRadius: 8,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: { y: { min: 0, max: 100 } },
    },
  });

  radarChart = new Chart(radarCtx, {
    type: "radar",
    data: {
      labels: ["Strength", "Thermal", "Sustainability", "Cost", "Risk"],
      datasets: materials.slice(0, 3).map((m, i) => {
        const colors = ["#147d68", "#2f8fdd", "#d96c2f"];
        return {
          label: m.name || `Option ${i + 1}`,
          data: [
            Number(m.strength || 0),
            Number(m.thermal || 0),
            Number(m.sustainability || 0),
            Number(m.cost || 0),
            Number(m.risk || 0),
          ],
          borderColor: colors[i],
          backgroundColor: `${colors[i]}33`,
          fill: true,
        };
      }),
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: { r: { min: 0, max: 100 } },
    },
  });
}

function renderMarkdownReport(markdownText = "") {
  const html = window.marked ? marked.parse(markdownText) : markdownText;
  reportContent.innerHTML = window.DOMPurify ? DOMPurify.sanitize(html) : html;
}

async function runAnalysis(event) {
  event.preventDefault();
  analyzeBtn.disabled = true;
  formMessage.style.color = "#4a5e56";
  formMessage.textContent = "Generating report...";

  const payload = toPayload(new FormData(form));

  try {
    const response = await fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const data = await response.json();
    if (!response.ok || data.status !== "success") {
      throw new Error(data.message || "Unable to generate report.");
    }

    const materials = data.visual_data?.material_scores || [];

    reportMeta.textContent = `Generated for ${data.user_input?.building_type || "project"} in ${data.user_input?.location || "specified location"}.`;
    renderTopRecommendation(materials);
    renderSnapshot(data.user_input || {});
    renderEngineering(data.engineering_measures || {});
    renderMaterialsTable(materials);
    renderCharts(data.visual_data || {});
    renderMarkdownReport(data.report || "");

    formMessage.textContent = "";
    downloadPdfBtn.disabled = false;
    switchToReport();
  } catch (error) {
    formMessage.style.color = "#8c2727";
    formMessage.textContent = error.message;
  } finally {
    analyzeBtn.disabled = false;
  }
}

function downloadPdf() {
  if (!window.html2pdf) {
    return;
  }

  downloadPdfBtn.disabled = true;
  const options = {
    margin: [8, 8, 8, 8],
    filename: `eco-material-report-${Date.now()}.pdf`,
    image: { type: "jpeg", quality: 0.98 },
    html2canvas: { scale: 2, useCORS: true },
    jsPDF: { unit: "mm", format: "a4", orientation: "portrait" },
    pagebreak: { mode: ["css", "legacy"] },
  };

  window
    .html2pdf()
    .set(options)
    .from(reportPaper)
    .save()
    .finally(() => {
      downloadPdfBtn.disabled = false;
    });
}

form.addEventListener("submit", runAnalysis);
backBtn.addEventListener("click", switchToInput);
downloadPdfBtn.addEventListener("click", downloadPdf);
