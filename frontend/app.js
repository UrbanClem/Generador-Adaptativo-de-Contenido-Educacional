// ========== ESTADO GLOBAL ==========
let currentStudent = null;
let currentStudentName = "";
let diagnosticQuestions = [];
let currentQuestionIndex = 0;
let userAnswers = [];
let currentDiagnosticSession = null;
let diagnosticStartTime = null;
let currentQuestionsBatch = [];
let currentQuestionBatchIndex = 0;

const LEVEL_LABELS = { basico: "Básico", intermedio: "Intermedio", avanzado: "Avanzado" };

// ========== LOADER CONTROL ==========
function showLoader() {
    const loader = document.getElementById('global-loader');
    if (loader) loader.classList.remove('hidden');
}

function hideLoader() {
    const loader = document.getElementById('global-loader');
    if (loader) loader.classList.add('hidden');
}

// ========== NAVEGACIÓN ==========
function showView(id) {
    document.querySelectorAll(".view").forEach(v => v.classList.remove("active"));
    document.getElementById(id).classList.add("active");
}

// ========== VISTA: BIENVENIDA / LOGIN ==========
async function login() {
    const name = document.getElementById('input-name').value.trim();
    const errorEl = document.getElementById('welcome-error');
    errorEl.classList.add('hidden');

    if (!name) {
        showError(errorEl, "Ingresa tu nombre para continuar.");
        return;
    }

    // El nombre se queda en el navegador para saludar; al servidor solo
    // llega para calcular su huella y nunca se almacena (ver seudonimo.py).
    currentStudentName = name;

    showLoader(true);
    try {
        // Primero verificar si el estudiante ya existe
        const res = await fetch(`/students/${encodeURIComponent(name)}`);
        
        if (res.ok) {
            currentStudent = await res.json();
            loadDashboard();
        } else if (res.status === 404) {
            // Estudiante nuevo: NO crear aún, primero probar diagnóstico
            // Guardar nombre temporalmente
            currentStudentName = name;
            
            // Probar inicio de diagnóstico para verificar que la IA funciona
            const testRes = await fetch('/diagnostic/test', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    student_name: name 
                })
            });
            
            if (!testRes.ok) {
                const errorData = await testRes.json();
                showError(errorEl, `No se puede iniciar diagnóstico: ${errorData.error || 'Error de IA'}`);
                hideLoader();
                return;
            }
            
            // Si el test funciona, crear estudiante
            const createRes = await fetch('/students', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    name: name, 
                    level: 'basico', 
                    diagnostic_results: {} 
                })
            });
            
            if (!createRes.ok) {
                throw new Error(`Error creando estudiante: ${createRes.status}`);
            }
            
            currentStudent = await createRes.json();
            console.log("Estudiante creado:", currentStudent);
            await startAdaptiveDiagnostic();
        } else {
            showError(errorEl, `Error del servidor: ${res.status}`);
        }
    } catch (error) {
        console.error("Error en login:", error);
        showError(errorEl, `No se pudo conectar: ${error.message}`);
    } finally {
        hideLoader();
    }
}

document.getElementById("btn-enter").addEventListener("click", login);
document.getElementById("input-name").addEventListener("keydown", (e) => {
    if (e.key === "Enter") login();
});

// ========== DIAGNÓSTICO ADAPTATIVO CON IA ==========
async function startAdaptiveDiagnostic() {
    if (!currentStudent || !currentStudent.id) {
        console.error("No hay estudiante logueado");
        return;
    }
    
    showLoader(true);
    
    try {
        const res = await fetch('/diagnostic/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                student_id: currentStudent.id,
                student_name: currentStudent.name
            })
        });
        
        const data = await res.json();
        
        currentDiagnosticSession = {
            id: data.session_id,
            round: data.round,
            totalRounds: data.total_rounds
        };
        currentQuestionBatchIndex = 0;
        currentQuestionsBatch = data.questions;
        diagnosticStartTime = Date.now();
        
        if (currentQuestionsBatch && currentQuestionsBatch.length > 0) {
            displayAdaptiveQuestion(currentQuestionsBatch[0], 1, currentQuestionsBatch.length);
        }
        
        document.getElementById('adaptive-level-info').innerHTML = `Nivel actual: ${data.current_level}`;
        document.getElementById('adaptive-progress').textContent = `Ronda ${currentDiagnosticSession.round} de ${currentDiagnosticSession.totalRounds}`;
        
        showView('view-adaptive-diagnostic');
    } catch (error) {
        console.error("Error iniciando diagnóstico adaptativo:", error);
        alert("Error al iniciar el diagnóstico. Intenta de nuevo.");
    } finally {
        hideLoader();
    }
}

function displayAdaptiveQuestion(question, index, total) {
    document.getElementById('adaptive-question-counter').textContent = `Pregunta ${index} de ${total}`;
    document.getElementById('adaptive-question-text').textContent = question.pregunta;
    document.getElementById('adaptive-answer-input').value = '';
    document.getElementById('adaptive-answer-input').focus();
    
    const hintContainer = document.getElementById('adaptive-scaffolding-hint');
    if (question.scaffolding_hint) {
        hintContainer.textContent = `💡 Pista: ${question.scaffolding_hint}`;
        hintContainer.classList.remove('hidden');
    } else {
        hintContainer.classList.add('hidden');
    }
    
    const feedbackDiv = document.getElementById('adaptive-feedback');
    feedbackDiv.classList.add('hidden');
}

async function submitAdaptiveAnswer() {
    const answer = document.getElementById('adaptive-answer-input').value.trim();
    if (!answer) {
        alert("Por favor ingresa una respuesta");
        return;
    }
    
    const currentQuestion = currentQuestionsBatch[currentQuestionBatchIndex];
    const responseTime = (Date.now() - diagnosticStartTime) / 1000;
    
    // === DESHABILITAR BOTÓN ===
    const submitBtn = document.getElementById('btn-submit-adaptive');
    const cancelBtn = document.getElementById('btn-cancel-diagnostic');
    
    submitBtn.disabled = true;
    submitBtn.style.opacity = '0.6';
    submitBtn.style.cursor = 'not-allowed';
    cancelBtn.disabled = true;
    cancelBtn.style.opacity = '0.6';
    cancelBtn.style.cursor = 'not-allowed';
    
    showLoader(true);
    
    try {
        const res = await fetch('/diagnostic/answer', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: currentDiagnosticSession.id,
                question: currentQuestion.pregunta,
                student_answer: answer,
                expected_answer: currentQuestion.respuesta_esperada,
                response_time: responseTime
            })
        });
        
        const data = await res.json();
        
        const feedbackDiv = document.getElementById('adaptive-feedback');
        if (data.is_correct) {
            feedbackDiv.innerHTML = `✅ ¡Correcto! ${data.feedback?.reasoning || ''}`;
            feedbackDiv.className = 'feedback-correct';
        } else {
            feedbackDiv.innerHTML = `❌ Incorrecto. La respuesta correcta era: ${currentQuestion.respuesta_esperada}<br>${data.feedback?.reasoning || ''}`;
            feedbackDiv.className = 'feedback-incorrect';
        }
        feedbackDiv.classList.remove('hidden');
        
        document.getElementById('adaptive-level-info').innerHTML = `
            Nivel actual: ${data.current_level}<br>
            Fortalezas: ${data.profile_feedback?.strengths?.slice(0, 2).join(', ') || 'Identificando...'}
        `;
        
        if (data.is_complete) {
            feedbackDiv.innerHTML += '<br><br>🎉 ¡Diagnóstico completado! Redirigiendo al dashboard...';
            setTimeout(() => {
                loadDashboard();
                showView('view-dashboard');
                currentDiagnosticSession = null;
            }, 3000);
            hideLoader();
            return;
        }
        
        currentQuestionBatchIndex++;
        
        if (currentQuestionBatchIndex < currentQuestionsBatch.length) {
            setTimeout(() => {
                feedbackDiv.classList.add('hidden');
                displayAdaptiveQuestion(
                    currentQuestionsBatch[currentQuestionBatchIndex], 
                    currentQuestionBatchIndex + 1, 
                    currentQuestionsBatch.length
                );
                diagnosticStartTime = Date.now();
                // === REHABILITAR BOTÓN ===
                submitBtn.disabled = false;
                submitBtn.style.opacity = '1';
                submitBtn.style.cursor = 'pointer';
                cancelBtn.disabled = false;
                cancelBtn.style.opacity = '1';
                cancelBtn.style.cursor = 'pointer';
            }, 2000);
        } 
        else if (data.next_questions && data.next_questions.length > 0) {
            currentQuestionsBatch = data.next_questions;
            currentQuestionBatchIndex = 0;
            
            if (data.next_round) {
                currentDiagnosticSession.round = data.next_round;
            }
            document.getElementById('adaptive-progress').textContent = `Ronda ${currentDiagnosticSession.round} de ${currentDiagnosticSession.totalRounds}`;
            
            setTimeout(() => {
                feedbackDiv.classList.add('hidden');
                displayAdaptiveQuestion(
                    currentQuestionsBatch[0], 
                    1, 
                    currentQuestionsBatch.length
                );
                diagnosticStartTime = Date.now();
                // === REHABILITAR BOTÓN ===
                submitBtn.disabled = false;
                submitBtn.style.opacity = '1';
                submitBtn.style.cursor = 'pointer';
                cancelBtn.disabled = false;
                cancelBtn.style.opacity = '1';
                cancelBtn.style.cursor = 'pointer';
            }, 2000);
        }
        
    } catch (error) {
        console.error("Error enviando respuesta:", error);
        alert("Error al procesar la respuesta. Intenta de nuevo.");
        // === REHABILITAR BOTÓN EN CASO DE ERROR ===
        submitBtn.disabled = false;
        submitBtn.style.opacity = '1';
        submitBtn.style.cursor = 'pointer';
        cancelBtn.disabled = false;
        cancelBtn.style.opacity = '1';
        cancelBtn.style.cursor = 'pointer';
    } finally {
        hideLoader();
    }
}

document.getElementById("btn-submit-adaptive").addEventListener("click", submitAdaptiveAnswer);
document.getElementById("adaptive-answer-input").addEventListener("keydown", (e) => {
    if (e.key === "Enter") submitAdaptiveAnswer();
});
document.getElementById("btn-cancel-diagnostic").addEventListener("click", () => {
    currentDiagnosticSession = null;
    showView("view-welcome");
});

// ========== DASHBOARD ==========
function loadDashboard() {
    const saludo = currentStudentName || currentStudent.name;
    document.getElementById("dashboard-name").textContent = `Bienvenido, ${saludo}`;
    document.getElementById("dashboard-level").textContent = LEVEL_LABELS[currentStudent.level] || currentStudent.level;
    showView("view-dashboard");
}

document.getElementById("btn-logout").addEventListener("click", () => {
    currentStudent = null;
    currentStudentName = null;
    document.getElementById("input-name").value = "";
    document.getElementById("welcome-error").classList.add("hidden");
    showView("view-welcome");
});

// ========== NAVEGACION DEL MENU ==========
// Se registra con alClic y no con getElementById directo: la vista de
// retroalimentacion ya no existe en el HTML, y el error que lanzaba
// btn-feedback cortaba el script y dejaba sin listener a todo lo de abajo
// (por eso "Generar ejercicios" no hacia nada).
function alClic(id, manejador) {
    const el = document.getElementById(id);
    if (!el) {
        console.warn(`No existe el elemento "${id}", se omite su listener`);
        return;
    }
    el.addEventListener("click", manejador);
}

alClic("btn-explain", () => showView("view-explain"));
alClic("btn-exercises", () => showView("view-exercises"));
alClic("btn-feedback", () => showView("view-feedback"));
alClic("back-explain", () => showView("view-dashboard"));
alClic("back-exercises", () => showView("view-dashboard"));
alClic("back-feedback", () => showView("view-dashboard"));

// ========== EXPLICACIÓN PERSONALIZADA ==========
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

// ========== EJERCICIOS INTERACTIVOS ==========

let currentExercises = [];
let exerciseAnswers = [];
let exerciseResults = [];

document.getElementById("btn-generate-exercises").addEventListener("click", async () => {
    const topic = document.getElementById("input-topic-exercises").value.trim();
    if (!topic) {
        alert("Ingresa un tema");
        return;
    }
    
    showLoader(true);
    
    try {
        const res = await fetch('/exercises', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                topic: topic,
                student_level: currentStudent.level,
                quantity: 3
            })
        });
        
        const data = await res.json();
        currentExercises = data.exercises;
        exerciseAnswers = [];
        exerciseResults = [];
        
        renderExercises();
        
    } catch (error) {
        console.error("Error generando ejercicios:", error);
        alert("Error al generar ejercicios");
    } finally {
        hideLoader();
    }
});

function renderExercises() {
    const container = document.getElementById('exercises-container');
    const resultsDiv = document.getElementById('exercises-results');
    
    if (!currentExercises || currentExercises.length === 0) {
        container.innerHTML = '<p>No se generaron ejercicios. Intenta de nuevo.</p>';
        container.classList.remove('hidden');
        return;
    }
    
    let html = '';
    
    currentExercises.forEach((ex, index) => {
        const userAnswer = exerciseAnswers[index] || '';
        const result = exerciseResults[index];
        
        let feedbackClass = 'pending';
        let feedbackText = 'Esperando respuesta...';
        
        if (result === true) {
            feedbackClass = 'correct';
            feedbackText = '✅ ¡Correcto!';
        } else if (result === false) {
            feedbackClass = 'incorrect';
            feedbackText = `❌ Incorrecto. La respuesta correcta era: ${ex.respuesta_esperada}`;
        }
        
        html += `
            <div class="exercise-item" data-index="${index}">
                <div class="exercise-question">${index + 1}. ${ex.pregunta}</div>
                <div class="exercise-hint">💡 Pista: ${ex.pista || 'Resuelve paso a paso'}</div>
                <input type="number" class="exercise-input" id="answer-${index}" 
                       placeholder="Tu respuesta" value="${userAnswer}" ${result !== undefined ? 'disabled' : ''}>
                ${!result ? `<button class="btn-check-exercise" onclick="checkExercise(${index})">Verificar</button>` : ''}
                <div class="exercise-feedback ${feedbackClass}">${feedbackText}</div>
            </div>
        `;
    });
    
    // Mostrar resumen si todos están respondidos
    const allAnswered = exerciseResults.length === currentExercises.length && 
                        exerciseResults.every(r => r !== undefined);
    
    if (allAnswered) {
        const correctCount = exerciseResults.filter(r => r === true).length;
        const score = (correctCount / currentExercises.length) * 100;
        
        html += `
            <div class="exercises-summary">
                <h4>📊 Resumen</h4>
                <p>Correctos: ${correctCount} de ${currentExercises.length}</p>
                <p>Puntaje: ${score}%</p>
                <button id="btn-retry-exercises" class="btn-primary" style="margin-top: 10px;">Generar nuevos ejercicios</button>
            </div>
        `;
        
        setTimeout(() => {
            const retryBtn = document.getElementById('btn-retry-exercises');
            if (retryBtn) {
                retryBtn.addEventListener('click', () => {
                    document.getElementById("btn-generate-exercises").click();
                });
            }
        }, 100);
    }
    
    container.innerHTML = html;
    container.classList.remove('hidden');
    resultsDiv.classList.add('hidden');
    
    // Agregar event listeners a los inputs
    currentExercises.forEach((_, index) => {
        const input = document.getElementById(`answer-${index}`);
        if (input && exerciseResults[index] === undefined) {
            input.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    checkExercise(index);
                }
            });
        }
    });
}

window.checkExercise = function(index) {
    const input = document.getElementById(`answer-${index}`);
    const userAnswer = input.value.trim();
    
    if (!userAnswer) {
        alert("Ingresa una respuesta");
        return;
    }
    
    const exercise = currentExercises[index];
    const isCorrect = parseInt(userAnswer) === parseInt(exercise.respuesta_esperada);
    
    exerciseAnswers[index] = userAnswer;
    exerciseResults[index] = isCorrect;
    
    // Actualizar el perfil del estudiante con el resultado
    updateStudentProgress(exercise.pregunta, isCorrect);
    
    renderExercises();
};

async function updateStudentProgress(question, isCorrect) {
    // Opcional: enviar al backend para actualizar el perfil del estudiante
    try {
        await fetch('/student/progress', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                student_id: currentStudent.id,
                question: question,
                is_correct: isCorrect,
                topic: 'ejercicios'
            })
        });
    } catch (error) {
        console.error("Error actualizando progreso:", error);
    }
}

// ========== FUNCIÓN GENÉRICA PARA LLAMADAS API ==========
async function callApi({ url, body, btnId, btnLabel, resultId }) {
    const btn = document.getElementById(btnId);
    const resultEl = document.getElementById(resultId);

    btn.disabled = true;
    btn.textContent = "Generando...";
    setResult(resultEl, "", true);
    showLoader();

    try {
        const res = await fetch(url, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
        });
        const data = await res.json();
        let texto = data.content || data.detail || "Sin respuesta.";
        if (data.fragmentos && data.fragmentos.length) {
            texto += "\n\n— Fragmentos del material que sustentan la respuesta —";
            data.fragmentos.forEach(f => {
                texto += `\n\n[${f.fuente}]\n${f.texto}`;
            });
        } else if (data.fuentes && data.fuentes.length) {
            texto += "\n\nMaterial del curso consultado: " + data.fuentes.join(", ");
        }
        setResult(resultEl, texto);
    } catch (error) {
        setResult(resultEl, "Error al procesar la solicitud. Verifica que el servidor esté activo.");
        console.error("API Error:", error);
    } finally {
        btn.disabled = false;
        btn.textContent = btnLabel;
        hideLoader();
    }
}

// ========== HELPERS ==========
function setResult(el, text, loading = false) {
    el.textContent = text;
    el.className = loading ? "result-box loading" : "result-box";
    el.classList.remove("hidden");
}

function showError(el, msg) {
    el.textContent = msg;
    el.classList.remove("hidden");
}

// ========== PANEL DEL DOCENTE ==========
// Permite crear y administrar tareas y actividades. A diferencia del flujo
// del estudiante, aquí no hay diagnóstico ni seudónimos: el docente entra
// directo al panel (es un prototipo, todavía sin autenticación).

let teacherAssignments = [];
let teacherFilter = "todas";
let generatedContent = null; // { ejercicios: [...], explicacion: "" }

function escapeHtml(texto) {
    return String(texto == null ? "" : texto)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
}

function openTeacherPanel() {
    marcarNav("btn-teacher-home");
    showView("view-teacher");
    loadAssignments();
}

async function loadAssignments() {
    const listEl = document.getElementById("assignments-list");
    const emptyEl = document.getElementById("assignments-empty");
    listEl.innerHTML = '<p class="empty-msg">Cargando...</p>';
    emptyEl.classList.add("hidden");

    try {
        const res = await fetch("/teacher/assignments");
        if (!res.ok) throw new Error(`Error ${res.status}`);
        teacherAssignments = await res.json();
        renderAssignments();
    } catch (error) {
        console.error("Error cargando tareas:", error);
        listEl.innerHTML = '<p class="empty-msg">No se pudieron cargar las tareas. ¿Está activo el servidor?</p>';
    }
}

function renderAssignments() {
    const listEl = document.getElementById("assignments-list");
    const emptyEl = document.getElementById("assignments-empty");

    const filtradas = teacherFilter === "todas"
        ? teacherAssignments
        : teacherAssignments.filter(a => a.tipo === teacherFilter);

    if (filtradas.length === 0) {
        listEl.innerHTML = "";
        emptyEl.classList.remove("hidden");
        return;
    }
    emptyEl.classList.add("hidden");

    listEl.innerHTML = filtradas.map(a => {
        const ejercicios = (a.content && a.content.ejercicios) || [];
        const explicacion = (a.content && a.content.explicacion) || "";
        const tieneDetalle = ejercicios.length > 0 || explicacion;

        let detalle = "";
        if (tieneDetalle) {
            let ejerciciosHtml = "";
            if (ejercicios.length > 0) {
                ejerciciosHtml = "<h4>Ejercicios</h4><ol>" + ejercicios.map(ex =>
                    `<li>${escapeHtml(ex.pregunta)} — <span class="answer">${escapeHtml(ex.respuesta_esperada)}</span>` +
                    (ex.pista ? ` <em>(${escapeHtml(ex.pista)})</em>` : "") + "</li>"
                ).join("") + "</ol>";
            }
            let explicacionHtml = "";
            if (explicacion) {
                explicacionHtml = "<h4>Explicación</h4><div class=\"assignment-explanation\">" +
                    escapeHtml(explicacion) + "</div>";
            }
            detalle = `<div class="assignment-detail hidden" data-detail="${a.id}">
                ${ejerciciosHtml}${explicacionHtml}
            </div>`;
        }

        const due = a.tipo === "tarea" && a.due_date
            ? `<span class="badge badge-neutral">Entrega: ${escapeHtml(a.due_date)}</span>` : "";
        const tema = a.tema ? `<span class="badge badge-neutral">${escapeHtml(a.tema)}</span>` : "";
        const nivel = `<span class="badge badge-neutral">${LEVEL_LABELS[a.level] || escapeHtml(a.level)}</span>`;
        const nEj = ejercicios.length > 0
            ? `<span class="badge badge-neutral">${ejercicios.length} ejercicio(s)</span>` : "";

        return `
            <div class="assignment-card tipo-${a.tipo}">
                <div class="assignment-head">
                    <div>
                        <div class="assignment-title">${escapeHtml(a.titulo)}</div>
                        <div class="assignment-meta">
                            <span class="badge badge-tipo-${a.tipo}">${a.tipo}</span>
                            ${tema}${nivel}${nEj}${due}
                        </div>
                    </div>
                    <button class="btn-delete" data-delete="${a.id}">Eliminar</button>
                </div>
                ${a.descripcion ? `<p class="assignment-desc">${escapeHtml(a.descripcion)}</p>` : ""}
                ${tieneDetalle ? `<button class="assignment-toggle" data-toggle="${a.id}">Ver contenido ▾</button>${detalle}` : ""}
            </div>
        `;
    }).join("");
}

// Delegación de eventos para los botones dinámicos de la lista
document.getElementById("assignments-list").addEventListener("click", async (e) => {
    const toggleId = e.target.getAttribute("data-toggle");
    const deleteId = e.target.getAttribute("data-delete");

    if (toggleId) {
        const detail = document.querySelector(`[data-detail="${toggleId}"]`);
        if (detail) {
            detail.classList.toggle("hidden");
            const abierto = !detail.classList.contains("hidden");
            e.target.textContent = abierto ? "Ocultar contenido ▴" : "Ver contenido ▾";
        }
    }

    if (deleteId) {
        if (!confirm("¿Eliminar esta tarea/actividad?")) return;
        try {
            const res = await fetch(`/teacher/assignments/${deleteId}`, { method: "DELETE" });
            if (!res.ok) throw new Error(`Error ${res.status}`);
            teacherAssignments = teacherAssignments.filter(a => String(a.id) !== deleteId);
            renderAssignments();
        } catch (error) {
            console.error("Error eliminando:", error);
            alert("No se pudo eliminar. Intenta de nuevo.");
        }
    }
});

// Filtros (Todas / Tareas / Actividades)
document.querySelectorAll(".filter-tabs .tab").forEach(tab => {
    tab.addEventListener("click", () => {
        document.querySelectorAll(".filter-tabs .tab").forEach(t => t.classList.remove("active"));
        tab.classList.add("active");
        teacherFilter = tab.getAttribute("data-filter");
        renderAssignments();
    });
});

document.getElementById("btn-teacher-access").addEventListener("click", openTeacherPanel);
document.getElementById("btn-teacher-logout").addEventListener("click", () => showView("view-welcome"));
document.getElementById("btn-new-assignment").addEventListener("click", openCreateForm);
document.getElementById("back-teacher-create").addEventListener("click", () => {
    showView("view-teacher");
    loadAssignments();
});

function openCreateForm() {
    document.getElementById("input-assign-type").value = "tarea";
    document.getElementById("input-assign-level").value = "basico";
    document.getElementById("input-assign-title").value = "";
    document.getElementById("input-assign-desc").value = "";
    document.getElementById("input-assign-topic").value = "";
    document.getElementById("input-assign-quantity").value = "3";
    document.getElementById("input-assign-due").value = "";
    document.getElementById("input-assign-explanation").checked = false;
    generatedContent = null;
    document.getElementById("generated-preview").classList.add("hidden");
    document.getElementById("generated-preview").innerHTML = "";
    toggleDueDate();
    showView("view-teacher-create");
}

// La fecha de entrega solo aplica a las tareas
function toggleDueDate() {
    const tipo = document.getElementById("input-assign-type").value;
    document.getElementById("due-date-group").classList.toggle("hidden", tipo !== "tarea");
}
document.getElementById("input-assign-type").addEventListener("change", toggleDueDate);

document.getElementById("btn-generate-content").addEventListener("click", async () => {
    const topic = document.getElementById("input-assign-topic").value.trim();
    if (!topic) {
        alert("Indica un tema para generar los ejercicios");
        return;
    }

    const btn = document.getElementById("btn-generate-content");
    btn.disabled = true;
    btn.textContent = "Generando...";
    showLoader();

    try {
        const res = await fetch("/teacher/assignments/generate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                topic: topic,
                student_level: document.getElementById("input-assign-level").value,
                quantity: parseInt(document.getElementById("input-assign-quantity").value) || 3,
                incluir_explicacion: document.getElementById("input-assign-explanation").checked
            })
        });

        const data = await res.json();
        if (!res.ok) throw new Error(data.error || `Error ${res.status}`);

        generatedContent = {
            ejercicios: data.exercises || [],
            explicacion: data.explicacion || "",
            fuentes: data.fuentes || []
        };
        renderGeneratedPreview();
    } catch (error) {
        console.error("Error generando contenido:", error);
        alert("No se pudo generar el contenido: " + error.message);
    } finally {
        btn.disabled = false;
        btn.textContent = "✨ Generar contenido con IA";
        hideLoader();
    }
});

function renderGeneratedPreview() {
    const preview = document.getElementById("generated-preview");
    if (!generatedContent) {
        preview.classList.add("hidden");
        return;
    }

    const ejercicios = generatedContent.ejercicios || [];
    let html = "<h4>Contenido generado (revisa antes de guardar)</h4>";

    if (ejercicios.length > 0) {
        html += "<ol>" + ejercicios.map((ex, i) =>
            `<li>${escapeHtml(ex.pregunta)} — <span class="answer">${escapeHtml(ex.respuesta_esperada)}</span>` +
            (ex.pista ? ` <em>(${escapeHtml(ex.pista)})</em>` : "") +
            ` <button class="exercise-remove" data-remove-ex="${i}">quitar</button></li>`
        ).join("") + "</ol>";
    }

    if (generatedContent.explicacion) {
        html += "<h4>Explicación</h4><div class=\"assignment-explanation\">" +
            escapeHtml(generatedContent.explicacion) + "</div>";
        if (generatedContent.fuentes && generatedContent.fuentes.length) {
            html += `<p class="assignment-desc" style="margin-top:8px;">Material consultado: ${escapeHtml(generatedContent.fuentes.join(", "))}</p>`;
        }
    }

    preview.innerHTML = html;
    preview.classList.remove("hidden");
}

// Quitar un ejercicio generado antes de guardar
document.getElementById("generated-preview").addEventListener("click", (e) => {
    const idx = e.target.getAttribute("data-remove-ex");
    if (idx === null || !generatedContent) return;
    generatedContent.ejercicios.splice(parseInt(idx), 1);
    renderGeneratedPreview();
});

document.getElementById("btn-save-assignment").addEventListener("click", async () => {
    const titulo = document.getElementById("input-assign-title").value.trim();
    if (!titulo) {
        alert("El título es obligatorio");
        return;
    }

    const tipo = document.getElementById("input-assign-type").value;
    const payload = {
        tipo: tipo,
        titulo: titulo,
        descripcion: document.getElementById("input-assign-desc").value.trim(),
        tema: document.getElementById("input-assign-topic").value.trim(),
        level: document.getElementById("input-assign-level").value,
        due_date: tipo === "tarea" ? (document.getElementById("input-assign-due").value || null) : null,
        content: generatedContent || {}
    };

    const btn = document.getElementById("btn-save-assignment");
    btn.disabled = true;
    showLoader();

    try {
        const res = await fetch("/teacher/assignments", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || `Error ${res.status}`);

        showView("view-teacher");
        await loadAssignments();
    } catch (error) {
        console.error("Error guardando:", error);
        alert("No se pudo guardar: " + error.message);
    } finally {
        btn.disabled = false;
        hideLoader();
    }
});

// ========== DOCENTE: NAVEGACIÓN ENTRE SECCIONES ==========
function marcarNav(activo) {
    ["btn-teacher-home", "btn-teacher-review", "btn-teacher-corpus", "btn-teacher-metrics"]
        .forEach(id => {
            const el = document.getElementById(id);
            if (el) el.classList.toggle("active", id === activo);
        });
}

function volverAlPanel() {
    detenerTimerReview();
    marcarNav("btn-teacher-home");
    showView("view-teacher");
    loadAssignments();
}

document.getElementById("btn-teacher-home").addEventListener("click", openTeacherPanel);
document.getElementById("btn-teacher-review").addEventListener("click", () => {
    marcarNav("btn-teacher-review");
    openReviewView();
});
document.getElementById("btn-teacher-corpus").addEventListener("click", () => {
    marcarNav("btn-teacher-corpus");
    openCorpusView();
});
document.getElementById("btn-teacher-metrics").addEventListener("click", () => {
    marcarNav("btn-teacher-metrics");
    openMetricsView();
});
document.getElementById("back-teacher-review").addEventListener("click", volverAlPanel);
document.getElementById("back-teacher-corpus").addEventListener("click", volverAlPanel);
document.getElementById("back-teacher-metrics").addEventListener("click", volverAlPanel);

// ========== DOCENTE: REVISIÓN DE MATERIAL (RF10, RF12, RF13) ==========

let reviewMaterial = null;
let reviewSegundos = 0;
let reviewTimerId = null;

function openReviewView() {
    detenerTimerReview();
    reviewMaterial = null;
    reviewSegundos = 0;
    document.getElementById("review-area").classList.add("hidden");
    document.getElementById("review-msg").classList.add("hidden");
    document.getElementById("review-editor").innerHTML = "";
    document.getElementById("review-fragments-list").innerHTML = "";
    document.getElementById("input-review-tema").value = "";
    document.getElementById("input-review-tipo").value = "explicacion";
    document.getElementById("input-review-level").value = "basico";
    document.getElementById("input-review-quantity").value = "3";
    toggleReviewQuantity();
    showView("view-teacher-review");
}

function toggleReviewQuantity() {
    const tipo = document.getElementById("input-review-tipo").value;
    document.getElementById("review-quantity-group").classList.toggle("hidden", tipo !== "ejercicios");
}
document.getElementById("input-review-tipo").addEventListener("change", toggleReviewQuantity);

function iniciarTimerReview() {
    detenerTimerReview();
    reviewSegundos = 0;
    actualizarTimerReview();
    reviewTimerId = setInterval(() => {
        reviewSegundos++;
        actualizarTimerReview();
    }, 1000);
}

function actualizarTimerReview() {
    const el = document.getElementById("review-timer");
    if (el) el.textContent = `⏱ Tiempo de revisión: ${reviewSegundos} s`;
}

function detenerTimerReview() {
    if (reviewTimerId) {
        clearInterval(reviewTimerId);
        reviewTimerId = null;
    }
}

document.getElementById("btn-review-generate").addEventListener("click", async () => {
    const tema = document.getElementById("input-review-tema").value.trim();
    if (!tema) {
        alert("Indica un tema para generar el material");
        return;
    }
    const tipo = document.getElementById("input-review-tipo").value;
    const btn = document.getElementById("btn-review-generate");
    btn.disabled = true;
    btn.textContent = "Generando...";
    showLoader();

    try {
        const res = await fetch("/teacher/material/generate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                tema: tema,
                tipo: tipo,
                level: document.getElementById("input-review-level").value,
                quantity: parseInt(document.getElementById("input-review-quantity").value) || 3
            })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || `Error ${res.status}`);

        reviewMaterial = data;
        renderReview(data);
        document.getElementById("review-area").classList.remove("hidden");
        document.getElementById("review-msg").classList.add("hidden");
        iniciarTimerReview();
    } catch (error) {
        console.error("Error generando material para revisión:", error);
        alert("No se pudo generar el material: " + error.message);
    } finally {
        btn.disabled = false;
        btn.textContent = "Generar material";
        hideLoader();
    }
});

function renderReview(data) {
    const editor = document.getElementById("review-editor");

    if (data.tipo === "explicacion") {
        editor.innerHTML = `<div class="form-group">
            <textarea id="review-text">${escapeHtml(data.contenido.texto)}</textarea>
        </div>`;
    } else {
        const ejs = data.contenido.ejercicios || [];
        editor.innerHTML = ejs.length ? ejs.map((ex, i) => `
            <div class="review-exercise">
                <div class="form-group">
                    <label>Ejercicio ${i + 1}</label>
                    <input type="text" id="review-ej-question-${i}" value="${escapeHtml(ex.pregunta)}" />
                </div>
                <div class="form-row">
                    <div class="form-group">
                        <label>Respuesta esperada</label>
                        <input type="text" id="review-ej-answer-${i}" value="${escapeHtml(ex.respuesta_esperada)}" />
                    </div>
                    <div class="form-group">
                        <label>Pista</label>
                        <input type="text" id="review-ej-hint-${i}" value="${escapeHtml(ex.pista || '')}" />
                    </div>
                </div>
            </div>
        `).join("") : "<p class='empty-msg'>No se generaron ejercicios.</p>";
    }

    const frags = data.fragmentos || [];
    document.getElementById("review-fragments-list").innerHTML = frags.length
        ? frags.map(f => `<div class="fragment-card">
              <div class="fragment-source">📄 ${escapeHtml(f.fuente)}</div>
              <div class="fragment-text">${escapeHtml(f.texto)}</div>
           </div>`).join("")
        : "<p class='empty-msg'>No se recuperó material del corpus para este tema.</p>";
}

function contenidoOriginalTexto(data) {
    if (data.tipo === "explicacion") return data.contenido.texto || "";
    return (data.contenido.ejercicios || []).map((ex, i) =>
        `${i + 1}. ${ex.pregunta} | respuesta: ${ex.respuesta_esperada} | pista: ${ex.pista || ''}`
    ).join("\n");
}

function contenidoEditadoTexto() {
    if (!reviewMaterial) return "";
    if (reviewMaterial.tipo === "explicacion") {
        const ta = document.getElementById("review-text");
        return ta ? ta.value : "";
    }
    return (reviewMaterial.contenido.ejercicios || []).map((_, i) =>
        `${i + 1}. ${document.getElementById("review-ej-question-" + i).value} | ` +
        `respuesta: ${document.getElementById("review-ej-answer-" + i).value} | ` +
        `pista: ${document.getElementById("review-ej-hint-" + i).value}`
    ).join("\n");
}

async function decidirReview(decision) {
    if (!reviewMaterial) return;
    detenerTimerReview();

    const payload = {
        docente: "",
        tipo: reviewMaterial.tipo,
        tema: reviewMaterial.tema,
        level: reviewMaterial.level,
        contenido_original: contenidoOriginalTexto(reviewMaterial),
        contenido_final: decision === "rechazado" ? "" : contenidoEditadoTexto(),
        decision: decision,
        segundos: reviewSegundos,
        fragmentos: reviewMaterial.fragmentos || []
    };

    try {
        const res = await fetch("/teacher/material/decision", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || `Error ${res.status}`);

        const msg = document.getElementById("review-msg");
        msg.textContent = `✔ Decisión registrada: ${decision} (tiempo de revisión: ${reviewSegundos} s).`;
        msg.classList.remove("hidden");

        reviewMaterial = null;
        document.getElementById("review-editor").innerHTML = "";
        document.getElementById("review-fragments-list").innerHTML = "";
        document.getElementById("review-area").classList.add("hidden");
    } catch (error) {
        console.error("Error registrando la decisión:", error);
        alert("No se pudo registrar la decisión: " + error.message);
    }
}

document.getElementById("btn-review-accept").addEventListener("click", () => decidirReview("aceptado"));
document.getElementById("btn-review-save").addEventListener("click", () => decidirReview("editado"));
document.getElementById("btn-review-reject").addEventListener("click", () => decidirReview("rechazado"));

// ========== DOCENTE: CORPUS PROPIO (RF11) ==========

function openCorpusView() {
    document.getElementById("input-corpus-file").value = "";
    document.getElementById("input-corpus-text").value = "";
    document.getElementById("input-corpus-name").value = "";
    showView("view-teacher-corpus");
    loadCorpus();
}

async function loadCorpus() {
    const cont = document.getElementById("corpus-list");
    cont.innerHTML = "<p class='empty-msg'>Cargando...</p>";
    try {
        const res = await fetch("/teacher/corpus");
        const docs = await res.json();
        if (!docs.length) {
            cont.innerHTML = "<p class='empty-msg'>El corpus está vacío.</p>";
            return;
        }
        cont.innerHTML = docs.map(d => `
            <div class="assignment-card">
                <div class="assignment-head">
                    <div>
                        <div class="assignment-title">${escapeHtml(d.nombre)}</div>
                        <div class="assignment-meta">
                            <span class="badge ${d.docente ? 'badge-tipo-actividad' : 'badge-neutral'}">${d.docente ? 'Del docente' : 'De referencia'}</span>
                            <span class="badge badge-neutral">${d.fragmentos} fragmento(s)</span>
                            <span class="badge badge-neutral">${d.tamano} caracteres</span>
                        </div>
                    </div>
                    ${d.docente ? `<button class="btn-delete" data-del-corpus="${escapeHtml(d.nombre)}">Eliminar</button>` : ''}
                </div>
            </div>
        `).join("");
    } catch (error) {
        console.error("Error cargando el corpus:", error);
        cont.innerHTML = "<p class='empty-msg'>No se pudo cargar el corpus. ¿Está activo el servidor?</p>";
    }
}

document.getElementById("input-corpus-file").addEventListener("change", (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
        document.getElementById("input-corpus-text").value = reader.result;
        const nombreEl = document.getElementById("input-corpus-name");
        if (!nombreEl.value) nombreEl.value = file.name;
    };
    reader.readAsText(file);
});

document.getElementById("btn-corpus-upload").addEventListener("click", async () => {
    const fileInput = document.getElementById("input-corpus-file");
    const nombre = document.getElementById("input-corpus-name").value.trim()
        || (fileInput.files[0] ? fileInput.files[0].name : "");
    const contenido = document.getElementById("input-corpus-text").value;

    if (!nombre) {
        alert("Indica el nombre del documento");
        return;
    }
    if (!contenido.trim()) {
        alert("Selecciona un archivo o pega el contenido del documento");
        return;
    }

    const btn = document.getElementById("btn-corpus-upload");
    btn.disabled = true;
    btn.textContent = "Subiendo y reindexando...";
    showLoader();

    try {
        const res = await fetch("/teacher/corpus", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ nombre: nombre, contenido: contenido })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || `Error ${res.status}`);

        fileInput.value = "";
        document.getElementById("input-corpus-text").value = "";
        document.getElementById("input-corpus-name").value = "";
        await loadCorpus();
        alert(`Documento cargado. Índice reconstruido con ${data.fragmentos_indexados} fragmentos.`);
    } catch (error) {
        console.error("Error subiendo el corpus:", error);
        alert("No se pudo subir el documento: " + error.message);
    } finally {
        btn.disabled = false;
        btn.textContent = "Subir y reindexar";
        hideLoader();
    }
});

document.getElementById("corpus-list").addEventListener("click", async (e) => {
    const nombre = e.target.getAttribute("data-del-corpus");
    if (!nombre) return;
    if (!confirm(`¿Eliminar "${nombre}" del corpus?`)) return;
    try {
        const res = await fetch("/teacher/corpus/" + encodeURIComponent(nombre), { method: "DELETE" });
        if (!res.ok) throw new Error(`Error ${res.status}`);
        await loadCorpus();
    } catch (error) {
        console.error("Error eliminando del corpus:", error);
        alert("No se pudo eliminar el documento.");
    }
});

// ========== DOCENTE: MÉTRICAS ==========

function openMetricsView() {
    showView("view-teacher-metrics");
    loadMetrics();
}

function metricCard(valor, etiqueta) {
    return `<div class="metric-card">
        <div class="metric-value">${valor}</div>
        <div class="metric-label">${etiqueta}</div>
    </div>`;
}

async function loadMetrics() {
    const cards = document.getElementById("metrics-cards");
    const hist = document.getElementById("metrics-history");
    cards.innerHTML = "<p class='empty-msg'>Cargando...</p>";

    try {
        const [m, reviews] = await Promise.all([
            fetch("/teacher/metrics").then(r => r.json()),
            fetch("/teacher/materials?limit=20").then(r => r.json())
        ]);

        const pct = (m.aceptacion_sin_edicion * 100).toFixed(0);
        cards.innerHTML = [
            metricCard(m.total, "Materiales revisados"),
            metricCard(pct + "%", "Aceptados sin edición"),
            metricCard(m.tiempo_medio.toFixed(1) + " s", "Tiempo medio de decisión"),
            metricCard(m.tiempo_medio_edicion.toFixed(1) + " s", "Tiempo medio al editar")
        ].join("");

        hist.innerHTML = reviews.length ? reviews.map(r => `
            <div class="assignment-card">
                <div class="assignment-head">
                    <div>
                        <div class="assignment-title">${escapeHtml(r.tema || '(sin tema)')}</div>
                        <div class="assignment-meta">
                            <span class="decision-badge decision-${r.decision}">${r.decision}</span>
                            <span class="badge badge-neutral">${escapeHtml(r.tipo)}</span>
                            <span class="badge badge-neutral">${r.segundos} s</span>
                        </div>
                    </div>
                </div>
            </div>
        `).join("") : "<p class='empty-msg'>Aún no hay decisiones registradas.</p>";
    } catch (error) {
        console.error("Error cargando métricas:", error);
        cards.innerHTML = "<p class='empty-msg'>No se pudieron cargar las métricas. ¿Está activo el servidor?</p>";
    }
}