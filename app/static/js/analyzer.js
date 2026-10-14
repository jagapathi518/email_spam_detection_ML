/* SpamGuard AI — Analyzer Page Logic */
(function () {
    "use strict";

    /* --- DOM Elements --- */
    var subjectInput = document.getElementById("subject-input");
    var bodyInput = document.getElementById("body-input");
    var subjectCounter = document.getElementById("subject-counter");
    var bodyCounter = document.getElementById("body-counter");
    var analyzeBtn = document.getElementById("analyze-btn");
    var clearBtn = document.getElementById("clear-btn");
    var sampleSpamBtn = document.getElementById("sample-spam-btn");
    var sampleLegitBtn = document.getElementById("sample-legit-btn");
    var loadingOverlay = document.getElementById("loading-overlay");
    var loadingText = document.getElementById("loading-text");
    var resultsContainer = document.getElementById("results-container");
    var predictionBlock = document.getElementById("prediction-block");
    var signalsBlock = document.getElementById("signals-block");
    var nextStepsBlock = document.getElementById("next-steps-block");
    var disclaimerBlock = document.getElementById("disclaimer-block");
    var errorBlock = document.getElementById("error-block");
    var errorMessage = document.getElementById("error-message");
    var retryBtn = document.getElementById("retry-btn");
    var statusAnnouncer = document.getElementById("status-announcer");

    var SUBJECT_MAX = 300;
    var BODY_MAX = 20000;
    var FETCH_TIMEOUT = 90000; /* 90 seconds for cold start */
    var WAKEUP_DELAY = 5000;   /* Show wakeup message after 5s */

    /* --- Sample Data --- */
    var SAMPLE_SPAM = {
        subject: "URGENT: You Have Won $1,000,000! Claim Now!",
        body: "Dear Lucky Winner,\n\nCongratulations! You have been selected as the winner of our international lottery program. You have won $1,000,000 USD!\n\nTo claim your prize, please send us your full name, address, phone number, bank account details, and a copy of your ID.\n\nThis offer expires in 24 hours. Act now or lose your winnings forever!\n\nClick here to verify your identity: http://192.168.1.1/claim-prize\n\nBest regards,\nInternational Lottery Commission"
    };

    var SAMPLE_LEGIT = {
        subject: "Team Meeting Notes - October 2024",
        body: "Hi everyone,\n\nHere are the key takeaways from today's team meeting:\n\n1. The Q3 report is due next Friday. Please submit your sections by Wednesday.\n2. We'll be moving to the new office space starting November 1st.\n3. The annual company picnic is scheduled for October 28th.\n\nPlease let me know if you have any questions.\n\nBest,\nSarah"
    };

    /* --- Character Counters --- */
    function updateCounter(input, counter, max) {
        var len = input.value.length;
        counter.textContent = len + " / " + max;

        counter.className = "char-counter";
        if (len > max) {
            counter.classList.add("char-counter--danger");
        } else if (len > max * 0.9) {
            counter.classList.add("char-counter--warning");
        }
    }

    if (subjectInput && subjectCounter) {
        subjectInput.addEventListener("input", function () {
            updateCounter(subjectInput, subjectCounter, SUBJECT_MAX);
        });
    }

    if (bodyInput && bodyCounter) {
        bodyInput.addEventListener("input", function () {
            updateCounter(bodyInput, bodyCounter, BODY_MAX);
        });
    }

    /* --- Form Validation --- */
    function validate() {
        var body = bodyInput ? bodyInput.value.trim() : "";
        var subject = subjectInput ? subjectInput.value : "";

        if (!body) {
            showError("Please enter the email body text to analyze.");
            return false;
        }

        if (subject.length > SUBJECT_MAX) {
            showError("Subject exceeds " + SUBJECT_MAX + " characters.");
            return false;
        }

        if (body.length > BODY_MAX) {
            showError("Body exceeds " + BODY_MAX + " characters.");
            return false;
        }

        return true;
    }

    /* --- Error Display --- */
    function showError(message) {
        if (errorBlock) {
            errorMessage.textContent = message;
            errorBlock.style.display = "block";
        }
        if (resultsContainer) resultsContainer.classList.remove("visible");
        if (loadingOverlay) loadingOverlay.classList.remove("active");
        announce(message);
    }

    function hideError() {
        if (errorBlock) errorBlock.style.display = "none";
    }

    /* --- Accessibility: aria-live announcements --- */
    function announce(message) {
        if (statusAnnouncer) {
            statusAnnouncer.textContent = message;
        }
    }

    /* --- Loading State --- */
    function showLoading() {
        if (loadingOverlay) loadingOverlay.classList.add("active");
        if (resultsContainer) resultsContainer.classList.remove("visible");
        hideError();
        if (analyzeBtn) analyzeBtn.disabled = true;
        if (loadingText) loadingText.textContent = "Analyzing your email...";
        announce("Analyzing your email. Please wait.");
    }

    function hideLoading() {
        if (loadingOverlay) loadingOverlay.classList.remove("active");
        if (analyzeBtn) analyzeBtn.disabled = false;
    }

    /* --- Analyze --- */
    function analyzeEmail() {
        if (!validate()) return;

        showLoading();

        var subject = subjectInput ? subjectInput.value : "";
        var body = bodyInput ? bodyInput.value.trim() : "";

        /* Wakeup message timer */
        var wakeupTimer = setTimeout(function () {
            if (loadingText) {
                loadingText.textContent = "The free server is waking up — this can take about a minute...";
            }
            announce("The free server is waking up. This can take about a minute.");
        }, WAKEUP_DELAY);

        var controller = new AbortController();
        var timeoutId = setTimeout(function () {
            controller.abort();
        }, FETCH_TIMEOUT);

        fetch("/api/predict", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ subject: subject, body: body }),
            signal: controller.signal
        })
        .then(function (response) {
            clearTimeout(wakeupTimer);
            clearTimeout(timeoutId);

            if (response.status === 429) {
                throw new Error("Rate limit exceeded. Please wait a moment and try again.");
            }
            if (response.status === 503) {
                throw new Error("The analysis service is temporarily unavailable. Please try again in a moment.");
            }
            if (!response.ok) {
                return response.json().then(function (data) {
                    throw new Error(data.error || "An error occurred (HTTP " + response.status + ").");
                });
            }
            return response.json();
        })
        .then(function (data) {
            hideLoading();
            displayResults(data);
        })
        .catch(function (err) {
            clearTimeout(wakeupTimer);
            clearTimeout(timeoutId);
            hideLoading();

            var msg = err.message;
            if (err.name === "AbortError") {
                msg = "Request timed out. The server may be starting up. Please try again.";
            }
            showError(msg);
        });
    }

    /* --- Display Results --- */
    function displayResults(data) {
        if (!resultsContainer) return;

        /* Prediction block */
        if (predictionBlock) {
            var labelText = "";
            var badgeClass = "";
            var icon = "";

            if (data.label === "spam") {
                labelText = "Likely Spam";
                badgeClass = "result-badge--spam";
                icon = "⚠️";
            } else if (data.label === "not_spam") {
                labelText = "Likely Not Spam";
                badgeClass = "result-badge--not-spam";
                icon = "✅";
            } else {
                labelText = "Uncertain";
                badgeClass = "result-badge--uncertain";
                icon = "🔍";
            }

            var scorePercent = Math.round(data.score * 100);
            var barColor = data.label === "spam" ? "var(--color-danger)" :
                           data.label === "not_spam" ? "var(--color-success)" : "var(--color-warning)";

            predictionBlock.innerHTML = "";

            var header = document.createElement("div");
            header.className = "result-header";
            header.textContent = "Model Prediction";
            predictionBlock.appendChild(header);

            var badge = document.createElement("div");
            badge.className = "result-badge " + badgeClass;
            badge.textContent = icon + " " + labelText;
            predictionBlock.appendChild(badge);

            var scoreInfo = document.createElement("p");
            scoreInfo.className = "text-muted";
            scoreInfo.style.marginTop = "var(--space-md)";
            scoreInfo.style.fontSize = "var(--text-sm)";
            scoreInfo.textContent = "Model score: " + data.score.toFixed(4) +
                " (This is a model score, not a calibrated probability.)";
            predictionBlock.appendChild(scoreInfo);

            var barContainer = document.createElement("div");
            barContainer.className = "score-bar";
            var barFill = document.createElement("div");
            barFill.className = "score-fill";
            barFill.style.width = scorePercent + "%";
            barFill.style.background = barColor;
            barContainer.appendChild(barFill);
            predictionBlock.appendChild(barContainer);

            var versionInfo = document.createElement("p");
            versionInfo.className = "text-muted";
            versionInfo.style.fontSize = "var(--text-xs)";
            versionInfo.textContent = "Model version: " + (data.model_version || "unknown");
            predictionBlock.appendChild(versionInfo);
        }

        /* Signals block */
        if (signalsBlock) {
            signalsBlock.innerHTML = "";

            var sigHeader = document.createElement("div");
            sigHeader.className = "result-header";
            sigHeader.textContent = "Heuristic Signals";
            signalsBlock.appendChild(sigHeader);

            if (data.signals && data.signals.length > 0) {
                var sigList = document.createElement("div");
                sigList.className = "signal-list";

                for (var i = 0; i < data.signals.length; i++) {
                    var sig = data.signals[i];
                    var sigItem = document.createElement("div");
                    sigItem.className = "signal-item signal-item--" + sig.severity;

                    var sigContent = document.createElement("div");

                    var sigName = document.createElement("div");
                    sigName.className = "signal-name";
                    sigName.textContent = sig.name;
                    sigContent.appendChild(sigName);

                    var sigDesc = document.createElement("div");
                    sigDesc.className = "signal-description";
                    sigDesc.textContent = sig.description;
                    sigContent.appendChild(sigDesc);

                    sigItem.appendChild(sigContent);
                    sigList.appendChild(sigItem);
                }

                signalsBlock.appendChild(sigList);
            } else {
                var noSig = document.createElement("p");
                noSig.className = "text-muted";
                noSig.style.fontSize = "var(--text-sm)";
                noSig.textContent = "No common spam or phishing patterns detected by heuristic rules.";
                signalsBlock.appendChild(noSig);
            }

            var sigNote = document.createElement("p");
            sigNote.className = "text-muted";
            sigNote.style.fontSize = "var(--text-xs)";
            sigNote.style.marginTop = "var(--space-md)";
            sigNote.textContent = "These are pattern-based heuristic checks, separate from the ML model prediction.";
            signalsBlock.appendChild(sigNote);
        }

        /* Next steps block */
        if (nextStepsBlock) {
            nextStepsBlock.innerHTML = "";

            var stepsHeader = document.createElement("div");
            stepsHeader.className = "result-header";
            stepsHeader.textContent = "Safe Next Steps";
            nextStepsBlock.appendChild(stepsHeader);

            var steps = [];
            if (data.label === "spam") {
                steps = [
                    "Do not click any links or download attachments from this email.",
                    "Do not reply or provide personal information.",
                    "Mark it as spam in your email client so similar messages are filtered.",
                    "If it claims to be from a known organization, contact them directly through their official website.",
                    "Report phishing attempts to your IT department or email provider."
                ];
            } else if (data.label === "uncertain") {
                steps = [
                    "Exercise caution — this email has some characteristics that could not be definitively classified.",
                    "Verify the sender through an independent channel before taking any action.",
                    "Do not click links or share sensitive information until you confirm legitimacy.",
                    "Check the sender's email address carefully for misspellings or unusual domains.",
                    "When in doubt, consult your IT department or a trusted advisor."
                ];
            } else {
                steps = [
                    "This email appears legitimate, but always stay cautious.",
                    "Verify unexpected requests, especially those involving money or personal data.",
                    "Be wary of emails that create urgency, even if they look legitimate.",
                    "Remember: this tool provides a best-effort analysis and does not guarantee safety."
                ];
            }

            var stepsList = document.createElement("ul");
            stepsList.className = "next-steps";
            for (var j = 0; j < steps.length; j++) {
                var li = document.createElement("li");
                li.textContent = steps[j];
                stepsList.appendChild(li);
            }
            nextStepsBlock.appendChild(stepsList);
        }

        /* Disclaimer */
        if (disclaimerBlock && data.disclaimer) {
            disclaimerBlock.textContent = data.disclaimer;
        }

        resultsContainer.classList.add("visible");
        announce("Analysis complete. " + (data.label === "spam" ? "This email is likely spam." :
                 data.label === "not_spam" ? "This email appears legitimate." : "The result is uncertain."));

        /* Scroll to results */
        resultsContainer.scrollIntoView({ behavior: "smooth", block: "start" });
    }

    /* --- Clear Form --- */
    function clearForm() {
        if (subjectInput) subjectInput.value = "";
        if (bodyInput) bodyInput.value = "";
        if (subjectCounter) subjectCounter.textContent = "0 / " + SUBJECT_MAX;
        if (bodyCounter) bodyCounter.textContent = "0 / " + BODY_MAX;
        if (resultsContainer) resultsContainer.classList.remove("visible");
        hideError();
        hideLoading();
        announce("Form cleared.");
        if (bodyInput) bodyInput.focus();
    }

    /* --- Sample Data --- */
    function loadSample(sample) {
        if (subjectInput) {
            subjectInput.value = sample.subject;
            updateCounter(subjectInput, subjectCounter, SUBJECT_MAX);
        }
        if (bodyInput) {
            bodyInput.value = sample.body;
            updateCounter(bodyInput, bodyCounter, BODY_MAX);
        }
        if (resultsContainer) resultsContainer.classList.remove("visible");
        hideError();
        announce("Sample email loaded. Press Analyze to check it.");
    }

    /* --- Event Listeners --- */
    if (analyzeBtn) {
        analyzeBtn.addEventListener("click", analyzeEmail);
    }
    if (clearBtn) {
        clearBtn.addEventListener("click", clearForm);
    }
    if (sampleSpamBtn) {
        sampleSpamBtn.addEventListener("click", function () {
            loadSample(SAMPLE_SPAM);
        });
    }
    if (sampleLegitBtn) {
        sampleLegitBtn.addEventListener("click", function () {
            loadSample(SAMPLE_LEGIT);
        });
    }
    if (retryBtn) {
        retryBtn.addEventListener("click", analyzeEmail);
    }

    /* Keyboard: Enter in subject field triggers analyze */
    if (subjectInput) {
        subjectInput.addEventListener("keydown", function (e) {
            if (e.key === "Enter") {
                e.preventDefault();
                analyzeEmail();
            }
        });
    }
})();
