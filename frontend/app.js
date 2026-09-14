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
        if (data.fuentes && data.fuentes.length) {
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