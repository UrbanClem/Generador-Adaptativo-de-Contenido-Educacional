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
let currentDiagnosticData = null;  // Guardar datos de la respuesta actual
let lastExerciseTopic = "";        // Guardar el último tema de ejercicios usado
let lastExplanation = "";          // Guardar la última explicación generada

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

// ========== FORMATEO DE DECIMALES ==========
function formatDecimalAnswer(answer) {
    if (!answer) return answer;
    
    let answerStr = answer.toString().trim();
    let num = parseFloat(answerStr);
    if (isNaN(num)) return answerStr;
    
    let rounded = Math.round(num * 100) / 100;
    
    if (Math.abs(num - rounded) < 0.001) {
        return answerStr;
    }
    
    console.log(`Respuesta original: ${answerStr}, redondeada a: ${rounded}`);
    return rounded.toString();
}

function showDecimalWarning(original, rounded) {
    let warningEl = document.getElementById('decimal-warning');
    if (!warningEl) {
        warningEl = document.createElement('div');
        warningEl.id = 'decimal-warning';
        warningEl.className = 'decimal-warning';
        const container = document.querySelector('.form-group');
        if (container) container.appendChild(warningEl);
    }
    warningEl.innerHTML = `⚠️ Se ha redondeado tu respuesta de "${original}" a "${rounded}" (máximo 2 decimales)`;
    warningEl.classList.remove('hidden');
    
    setTimeout(() => {
        warningEl.classList.add('hidden');
    }, 3000);
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

// ========== NOTIFICACIÓN DE NIVEL ==========
function showLevelUpNotification(newLevel) {
    const notification = document.createElement('div');
    notification.className = 'level-up-notification';
    notification.innerHTML = `
        <div class="level-up-content">
            <span class="level-up-icon">🎉</span>
            <span>¡Has subido de nivel a <strong>${LEVEL_LABELS[newLevel] || newLevel}</strong>!</span>
            <span class="level-up-icon">🎉</span>
        </div>
    `;
    document.body.appendChild(notification);
    
    setTimeout(() => notification.classList.add('show'), 10);
    
    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => notification.remove(), 500);
    }, 4000);
}

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
        currentDiagnosticData = null;
        
        if (currentQuestionsBatch && currentQuestionsBatch.length > 0) {
            displayAdaptiveQuestion(currentQuestionsBatch[0], 1, currentQuestionsBatch.length);
        }
        
        const levelInfoEl = document.getElementById('adaptive-level-info');
        const progressEl = document.getElementById('adaptive-progress');
        if (levelInfoEl) levelInfoEl.innerHTML = `Nivel actual: ${data.current_level}`;
        if (progressEl) progressEl.textContent = `Ronda ${currentDiagnosticSession.round} de ${currentDiagnosticSession.totalRounds}`;
        
        const submitBtn = document.getElementById('btn-submit-adaptive');
        const nextBtn = document.getElementById('btn-next-question');
        if (submitBtn) submitBtn.classList.remove('hidden');
        if (nextBtn) nextBtn.classList.add('hidden');
        
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
        answerInput.disabled = false;
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
    
    if (feedbackDiv) {
        feedbackDiv.classList.add('hidden');
        feedbackDiv.innerHTML = '';
    }
    
    const submitBtn = document.getElementById('btn-submit-adaptive');
    const nextBtn = document.getElementById('btn-next-question');
    const cancelBtn = document.getElementById('btn-cancel-diagnostic');
    
    if (submitBtn) {
        submitBtn.classList.remove('hidden');
        submitBtn.disabled = false;
        submitBtn.style.opacity = '1';
        submitBtn.style.cursor = 'pointer';
    }
    if (nextBtn) nextBtn.classList.add('hidden');
    if (cancelBtn) {
        cancelBtn.disabled = false;
        cancelBtn.style.opacity = '1';
        cancelBtn.style.cursor = 'pointer';
    }
    
    currentDiagnosticData = null;
}

async function submitAdaptiveAnswer() {
    const answerInput = document.getElementById('adaptive-answer-input');
    let answer = answerInput ? answerInput.value.trim() : '';
    if (!answer) {
        alert("Por favor ingresa una respuesta");
        return;
    }
    
    const originalAnswer = answer;
    const formattedAnswer = formatDecimalAnswer(answer);
    if (formattedAnswer !== originalAnswer) {
        showDecimalWarning(originalAnswer, formattedAnswer);
        answer = formattedAnswer;
        answerInput.value = formattedAnswer;
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
    
    if (answerInput) answerInput.disabled = true;
    
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
        currentDiagnosticData = data;
        
        // ✅ ACTUALIZAR NIVEL DEL ESTUDIANTE EN EL FRONTEND
        if (data.current_level && data.current_level !== currentStudent.level) {
            console.log(`🎉 Nivel actualizado: ${currentStudent.level} → ${data.current_level}`);
            const oldLevel = currentStudent.level;
            currentStudent.level = data.current_level;
            
            // Actualizar también level_score si viene
            if (data.level_score) currentStudent.level_score = data.level_score;
            
            // Mostrar notificación si subió de nivel
            if (data.current_level !== oldLevel) {
                showLevelUpNotification(data.current_level);
            }
        }
        
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
            // ✅ Asegurar nivel final
            if (data.current_level) {
                currentStudent.level = data.current_level;
            }
            if (feedbackDiv) feedbackDiv.innerHTML += '<br><br>🎉 ¡Diagnóstico completado! Redirigiendo al dashboard...';
            setTimeout(() => {
                loadDashboard();
                showView('view-dashboard');
                currentDiagnosticSession = null;
            }, 3000);
            hideLoader();
            return;
        }
        
        if (submitBtn) submitBtn.classList.add('hidden');
        const nextBtn = document.getElementById('btn-next-question');
        if (nextBtn) nextBtn.classList.remove('hidden');
        
        if (cancelBtn) {
            cancelBtn.disabled = false;
            cancelBtn.style.opacity = '1';
            cancelBtn.style.cursor = 'pointer';
        }
        
    } catch (error) {
        console.error("Error enviando respuesta:", error);
        alert("Error al procesar la respuesta. Intenta de nuevo.");
        
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.style.opacity = '1';
            submitBtn.style.cursor = 'pointer';
        }
        if (answerInput) answerInput.disabled = false;
        if (cancelBtn) {
            cancelBtn.disabled = false;
            cancelBtn.style.opacity = '1';
            cancelBtn.style.cursor = 'pointer';
        }
    } finally {
        hideLoader();
    }
}

async function nextQuestion() {
    if (!currentDiagnosticData) {
        console.error("No hay datos para la siguiente pregunta");
        return;
    }
    
    const data = currentDiagnosticData;
    const submitBtn = document.getElementById('btn-submit-adaptive');
    const nextBtn = document.getElementById('btn-next-question');
    const feedbackDiv = document.getElementById('adaptive-feedback');
    const cancelBtn = document.getElementById('btn-cancel-diagnostic');
    const answerInput = document.getElementById('adaptive-answer-input');
    
    currentQuestionBatchIndex++;
    
    if (currentQuestionBatchIndex < currentQuestionsBatch.length) {
        if (feedbackDiv) feedbackDiv.classList.add('hidden');
        displayAdaptiveQuestion(
            currentQuestionsBatch[currentQuestionBatchIndex], 
            currentQuestionBatchIndex + 1, 
            currentQuestionsBatch.length
        );
        diagnosticStartTime = Date.now();
        
        if (submitBtn) {
            submitBtn.classList.remove('hidden');
            submitBtn.disabled = false;
            submitBtn.style.opacity = '1';
            submitBtn.style.cursor = 'pointer';
        }
        if (nextBtn) nextBtn.classList.add('hidden');
        if (cancelBtn) {
            cancelBtn.disabled = false;
            cancelBtn.style.opacity = '1';
            cancelBtn.style.cursor = 'pointer';
        }
        
    } else if (data.next_questions && data.next_questions.length > 0) {
        currentQuestionsBatch = data.next_questions;
        currentQuestionBatchIndex = 0;
        
        if (data.next_round && currentDiagnosticSession) {
            currentDiagnosticSession.round = data.next_round;
        }
        const progressEl = document.getElementById('adaptive-progress');
        if (progressEl && currentDiagnosticSession) {
            progressEl.textContent = `Ronda ${currentDiagnosticSession.round} de ${currentDiagnosticSession.totalRounds}`;
        }
        
        if (feedbackDiv) feedbackDiv.classList.add('hidden');
        displayAdaptiveQuestion(
            currentQuestionsBatch[0], 
            1, 
            currentQuestionsBatch.length
        );
        diagnosticStartTime = Date.now();
        
        if (submitBtn) {
            submitBtn.classList.remove('hidden');
            submitBtn.disabled = false;
            submitBtn.style.opacity = '1';
            submitBtn.style.cursor = 'pointer';
        }
        if (nextBtn) nextBtn.classList.add('hidden');
        if (cancelBtn) {
            cancelBtn.disabled = false;
            cancelBtn.style.opacity = '1';
            cancelBtn.style.cursor = 'pointer';
        }
    }
    
    currentDiagnosticData = null;
}

// ========== EXPLICACIÓN PERSONALIZADA CON FEEDBACK ==========
async function generateExplanation() {
    const topicInput = document.getElementById('input-topic-explain');
    const topic = topicInput ? topicInput.value.trim() : '';
    if (!topic) {
        alert("Ingresa un tema");
        return;
    }
    
    showLoader(true);
    const resultEl = document.getElementById('result-explain');
    const feedbackArea = document.getElementById('feedback-area');
    
    // Ocultar feedback area mientras se genera
    if (feedbackArea) feedbackArea.classList.add('hidden');
    
    try {
        const res = await fetch('/explain', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                topic: topic, 
                student_level: currentStudent.level,
                student_id: currentStudent.id
            })
        });
        const data = await res.json();
        
        if (resultEl) {
            const explanationContent = data.content || "Sin respuesta.";
            resultEl.textContent = explanationContent;
            resultEl.classList.remove('hidden');
            lastExplanation = explanationContent;
            
            // Detectar si es un mensaje de error (tema no matemático)
            const isErrorMessage = explanationContent.includes("⚠️ Lo siento, este sistema solo puede ayudarte con temas de MATEMÁTICAS");
            const isEmptyMessage = explanationContent === "Sin respuesta.";
            
            // Solo mostrar feedback si:
            // 1. No es mensaje de error
            // 2. No está vacío
            // 3. El contenido es válido
            if (feedbackArea && !isErrorMessage && !isEmptyMessage) {
                feedbackArea.classList.remove('hidden');
            } else {
                feedbackArea.classList.add('hidden');
            }
        }
    } catch (error) {
        console.error("Error:", error);
        if (resultEl) {
            resultEl.textContent = "Error al generar explicación.";
            resultEl.classList.remove('hidden');
        }
        if (feedbackArea) feedbackArea.classList.add('hidden');
    } finally {
        hideLoader();
    }
}

// Enviar retroalimentación de explicación
async function sendExplanationFeedback(feedback) {
    const topicInput = document.getElementById('input-topic-explain');
    const topic = topicInput ? topicInput.value.trim() : '';
    
    showLoader(true);
    
    try {
        const res = await fetch('/explain/feedback', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                student_id: currentStudent.id,
                topic: topic,
                feedback: feedback,
                explanation: lastExplanation
            })
        });
        
        const data = await res.json();
        if (data.success) {
            alert("✅ Gracias por tu retroalimentación. Mejoraré mis explicaciones.");
            // Ocultar área de feedback después de enviar
            const feedbackArea = document.getElementById('feedback-area');
            if (feedbackArea) feedbackArea.classList.add('hidden');
        }
    } catch (error) {
        console.error("Error enviando feedback:", error);
        alert("Error al enviar retroalimentación");
    } finally {
        hideLoader();
    }
}

// ========== EJERCICIOS INTERACTIVOS ==========
async function generateExercises(resetTopic = false) {
    let topic;
    
    if (resetTopic) {
        // Reiniciar: limpiar todo
        currentExercises = [];
        exerciseAnswers = [];
        exerciseResults = [];
        lastExerciseTopic = "";
        
        const topicInput = document.getElementById('input-topic-exercises');
        if (topicInput) {
            topicInput.value = '';
            topicInput.disabled = false;
            topicInput.focus();
        }
        
        const container = document.getElementById('exercises-container');
        if (container) {
            container.innerHTML = '';
            container.classList.add('hidden');
        }
        
        const resultsDiv = document.getElementById('exercises-results');
        if (resultsDiv) resultsDiv.classList.add('hidden');
        
        return;
    }
    
    // Generar nuevos ejercicios
    const topicInput = document.getElementById('input-topic-exercises');
    topic = topicInput ? topicInput.value.trim() : '';
    
    if (!topic) {
        // Si no hay tema pero hay un tema anterior, reutilizarlo
        if (lastExerciseTopic) {
            topic = lastExerciseTopic;
            if (topicInput) topicInput.value = topic;
        } else {
            alert("Ingresa un tema");
            return;
        }
    }
    
    // Guardar el tema para reutilizar
    lastExerciseTopic = topic;
    
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
            container.innerHTML = `<div class="error-message">❌ Error: ${error.message}<br><br>Verifica que el servidor esté corriendo y que el tema sea matemático.</div>`;
            container.classList.remove('hidden');
        }
    } finally {
        hideLoader();
    }
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
        
        html += `
            <div class="exercise-item" data-index="${index}">
                <div class="exercise-question">${index + 1}. ${ex.pregunta || '?'}</div>
                <div class="exercise-hint">💡 Pista: ${ex.pista || ex.scaffolding_hint || 'Resuelve paso a paso'}</div>
                <input type="number" class="exercise-input" id="answer-${index}" 
                       placeholder="Tu respuesta" value="${userAnswer}" ${result !== undefined ? 'disabled' : ''}>
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
                <div class="summary-buttons">
                    <button id="btn-generate-more" class="btn-primary" style="margin-top: 10px;">Generar más ejercicios</button>
                </div>
            </div>
        `;
        
        setTimeout(() => {
            const generateMoreBtn = document.getElementById('btn-generate-more');
            if (generateMoreBtn) {
                generateMoreBtn.addEventListener('click', () => generateExercises(false));
            }
            const resetFromSummaryBtn = document.getElementById('btn-reset-from-summary');
            if (resetFromSummaryBtn) {
                resetFromSummaryBtn.addEventListener('click', () => generateExercises(true));
            }
        }, 100);
    }
    
    container.innerHTML = html;
    container.classList.remove('hidden');
}

window.checkExercise = async function(index) {
    const input = document.getElementById(`answer-${index}`);
    if (!input) return;
    
    const userAnswer = input.value.trim();
    if (!userAnswer) {
        alert("Ingresa una respuesta");
        return;
    }
    
    const exercise = currentExercises[index];
    if (!exercise) return;
    
    const isCorrect = parseInt(userAnswer) === parseInt(exercise.respuesta_esperada);
    
    exerciseAnswers[index] = userAnswer;
    exerciseResults[index] = isCorrect;
    
    await updateStudentProgressAndLevel(exercise.pregunta, isCorrect);
    
    renderExercises();
};

async function updateStudentProgressAndLevel(question, isCorrect) {
    try {
        const res = await fetch('/student/update-level', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                student_id: currentStudent.id,
                question: question,
                is_correct: isCorrect,
                topic: 'ejercicios'
            })
        });
        
        const data = await res.json();
        
        if (data.new_level && data.new_level !== currentStudent.level) {
            console.log(`🎉 Nivel actualizado por ejercicios: ${currentStudent.level} → ${data.new_level}`);
            const oldLevel = currentStudent.level;
            currentStudent.level = data.new_level;
            currentStudent.level_score = data.new_level_score;
            
            if (data.new_level !== oldLevel) {
                showLevelUpNotification(data.new_level);
            }
            
            const levelEl = document.getElementById('dashboard-level');
            if (levelEl) {
                levelEl.textContent = LEVEL_LABELS[currentStudent.level] || currentStudent.level;
            }
        }
        
    } catch (error) {
        console.error("Error actualizando progreso:", error);
    }
}

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
    
    // Botones de explicación
    const btnGenerateExplain = document.getElementById('btn-generate-explain');
    if (btnGenerateExplain) btnGenerateExplain.addEventListener('click', generateExplanation);
    
    // Botones de ejercicios
    const btnGenerateExercises = document.getElementById('btn-generate-exercises');
    if (btnGenerateExercises) {
        btnGenerateExercises.addEventListener('click', () => generateExercises(false));
    }
    
    const btnResetExercises = document.getElementById('btn-reset-exercises');
    if (btnResetExercises) {
        btnResetExercises.addEventListener('click', () => generateExercises(true));
    }
    
    // Botones de diagnóstico adaptativo
    const submitBtn = document.getElementById('btn-submit-adaptive');
    if (submitBtn) submitBtn.addEventListener('click', submitAdaptiveAnswer);
    
    const nextBtn = document.getElementById('btn-next-question');
    if (nextBtn) nextBtn.addEventListener('click', nextQuestion);
    
    const adaptiveAnswerInput = document.getElementById('adaptive-answer-input');
    if (adaptiveAnswerInput) {
        adaptiveAnswerInput.addEventListener('keydown', (e) => {
            if (e.key === "Enter") {
                const nextQuestionBtn = document.getElementById('btn-next-question');
                if (nextQuestionBtn && !nextQuestionBtn.classList.contains('hidden')) {
                    nextQuestion();
                } else {
                    submitAdaptiveAnswer();
                }
            }
        });
    }
    
    const cancelDiagnosticBtn = document.getElementById('btn-cancel-diagnostic');
    if (cancelDiagnosticBtn) {
        cancelDiagnosticBtn.addEventListener('click', () => {
            currentDiagnosticSession = null;
            currentDiagnosticData = null;
            showView("view-welcome");
        });
    }
    
    // Botones de retroalimentación de explicaciones
    const feedbackBtns = document.querySelectorAll('.feedback-btn');
    feedbackBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const feedback = btn.getAttribute('data-feedback');
            sendExplanationFeedback(feedback);
        });
    });
    
    const submitFeedbackBtn = document.getElementById('submit-feedback');
    if (submitFeedbackBtn) {
        submitFeedbackBtn.addEventListener('click', () => {
            const customFeedback = document.getElementById('custom-feedback').value.trim();
            if (customFeedback) {
                sendExplanationFeedback(customFeedback);
                document.getElementById('custom-feedback').value = '';
            } else {
                alert("Escribe un comentario antes de enviar");
            }
        });
    }
});

function showError(el, msg) {
    if (el) {
        el.textContent = msg;
        el.classList.remove('hidden');
    }
}