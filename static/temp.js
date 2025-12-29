/* =========================================
   GLOBAL STATE & MODE DETECTION
   ========================================= */
const isMapMode = typeof SERVER_TASKS !== 'undefined';
const isFocusMode = typeof CURRENT_TASK !== 'undefined';

let currentFocusInterval = null;
let idleTime = 0;
const IDLE_LIMIT = 6; // Seconds before "Zone Check"

// --- EXPOSE FUNCTIONS TO WINDOW (Fixes "Not Defined" errors in HTML) ---
window.enterDeepDive = enterDeepDive;
window.exitDeepDive = exitDeepDive;
window.toggleFocusState = toggleFocusState;
window.completeCurrentTask = completeCurrentTask;
window.toggleSubtask = toggleSubtask;

document.addEventListener('DOMContentLoaded', () => {
    // Only run Map logic if the container exists
    if (document.getElementById('octopus-arms-container')) {
        initMap();
        initSliders();
    }

    // Only run Focus logic if the stage exists
    if (document.getElementById('active-task-stage')) {
        initFocusMode();
        initIdleDetector();
    }
});

/* =========================================
   PART A: MAP MODE LOGIC (temp.html)
   ========================================= */

function initMap() {
    if (!isMapMode) return;

    const armContainer = document.getElementById('octopus-arms-container');
    const reserveList = document.getElementById('reserve-list');

    // 1. Sort & Filter Tasks
    // Sort logic: Active first, then by priority
    const activeAndPending = SERVER_TASKS.filter(t => t.status !== 'completed');
    const completed = SERVER_TASKS.filter(t => t.status === 'completed');

    activeAndPending.sort((a, b) => b.priority - a.priority);

    // Top 8 go to the "Octopus Arms", rest go to Reserve Tank
    const top8 = activeAndPending.slice(0, 8);
    const reserve = [...activeAndPending.slice(8), ...completed];

    // 2. Render Arms
    const radius = 220; // Distance from center
    const totalArms = 8;

    top8.forEach((task, index) => {
        const angleDeg = (360 / totalArms) * index - 90; // -90 to start at top
        const angleRad = angleDeg * (Math.PI / 180);

        const x = radius * Math.cos(angleRad);
        const y = radius * Math.sin(angleRad);

        const node = document.createElement('div');
        // Add classes for styling priorities
        node.className = `task-node ${task.priority > 8 ? 'priority-high' : ''} ${task.status === 'active' ? 'active-node' : ''}`;
        node.style.transform = `translate(${x}px, ${y}px)`;

        node.innerHTML = `
            <div><strong>${task.title}</strong></div>
            <div style="font-size:0.7rem; margin-top:5px; color:#aaa;">P: ${task.priority.toFixed(1)}</div>
        `;

        node.onclick = () => window.location.href = `/focus/${task.id}`;
        armContainer.appendChild(node);
    });

    // 3. Render Reserve
    if (reserveList) {
        reserveList.innerHTML = ''; // Clear existing content
        reserve.forEach(task => {
            const li = document.createElement('li');
            li.innerHTML = `<span>${task.title}</span> <span class="status-tag">${task.status}</span>`;

            // FIX: Make reserve items clickable
            li.style.cursor = 'pointer';
            li.onclick = () => window.location.href = `/focus/${task.id}`;

            // Hover effect logic handled in CSS usually, but added inline for safety
            li.onmouseover = () => li.style.color = '#fff';
            li.onmouseout = () => li.style.color = '#aaa';

            reserveList.appendChild(li);
        });
    }
}


function enterDeepDive() {
    if (!isMapMode) return;

    // 1. Check for ALREADY ACTIVE task
    const active = SERVER_TASKS.find(t => t.status === 'active');
    if (active) {
        window.location.href = `/focus/${active.id}`;
        return;
    }

    // 2. If no active task, find highest priority PENDING or PAUSED task
    // FIX: Added check for 'paused' so they aren't ignored
    const candidates = SERVER_TASKS.filter(t => t.status === 'pending' || t.status === 'paused');
    
    // Sort by priority (Highest first)
    candidates.sort((a, b) => b.priority - a.priority);

    const top = candidates[0];

    if (top) {
        window.location.href = `/focus/${top.id}`;
    } else {
        alert("NO DIRECTIVES FOUND. ADD NEW TASK.");
    }
}

/* =========================================
   PART B: SLIDERS & ADD TASK (Map Mode)
   ========================================= */

function initSliders() {
    const titleInput = document.getElementById('task_title');
    const scoreDisplay = document.getElementById('final_score');

    // --- SAFETY CHECK: STOP if elements are missing ---
    if (!titleInput) return;

    const inputs = {
        urgency: document.getElementById('urgency'),
        fear: document.getElementById('fear'),
        interest: document.getElementById('interest')
    };
    const labels = {
        urgency: document.getElementById('val_urgency'),
        fear: document.getElementById('val_fear'),
        interest: document.getElementById('val_interest')
    };

    // Helper to update visual numbers immediately
    function updateVisuals(u, f, i, score = null) {
        labels.urgency.textContent = u.toFixed(1);
        labels.fear.textContent = f.toFixed(1);
        labels.interest.textContent = i.toFixed(1);

        if (score !== null && scoreDisplay) {
            scoreDisplay.textContent = score.toFixed(2);
        }
    }

    // FIXED: Use Server-Side Calculation logic (consistent with script.js)
    async function updateScore() {
        if (!inputs.urgency) return;

        const u = parseFloat(inputs.urgency.value);
        const f = parseFloat(inputs.fear.value);
        const i = parseFloat(inputs.interest.value);

        // Update visuals immediately (optimistic)
        updateVisuals(u, f, i);

        try {
            const res = await fetch('/api/calculate_score', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ urgency: u, fear: f, interest: i })
            });
            const data = await res.json();

            if (scoreDisplay) scoreDisplay.textContent = data.priority_score.toFixed(2);
        } catch (e) {
            console.error("Score calc error:", e);
        }
    }

    // Attach listeners
    Object.values(inputs).forEach(input => {
        if (input) {
            input.addEventListener('input', updateScore);
        }
    });

    // AI Prediction
    let typingTimer;
    titleInput.addEventListener('keyup', () => {
        clearTimeout(typingTimer);
        typingTimer = setTimeout(async () => {
            const text = titleInput.value.trim();
            if (text.length < 3) return;
            if (scoreDisplay) scoreDisplay.textContent = "...";

            try {
                const res = await fetch('/api/predict', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ title: text })
                });
                const data = await res.json();

                if (inputs.urgency) {
                    inputs.urgency.value = data.urgency;
                    inputs.fear.value = data.fear;
                    inputs.interest.value = data.interest;

                    // Update visuals and score with the prediction data
                    updateVisuals(data.urgency, data.fear, data.interest, data.priority_score);
                }

            } catch (e) {
                console.log("Prediction skipped or failed:", e);
            }
        }, 800);
    });
}

/* =========================================
   PART C: FOCUS MODE LOGIC (focus.html)
   ========================================= */

function initFocusMode() {
    if (!isFocusMode) return;

    // 1. Set Title
    const titleEl = document.getElementById('focus-title');
    if (titleEl) titleEl.textContent = CURRENT_TASK.title.toUpperCase();

    if (titleEl) titleEl.textContent = CURRENT_TASK.title.toUpperCase();

    // --- FIX: Logic for COMPLETED vs ACTIVE tasks ---
    if (CURRENT_TASK.status === 'completed') {
        // 1. Show static final time (greyed out)
        const total = CURRENT_TASK.accumulated || 0;
        const m = Math.floor(total / 60).toString().padStart(2, '0');
        const s = (total % 60).toString().padStart(2, '0');
        
        const display = document.getElementById('focus-timer');
        if (display) {
            display.textContent = `${m}:${s}`;
            display.style.color = '#555'; // Dimmed color
            display.style.textShadow = 'none';
        }

        // 2. Hide control buttons (Pause / Complete)
        const controls = document.querySelector('.focus-controls');
        if (controls) controls.style.display = 'none';

        // 3. Mark title as complete
        if (titleEl) {
            titleEl.innerHTML += ' <span style="font-size:0.5em; color:var(--neon-green)">[COMPLETED]</span>';
        }

    } else {
        // --- NORMAL FLOW for Active/Pending ---
        startFocusTimer(CURRENT_TASK);

        // Auto-Start on page load if not already active
        if (CURRENT_TASK.status !== 'active') {
            fetch(`/start_task/${CURRENT_TASK.id}`, { method: 'POST' });
        }
    }

    renderChecklist(CURRENT_TASK.subtasks || []);
}

function renderChecklist(subtasks) {
    const container = document.getElementById('checklist-container');
    if (!container) return;

    container.innerHTML = '';

    subtasks.forEach(sub => {
        const row = document.createElement('div');
        row.className = `task-row ${sub.status === 'completed' ? 'completed' : ''}`;

        row.innerHTML = `
            <div class="task-row-content">${sub.title}</div>
            <div class="check-indicator"></div>
        `;

        row.onclick = () => toggleSubtask(row, sub.id);
        container.appendChild(row);
    });
}

async function toggleSubtask(rowEl, subId) {
    if (rowEl.classList.contains('completed')) return;

    // Optimistic UI update
    rowEl.classList.add('completed');

    try {
        await fetch(`/toggle_subtask/${subId}`, { method: 'POST' });
    } catch (err) {
        console.error("Failed to toggle subtask server-side", err);
        rowEl.classList.remove('completed');
    }
}

function startFocusTimer(task) {
    if (currentFocusInterval) clearInterval(currentFocusInterval);

    const display = document.getElementById('focus-timer');
    if (!display) return;

    const startTime = task.start ? new Date(task.start) : new Date();
    const accumulated = task.accumulated || 0;

    currentFocusInterval = setInterval(() => {
        const now = new Date();
        const delta = Math.floor((now - startTime) / 1000);
        const total = accumulated + delta;

        const m = Math.floor(total / 60).toString().padStart(2, '0');
        const s = (total % 60).toString().padStart(2, '0');
        display.textContent = `${m}:${s}`;
    }, 1000);
}

// FIXED: Remove page reload inconsistency
async function toggleFocusState() {
    const btn = document.getElementById('focus-toggle-btn');
    if (!btn) return;

    if (btn.textContent === 'PAUSE') {
        const res = await fetch(`/pause_task/${CURRENT_TASK.id}`, { method: 'POST' });
        const data = await res.json();

        btn.textContent = 'RESUME';
        clearInterval(currentFocusInterval);

        // Save state so we don't lose time if we resume later without reload
        if (data.time_spent) {
            CURRENT_TASK.accumulated = data.time_spent;
        }
    } else {
        await fetch(`/start_task/${CURRENT_TASK.id}`, { method: 'POST' });
        btn.textContent = 'PAUSE';

        // Update local state to resume timer immediately without reload
        CURRENT_TASK.status = 'active';
        CURRENT_TASK.start = new Date().toISOString();
        startFocusTimer(CURRENT_TASK);
    }
}

async function completeCurrentTask() {
    const res = await fetch(`/complete_task/${CURRENT_TASK.id}`, { method: 'POST' });
    const data = await res.json();

    if (data.success) {
        showModal(
            "MISSION ACCOMPLISHED",
            `+${data.xp_gained} XP ACQUIRED`,
            "RETURN TO BASE",
            () => window.location.href = "/"
        );
        const cancel = document.getElementById('modal-cancel-btn');
        if (cancel) cancel.style.display = "none";
    }
}

function exitDeepDive() {
    window.location.href = "/";
}

/* =========================================
   PART D: DISTRACTION DETECTOR
   ========================================= */

function initIdleDetector() {
    function resetTimer() { idleTime = 0; }

    document.onmousemove = resetTimer;
    document.onkeypress = resetTimer;
    document.onclick = resetTimer;

    setInterval(() => {
        idleTime++;
        if (idleTime >= IDLE_LIMIT) {
            showModal(
                "🧠 ZONE CHECK",
                "Sensors detect idle patterns. Are you still with me, Captain?",
                "I'm Stuck",
                () => handleStuckState()
            );
            const cancel = document.getElementById('modal-cancel-btn');
            if (cancel) {
                cancel.textContent = "I'm Focused";
                cancel.onclick = closeModal;
            }
        }
    }, 1000);
}

async function handleStuckState() {
    const msg = document.getElementById('modal-msg');
    if (msg) msg.textContent = "Scanning for dopamine...";

    try {
        const res = await fetch(`/recommend_switch/${CURRENT_TASK.id}`);
        const data = await res.json();

        if (data.found) {
            showModal(
                "ALTERNATIVE FOUND",
                data.message,
                "SWITCH TASK",
                () => window.location.href = `/focus/${data.task_id}`
            );
        } else {
            showModal("NO TASKS FOUND", "Maybe take a 5 min bio-break.", "COPY THAT", closeModal);
        }
    } catch (e) {
        console.error(e);
        closeModal();
    }
}

/* =========================================
   HELPER: MODAL SYSTEM
   ========================================= */
function showModal(title, msg, confirmText, onConfirm) {
    const modal = document.getElementById('octo-modal');
    if (!modal) return;

    document.getElementById('modal-title').textContent = title;
    document.getElementById('modal-msg').textContent = msg;

    const confirmBtn = document.getElementById('modal-confirm-btn');
    confirmBtn.textContent = confirmText;
    confirmBtn.onclick = onConfirm;

    const cancelBtn = document.getElementById('modal-cancel-btn');
    cancelBtn.style.display = 'inline-block';
    cancelBtn.onclick = closeModal;

    modal.style.display = 'flex';
}

function closeModal() {
    const modal = document.getElementById('octo-modal');
    if (modal) modal.style.display = 'none';
    idleTime = 0;
}