/**
 * Eco-Friendly Material Advisor - Optimized Frontend
 * Clean, efficient JavaScript with better error handling
 */

// ============================================
// DOM Elements Cache
// ============================================
const elements = {
  form: document.getElementById('advisorForm'),
  formMessage: document.getElementById('formMessage'),
  submitBtn: document.getElementById('submitButton'),
  resetBtn: document.getElementById('resetButton'),
  downloadBtn: document.getElementById('downloadPdfBtn'),
  resultStatus: document.getElementById('resultStatus'),
  resultContent: document.getElementById('result'),
  shortRecommendation: document.getElementById('shortRecommendation'),
  shortRecommendationText: document.getElementById('shortRecommendationText'),
  researchBlock: document.getElementById('researchBlock'),
  researchOutput: document.getElementById('researchOutput'),
  exportArea: document.getElementById('reportExportArea')
};

// ============================================
// API Configuration
// ============================================
const API_ENDPOINT = '/api/analyze';

// ============================================
// Event Listeners
// ============================================
document.addEventListener('DOMContentLoaded', () => {
  elements.form.addEventListener('submit', handleSubmit);
  elements.resetBtn.addEventListener('click', handleReset);
  elements.downloadBtn.addEventListener('click', handleDownload);
});

// ============================================
// Form Handlers
// ============================================
async function handleSubmit(event) {
  event.preventDefault();
  
  const payload = collectFormData();
  const validationError = validateForm(payload);
  
  if (validationError) {
    showFormMessage(validationError, true);
    return;
  }

  await submitRecommendationRequest(payload);
}

function handleReset() {
  elements.form.reset();
  resetResults();
  showFormMessage('');
}

// ============================================
// Data Collection
// ============================================
function collectFormData() {
  return {
    building_type: getValue('building_type'),
    floors: parseInt(getValue('floors')) || 0,
    location: getValue('location').trim(),
    budget_level: getValue('budget'),
    priority: getValue('priority'),
    rainfall: getValue('rainfall'),
    material_tone: getValue('material_tone'),
    timeline: getValue('timeline'),
    cost_preference: getValue('cost_vs_sustain'),
    notes: getValue('extra_notes').trim()
  };
}

function getValue(id) {
  const el = document.getElementById(id);
  return el ? el.value : '';
}

// ============================================
// Validation
// ============================================
function validateForm(payload) {
  if (!payload.location) {
    return 'Please enter a location for your project.';
  }
  
  if (!payload.floors || payload.floors < 1) {
    return 'Please enter a valid number of floors (at least 1).';
  }
  
  return null;
}

// ============================================
// API Request
// ============================================
async function submitRecommendationRequest(payload) {
  setLoadingState(true);
  prepareResultsArea();

  try {
    const requirement = buildRequirementText(payload);
    const response = await fetch(API_ENDPOINT, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...payload, requirement })
    });

    const data = await response.json();

    if (!response.ok || data.status === 'error') {
      throw new Error(data.message || 'Failed to generate recommendation');
    }

    handleSuccessResponse(data);
  } catch (error) {
    handleError(error);
  } finally {
    setLoadingState(false);
  }
}

function buildRequirementText(payload) {
  const priorities = {
    cooling: 'reduce cooling demand',
    cost: 'minimize cost',
    sustainability: 'maximize sustainability',
    durability: 'maximize durability'
  };

  const parts = [
    `Recommend eco-friendly materials for a ${payload.building_type} building in ${payload.location}.`,
    `Building: ${payload.floors} floor(s), ${payload.budget_level} budget.`,
    `Primary goal: ${priorities[payload.priority] || payload.priority}.`,
    `Climate: ${payload.rainfall} rainfall exposure.`,
    `Timeline: ${formatValue(payload.timeline)}.`,
    `Material preference: ${formatValue(payload.material_tone)}.`,
    `Tradeoff: ${formatValue(payload.cost_preference)}.`
  ];

  if (payload.notes) {
    parts.push(`Additional notes: ${payload.notes}`);
  }

  parts.push('Provide practical material recommendations with brief justifications.');
  
  return parts.join(' ');
}

function formatValue(value) {
  return value.replace(/_/g, ' ');
}

// ============================================
// Response Handling
// ============================================
function handleSuccessResponse(data) {
  showStatus('Recommendation ready!', 'success');
  
  const reportText = data.report || '';
  
  if (reportText) {
    renderShortSummary(reportText);
    renderFullReport(reportText);
  }
  
  if (data.research_data) {
    elements.researchOutput.textContent = data.research_data;
    elements.researchBlock.classList.remove('hidden');
  }
  
  elements.downloadBtn.disabled = false;
}

function handleError(error) {
  showStatus(error.message || 'An error occurred. Please try again.', 'error');
  elements.resultContent.innerHTML = `
    <div class="empty-state">
      <div class="empty-icon" style="background: var(--color-error-bg); color: var(--color-error);">
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10"/>
          <path d="M12 8v4M12 16h.01"/>
        </svg>
      </div>
      <h3>Something went wrong</h3>
      <p>${escapeHtml(error.message)}</p>
    </div>
  `;
}

// ============================================
// Rendering
// ============================================
function renderShortSummary(text) {
  const summary = extractSummary(text);
  elements.shortRecommendationText.textContent = summary;
  elements.shortRecommendation.classList.remove('hidden');
}

function extractSummary(text) {
  if (!text) return 'No summary available.';
  
  // Clean markdown
  const cleaned = text
    .replace(/```[\s\S]*?```/g, '')
    .replace(/[#*>`-]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
  
  // Extract first few sentences
  const sentences = cleaned.match(/[^.!?]+[.!?]+/g) || [cleaned];
  return sentences.slice(0, 2).join(' ').slice(0, 300).trim() || 'See full recommendation below.';
}

function renderFullReport(text) {
  if (!text) {
    elements.resultContent.innerHTML = '<p class="placeholder">No report generated.</p>';
    return;
  }

  // Use marked if available, otherwise render as plain text
  if (window.marked && window.marked.parse) {
    elements.resultContent.innerHTML = window.marked.parse(text);
  } else {
    const paragraphs = text.split(/\n{2,}/).filter(Boolean);
    elements.resultContent.innerHTML = paragraphs
      .map(p => `<p>${escapeHtml(p.trim())}</p>`)
      .join('');
  }
}

// ============================================
// PDF Download
// ============================================
async function handleDownload() {
  if (!window.html2pdf) {
    showStatus('PDF library not loaded. Please refresh the page.', 'error');
    return;
  }

  elements.downloadBtn.disabled = true;
  const filename = `eco-material-report-${new Date().toISOString().slice(0, 10)}.pdf`;

  try {
    await window.html2pdf()
      .from(elements.exportArea)
      .set({
        margin: 10,
        filename,
        image: { type: 'jpeg', quality: 0.98 },
        html2canvas: { scale: 2, useCORS: true },
        jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' },
        pagebreak: { mode: ['avoid-all', 'css', 'legacy'] }
      })
      .save();
      
    showStatus('PDF downloaded successfully!', 'success');
  } catch (error) {
    showStatus('Failed to generate PDF. Please try again.', 'error');
  } finally {
    elements.downloadBtn.disabled = false;
  }
}

// ============================================
// UI State Management
// ============================================
function setLoadingState(isLoading) {
  elements.submitBtn.disabled = isLoading;
  elements.submitBtn.classList.toggle('loading', isLoading);
  elements.downloadBtn.disabled = true;
}

function prepareResultsArea() {
  elements.resultStatus.classList.add('hidden');
  elements.researchBlock.classList.add('hidden');
  elements.shortRecommendation.classList.add('hidden');
  elements.researchOutput.textContent = '';
  elements.shortRecommendationText.textContent = '';
}

function resetResults() {
  elements.resultStatus.classList.add('hidden', 'success', 'error');
  elements.resultContent.innerHTML = `
    <div class="empty-state">
      <div class="empty-icon">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
        </svg>
      </div>
      <h3>Ready to Help! 🌱</h3>
      <p>Fill in your project details and we'll generate eco-friendly material recommendations tailored to your needs.</p>
    </div>
  `;
  elements.shortRecommendation.classList.add('hidden');
  elements.researchBlock.classList.add('hidden');
  elements.downloadBtn.disabled = true;
}

function showFormMessage(message, isError = false) {
  elements.formMessage.textContent = message;
}

function showStatus(message, type = 'success') {
  elements.resultStatus.textContent = message;
  elements.resultStatus.className = `status-badge ${type}`;
  elements.resultStatus.classList.remove('hidden');
}

// ============================================
// Utilities
// ============================================
function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// Export for potential module use
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { handleSubmit, handleReset, collectFormData };
}
