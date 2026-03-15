const form = document.getElementById("analyzeForm");
const requirementInput = document.getElementById("requirement");
const analyzeBtn = document.getElementById("analyzeBtn");
const downloadPdfBtn = document.getElementById("downloadPdfBtn");
const statusPanel = document.getElementById("statusPanel");
const resultSection = document.getElementById("resultSection");
const researchOutput = document.getElementById("researchOutput");
const reportOutput = document.getElementById("reportOutput");

let latestResult = null;

function setStatus(message, isError = false) {
  statusPanel.textContent = message;
  statusPanel.classList.remove("hidden", "error");
  if (isError) {
    statusPanel.classList.add("error");
  }
}

function clearStatus() {
  statusPanel.classList.add("hidden");
  statusPanel.classList.remove("error");
  statusPanel.textContent = "";
}

function markdownToHtml(text) {
  if (!text) return "<p>No content returned.</p>";
  return marked.parse(text);
}

async function analyzeRequirement(requirement) {
  const response = await fetch("/api/analyze", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ requirement })
  });

  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`);
  }

  return response.json();
}

function fillResults(data) {
  const research = data.research_data || "Research details were not explicitly returned by the agent.";
  const report = data.report || "No report generated.";

  researchOutput.innerHTML = markdownToHtml(research);
  reportOutput.innerHTML = markdownToHtml(report);

  resultSection.classList.remove("hidden");
  latestResult = {
    requirement: data.requirement,
    reportText: report,
    generatedAt: new Date()
  };

  downloadPdfBtn.disabled = false;
}

function makePdf() {
  if (!latestResult) {
    setStatus("Generate a report first, then download PDF.", true);
    return;
  }

  const { jsPDF } = window.jspdf;
  const doc = new jsPDF({ unit: "mm", format: "a4" });

  const left = 14;
  let y = 18;

  doc.setFont("helvetica", "bold");
  doc.setFontSize(16);
  doc.text("Sustainable Material Recommendation Report", left, y);

  y += 8;
  doc.setFont("helvetica", "normal");
  doc.setFontSize(10);
  doc.text(`Requirement: ${latestResult.requirement}`, left, y, { maxWidth: 182 });

  y += 10;
  const wrapped = doc.splitTextToSize(latestResult.reportText, 182);
  const pageHeight = 297;
  const bottomMargin = 16;
  const lineHeight = 5.2;

  doc.setFontSize(11);
  wrapped.forEach((line) => {
    if (y > pageHeight - bottomMargin) {
      doc.addPage();
      y = 20;
    }
    doc.text(line, left, y);
    y += lineHeight;
  });

  if (y > 280) {
    doc.addPage();
  }
  const footerY = 286;
  const stamp = latestResult.generatedAt.toLocaleString();
  doc.setFontSize(9);
  doc.text(`Generated on: ${stamp}`, left, footerY);

  doc.save("material-recommendation-report.pdf");
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const requirement = requirementInput.value.trim();

  if (!requirement) {
    setStatus("Please enter your construction requirement.", true);
    return;
  }

  analyzeBtn.disabled = true;
  analyzeBtn.textContent = "Generating...";
  downloadPdfBtn.disabled = true;
  clearStatus();

  try {
    setStatus("Analyzing requirement and preparing your report...");
    const data = await analyzeRequirement(requirement);

    if (data.status !== "success") {
      throw new Error(data.message || "Unknown API error");
    }

    fillResults(data);
    setStatus("Report generated successfully. You can now download the PDF.");
  } catch (error) {
    setStatus(`Unable to generate report: ${error.message}`, true);
  } finally {
    analyzeBtn.disabled = false;
    analyzeBtn.textContent = "Generate Recommendation";
  }
});

downloadPdfBtn.addEventListener("click", makePdf);
