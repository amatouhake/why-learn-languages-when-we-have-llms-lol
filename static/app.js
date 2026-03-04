(() => {
    "use strict";

    // --- State ---
    const RING_SIZE = 20;
    let state = "SETUP"; // SETUP | LOADING | READY | ANSWERED
    let quizMode = 4;
    let levels = [1, 2, 3];
    let sessionId = sessionStorage.getItem("session_id");
    if (!sessionId) {
        sessionId = typeof crypto.randomUUID === "function"
            ? crypto.randomUUID()
            : Array.from(crypto.getRandomValues(new Uint8Array(16)), b => b.toString(16).padStart(2, "0")).join("");
        sessionStorage.setItem("session_id", sessionId);
    }

    let lang = "en";
    let direction = "random";
    let currentQuestion = null;
    let timerStart = 0;
    let streak = 0;
    let bestStreak = 0;

    // Ring buffer of recent word_ids to exclude
    const recentIds = [];

    // --- DOM refs ---
    const setupScreen = document.getElementById("setup-screen");
    const quizScreen = document.getElementById("quiz-screen");
    const dashboardScreen = document.getElementById("dashboard-screen");
    const promptEl = document.getElementById("prompt");
    const promptSubEl = document.getElementById("prompt-sub");
    const optionsEl = document.getElementById("options");
    const streakEl = document.getElementById("streak");
    const bestStreakEl = document.getElementById("best-streak");
    const loadingEl = document.getElementById("loading-indicator");
    const backBtn = document.getElementById("back-btn");
    const dashboardBtn = document.getElementById("dashboard-btn");
    const dashboardBackBtn = document.getElementById("dashboard-back-btn");
    const exampleArea = document.getElementById("example-area");
    const exampleZhEl = document.getElementById("example-zh");
    const examplePinyinEl = document.getElementById("example-pinyin");
    const exampleMeaningEl = document.getElementById("example-meaning");

    // --- Setup screen ---
    document.querySelectorAll(".mode-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            const checked = document.querySelectorAll(".checkboxes input:checked");
            if (checked.length === 0) return;
            levels = Array.from(checked).map(cb => parseInt(cb.value));
            quizMode = parseInt(btn.dataset.mode);
            lang = document.querySelector('input[name="lang"]:checked').value;
            direction = document.querySelector('input[name="direction"]:checked').value;
            startQuiz();
        });
    });

    backBtn.addEventListener("click", () => {
        showScreen("SETUP");
    });

    dashboardBtn.addEventListener("click", () => {
        showScreen("DASHBOARD");
        loadDashboard();
    });

    dashboardBackBtn.addEventListener("click", () => {
        showScreen("SETUP");
    });

    function showScreen(screen) {
        setupScreen.classList.toggle("active", screen === "SETUP");
        quizScreen.classList.toggle("active", screen === "QUIZ");
        dashboardScreen.classList.toggle("active", screen === "DASHBOARD");
        if (screen === "SETUP" || screen === "DASHBOARD") state = screen;
    }

    // --- Quiz flow ---
    function startQuiz() {
        streak = 0;
        bestStreak = 0;
        recentIds.length = 0;
        updateStreakDisplay();
        showScreen("QUIZ");
        fetchQuestion();
    }

    async function fetchQuestion() {
        state = "LOADING";
        loadingEl.classList.add("active");
        optionsEl.innerHTML = "";
        promptEl.textContent = "";
        promptSubEl.textContent = "";

        const exclude = recentIds.join(",");
        const url = `/api/quiz?mode=${quizMode}&levels=${levels.join(",")}&exclude=${exclude}&lang=${lang}&direction=${direction}`;

        try {
            const res = await fetch(url);
            const data = await res.json();
            currentQuestion = data;
            renderQuestion(data);
        } catch (err) {
            loadingEl.textContent = "エラー: " + err.message;
        }
    }

    function renderQuestion(q) {
        loadingEl.classList.remove("active");
        exampleArea.style.display = "none";

        promptEl.textContent = q.prompt;
        promptSubEl.textContent = q.prompt_sub || "";

        // Adjust prompt size for meaning→hanzi (longer text)
        if (q.direction === "meaning_to_hanzi") {
            promptEl.style.fontSize = "2rem";
        } else {
            promptEl.style.fontSize = "";
        }

        // Options layout
        if (quizMode === 9) {
            optionsEl.className = "options grid-9";
        } else {
            optionsEl.className = "options";
        }

        optionsEl.innerHTML = "";
        for (const opt of q.options) {
            const btn = document.createElement("button");
            btn.className = "option-btn";
            btn.dataset.index = opt.index;

            const keySpan = document.createElement("span");
            keySpan.className = "option-key";
            keySpan.textContent = opt.index;

            const textSpan = document.createElement("span");
            textSpan.className = "option-text";
            textSpan.textContent = opt.text;

            btn.appendChild(keySpan);
            btn.appendChild(textSpan);
            btn.addEventListener("click", () => handleAnswer(opt.index));
            optionsEl.appendChild(btn);
        }

        // Play audio for hanzi→meaning
        if (q.direction === "hanzi_to_meaning" && q.has_audio) {
            playAudio(q.prompt);
        }

        timerStart = performance.now();
        state = "READY";
    }

    function playAudio(hanzi) {
        const audio = new Audio(`/audio/cmn-${encodeURIComponent(hanzi)}.mp3`);
        audio.play().catch(() => {}); // Ignore autoplay errors
    }

    function handleAnswer(chosenIndex) {
        if (state !== "READY") return;
        state = "ANSWERED";

        const elapsed = Math.round(performance.now() - timerStart);
        const isCorrect = chosenIndex === currentQuestion.correct_index;

        // Visual feedback
        const buttons = optionsEl.querySelectorAll(".option-btn");
        buttons.forEach(btn => {
            const idx = parseInt(btn.dataset.index);
            if (idx === currentQuestion.correct_index) {
                btn.classList.add("correct");
            } else if (idx === chosenIndex && !isCorrect) {
                btn.classList.add("incorrect");
            }
        });

        // Update streak locally
        if (isCorrect) {
            streak++;
            if (streak > bestStreak) bestStreak = streak;
        } else {
            streak = 0;
        }
        updateStreakDisplay();

        // Track recent word_ids (ring buffer)
        recentIds.push(currentQuestion.word_id);
        if (recentIds.length > RING_SIZE) recentIds.shift();

        // Fire-and-forget POST
        fetch("/api/answer", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                word_id: currentQuestion.word_id,
                correct: isCorrect,
                response_time_ms: elapsed,
                quiz_mode: quizMode,
                session_id: sessionId,
            }),
        }).then(res => res.json()).then(data => {
            // Sync best_streak from server
            if (data.best_streak > bestStreak) {
                bestStreak = data.best_streak;
                updateStreakDisplay();
            }
        }).catch(() => {});

        // Show example sentence if available
        let delay = 600;
        if (currentQuestion.example) {
            const ex = currentQuestion.example;
            exampleZhEl.textContent = ex.zh;
            examplePinyinEl.textContent = ex.pinyin;
            exampleMeaningEl.textContent = lang === "ja" && ex.ja ? ex.ja : ex.en;
            exampleArea.style.display = "block";
            delay = 2500;
        }

        // Next question after delay
        setTimeout(fetchQuestion, delay);
    }

    function updateStreakDisplay() {
        streakEl.textContent = "\u{1F525} " + streak;
        bestStreakEl.textContent = "Best: " + bestStreak;
    }

    // --- Keyboard handler ---
    document.addEventListener("keydown", (e) => {
        if (state !== "READY") return;
        const key = parseInt(e.key);
        if (key >= 1 && key <= quizMode) {
            e.preventDefault();
            handleAnswer(key);
        }
    });

    // --- Dashboard ---
    let dashData = null;
    let dashSort = "accuracy-asc";
    let dashLevels = new Set([1, 2, 3]);

    // Sort button handlers
    document.querySelectorAll(".sort-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            document.querySelectorAll(".sort-btn").forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            dashSort = btn.dataset.sort;
            renderDashboardTable();
        });
    });

    // Level filter handlers
    document.querySelectorAll(".dash-level-cb").forEach(cb => {
        cb.addEventListener("change", () => {
            dashLevels = new Set(
                Array.from(document.querySelectorAll(".dash-level-cb:checked")).map(c => parseInt(c.value))
            );
            renderDashboardCards();
            renderDashboardTable();
        });
    });

    async function loadDashboard() {
        try {
            const res = await fetch("/api/stats?levels=1,2,3");
            dashData = await res.json();
            renderDashboardCards();
            renderDashboardTable();
        } catch (err) {
            document.getElementById("level-cards").textContent = "読み込みエラー: " + err.message;
        }
    }

    function renderDashboardCards() {
        const container = document.getElementById("level-cards");
        container.innerHTML = "";
        if (!dashData) return;

        for (const lv of dashData.levels) {
            if (!dashLevels.has(lv.level)) continue;
            const card = document.createElement("div");
            card.className = "level-card";

            const accText = lv.accuracy != null ? Math.round(lv.accuracy * 100) + "%" : "---";
            const accClass = accColorClass(lv.accuracy, lv.total_attempts);
            const avgTime = lv.avg_time_ms != null ? (lv.avg_time_ms / 1000).toFixed(1) + "s" : "---";

            card.innerHTML = `
                <h3>HSK ${lv.level}</h3>
                <div class="accuracy-big ${accClass}">${accText}</div>
                <div class="stat-row"><span>練習済</span><span class="stat-value">${lv.practiced_words} / ${lv.total_words}</span></div>
                <div class="stat-row"><span>回答数</span><span class="stat-value">${lv.total_attempts}</span></div>
                <div class="stat-row"><span>平均速度</span><span class="stat-value">${avgTime}</span></div>
            `;
            container.appendChild(card);
        }
    }

    function renderDashboardTable() {
        const tbody = document.getElementById("words-tbody");
        tbody.innerHTML = "";
        if (!dashData) return;

        let words = dashData.words.filter(w => dashLevels.has(w.hsk_level));
        words = sortWords(words, dashSort);

        for (const w of words) {
            const tr = document.createElement("tr");
            const accText = w.accuracy != null ? Math.round(w.accuracy * 100) + "%" : "---";
            const accClass = accColorClass(w.accuracy, w.attempts);
            const avgTime = w.avg_time_ms != null ? (w.avg_time_ms / 1000).toFixed(1) + "s" : "---";

            tr.innerHTML = `
                <td class="col-hanzi">${w.simplified}</td>
                <td>${w.pinyin}</td>
                <td>${w.meaning_en}</td>
                <td>${w.hsk_level}</td>
                <td class="col-accuracy ${accClass}">${accText}</td>
                <td>${w.attempts}</td>
                <td>${avgTime}</td>
            `;
            tbody.appendChild(tr);
        }
    }

    function sortWords(words, mode) {
        const sorted = [...words];
        switch (mode) {
            case "accuracy-asc":
                sorted.sort((a, b) => (a.accuracy ?? -1) - (b.accuracy ?? -1));
                break;
            case "accuracy-desc":
                sorted.sort((a, b) => (b.accuracy ?? -1) - (a.accuracy ?? -1));
                break;
            case "level":
                sorted.sort((a, b) => a.hsk_level - b.hsk_level || a.simplified.localeCompare(b.simplified, "zh"));
                break;
            case "attempts":
                sorted.sort((a, b) => b.attempts - a.attempts);
                break;
            case "time":
                sorted.sort((a, b) => (a.avg_time_ms ?? Infinity) - (b.avg_time_ms ?? Infinity));
                break;
        }
        return sorted;
    }

    function accColorClass(accuracy, attempts) {
        if (attempts === 0 || accuracy == null) return "acc-unpracticed";
        if (accuracy < 0.5) return "acc-weak";
        if (accuracy < 0.8) return "acc-learning";
        return "acc-mastered";
    }
})();
