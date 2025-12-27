/* ================================
   1. SLIDER + SCORE LOGIC
   (Matches scoring_service.py)
================================ */

const urgencySlider = document.getElementById('urgency');
const fearSlider = document.getElementById('fear');
const interestSlider = document.getElementById('interest');
const scoreDisplay = document.getElementById('final_score');
const titleInput = document.getElementById('task_title');
const slidersArea = document.getElementById('sliders-area');

// Helper to update the slider positions and the text numbers
function updateVisuals(u, f, i, score = null) {
    // Update inputs
    urgencySlider.value = u;
    fearSlider.value = f;
    interestSlider.value = i;

    // Update text labels
    document.getElementById('val_urgency').textContent = u.toFixed(1);
    document.getElementById('val_fear').textContent = f.toFixed(1);
    document.getElementById('val_interest').textContent = i.toFixed(1);

    // Update score if provided
    if (score !== null) {
        scoreDisplay.textContent = score.toFixed(2);
    }
}

// This function is ONLY used when you manually drag a slider
async function updateScore() {
    const u = parseFloat(urgencySlider.value);
    const f = parseFloat(fearSlider.value);
    const i = parseFloat(interestSlider.value);

    // Update the numbers next to the sliders immediately
    updateVisuals(u, f, i);

    try {
        // ASK PYTHON FOR THE SCORE
        const res = await fetch('/api/calculate_score', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ urgency: u, fear: f, interest: i })
        });

        const data = await res.json();
        scoreDisplay.textContent = data.priority_score.toFixed(2);

    } catch (e) {
        console.error("Score calc error:", e);
    }
}

// Ensure the listeners are still attached for MANUAL dragging
[urgencySlider, fearSlider, interestSlider].forEach(slider => {
    slider.addEventListener('input', updateScore);
});

/* ================================
   2. LIVE NLP ANALYSIS (TYPING)
================================ */

let typingTimer;

titleInput.addEventListener('keyup', () => {
    if (slidersArea) slidersArea.style.opacity = "1";

    clearTimeout(typingTimer);
    typingTimer = setTimeout(async () => {
        const text = titleInput.value.trim();
        if (text.length < 3) return;

        scoreDisplay.textContent = "..."; // Visual feedback

        try {
            const res = await fetch('/api/predict', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ title: text })
            });

            if (!res.ok) throw new Error("API Error");

            const data = await res.json();

            updateVisuals(data.urgency, data.fear, data.interest, data.priority_score);

        } catch (e) {
            console.error('NLP error:', e);
            scoreDisplay.textContent = "Err";
        }
    }, 800);
});

/* ================================
   3. TASK STATE MANAGEMENT (Smooth DOM Update)
================================ */

async function updateState(taskId, action) {
    const url = `/${action}_task/${taskId}`;
    const card = document.getElementById(`card-${taskId}`);
    const btn = card.querySelector('.action-btn'); // Assuming your button has this class

    // Visual Feedback immediately (Optional: add a spinner or dim opactity)
    if (btn) btn.disabled = true;

    try {
        const res = await fetch(url, { method: 'POST' });
        const data = await res.json();

        if (data.success) {
            if (action === 'start') {
                handleStartUI(card, taskId);
            } else if (action === 'pause') {
                handlePauseUI(card, data.time_spent);
            } else if (action === 'complete') {
                handleCompleteUI(card);
            }
        }
    } catch (err) {
        console.error('State update error:', err);
        alert("Something went wrong. Refreshing page...");
        location.reload(); // Fallback
    } finally {
        if (btn) btn.disabled = false;
    }
}

// --- DOM HELPER FUNCTIONS ---

function handleStartUI(targetCard, taskId) {
    // 1. Deactivate any currently active card
    const currentActive = document.querySelector('.task-card.active');
    if (currentActive && currentActive !== targetCard) {
        // We manually "pause" the UI of the old card
        currentActive.classList.remove('active');
        const oldBtn = currentActive.querySelector('button[onclick*="pause"]');
        if (oldBtn) {
            oldBtn.textContent = "▶ Start";
            oldBtn.setAttribute('onclick', `updateState(${currentActive.id.replace('card-', '')}, 'start')`);
            oldBtn.classList.remove('btn-warning');
            oldBtn.classList.add('btn-primary'); // Adjust classes to match your CSS
        }
    }

    // 2. Activate the new card
    targetCard.classList.add('active');

    // 3. Update the button on the new card
    const btn = targetCard.querySelector('button[onclick*="start"]');
    if (btn) {
        btn.textContent = "⏸ Pause";
        btn.setAttribute('onclick', `updateState(${taskId}, 'pause')`);
        btn.classList.remove('btn-primary');
        btn.classList.add('btn-warning');
    }

    // 4. Set timer data (Local time is close enough for display)
    targetCard.setAttribute('data-start', new Date().toISOString());
}

function handlePauseUI(card, totalTimeSpent) {
    // 1. Remove active state
    card.classList.remove('active');

    // 2. Update button back to Start
    const btn = card.querySelector('button[onclick*="pause"]');
    if (btn) {
        btn.textContent = "▶ Resume"; // Or "Start"
        // Extract ID from card ID string "card-123"
        const id = card.id.replace('card-', '');
        btn.setAttribute('onclick', `updateState(${id}, 'start')`);
        btn.classList.remove('btn-warning');
        btn.classList.add('btn-primary');
    }

    // 3. Update accumulated time so the timer doesn't jump when we restart
    card.setAttribute('data-accumulated', totalTimeSpent);
    card.removeAttribute('data-start');

    // 4. Update the timer text immediately to show the final paused time
    const timerDisplay = card.querySelector('.live-timer');
    if (timerDisplay) {
        // Helper to format seconds to MM:SS (Reusing logic if you have it, or simple inline)
        const m = Math.floor(totalTimeSpent / 60);
        const s = totalTimeSpent % 60;
        timerDisplay.textContent = `${m}:${s.toString().padStart(2, '0')}m`;
    }
}

function handleCompleteUI(card) {
    // 1. Visual animation or style change
    card.style.opacity = '0.5';
    card.style.transform = 'scale(0.95)';

    // 2. Remove actions
    const actionsDiv = card.querySelector('.card-actions'); // Adjust selector based on your HTML
    if (actionsDiv) actionsDiv.innerHTML = '<span class="text-success">✔ Done</span>';

    // 3. Move to bottom (Optional)
    // card.parentElement.appendChild(card); 
}


/* ================================
   4. LIVE TIMER (ACTIVE TASK)
================================ */

setInterval(() => {
    const activeCard = document.querySelector('.task-card.active');
    if (!activeCard) return;

    const startTimeStr = activeCard.getAttribute('data-start');
    const accumulatedStr = activeCard.getAttribute('data-accumulated');

    if (!startTimeStr) return;

    const startTime = new Date(startTimeStr);
    const accumulatedSeconds = parseInt(accumulatedStr) || 0;
    const now = new Date();

    const currentSessionSeconds = Math.floor((now - startTime) / 1000);
    const totalSeconds = currentSessionSeconds + accumulatedSeconds;

    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;

    const display = activeCard.querySelector('.live-timer');
    if (!display) return;

    display.textContent = `${minutes}:${seconds.toString().padStart(2, '0')}m`;

    if (minutes > 45) {
        display.style.color = '#ff1744';
        display.style.fontWeight = 'bold';
    }
}, 1000);


/* ================================
   5. SUBTASK TOGGLE
================================ */
async function toggleSubtask(subId) {
    try {
        const res = await fetch(`/toggle_subtask/${subId}`, { method: 'POST' });
        const data = await res.json();

        if (data.success) {
            const checkbox = document.querySelector(`input[onchange="toggleSubtask(${subId})"]`);
            const label = checkbox.nextElementSibling;

            if (data.status === 'completed') {
                label.style.textDecoration = "line-through";
                label.style.color = "#aaa";
            } else {
                label.style.textDecoration = "none";
                label.style.color = "inherit";
            }
        }
    } catch (err) {
        console.error('Subtask toggle failed', err);
    }
}

/* ================================
   6. DISTRACTION DETECTOR
================================ */
let idleTime = 0;
const IDLE_LIMIT = 6; // seconds for testing

function resetIdleTimer() { idleTime = 0; }
document.onmousemove = resetIdleTimer;
document.onkeypress = resetIdleTimer;
document.onclick = resetIdleTimer;

// Get modal from DOM
function getModal() {
    return document.getElementById('octo-modal');
}

// Show modal with dynamic title, message, and confirm button action
function showModal(title, msg, onConfirmText, onConfirmAction) {
    const modal = getModal();
    if (!modal) return;

    document.getElementById('modal-title').textContent = title;
    document.getElementById('modal-msg').textContent = msg;

    const confirmBtn = document.getElementById('modal-confirm-btn');
    confirmBtn.textContent = onConfirmText;
    confirmBtn.onclick = onConfirmAction;

    document.getElementById('modal-cancel-btn').onclick = closeModal;

    modal.style.display = 'flex';
}

function closeModal() {
    const modal = getModal();
    if (modal) modal.style.display = 'none';
    resetIdleTimer();
}

// Idle check every second
setInterval(() => {
    const activeCard = document.querySelector('.task-card.active');
    if (activeCard) {
        idleTime++;
        if (idleTime >= IDLE_LIMIT) {
            showModal(
                "🧠 Zone Check",
                "You haven't clicked anything in a while. Are you still focused on this task?",
                "No, I'm Stuck",
                () => {
                    const currentId = activeCard.id.replace('card-', '');
                    fetchRecommendation(currentId);
                }
            );
            idleTime = 0;
        }
    }
}, 1000);

// Fetch recommendation and update modal
async function fetchRecommendation(currentTaskId) {
    document.getElementById('modal-msg').textContent = "Analyzing database for dopamine...";

    try {
        const res = await fetch(`/recommend_switch/${currentTaskId}`);
        const data = await res.json();

        if (data.found) {
            showModal(
                "Recommendation Found",
                data.message,
                "Let's Do It",
                () => {
                    // 1. Update the state and close modal
                    updateState(data.task_id, 'start');
                    closeModal();

                    // 2. Auto-scroll to the new task
                    setTimeout(() => {
                        const targetCard = document.getElementById(`card-${data.task_id}`);

                        if (targetCard) {
                            targetCard.scrollIntoView({
                                behavior: 'smooth',
                                block: 'center' // Puts the card in the middle of the screen
                            });

                            //  Add a temporary flash effect so the eye catches it
                            targetCard.style.transition = "transform 0.3s";
                            targetCard.style.transform = "scale(1.05)";
                            setTimeout(() => targetCard.style.transform = "scale(1)", 300);
                        }
                    }, 200); // 200ms delay to ensure DOM is ready
                }
            );
        } else {
            showModal("No Tasks Found", "Maybe take a quick walk?", "Okay", closeModal);
        }
    } catch (e) {
        console.error(e);
        closeModal();
    }
}
