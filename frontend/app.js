// Estado global
let currentStudent = null;
let currentStudentName = "";
let diagnosticQuestions = [];
let currentQuestionIndex = 0;
let userAnswers = [];

const LEVEL_LABELS = { basico: "Básico", intermedio: "Intermedio", avanzado: "Avanzado" };

// --- Navegación ---

function showView(id) {
    document.querySelectorAll(".view").forEach(v => v.classList.remove("active"));
    document.getElementById(id).classList.add("active");
}

// --- Vista: Bienvenida ---

document.getElementById("btn-enter").addEventListener("click", async () => {
    const name = document.getElementById("input-name").value.trim();
    const errorEl = document.getElementById("welcome-error");
    errorEl.classList.add("hidden");

    if (!name) {
        showError(errorEl, "Ingresa tu nombre para continuar.");
        return;
    }

    try {
        const res = await fetch(`/students/${encodeURIComponent(name)}`);
        if (res.ok) {
            currentStudent = await res.json();
            loadDashboard();
        } else if (res.status === 404) {
            await startDiagnostic(name);
        } else {
            showError(errorEl, "Error al conectar con el servidor.");
        }
    } catch {
        showError(errorEl, "No se pudo conectar con la API. Verifica que el servidor esté activo.");
    }
});

document.getElementById("input-name").addEventListener("keydown", (e) => {
    if (e.key === "Enter") document.getElementById("btn-enter").click();
});

// --- Vista: Diagnóstico ---

async function startDiagnostic(name) {
    currentStudentName = name;
    const res = await fetch("/diagnostic/questions");
    diagnosticQuestions = await res.json();
    currentQuestionIndex = 0;
    userAnswers = [];
    renderQuestion();
    showView("view-diagnostic");
}

function renderQuestion() {
    const q = diagnosticQuestions[currentQuestionIndex];
    document.getElementById("question-counter").textContent =
        `Pregunta ${currentQuestionIndex + 1} de ${diagnosticQuestions.length}`;
    document.getElementById("question-text").textContent = q.pregunta;
    document.getElementById("input-answer").value = "";
    document.getElementById("input-answer").focus();

    const isLast = currentQuestionIndex === diagnosticQuestions.length - 1;
    document.getElementById("btn-next").textContent = isLast ? "Finalizar" : "Siguiente";
}

document.getElementById("btn-next").addEventListener("click", () => {
    const answer = document.getElementById("input-answer").value.trim();
    userAnswers.push(answer || "");
    currentQuestionIndex++;

    if (currentQuestionIndex < diagnosticQuestions.length) {
        renderQuestion();
    } else {
        submitDiagnostic();
    }
});

document.getElementById("input-answer").addEventListener("keydown", (e) => {
    if (e.key === "Enter") document.getElementById("btn-next").click();
});

async function submitDiagnostic() {
    const evalRes = await fetch("/diagnostic/evaluate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ answers: userAnswers }),
    });
    const result = await evalRes.json();

    await fetch("/students", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            name: currentStudentName,
            level: result.level,
            diagnostic_results: result,
        }),
    });

    currentStudent = { name: currentStudentName, level: result.level };

    document.getElementById("result-level-badge").textContent =
        `Nivel asignado: ${LEVEL_LABELS[result.level] || result.level}`;
    document.getElementById("result-score").textContent =
        `Puntaje: ${result.score} de ${diagnosticQuestions.length} respuestas correctas`;

    showView("view-diagnostic-result");
}

document.getElementById("btn-continue").addEventListener("click", loadDashboard);

// --- Vista: Dashboard ---

function loadDashboard() {
    document.getElementById("dashboard-name").textContent = `Bienvenido, ${currentStudent.name}`;
    document.getElementById("dashboard-level").textContent =
        LEVEL_LABELS[currentStudent.level] || currentStudent.level;
    showView("view-dashboard");
}

document.getElementById("btn-logout").addEventListener("click", () => {
    currentStudent = null;
    document.getElementById("input-name").value = "";
    document.getElementById("welcome-error").classList.add("hidden");
    showView("view-welcome");
});

// --- Navegación del menú ---

document.getElementById("btn-explain").addEventListener("click",   () => showView("view-explain"));
document.getElementById("btn-exercises").addEventListener("click", () => showView("view-exercises"));
document.getElementById("btn-feedback").addEventListener("click",  () => showView("view-feedback"));

document.getElementById("back-explain").addEventListener("click",   () => showView("view-dashboard"));
document.getElementById("back-exercises").addEventListener("click", () => showView("view-dashboard"));
document.getElementById("back-feedback").addEventListener("click",  () => showView("view-dashboard"));

// --- Vista: Explicación ---

document.getElementById("btn-generate-explain").addEventListener("click", async () => {
    const topic = document.getElementById("input-topic-explain").value.trim();
    if (!topic) return;

    await callApi({
        url: "/explain",
        body: { topic, student_level: currentStudent.level },
        btnId: "btn-generate-explain",
        btnLabel: "Generar explicación",
        resultId: "result-explain",
    });
});

// --- Vista: Ejercicios ---

document.getElementById("btn-generate-exercises").addEventListener("click", async () => {
    const topic = document.getElementById("input-topic-exercises").value.trim();
    if (!topic) return;

    await callApi({
        url: "/exercises",
        body: { topic, student_level: currentStudent.level, quantity: 3 },
        btnId: "btn-generate-exercises",
        btnLabel: "Generar ejercicios",
        resultId: "result-exercises",
    });
});

// --- Vista: Retroalimentación ---

document.getElementById("btn-generate-feedback").addEventListener("click", async () => {
    const studentAnswer = document.getElementById("input-student-answer").value.trim();
    const correctAnswer = document.getElementById("input-correct-answer").value.trim();
    if (!studentAnswer || !correctAnswer) return;

    await callApi({
        url: "/feedback",
        body: {
            student_answer: studentAnswer,
            correct_answer: correctAnswer,
            student_level: currentStudent.level,
        },
        btnId: "btn-generate-feedback",
        btnLabel: "Obtener retroalimentación",
        resultId: "result-feedback",
    });
});

// --- Función genérica para llamadas al LLM ---

async function callApi({ url, body, btnId, btnLabel, resultId }) {
    const btn = document.getElementById(btnId);
    const resultEl = document.getElementById(resultId);

    btn.disabled = true;
    btn.textContent = "Generando...";
    setResult(resultEl, "Procesando solicitud...", true);

    try {
        const res = await fetch(url, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
        });
        const data = await res.json();
        setResult(resultEl, data.content || data.detail || "Sin respuesta.");
    } catch {
        setResult(resultEl, "Error al procesar la solicitud. Verifica que el servidor esté activo.");
    } finally {
        btn.disabled = false;
        btn.textContent = btnLabel;
    }
}

// --- Helpers ---

function setResult(el, text, loading = false) {
    el.textContent = text;
    el.className = loading ? "result-box loading" : "result-box";
    el.classList.remove("hidden");
}

function showError(el, msg) {
    el.textContent = msg;
    el.classList.remove("hidden");
}
