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
let currentExercises = [];
let exerciseAnswers = [];
let exerciseResults = [];

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
    const targetView = document.getElementById(id);
    if (targetView) targetView.classList.add("active");
}

// ========== VISTA: BIENVENIDA / LOGIN ==========
async function login() {
    const name = document.getElementById('input-name').value.trim();
    const errorEl = document.getElementById('welcome-error');
    if (!errorEl) return;
    errorEl.classList.add('hidden');

    if (!name) {
        showError(errorEl, "Ingresa tu nombre para continuar.");
        return;
    }

    showLoader(true);
    try {
        const res = await fetch(`/students/${encodeURIComponent(name)}`);
        
        if (res.ok) {
            currentStudent = await res.json();
            loadDashboard();
        } else if (res.status === 404) {
            currentStudentName = name;
            
            const testRes = await fetch('/diagnostic/test', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ student_name: name })
            });
            
            if (!testRes.ok) {
                const errorData = await testRes.json();
                showError(errorEl, `No se puede iniciar diagnóstico: ${errorData.error || 'Error de IA'}`);
                hideLoader();
                return;
            }
            
            const createRes = await fetch('/students', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: name, level: 'basico', diagnostic_results: {} })
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

// ========== DASHBOARD ==========
function loadDashboard() {
    const nameEl = document.getElementById('dashboard-name');
    const levelEl = document.getElementById('dashboard-level');
    if (nameEl) nameEl.textContent = `Bienvenido, ${currentStudent.name}`;
    if (levelEl) levelEl.textContent = LEVEL_LABELS[currentStudent.level] || currentStudent.level;
    showView("view-dashboard");
}

// ========== DIAGNÓSTICO ADAPTATIVO ==========
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
        
        const levelInfoEl = document.getElementById('adaptive-level-info');
        const progressEl = document.getElementById('adaptive-progress');
        if (levelInfoEl) levelInfoEl.innerHTML = `Nivel actual: ${data.current_level}`;
        if (progressEl) progressEl.textContent = `Ronda ${currentDiagnosticSession.round} de ${currentDiagnosticSession.totalRounds}`;
        
        showView('view-adaptive-diagnostic');
    } catch (error) {
        console.error("Error iniciando diagnóstico adaptativo:", error);
        alert("Error al iniciar el diagnóstico. Intenta de nuevo.");
    } finally {
        hideLoader();
    }
}

function displayAdaptiveQuestion(question, index, total) {
    const counterEl = document.getElementById('adaptive-question-counter');
    const textEl = document.getElementById('adaptive-question-text');
    const answerInput = document.getElementById('adaptive-answer-input');
    const hintContainer = document.getElementById('adaptive-scaffolding-hint');
    const feedbackDiv = document.getElementById('adaptive-feedback');
    
    if (counterEl) counterEl.textContent = `Pregunta ${index} de ${total}`;
    if (textEl) textEl.textContent = question.pregunta;
    if (answerInput) {
        answerInput.value = '';
        answerInput.focus();
    }
    
    if (hintContainer) {
        if (question.scaffolding_hint) {
            hintContainer.textContent = `💡 Pista: ${question.scaffolding_hint}`;
            hintContainer.classList.remove('hidden');
        } else {
            hintContainer.classList.add('hidden');
        }
    }
    
    if (feedbackDiv) feedbackDiv.classList.add('hidden');
}

async function submitAdaptiveAnswer() {
    const answerInput = document.getElementById('adaptive-answer-input');
    const answer = answerInput ? answerInput.value.trim() : '';
    if (!answer) {
        alert("Por favor ingresa una respuesta");
        return;
    }
    
    const currentQuestion = currentQuestionsBatch[currentQuestionBatchIndex];
    const responseTime = (Date.now() - diagnosticStartTime) / 1000;
    
    const submitBtn = document.getElementById('btn-submit-adaptive');
    const cancelBtn = document.getElementById('btn-cancel-diagnostic');
    
    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.style.opacity = '0.6';
        submitBtn.style.cursor = 'not-allowed';
    }
    if (cancelBtn) {
        cancelBtn.disabled = true;
        cancelBtn.style.opacity = '0.6';
        cancelBtn.style.cursor = 'not-allowed';
    }
    
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
        if (feedbackDiv) {
            if (data.is_correct) {
                feedbackDiv.innerHTML = `✅ ¡Correcto! ${data.feedback?.reasoning || ''}`;
                feedbackDiv.className = 'feedback-correct';
            } else {
                feedbackDiv.innerHTML = `❌ Incorrecto. La respuesta correcta era: ${currentQuestion.respuesta_esperada}<br>${data.feedback?.reasoning || ''}`;
                feedbackDiv.className = 'feedback-incorrect';
            }
            feedbackDiv.classList.remove('hidden');
        }
        
        const levelInfoEl = document.getElementById('adaptive-level-info');
        if (levelInfoEl) {
            levelInfoEl.innerHTML = `Nivel actual: ${data.current_level}<br>Fortalezas: ${data.profile_feedback?.strengths?.slice(0, 2).join(', ') || 'Identificando...'}`;
        }
        
        if (data.is_complete) {
            if (feedbackDiv) feedbackDiv.innerHTML += '<br><br>🎉 ¡Diagnóstico completado! Redirigiendo al dashboard...';
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
                if (feedbackDiv) feedbackDiv.classList.add('hidden');
                displayAdaptiveQuestion(currentQuestionsBatch[currentQuestionBatchIndex], currentQuestionBatchIndex + 1, currentQuestionsBatch.length);
                diagnosticStartTime = Date.now();
                if (submitBtn) {
                    submitBtn.disabled = false;
                    submitBtn.style.opacity = '1';
                    submitBtn.style.cursor = 'pointer';
                }
                if (cancelBtn) {
                    cancelBtn.disabled = false;
                    cancelBtn.style.opacity = '1';
                    cancelBtn.style.cursor = 'pointer';
                }
            }, 2000);
        } 
        else if (data.next_questions && data.next_questions.length > 0) {
            currentQuestionsBatch = data.next_questions;
            currentQuestionBatchIndex = 0;
            
            if (data.next_round && currentDiagnosticSession) {
                currentDiagnosticSession.round = data.next_round;
            }
            const progressEl = document.getElementById('adaptive-progress');
            if (progressEl && currentDiagnosticSession) {
                progressEl.textContent = `Ronda ${currentDiagnosticSession.round} de ${currentDiagnosticSession.totalRounds}`;
            }
            
            setTimeout(() => {
                if (feedbackDiv) feedbackDiv.classList.add('hidden');
                displayAdaptiveQuestion(currentQuestionsBatch[0], 1, currentQuestionsBatch.length);
                diagnosticStartTime = Date.now();
                if (submitBtn) {
                    submitBtn.disabled = false;
                    submitBtn.style.opacity = '1';
                    submitBtn.style.cursor = 'pointer';
                }
                if (cancelBtn) {
                    cancelBtn.disabled = false;
                    cancelBtn.style.opacity = '1';
                    cancelBtn.style.cursor = 'pointer';
                }
            }, 2000);
        }
        
    } catch (error) {
        console.error("Error enviando respuesta:", error);
        alert("Error al procesar la respuesta. Intenta de nuevo.");
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.style.opacity = '1';
            submitBtn.style.cursor = 'pointer';
        }
        if (cancelBtn) {
            cancelBtn.disabled = false;
            cancelBtn.style.opacity = '1';
            cancelBtn.style.cursor = 'pointer';
        }
    } finally {
        hideLoader();
    }
}

// ========== EXPLICACIÓN PERSONALIZADA ==========
async function generateExplanation() {
    const topicInput = document.getElementById('input-topic-explain');
    const topic = topicInput ? topicInput.value.trim() : '';
    if (!topic) {
        alert("Ingresa un tema");
        return;
    }
    
    showLoader(true);
    const resultEl = document.getElementById('result-explain');
    
    try {
        const res = await fetch('/explain', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ topic: topic, student_level: currentStudent.level })
        });
        const data = await res.json();
        if (resultEl) {
            resultEl.textContent = data.content || "Sin respuesta.";
            resultEl.classList.remove('hidden');
        }
    } catch (error) {
        console.error("Error:", error);
        if (resultEl) {
            resultEl.textContent = "Error al generar explicación.";
            resultEl.classList.remove('hidden');
        }
    } finally {
        hideLoader();
    }
}

// ========== EJERCICIOS INTERACTIVOS ==========
async function generateExercises() {
    const topicInput = document.getElementById('input-topic-exercises');
    const topic = topicInput ? topicInput.value.trim() : '';
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
        
        if (!res.ok) {
            const errorData = await res.json();
            throw new Error(errorData.error || `HTTP error! status: ${res.status}`);
        }
        
        const data = await res.json();
        console.log("Ejercicios recibidos:", data);
        
        if (data.error) {
            throw new Error(data.error);
        }
        
        if (data.exercises && Array.isArray(data.exercises) && data.exercises.length > 0) {
            currentExercises = data.exercises;
            exerciseAnswers = new Array(currentExercises.length).fill('');
            exerciseResults = new Array(currentExercises.length).fill(undefined);
            renderExercises();
        } else {
            throw new Error("El servidor no devolvió ejercicios válidos");
        }
        
    } catch (error) {
        console.error("Error generando ejercicios:", error);
        const container = document.getElementById('exercises-container');
        if (container) {
            container.innerHTML = `<div class="error-message">❌ Error: ${error.message}<br><br>Intenta con otro tema o más tarde.</div>`;
            container.classList.remove('hidden');
        }
    } finally {
        hideLoader();
    }
}

function formatMathText(text) {
    if (!text) return '';
    
    // Convertir **texto** a <strong>texto</strong> (negritas)
    text = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    
    // Convertir *texto* a <em>texto</em> (cursiva)
    text = text.replace(/\*(.*?)\*/g, '<em>$1</em>');
    
    // Convertir expresiones matemáticas como \( ... \) a formato legible
    text = text.replace(/\\\((.*?)\\\)/g, '<span class="math-inline">$1</span>');
    text = text.replace(/\\\[(.*?)\\\]/g, '<span class="math-block">$1</span>');
    
    return text;
}

function renderExercises() {
    const container = document.getElementById('exercises-container');
    if (!container) return;
    
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
        
        // Formatear pregunta y pista para eliminar asteriscos
        const preguntaFormateada = formatMathText(ex.pregunta || '?');
        const pistaFormateada = formatMathText(ex.pista || ex.scaffolding_hint || 'Resuelve paso a paso');
        
        const inputType = ex.is_math ? 'number' : 'text';
        const inputStep = ex.is_math ? 'step="any"' : '';
        const placeholder = ex.is_math ? 'Tu respuesta (solo número)' : 'Tu respuesta';
        
        html += `
            <div class="exercise-item" data-index="${index}">
                <div class="exercise-question">${index + 1}. ${preguntaFormateada}</div>
                <div class="exercise-hint">💡 Pista: ${pistaFormateada}</div>
                <input type="${inputType}" ${inputStep} class="exercise-input" id="answer-${index}" 
                       placeholder="${placeholder}" value="${userAnswer}" ${result !== undefined ? 'disabled' : ''}>
                ${result === undefined ? `<button class="btn-check-exercise" onclick="checkExercise(${index})">Verificar</button>` : ''}
                <div class="exercise-feedback ${feedbackClass}">${feedbackText}</div>
            </div>
        `;
    });
    
    const allAnswered = exerciseResults.length === currentExercises.length && 
                        exerciseResults.every(r => r !== undefined);
    
    if (allAnswered) {
        const correctCount = exerciseResults.filter(r => r === true).length;
        const score = (correctCount / currentExercises.length) * 100;
        
        html += `
            <div class="exercises-summary">
                <h4>📊 Resumen</h4>
                <p>Correctos: ${correctCount} de ${currentExercises.length}</p>
                <p>Puntaje: ${score.toFixed(0)}%</p>
                <button id="btn-retry-exercises" class="btn-primary" style="margin-top: 10px;">Generar nuevos ejercicios</button>
            </div>
        `;
        
        setTimeout(() => {
            const retryBtn = document.getElementById('btn-retry-exercises');
            if (retryBtn) {
                retryBtn.addEventListener('click', generateExercises);
            }
        }, 100);
    }
    
    container.innerHTML = html;
    container.classList.remove('hidden');
}

window.checkExercise = function(index) {
    const input = document.getElementById(`answer-${index}`);
    if (!input) return;
    
    const userAnswer = input.value.trim();
    if (!userAnswer) {
        alert("Ingresa una respuesta");
        return;
    }
    
    const exercise = currentExercises[index];
    if (!exercise) return;
    
    let isCorrect = false;
    
    if (exercise.is_math) {
        // Comparación numérica con tolerancia para ejercicios de matemáticas
        const studentNum = parseFloat(userAnswer);
        const expectedNum = parseFloat(exercise.respuesta_esperada);
        if (!isNaN(studentNum) && !isNaN(expectedNum)) {
            isCorrect = Math.abs(studentNum - expectedNum) < 0.01;
        }
    } else {
        // Comparación por texto para otros temas
        isCorrect = userAnswer.toLowerCase() === String(exercise.respuesta_esperada).toLowerCase();
    }
    
    exerciseAnswers[index] = userAnswer;
    exerciseResults[index] = isCorrect;
    
    renderExercises();
};

// ========== INICIALIZAR EVENTOS ==========
document.addEventListener('DOMContentLoaded', () => {
    // Botones de navegación
    const btnEnter = document.getElementById('btn-enter');
    if (btnEnter) btnEnter.addEventListener('click', login);
    
    const inputName = document.getElementById('input-name');
    if (inputName) inputName.addEventListener('keydown', (e) => { if (e.key === "Enter") login(); });
    
    const btnLogout = document.getElementById('btn-logout');
    if (btnLogout) btnLogout.addEventListener('click', () => {
        currentStudent = null;
        const nameInput = document.getElementById('input-name');
        if (nameInput) nameInput.value = "";
        showView("view-welcome");
    });
    
    const btnExplain = document.getElementById('btn-explain');
    if (btnExplain) btnExplain.addEventListener('click', () => showView("view-explain"));
    
    const btnExercises = document.getElementById('btn-exercises');
    if (btnExercises) btnExercises.addEventListener('click', () => showView("view-exercises"));
    
    const backExplain = document.getElementById('back-explain');
    if (backExplain) backExplain.addEventListener('click', () => showView("view-dashboard"));
    
    const backExercises = document.getElementById('back-exercises');
    if (backExercises) backExercises.addEventListener('click', () => showView("view-dashboard"));
    
    const btnGenerateExplain = document.getElementById('btn-generate-explain');
    if (btnGenerateExplain) btnGenerateExplain.addEventListener('click', generateExplanation);
    
    const btnGenerateExercises = document.getElementById('btn-generate-exercises');
    if (btnGenerateExercises) btnGenerateExercises.addEventListener('click', generateExercises);
    
    const btnSubmitAdaptive = document.getElementById('btn-submit-adaptive');
    if (btnSubmitAdaptive) btnSubmitAdaptive.addEventListener('click', submitAdaptiveAnswer);
    
    const adaptiveAnswerInput = document.getElementById('adaptive-answer-input');
    if (adaptiveAnswerInput) adaptiveAnswerInput.addEventListener('keydown', (e) => { if (e.key === "Enter") submitAdaptiveAnswer(); });
    
    const btnCancelDiagnostic = document.getElementById('btn-cancel-diagnostic');
    if (btnCancelDiagnostic) btnCancelDiagnostic.addEventListener('click', () => {
        currentDiagnosticSession = null;
        showView("view-welcome");
    });
});

// ========== HELPERS ==========
function showError(el, msg) {
    if (el) {
        el.textContent = msg;
        el.classList.remove('hidden');
    }
}