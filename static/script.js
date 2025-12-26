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

// This function is ONLY used when you manually drag a slider
async function updateScore() {
    const u = parseFloat(urgencySlider.value);
    const f = parseFloat(fearSlider.value);
    const i = parseFloat(interestSlider.value);

    // Update the numbers next to the sliders immediately
    document.getElementById('val_urgency').textContent = u.toFixed(1);
    document.getElementById('val_fear').textContent = f.toFixed(1);
    document.getElementById('val_interest').textContent = i.toFixed(1);

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

            // 1. Update Slider Values (Visual Position)
            urgencySlider.value = data.urgency;
            fearSlider.value = data.fear;
            interestSlider.value = data.interest;

            // 2. Update Text Labels (Numbers next to sliders)
            document.getElementById('val_urgency').textContent = data.urgency.toFixed(1);
            document.getElementById('val_fear').textContent = data.fear.toFixed(1);
            document.getElementById('val_interest').textContent = data.interest.toFixed(1);

            // 3. Update Final Score DIRECTLY (No 2nd API Call)
            if (data.priority_score !== undefined) {
                scoreDisplay.textContent = data.priority_score.toFixed(2);
            } else {
                scoreDisplay.textContent = "Err";
            }

        } catch (e) {
            console.error('NLP error:', e);
            scoreDisplay.textContent = "Err";
        }
    }, 800);
});


/* ================================
   3. TASK STATE MANAGEMENT
================================ */

async function updateState(taskId, action) {
    const url = `/${action}_task/${taskId}`;

    try {
        const res = await fetch(url, { method: 'POST' });
        const data = await res.json();

        if (data.success) {
            location.reload();
        }
    } catch (err) {
        console.error('State update error:', err);
    }
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
                () => updateState(data.task_id, 'start')
            );
        } else {
            showModal("No Tasks Found", "Maybe take a quick walk?", "Okay", closeModal);
        }
    } catch (e) {
        console.error(e);
        closeModal();
    }
}
