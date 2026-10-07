/**
 * ORBITGUARD AI - Mission Control Frontend Controller
 * Connects UI actions to Flask API endpoints and synchronizes orbital telemetry.
 */

let selectedManeuverId = "B";
let currentSimData = null;

document.addEventListener("DOMContentLoaded", () => {
    initOrbitCanvas();
    startMissionClock();
    fetchInitialState();

    // Resize canvas dynamically
    window.addEventListener("resize", () => {
        if (orbitVisualizer) {
            orbitVisualizer.setupDPI();
        }
    });
});

/* ================= CLOCK & INITIAL STATE ================= */
function startMissionClock() {
    function updateClock() {
        const now = new Date();
        const utcStr = now.toISOString().substring(11, 19) + " UTC";
        const clockEl = document.getElementById("utcClock");
        if (clockEl) clockEl.innerText = utcStr;
    }
    updateClock();
    setInterval(updateClock, 1000);
}

async function fetchInitialState() {
    try {
        const res = await fetch("/api/state");
        const data = await res.json();
        if (data.success) {
            updateTelemetryUI(data.telemetry);
            if (data.logs) renderLogs(data.logs);
        }
    } catch (err) {
        console.error("Failed to load initial state:", err);
    }
}

/* ================= TELEMETRY UI SYNC ================= */
function updateTelemetryUI(telemetry) {
    if (!telemetry || !telemetry.satellite) return;
    const sat = telemetry.satellite;

    // Numerical telemetry
    setElText("satAltitude", `${sat.altitude_km.toFixed(1)} km`);
    setElText("satVelocity", `${sat.velocity_km_s.toFixed(2)} km/s`);
    setElText("satTemp", `${sat.temperature_c.toFixed(1)} °C`);
    setElText("satComms", `${sat.comm_signal_pct.toFixed(0)}%`);

    // Battery
    setElText("batteryPctText", `${sat.battery_pct.toFixed(1)}%`);
    const batBar = document.getElementById("batteryBar");
    if (batBar) {
        batBar.style.width = `${Math.min(100, Math.max(0, sat.battery_pct))}%`;
        batBar.className = sat.battery_pct < 25 ? "bar-fill danger-fill" : "bar-fill";
    }

    // Propellant
    setElText("propellantText", `${sat.propellant_kg.toFixed(1)} kg / ${sat.max_delta_v_m_s.toFixed(1)} m/s`);
    const propBar = document.getElementById("propellantBar");
    if (propBar) {
        const propPct = (sat.propellant_kg / 50.0) * 100;
        propBar.style.width = `${Math.min(100, Math.max(0, propPct))}%`;
    }

    // Orientation
    if (sat.orientation_deg) {
        setElText("attRoll", `${sat.orientation_deg.roll.toFixed(1)}°`);
        setElText("attPitch", `${sat.orientation_deg.pitch.toFixed(1)}°`);
        setElText("attYaw", `${sat.orientation_deg.yaw.toFixed(1)}°`);
    }

    // Mission status badge
    const badge = document.getElementById("satMissionBadge");
    if (badge) {
        badge.innerText = sat.mission_status || "OPERATIONAL";
        badge.className = sat.mission_status === "OPERATIONAL" ? "status-badge badge-active" : "status-badge badge-warning";
    }

    // Subsystem indicators
    const starTag = document.getElementById("tagStarTracker");
    if (starTag) {
        const isDegraded = (sat.mission_status === "SENSOR_DEGRADED");
        starTag.className = isDegraded ? "sub-tag degraded" : "sub-tag ok";
        starTag.innerText = isDegraded ? "STAR TRACKER (DEGRADED)" : "STAR TRACKER";
    }

    // Tracked debris catalog list
    renderDebrisCatalog(telemetry.all_debris);

    // Update Canvas
    updateOrbitData(telemetry, null, null, null);
}

function renderDebrisCatalog(debrisList) {
    const container = document.getElementById("debrisListContainer");
    if (!container || !debrisList) return;

    setElText("debrisCount", debrisList.length);
    container.innerHTML = "";

    debrisList.forEach(deb => {
        const item = document.createElement("div");
        item.className = `debris-cat-item ${deb.is_primary ? "primary" : ""}`;
        item.innerHTML = `
            <span>${deb.is_primary ? "☄️ " : "🔹 "}${deb.name || deb.id}</span>
            <span style="color: ${deb.is_primary ? "var(--red)" : "var(--yellow)"}">
                ${deb.altitude_km} km &bull; ${deb.classification_category || "THREAT"}
            </span>
        `;
        container.appendChild(item);
    });
}

/* ================= 1. SIMULATE CONJUNCTION ================= */
async function simulateConjunction() {
    setPrompt("Executing numerical orbital propagation and multi-factor risk analysis...");
    const btnSim = document.getElementById("btnSimulate");
    if (btnSim) btnSim.classList.add("disabled");

    try {
        const res = await fetch("/api/simulate", { method: "POST" });
        const data = await res.json();
        if (!data.success) throw new Error(data.message);

        currentSimData = data;

        // 1. Update Collision Risk Gauge
        updateRiskGauge(data.risk_analysis);

        // 2. Update Ribbon
        setElText("liveDistance", `${data.conjunction.min_distance_km.toFixed(2)} km`);
        setElText("liveRelVel", `${data.risk_analysis.relative_velocity_km_s.toFixed(2)} km/s`);
        setElText("liveTca", `${data.conjunction.tca_minutes.toFixed(1)} min`);
        setElText("liveMinDist", `${data.conjunction.min_distance_m.toFixed(0)} m`);

        // 3. Update AI Recommendation
        if (data.ai_recommendation) {
            selectedManeuverId = data.ai_recommendation.best_option_id;
            setElText("aiRecName", `${data.ai_recommendation.best_option_name} ⭐`);
            setElText("aiRecReason", data.ai_recommendation.recommendation_reason);
        }

        // 4. Update Maneuver Cards
        updateManeuverCards(data.maneuvers, selectedManeuverId);

        // 5. Update Canvas Trajectories
        updateOrbitData(null, data.trajectories, null, data.conjunction);

        // 6. Enable Action Buttons
        enableButton("btnApprove", true);
        enableButton("btnReject", true);

        // 7. Hide Before/After card until execution
        hideBeforeAfterCard();

        setPrompt(`Conjunction analyzed: ${data.risk_analysis.status} RISK. AI recommends Maneuver ${selectedManeuverId} ⭐. Click [APPROVE & EXECUTE].`);

        fetchLogs();

    } catch (err) {
        console.error("Simulation error:", err);
        setPrompt("Error running simulation. Check server connection.");
    } finally {
        if (btnSim) btnSim.classList.remove("disabled");
    }
}

/* ================= 2. APPROVE & EXECUTE MANEUVER ================= */
async function approveAndExecute() {
    setPrompt(`Executing Maneuver ${selectedManeuverId} via Virtual Actuator & verifying with Virtual Sensor...`);
    enableButton("btnApprove", false);

    try {
        const res = await fetch("/api/approve-maneuver", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ maneuver_id: selectedManeuverId })
        });
        const data = await res.json();
        if (!data.success) throw new Error(data.message);

        // 1. Update Hardware Telemetry Readout
        if (data.actuator_telemetry) {
            setElText("actuatorStatusText", `EXECUTED ✅ &bull; ΔV Delivered: ${data.actuator_telemetry.actual_delta_v_delivered_m_s} m/s`);
            setElText("actuatorDetails", `${data.actuator_telemetry.message} Slew duration: ${data.actuator_telemetry.attitude_slew_duration_s}s.`);
        }
        if (data.sensor_telemetry) {
            setElText("sensorStatusText", `${data.sensor_telemetry.status_text}`);
            setElText("sensorDetails", `${data.sensor_telemetry.message}`);
            const hwPill = document.getElementById("hardwareStatusPill");
            if (hwPill) {
                hwPill.className = data.sensor_telemetry.is_verified ? "sub-tag ok" : "sub-tag degraded";
                hwPill.innerText = data.sensor_telemetry.is_verified ? "VERIFIED" : "DISCREPANCY";
            }
        }

        // 2. Update Risk Gauge with Post-Maneuver Recalculation
        if (data.post_risk_analysis) {
            updateRiskGauge(data.post_risk_analysis);
        }

        // 3. Update Ribbon with new clearance
        if (data.selected_maneuver) {
            setElText("liveMinDist", `${data.selected_maneuver.post_min_distance_m.toFixed(0)} m (Safe Clearance)`);
            setElText("liveDistance", `${data.selected_maneuver.post_min_distance_km.toFixed(2)} km`);
        }

        // 4. Reveal Before vs After Comparison Card
        showBeforeAfterCard(data);

        // 5. Update Orbit Canvas with Deflected Post-Maneuver Trajectory
        if (data.post_trajectories) {
            updateOrbitData(null, currentSimData ? currentSimData.trajectories : null, data.post_trajectories, null);
        }

        // 6. Refresh satellite telemetry
        fetchInitialState();

        // 7. Closed-loop decision evaluation
        if (data.is_safe) {
            setPrompt(`🎉 Closed-loop check passed! Post-maneuver risk reduced to ${data.post_risk_analysis.risk_score}%. STATUS: SAFE ✅.`);
        } else {
            setPrompt(`⚠️ Post-maneuver risk still elevated (${data.post_risk_analysis.risk_score}%). REASSESS required.`);
            enableButton("btnApprove", true);
        }

        fetchLogs();

    } catch (err) {
        console.error("Execution error:", err);
        setPrompt("Error executing maneuver: " + err.message);
        enableButton("btnApprove", true);
    }
}

/* ================= 3. REJECT MANEUVER ================= */
function rejectManeuver() {
    setPrompt(`Maneuver ${selectedManeuverId} rejected by Mission Director. Choose an alternative maneuver or click [REASSESS].`);
    enableButton("btnApprove", false);
    enableButton("btnReject", false);
}

/* ================= 4. REASSESS SAFETY ================= */
async function reassessSafety() {
    setPrompt("Re-analyzing orbital conjunction geometry and tracking updates...");
    try {
        const res = await fetch("/api/reassess", { method: "POST" });
        const data = await res.json();
        if (data.success && data.risk_analysis) {
            updateRiskGauge(data.risk_analysis);
            setPrompt(`Reassessment complete. Current orbital risk: ${data.risk_analysis.risk_score}%. ${data.risk_analysis.status}`);
            fetchLogs();
        }
    } catch (err) {
        console.error("Reassessment error:", err);
    }
}

/* ================= 5. SCENARIO / FAULT INJECTION ================= */
async function handleScenarioChange() {
    const select = document.getElementById("scenarioSelect");
    const scenario = select.value;
    setPrompt(`Loading scenario: ${scenario}...`);

    try {
        const res = await fetch("/api/inject-fault", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ scenario: scenario })
        });
        const data = await res.json();
        if (data.success) {
            resetRiskGauge();
            hideBeforeAfterCard();
            enableButton("btnApprove", false);
            enableButton("btnReject", false);
            fetchInitialState();
            fetchLogs();
            setPrompt(`Scenario loaded: ${data.scenario_title}. Click [SIMULATE CONJUNCTION] to test AI response.`);
        }
    } catch (err) {
        console.error("Scenario error:", err);
    }
}

/* ================= 6. RESET SYSTEM ================= */
async function resetAll() {
    setPrompt("Resetting OrbitGuard AI simulation to initial standby state...");
    try {
        const res = await fetch("/api/reset", { method: "POST" });
        const data = await res.json();
        if (data.success) {
            resetRiskGauge();
            hideBeforeAfterCard();
            enableButton("btnApprove", false);
            enableButton("btnReject", false);

            setElText("liveDistance", "-- km");
            setElText("liveRelVel", "-- km/s");
            setElText("liveTca", "-- min");
            setElText("liveMinDist", "-- m");

            setElText("actuatorStatusText", "IDLE • Ready for Burn Command");
            setElText("actuatorDetails", "Software actuator models 3-axis reaction wheel torque and cold-gas thruster delta-V injection.");
            setElText("sensorStatusText", "CALIBRATED • Monitoring Telemetry");
            setElText("sensorDetails", "Cross-checks commanded attitude slew & delta-V against simulated measurements within tolerance.");

            const hwPill = document.getElementById("hardwareStatusPill");
            if (hwPill) {
                hwPill.className = "sub-tag ok";
                hwPill.innerText = "READY";
            }

            fetchInitialState();
            fetchLogs();
            setPrompt("System reset complete. Ready for new simulation.");
        }
    } catch (err) {
        console.error("Reset error:", err);
    }
}

/* ================= UI HELPERS ================= */
function updateRiskGauge(risk) {
    if (!risk) return;

    // Numerical score
    const scoreVal = Math.round(risk.risk_score);
    setElText("riskScoreVal", scoreVal);

    // SVG circular meter (circumference = 2 * PI * 50 = 314.15)
    const meter = document.getElementById("riskMeter");
    if (meter) {
        const offset = 314 - (314 * (scoreVal / 100));
        meter.style.strokeDashoffset = offset;
        meter.style.stroke = risk.status_color || "#ff334b";
    }

    // Status label
    const statusText = document.getElementById("riskStatusText");
    if (statusText) {
        statusText.innerText = `${risk.status_icon || ""} ${risk.status}`;
        statusText.style.color = risk.status_color || "#fff";
    }

    // Header badge
    const badge = document.getElementById("riskStatusBadge");
    if (badge) {
        badge.innerText = risk.status;
        badge.className = `status-badge badge-${risk.status.toLowerCase()}`;
    }

    // Factors
    if (risk.factors) {
        setElText("factorProximity", `${risk.factors.proximity} / 45`);
        setBarWidth("factorProxBar", (risk.factors.proximity / 45) * 100);

        setElText("factorKinetic", `${risk.factors.kinetic} / 25`);
        setBarWidth("factorKinBar", (risk.factors.kinetic / 25) * 100);

        setElText("factorUrgency", `${risk.factors.urgency} / 20`);
        setBarWidth("factorUrgBar", (risk.factors.urgency / 20) * 100);

        setElText("factorHealth", `${risk.factors.uncertainty_and_health} / 10`);
        setBarWidth("factorHlthBar", (risk.factors.uncertainty_and_health / 10) * 100);
    }

    // Reasons list
    const reasonsContainer = document.getElementById("riskReasonsList");
    if (reasonsContainer && risk.explanations) {
        reasonsContainer.innerHTML = "";
        risk.explanations.forEach(exp => {
            const li = document.createElement("li");
            li.innerText = exp;
            reasonsContainer.appendChild(li);
        });
    }

    // Threat vs Resource Classification
    if (risk.classification) {
        const clsBadge = document.getElementById("debrisClassBadge");
        if (clsBadge) {
            clsBadge.innerText = risk.classification.badge;
            clsBadge.className = `class-badge badge-${risk.classification.category.toLowerCase()}`;
        }
        setElText("debrisClassRationale", risk.classification.rationale);
    }
}

function resetRiskGauge() {
    setElText("riskScoreVal", "--");
    const meter = document.getElementById("riskMeter");
    if (meter) meter.style.strokeDashoffset = 314;
    setElText("riskStatusText", "WAITING FOR SIMULATION");
    const badge = document.getElementById("riskStatusBadge");
    if (badge) {
        badge.innerText = "STANDBY";
        badge.className = "status-badge badge-neutral";
    }
    setBarWidth("factorProxBar", 0);
    setBarWidth("factorKinBar", 0);
    setBarWidth("factorUrgBar", 0);
    setBarWidth("factorHlthBar", 0);
}

function updateManeuverCards(maneuvers, bestId) {
    if (!maneuvers) return;

    maneuvers.forEach(m => {
        const card = document.getElementById(`cardManeuver${m.id}`);
        if (!card) return;

        // Is recommended
        const isBest = (m.id === bestId);
        if (isBest) {
            card.classList.add("recommended-card");
        } else {
            card.classList.remove("recommended-card");
        }
    });
}

function selectManeuver(optionId) {
    selectedManeuverId = optionId;
    ["A", "B", "C"].forEach(id => {
        const card = document.getElementById(`cardManeuver${id}`);
        if (card) {
            if (id === optionId) {
                card.style.outline = "2px solid var(--cyan)";
            } else {
                card.style.outline = "none";
            }
        }
    });
    setPrompt(`Selected Maneuver ${optionId}. Click [APPROVE & EXECUTE] to initiate burn.`);
}

function showBeforeAfterCard(data) {
    const card = document.getElementById("beforeAfterSection");
    if (!card) return;
    card.classList.remove("hidden");

    const beforeRisk = currentSimData && currentSimData.risk_analysis ? currentSimData.risk_analysis.risk_score : 87.5;
    const beforeDist = currentSimData && currentSimData.conjunction ? `${currentSimData.conjunction.min_distance_m} m` : "180 m";

    const afterRisk = data.post_risk_analysis ? data.post_risk_analysis.risk_score : 3.2;
    const afterDist = data.selected_maneuver ? `${data.selected_maneuver.post_min_distance_km} km` : "14.2 km";

    setElText("baBeforeRisk", `${beforeRisk} / 100`);
    setElText("baBeforeDist", beforeDist);
    setElText("baAfterRisk", `${afterRisk} / 100`);
    setElText("baAfterDist", afterDist);

    const safetyBadge = document.getElementById("baSafetyBadge");
    if (safetyBadge) {
        safetyBadge.innerText = data.is_safe ? "SAFE ✅ SUCCESS" : "REASSESS 🔄";
        safetyBadge.className = data.is_safe ? "status-badge badge-safe" : "status-badge badge-warning";
    }
}

function hideBeforeAfterCard() {
    const card = document.getElementById("beforeAfterSection");
    if (card) card.classList.add("hidden");
}

function renderLogs(logs) {
    const terminal = document.getElementById("eventLogsTerminal");
    if (!terminal || !logs) return;

    terminal.innerHTML = "";
    logs.forEach(log => {
        const div = document.createElement("div");
        div.className = "log-entry";
        div.innerHTML = `
            <span class="log-time">[${log.timestamp}]</span>
            <span class="log-msg">${log.message}</span>
        `;
        terminal.appendChild(div);
    });
    terminal.scrollTop = terminal.scrollHeight;
}

async function fetchLogs() {
    try {
        const res = await fetch("/api/logs");
        const data = await res.json();
        if (data.success && data.logs) {
            renderLogs(data.logs);
        }
    } catch (err) {
        console.error("Log fetch error:", err);
    }
}

async function clearEventLogs() {
    try {
        await fetch("/api/clear-logs", { method: "POST" });
        const terminal = document.getElementById("eventLogsTerminal");
        if (terminal) terminal.innerHTML = "";
    } catch (err) {
        console.error("Log clear error:", err);
    }
}

function setElText(id, text) {
    const el = document.getElementById(id);
    if (el) el.innerText = text;
}

function setBarWidth(id, pct) {
    const el = document.getElementById(id);
    if (el) el.style.width = `${Math.min(100, Math.max(0, pct))}%`;
}

function setPrompt(text) {
    const el = document.getElementById("footerStatusPrompt");
    if (el) el.innerText = text;
}

function enableButton(id, isEnabled) {
    const btn = document.getElementById(id);
    if (btn) {
        btn.disabled = !isEnabled;
        if (isEnabled) {
            btn.classList.remove("disabled");
        } else {
            btn.classList.add("disabled");
        }
    }
}