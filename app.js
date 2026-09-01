"use strict";

const PATHS = {
  checklist: "data/fall26_checklist.json",
  settings: "config/settings.json",
};

const STATUS = Object.freeze({
  PASS: "cumple",
  FAIL: "no_cumple",
  NA: "na",
});

const dom = {};
let settings;
let checklist;
let questions = [];
let state;
let toastTimer;
let autoAdvanceTimer;
let editingOpportunityId = null;

document.addEventListener("DOMContentLoaded", init);

async function init() {
  bindDom();
  try {
    [settings, checklist] = await Promise.all([
      fetchJson(PATHS.settings),
      fetchJson(PATHS.checklist),
    ]);
    questions = flattenChecklist(checklist);
    applyExperienceSettings();
    validateContent();
    state = createEmptyState();
    bindEvents();
    renderSectionRail();
    prepareResume();
    maybeShowPrivacyDialog();
    registerServiceWorker();
  } catch (error) {
    console.error(error);
    dom.startError.textContent = "No fue posible cargar la validación. Actualiza la página o revisa los archivos del proyecto.";
    dom.startForm.querySelector("button[type='submit']").disabled = true;
  }
}

function bindDom() {
  const ids = [
    "startView", "validationView", "summaryView", "startForm", "storeInput", "validatorInput",
    "privacyConfirm", "resumeButton", "startError", "headerProgress", "headerStep", "headerScore",
    "backToStart", "sectionLabel", "questionCounter", "liveScore", "progressBar", "questionNumber",
    "questionTitle", "appliesBadge", "referenceButton", "referenceImage", "noImageCue", "questionText",
    "criterionText", "statusOptions", "responseGuidance", "responseGuidanceIcon", "responseGuidanceTitle",
    "responseGuidanceText", "applyCorrection", "commentWrap", "commentHint", "commentInput", "commentCount",
    "previousButton", "nextButton", "questionError", "summaryStore", "summaryValidator", "scoreRing",
    "summaryScore", "passCount", "failCount", "naCount", "answeredCount", "resultBadge", "resultMessage",
    "sectionResults", "strengthCount", "strengthsList", "opportunityCount", "opportunitiesList", "printReport", "restartButton",
    "imageDialog", "closeImageDialog", "dialogImage", "dialogTitle", "dialogDate", "toast",
    "privacyClassification", "privacyNotice", "headerEyebrow", "startTitle", "heroImage", "heroIntro", "heroPromise",
    "retentionHours", "responsibilityTitle", "responsibilityText", "clearLocalData", "sectionRail",
    "saveStatus", "summaryPrivacyWarning", "openPrivacy", "openPrivacyFooter",
    "privacyDialog", "closePrivacyDialog", "acknowledgePrivacy",
  ];
  ids.forEach((id) => { dom[id] = document.getElementById(id); });
}

async function fetchJson(path) {
  const response = await fetch(path, { cache: "no-store", credentials: "same-origin" });
  if (!response.ok) throw new Error(`No se pudo cargar ${path}: ${response.status}`);
  return response.json();
}

function flattenChecklist(data) {
  return data.sections.flatMap((section) => section.items.map((item) => ({
    ...item,
    sectionId: section.id,
    sectionTitle: section.title,
    journeyStageId: section.journeyStageId,
  })));
}

function validateContent() {
  if (!settings?.storageKey || !settings?.privacy?.responsibilityText || !Array.isArray(checklist?.sections)) throw new Error("Configuración incompleta.");
  if (!Array.isArray(checklist?.journeyStages) || checklist.journeyStages.length !== 5) throw new Error("El Customer Journey debe contener cinco momentos.");
  if (questions.length !== 36) throw new Error(`Se esperaban 36 controles y se encontraron ${questions.length}.`);
  const ids = new Set(questions.map((item) => item.id));
  const stageIds = new Set(checklist.journeyStages.map((stage) => stage.id));
  if (ids.size !== questions.length) throw new Error("Existen controles duplicados.");
  questions.forEach((item, index) => {
    if (item.id !== `q${String(index + 1).padStart(2, "0")}`) throw new Error(`Orden inválido en ${item.id}.`);
    if (!item.question || !item.title || !item.applies) throw new Error(`Control incompleto: ${item.id}.`);
    if (!stageIds.has(item.journeyStageId)) throw new Error(`Momento de Customer Journey inválido: ${item.id}.`);
    if (!correctionActionFor(item)) throw new Error(`Falta corrección inmediata: ${item.id}.`);
  });
}

function createEmptyState() {
  return {
    schemaVersion: 1,
    campaign: checklist?.campaign || "Fall 26",
    store: "",
    validator: "",
    startedAt: null,
    completedAt: null,
    currentIndex: 0,
    privacyAcceptedAt: null,
    answers: {},
  };
}

function bindEvents() {
  dom.startForm.addEventListener("submit", startValidation);
  dom.resumeButton.addEventListener("click", resumeValidation);
  dom.statusOptions.addEventListener("click", handleChoice);
  dom.commentInput.addEventListener("input", handleComment);
  dom.previousButton.addEventListener("click", previousQuestion);
  dom.nextButton.addEventListener("click", nextQuestion);
  dom.backToStart.addEventListener("click", () => {
    editingOpportunityId = null;
    showView("start");
  });
  dom.referenceButton.addEventListener("click", openImageDialog);
  dom.closeImageDialog.addEventListener("click", () => dom.imageDialog.close());
  dom.imageDialog.addEventListener("click", (event) => {
    if (event.target === dom.imageDialog) dom.imageDialog.close();
  });
  dom.applyCorrection.addEventListener("click", applySuggestedCorrection);
  dom.printReport.addEventListener("click", exportSummaryPdf);
  dom.opportunitiesList.addEventListener("click", handleOpportunityEdit);
  dom.restartButton.addEventListener("click", restartValidation);
  dom.clearLocalData.addEventListener("click", clearSavedValidation);
  dom.sectionRail.addEventListener("click", handleSectionJump);
  dom.openPrivacy.addEventListener("click", openPrivacyDialog);
  dom.openPrivacyFooter.addEventListener("click", openPrivacyDialog);
  dom.closePrivacyDialog.addEventListener("click", closePrivacyDialog);
  dom.acknowledgePrivacy.addEventListener("click", closePrivacyDialog);
  dom.privacyDialog.addEventListener("click", (event) => {
    if (event.target === dom.privacyDialog) closePrivacyDialog();
  });
  document.addEventListener("keydown", handleKeyboard);
}

function prepareResume() {
  const saved = readSavedState();
  if (!saved || !saved.store || !saved.validator) return;
  const answered = Object.values(saved.answers || {}).filter((answer) => answer?.status).length;
  dom.resumeButton.hidden = false;
  dom.resumeButton.textContent = saved.completedAt
    ? `Ver último resultado · ${saved.store}`
    : `Continuar ${answered}/36 · ${saved.store}`;
  dom.storeInput.value = saved.store;
  dom.validatorInput.value = saved.validator;
}

function startValidation(event) {
  event.preventDefault();
  const store = dom.storeInput.value.trim();
  const validator = dom.validatorInput.value.trim();
  if (!store || !validator || !dom.privacyConfirm.checked) {
    dom.startError.textContent = "Completa tienda, quién valida y confirma el uso interno.";
    return;
  }
  state = createEmptyState();
  state.store = store;
  state.validator = validator;
  state.startedAt = new Date().toISOString();
  state.privacyAcceptedAt = new Date().toISOString();
  saveState();
  showValidation();
}

function resumeValidation() {
  const saved = readSavedState();
  if (!saved) return;
  if (!dom.privacyConfirm.checked) {
    dom.startError.textContent = "Confirma nuevamente la responsabilidad de uso para continuar.";
    dom.privacyConfirm.focus();
    return;
  }
  state = sanitizeState(saved);
  state.privacyAcceptedAt = new Date().toISOString();
  saveState();
  if (state.completedAt) showSummary();
  else showValidation();
}

function sanitizeState(candidate) {
  const safe = createEmptyState();
  safe.store = String(candidate.store || "").slice(0, 80);
  safe.validator = String(candidate.validator || "").slice(0, 80);
  safe.startedAt = candidate.startedAt || new Date().toISOString();
  safe.completedAt = candidate.completedAt || null;
  safe.currentIndex = Math.max(0, Math.min(Number(candidate.currentIndex) || 0, questions.length - 1));
  safe.privacyAcceptedAt = candidate.privacyAcceptedAt || null;
  questions.forEach((item) => {
    const answer = candidate.answers?.[item.id];
    if (!answer || !Object.values(STATUS).includes(answer.status)) return;
    safe.answers[item.id] = {
      status: answer.status,
      comment: String(answer.comment || "").slice(0, settings.maxCommentLength),
      updatedAt: answer.updatedAt || null,
    };
  });
  return safe;
}

function showValidation() {
  state.completedAt = null;
  showView("validation");
  renderQuestion();
}

function showView(view) {
  cancelAutoAdvance();
  dom.startView.hidden = view !== "start";
  dom.validationView.hidden = view !== "validation";
  dom.summaryView.hidden = view !== "summary";
  dom.headerProgress.hidden = view === "start";
  if (view === "start") prepareResume();
  scrollTop();
}

function renderQuestion() {
  const item = questions[state.currentIndex];
  const answer = state.answers[item.id] || { status: null, comment: "" };
  const number = state.currentIndex + 1;
  const editingOpportunity = editingOpportunityId === item.id;
  const stage = journeyStageFor(item);
  dom.sectionLabel.textContent = `${stage?.title || "Recorrido"} · ${item.sectionTitle}`;
  dom.questionCounter.textContent = `Pregunta ${number} de ${questions.length}`;
  dom.questionNumber.textContent = String(number).padStart(2, "0");
  dom.questionTitle.textContent = item.title;
  dom.appliesBadge.textContent = item.applies;
  dom.questionText.textContent = item.question;
  dom.criterionText.textContent = item.criterion;
  dom.progressBar.style.width = `${Math.round(number / questions.length * 100)}%`;
  dom.headerStep.textContent = `${number} / ${questions.length}`;

  const hasImage = Boolean(item.image);
  dom.referenceButton.hidden = !hasImage;
  dom.noImageCue.hidden = hasImage;
  if (hasImage) {
    dom.referenceImage.src = item.image;
    dom.referenceImage.alt = item.imageAlt || `Referencia de ${item.title}`;
  } else {
    dom.referenceImage.removeAttribute("src");
    dom.referenceImage.alt = "";
  }

  [...dom.statusOptions.querySelectorAll(".choice")].forEach((button) => {
    button.classList.toggle("is-selected", button.dataset.status === answer.status);
    button.setAttribute("aria-pressed", button.dataset.status === answer.status ? "true" : "false");
  });
  dom.commentInput.value = answer.comment || "";
  updateCommentUi(answer.status);
  renderResponseGuidance(answer.status);
  dom.previousButton.disabled = editingOpportunity || state.currentIndex === 0;
  dom.nextButton.textContent = editingOpportunity
    ? "Guardar ajuste y volver →"
    : number === questions.length ? "Terminar recorrido →" : "Guardar y continuar →";
  dom.sectionRail.classList.toggle("is-locked", editingOpportunity);
  dom.questionError.textContent = "";
  updateSectionRail();
  updateLiveMetrics();
  saveState();
}

function handleChoice(event) {
  const button = event.target.closest("[data-status]");
  if (!button) return;
  cancelAutoAdvance();
  const item = questions[state.currentIndex];
  const previous = state.answers[item.id] || { comment: "" };
  state.answers[item.id] = {
    status: button.dataset.status,
    comment: previous.comment || "",
    updatedAt: new Date().toISOString(),
  };
  updateCommentUi(button.dataset.status);
  renderChoiceState(button.dataset.status);
  renderResponseGuidance(button.dataset.status);
  updateLiveMetrics();
  saveState();
  if (button.dataset.status === STATUS.FAIL) dom.applyCorrection.focus();
  else scheduleAutoAdvance(item.id, button.dataset.status);
}

function scheduleAutoAdvance(itemId, status) {
  const navigation = settings.experience?.navigation || {};
  const enabled = Array.isArray(navigation.autoAdvanceStatuses)
    && navigation.autoAdvanceStatuses.includes(status);
  if (!enabled) {
    dom.nextButton.focus();
    return;
  }
  const delay = Math.max(350, Math.min(Number(navigation.autoAdvanceDelayMs) || 650, 1500));
  dom.nextButton.textContent = "Continuando…";
  autoAdvanceTimer = setTimeout(() => {
    autoAdvanceTimer = null;
    const current = questions[state.currentIndex];
    if (current?.id !== itemId || state.answers[itemId]?.status !== status) return;
    nextQuestion();
  }, delay);
}

function cancelAutoAdvance() {
  if (!autoAdvanceTimer) return;
  clearTimeout(autoAdvanceTimer);
  autoAdvanceTimer = null;
}

function renderChoiceState(status) {
  [...dom.statusOptions.querySelectorAll(".choice")].forEach((button) => {
    const selected = button.dataset.status === status;
    button.classList.toggle("is-selected", selected);
    button.setAttribute("aria-pressed", selected ? "true" : "false");
  });
}

function handleComment() {
  const item = questions[state.currentIndex];
  const answer = state.answers[item.id] || { status: null };
  state.answers[item.id] = {
    ...answer,
    comment: dom.commentInput.value.slice(0, settings.maxCommentLength),
    updatedAt: new Date().toISOString(),
  };
  dom.commentCount.textContent = `${dom.commentInput.value.length}/${settings.maxCommentLength}`;
  if (dom.questionError.textContent) validateCurrentQuestion(false);
  saveState();
}

function updateCommentUi(status) {
  const required = status === STATUS.FAIL;
  dom.commentWrap.classList.toggle("is-required", required);
  dom.commentHint.textContent = required ? "requerido para No cumple" : "opcional";
  dom.commentInput.placeholder = required ? "¿Qué debe corregirse?" : "Comentario breve (opcional)";
  dom.commentCount.textContent = `${dom.commentInput.value.length}/${settings.maxCommentLength}`;
}

function correctionActionFor(item) {
  return checklist?.guidance?.correctiveActions?.[item.id] || item.criterion || "Corrige el estándar y vuelve a validar.";
}

function renderResponseGuidance(status) {
  const item = questions[state.currentIndex];
  const guidance = checklist.guidance || {};
  if (!settings.experience?.navigation?.showImmediateGuidance) {
    dom.responseGuidance.hidden = true;
    return;
  }
  dom.responseGuidance.hidden = !status;
  dom.responseGuidance.className = `response-guidance${status ? ` is-${status}` : ""}`;
  dom.applyCorrection.hidden = status !== STATUS.FAIL;
  if (!status) return;
  if (status === STATUS.PASS) {
    dom.responseGuidanceIcon.textContent = "✓";
    dom.responseGuidanceTitle.textContent = guidance.successTitle || "¡Bien hecho!";
    dom.responseGuidanceText.textContent = guidance.successText || "El estándar está listo. Reconoce al equipo.";
  } else if (status === STATUS.FAIL) {
    dom.responseGuidanceIcon.textContent = "↻";
    dom.responseGuidanceTitle.textContent = guidance.failTitle || "Corrección inmediata sugerida";
    dom.responseGuidanceText.textContent = correctionActionFor(item);
  } else {
    dom.responseGuidanceIcon.textContent = "•";
    dom.responseGuidanceTitle.textContent = guidance.naTitle || "No aplica en esta tienda";
    dom.responseGuidanceText.textContent = guidance.naText || "Este punto queda fuera de la calificación.";
  }
}

function applySuggestedCorrection() {
  const item = questions[state.currentIndex];
  const answer = state.answers[item.id];
  if (answer?.status !== STATUS.FAIL) return;
  const suggestion = correctionActionFor(item).slice(0, settings.maxCommentLength);
  dom.commentInput.value = suggestion;
  handleComment();
  dom.nextButton.focus();
  showToast("Acción sugerida agregada. Puedes ajustarla antes de continuar.");
}

function validateCurrentQuestion(showError = true) {
  const item = questions[state.currentIndex];
  const answer = state.answers[item.id];
  let message = "";
  if (!answer?.status) message = "Selecciona Cumple, No cumple o No aplica.";
  else if (answer.status === STATUS.FAIL && !answer.comment.trim()) message = "Agrega una acción breve para este No cumple.";
  if (showError) dom.questionError.textContent = message;
  return !message;
}

function previousQuestion() {
  cancelAutoAdvance();
  if (state.currentIndex === 0) return;
  state.currentIndex -= 1;
  renderQuestion();
  scrollTop();
}

function nextQuestion() {
  cancelAutoAdvance();
  if (!validateCurrentQuestion(true)) return;
  if (editingOpportunityId === questions[state.currentIndex].id) {
    editingOpportunityId = null;
    state.completedAt = new Date().toISOString();
    saveState();
    showSummary();
    showToast("Acuerdo actualizado en tu ruta de mejora.");
    return;
  }
  if (state.currentIndex === questions.length - 1) {
    const invalid = questions.filter((item) => {
      const answer = state.answers[item.id];
      return !answer?.status || (answer.status === STATUS.FAIL && !answer.comment.trim());
    });
    if (invalid.length) {
      state.currentIndex = questions.indexOf(invalid[0]);
      renderQuestion();
      dom.questionError.textContent = `Faltan ${invalid.length} controles por completar correctamente.`;
      return;
    }
    state.completedAt = new Date().toISOString();
    saveState();
    showSummary();
    return;
  }
  state.currentIndex += 1;
  renderQuestion();
  scrollTop();
}

function calculateStats(items = questions) {
  let pass = 0;
  let fail = 0;
  let na = 0;
  let unanswered = 0;
  items.forEach((item) => {
    const status = state.answers[item.id]?.status;
    if (status === STATUS.PASS) pass += 1;
    else if (status === STATUS.FAIL) fail += 1;
    else if (status === STATUS.NA) na += 1;
    else unanswered += 1;
  });
  const applicable = pass + fail;
  const score = applicable ? Math.round(pass / applicable * 1000) / 10 : null;
  return { pass, fail, na, unanswered, applicable, answered: pass + fail + na, score };
}

function updateLiveMetrics() {
  const stats = calculateStats();
  const score = stats.score === null ? "—" : `${stats.score}%`;
  dom.liveScore.textContent = score;
  dom.headerScore.textContent = score;
}

function showSummary() {
  showView("summary");
  const stats = calculateStats();
  dom.summaryStore.textContent = state.store;
  dom.summaryValidator.textContent = state.validator;
  dom.summaryScore.textContent = stats.score === null ? "—" : `${stats.score}%`;
  dom.scoreRing.style.setProperty("--score", stats.score || 0);
  dom.passCount.textContent = stats.pass;
  dom.failCount.textContent = stats.fail;
  dom.naCount.textContent = stats.na;
  dom.answeredCount.textContent = stats.answered;

  const reading = classifyResult(stats.score);
  dom.resultBadge.textContent = reading.label;
  dom.resultMessage.textContent = reading.message;
  renderJourneyStages();
  renderStrengths();
  renderOpportunities();
  dom.headerStep.textContent = "36 / 36";
  dom.headerScore.textContent = stats.score === null ? "—" : `${stats.score}%`;
}

function classifyResult(score) {
  if (score === null) return { label: "SIN PUNTAJE", message: "No existen controles aplicables para calcular la tasa de éxito." };
  if (score >= 90) return { label: "ARRANQUE CONSISTENTE", message: "¡Gran trabajo! Reconoce al equipo por lo que ya está sólido y cierra las oportunidades puntuales." };
  if (score >= 75) return { label: "VAMOS BIEN", message: "La campaña está encaminada. Celebra los puntos a favor y completa las correcciones antes del siguiente turno." };
  return { label: "ENFOQUE INMEDIATO", message: "Hay una base para avanzar. Atiende primero las correcciones sugeridas y vuelve a validar los puntos prioritarios." };
}

function renderJourneyStages() {
  dom.sectionResults.replaceChildren();
  checklist.journeyStages.forEach((stage) => {
    const stageItems = questions.filter((item) => item.journeyStageId === stage.id);
    const stats = calculateStats(stageItems);
    const score = stats.score === null ? 0 : stats.score;
    const row = document.createElement("article");
    row.className = "section-result";
    row.innerHTML = `
      <div>
        <header><span>${escapeHtml(stage.title)} <em>${escapeHtml(stage.subtitle)}</em></span><small>${stats.pass} C · ${stats.fail} NC · ${stats.na} N/A</small></header>
        <div class="mini-track"><i style="width:${score}%"></i></div>
      </div>
      <strong>${stats.score === null ? "—" : `${stats.score}%`}</strong>`;
    dom.sectionResults.append(row);
  });
}

function renderOpportunities() {
  const opportunities = questions.filter((item) => state.answers[item.id]?.status === STATUS.FAIL);
  dom.opportunityCount.textContent = opportunities.length;
  dom.opportunitiesList.replaceChildren();
  if (!opportunities.length) {
    const empty = document.createElement("div");
    empty.className = "empty-opportunities";
    empty.textContent = "Sin No cumple registrados. Mantén el estándar y reconoce al equipo.";
    dom.opportunitiesList.append(empty);
    return;
  }
  opportunities.forEach((item) => {
    const answer = state.answers[item.id];
    const stage = journeyStageFor(item);
    const row = document.createElement("article");
    row.className = "opportunity";
    row.innerHTML = `
      <b>×</b>
      <div>
        <strong>${escapeHtml(stage?.title || item.sectionTitle)} · ${escapeHtml(item.title)}</strong>
        <p><span>Corrige ahora:</span> ${escapeHtml(correctionActionFor(item))}</p>
        <small><b>Acuerdo:</b> ${escapeHtml(answer.comment)}</small>
        <button class="opportunity-edit" type="button" data-edit-question="${escapeHtml(item.id)}">Ajustar acuerdo</button>
      </div>
      <span>${escapeHtml(item.applies)}</span>`;
    dom.opportunitiesList.append(row);
  });
}

function renderStrengths() {
  const strengths = questions.filter((item) => state.answers[item.id]?.status === STATUS.PASS);
  dom.strengthCount.textContent = strengths.length;
  dom.strengthsList.replaceChildren();
  checklist.journeyStages.forEach((stage) => {
    const ready = strengths.filter((item) => item.journeyStageId === stage.id);
    if (!ready.length) return;
    const row = document.createElement("article");
    row.className = "strength";
    row.innerHTML = `<b>✓</b><div><strong>${escapeHtml(stage.title)}</strong><p>${ready.length} ${ready.length === 1 ? "estándar listo" : "estándares listos"}</p></div>`;
    dom.strengthsList.append(row);
  });
  if (!strengths.length) {
    const empty = document.createElement("div");
    empty.className = "empty-opportunities";
    empty.textContent = "Al corregir y volver a validar, aquí aparecerán los puntos a reconocer.";
    dom.strengthsList.append(empty);
  }
}

function handleOpportunityEdit(event) {
  const button = event.target.closest("[data-edit-question]");
  if (!button) return;
  const target = questions.find((item) => item.id === button.dataset.editQuestion);
  if (!target) return;
  state.currentIndex = questions.indexOf(target);
  editingOpportunityId = target.id;
  state.completedAt = null;
  saveState();
  showValidation();
  requestAnimationFrame(() => {
    dom.commentInput.focus();
    dom.commentInput.select();
  });
  showToast("Ajusta el acuerdo y continúa. La oportunidad se conservará en el resumen.");
}

function exportSummaryPdf() {
  const originalTitle = document.title;
  const store = String(state.store || "Tienda").normalize("NFD").replace(/[\u0300-\u036f]/g, "")
    .replace(/[^A-Za-z0-9_-]+/g, "_").replace(/^_+|_+$/g, "").slice(0, 40) || "Tienda";
  document.title = `Fall26_${store}_${new Date().toISOString().slice(0, 10)}`;
  window.print();
  setTimeout(() => { document.title = originalTitle; }, 1500);
}

function restartValidation() {
  if (!window.confirm("¿Iniciar una nueva validación? El recorrido guardado se reemplazará.")) return;
  localStorage.removeItem(settings.storageKey);
  editingOpportunityId = null;
  state = createEmptyState();
  dom.storeInput.value = "";
  dom.validatorInput.value = "";
  dom.privacyConfirm.checked = false;
  dom.resumeButton.hidden = true;
  showView("start");
}

function openImageDialog() {
  const item = questions[state.currentIndex];
  if (!item.image) return;
  dom.dialogImage.src = item.image;
  dom.dialogImage.alt = item.imageAlt || item.title;
  dom.dialogTitle.textContent = item.title;
  dom.dialogDate.textContent = item.applies;
  dom.imageDialog.showModal();
}

function handleKeyboard(event) {
  if (!settings.experience?.navigation?.keyboardShortcuts || dom.validationView.hidden || event.altKey || event.ctrlKey || event.metaKey) return;
  if (event.target.matches("input, textarea")) return;
  const map = { "1": STATUS.PASS, "0": STATUS.FAIL, "n": STATUS.NA, "N": STATUS.NA };
  if (map[event.key]) {
    const button = dom.statusOptions.querySelector(`[data-status="${map[event.key]}"]`);
    button?.click();
  } else if (event.key === "ArrowRight") nextQuestion();
  else if (event.key === "ArrowLeft") previousQuestion();
}

function saveState() {
  try {
    localStorage.setItem(settings.storageKey, JSON.stringify(state));
    if (dom.saveStatus) dom.saveStatus.textContent = "Avance guardado sólo en este dispositivo";
  }
  catch (error) { console.warn("No se pudo guardar el avance local.", error); }
}

function readSavedState() {
  try {
    const raw = localStorage.getItem(settings.storageKey);
    if (!raw) return null;
    const saved = JSON.parse(raw);
    if (!isSavedStateFresh(saved, settings.privacy?.retentionHours || 24)) {
      localStorage.removeItem(settings.storageKey);
      return null;
    }
    return saved;
  } catch { return null; }
}

function isSavedStateFresh(saved, retentionHours, now = Date.now()) {
  const reference = Date.parse(saved?.completedAt || saved?.startedAt || "");
  const age = now - reference;
  const retentionMs = Number(retentionHours) * 60 * 60 * 1000;
  return Number.isFinite(reference) && Number.isFinite(retentionMs) && retentionMs > 0 && age >= -5 * 60 * 1000 && age <= retentionMs;
}

function applyExperienceSettings() {
  const theme = settings.experience?.theme || {};
  const palette = theme.palette || {};
  const cssVariables = {
    green: "--green",
    dark: "--dark",
    orange: "--orange",
    pumpkin: "--pumpkin",
    cream: "--cream",
    ink: "--ink",
  };
  Object.entries(cssVariables).forEach(([key, variable]) => {
    const color = String(palette[key] || "");
    if (/^#[0-9a-f]{6}$/i.test(color)) document.documentElement.style.setProperty(variable, color);
  });

  const copy = settings.experience?.copy || {};
  dom.headerEyebrow.textContent = copy.eyebrow || "JUNTÉMONOS MÁS";
  dom.startTitle.textContent = copy.heroTitle || "Fall ya está aquí.";
  dom.heroIntro.textContent = copy.heroIntro || "Hagamos que esta temporada se viva en cada tienda.";
  dom.heroPromise.textContent = copy.heroPromise || "Un recorrido rápido y objetivo.";
  if (/^[a-z0-9_./-]+$/i.test(theme.heroImage || "")) dom.heroImage.src = theme.heroImage;

  const privacy = settings.privacy;
  dom.privacyClassification.textContent = privacy.classification;
  dom.privacyNotice.textContent = privacy.shortNotice;
  dom.responsibilityTitle.textContent = privacy.responsibilityTitle;
  dom.responsibilityText.textContent = privacy.responsibilityText;
  dom.retentionHours.textContent = `${privacy.retentionHours} horas`;
  dom.summaryPrivacyWarning.textContent = privacy.exportWarning;
}

function journeyStageFor(itemOrId) {
  const stageId = typeof itemOrId === "string" ? itemOrId : itemOrId?.journeyStageId;
  return checklist?.journeyStages?.find((stage) => stage.id === stageId) || null;
}

function renderSectionRail() {
  dom.sectionRail.hidden = !settings.experience?.navigation?.showSectionRail;
  dom.sectionRail.replaceChildren();
  checklist.journeyStages.forEach((stage, index) => {
    const button = document.createElement("button");
    const number = document.createElement("b");
    const label = document.createElement("span");
    const detail = document.createElement("small");
    button.type = "button";
    button.className = "section-chip";
    button.dataset.stageId = stage.id;
    button.title = `Ir a ${stage.title}: ${stage.subtitle}`;
    number.textContent = String(index + 1).padStart(2, "0");
    label.textContent = stage.title;
    detail.textContent = stage.subtitle;
    label.append(detail);
    button.append(number, label);
    dom.sectionRail.append(button);
  });
}

function updateSectionRail() {
  const current = questions[state.currentIndex];
  dom.sectionRail.querySelectorAll("[data-stage-id]").forEach((button) => {
    const items = questions.filter((item) => item.journeyStageId === button.dataset.stageId);
    const complete = items.every((item) => state.answers[item.id]?.status);
    const active = current.journeyStageId === button.dataset.stageId;
    button.classList.toggle("is-complete", complete);
    button.classList.toggle("is-active", active);
    if (active) button.setAttribute("aria-current", "step");
    else button.removeAttribute("aria-current");
  });
  const active = dom.sectionRail.querySelector(".is-active");
  active?.scrollIntoView({ behavior: "smooth", block: "nearest", inline: "center" });
}

function handleSectionJump(event) {
  cancelAutoAdvance();
  const button = event.target.closest("[data-stage-id]");
  if (!button || !settings.experience?.navigation?.allowSectionJump) return;
  if (editingOpportunityId) {
    showToast("Guarda el ajuste para volver al resumen.");
    dom.commentInput.focus();
    return;
  }
  const currentAnswer = state.answers[questions[state.currentIndex].id];
  if (currentAnswer?.status === STATUS.FAIL && !currentAnswer.comment.trim()) {
    dom.questionError.textContent = "Agrega una acción breve antes de cambiar de sección.";
    dom.commentInput.focus();
    return;
  }
  const items = questions.filter((item) => item.journeyStageId === button.dataset.stageId);
  const target = items.find((item) => !state.answers[item.id]?.status) || items[0];
  state.currentIndex = questions.indexOf(target);
  renderQuestion();
  scrollTop();
}

function clearSavedValidation() {
  if (!window.confirm("¿Borrar el recorrido guardado en este dispositivo? Esta acción no se puede deshacer.")) return;
  localStorage.removeItem(settings.storageKey);
  editingOpportunityId = null;
  state = createEmptyState();
  dom.startForm.reset();
  dom.resumeButton.hidden = true;
  dom.startError.textContent = "";
  showToast("Datos locales eliminados de este dispositivo.");
}

function maybeShowPrivacyDialog() {
  try {
    if (sessionStorage.getItem(`${settings.appId}-privacy-seen`) !== "1") openPrivacyDialog();
  } catch {
    openPrivacyDialog();
  }
}

function openPrivacyDialog() {
  if (!dom.privacyDialog.open) dom.privacyDialog.showModal();
}

function closePrivacyDialog() {
  if (dom.privacyDialog.open) dom.privacyDialog.close();
  try { sessionStorage.setItem(`${settings.appId}-privacy-seen`, "1"); }
  catch { /* El aviso sigue disponible desde encabezado y pie. */ }
}

function scrollTop() {
  const behavior = settings.experience?.navigation?.scrollBehavior === "auto" ? "auto" : "smooth";
  window.scrollTo({ top: 0, behavior });
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>'"]/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" }[character]));
}

function showToast(message) {
  clearTimeout(toastTimer);
  dom.toast.textContent = message;
  dom.toast.classList.add("is-visible");
  toastTimer = setTimeout(() => dom.toast.classList.remove("is-visible"), 2600);
}

function registerServiceWorker() {
  if (!("serviceWorker" in navigator) || location.protocol === "file:") return;
  navigator.serviceWorker.register("service-worker.js").catch((error) => console.warn("Modo offline no disponible.", error));
}
