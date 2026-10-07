# 🛰️ ORBITGUARD AI
### *Explainable, Mission-Aware Satellite Collision Avoidance & Software Simulation System*

> **Judge-Facing One-Line Pitch:**  
> *"ORBITGUARD AI doesn't just predict a satellite collision; it explains the risk, selects the safest avoidance maneuver, simulates the maneuver in software, verifies the result, and reassesses the satellite's safety."*

---

## 📌 Executive Summary
Most orbital debris projects focus exclusively on detection or predicting points of closest approach. **ORBITGUARD AI focuses on the DECISION LAYER**:
1. **Which avoidance maneuver should the satellite execute?**
2. **Why is it the optimal option under multi-objective mission constraints?**
3. **Did the software-simulated maneuver actually reduce collision probability into the verified SAFE zone?**

ORBITGUARD AI is a **100% software-based system** engineered for zero physical hardware dependency. All propulsion dynamics, attitude changes, and telemetry feedback are modeled through mathematically grounded **Virtual Actuators** and **Virtual Sensors**.

---

## 🚀 Key Architectural Features

| Module | Purpose & Physical Implementation |
| :--- | :--- |
| **Virtual Satellite Simulator** (`simulator.py`) | Keplerian two-body physics ($\mu = 398600.44\text{ km}^3/\text{s}^2$, $R_E = 6371\text{ km}$). Models altitude (550 km LEO), velocity ($7.59\text{ km/s}$), true anomaly, battery reserve, propellant budget, and 3-axis orientation. |
| **Multi-Debris Simulation** (`simulator.py`) | Models multiple crossing debris fragments with radar cross-sections (RCS), relative velocities, and material compositions. |
| **Trajectory Prediction** (`simulator.py`) | Numerical propagation using NumPy to compute Time of Closest Approach (TCA), conjunction geometry, and predicted orbital paths. |
| **Explainable Risk Engine** (`risk_engine.py`) | Multi-factor risk scoring (0–100) decomposed into: Proximity hazard, Hypervelocity kinetic energy, Urgency (TCA), and Health/Sensor covariance penalties. Categorized as `SAFE`, `MONITOR`, `WARNING`, or `CRITICAL`. |
| **Tactical Maneuver Generation** (`maneuver_engine.py`) | Synthesizes 3 distinct physical avoidance maneuvers: **Maneuver A** (Altitude Boost), **Maneuver B** (Phasing Timing Shift), and **Maneuver C** (Out-of-Plane Cross-Track Burn) with computed $\Delta V$, propellant mass, and mission impact. |
| **Explainable AI Decision Engine** (`ai_engine.py`) | Multi-Attribute Utility Optimization (MAUT) balancing safety margin, $\Delta V$ cost, instrument downtime, and satellite health. Generates clear natural-language technical justifications. |
| **Virtual Actuator** (`virtual_hardware.py`) | Software reaction wheel assembly (RWA) and reaction control system (RCS) thruster simulation modeling attitude slew duration, valve firing, and delivered $\Delta V$. |
| **Virtual Sensor** (`virtual_hardware.py`) | Star tracker and IMU accelerometer verification with Gaussian noise modeling, verifying commanded vs measured state within engineering tolerances (`MANEUVER VERIFIED ✅`). |
| **Closed-Loop Reassessment** (`app.py`) | Recalculates orbital trajectory and collision risk post-maneuver. Confirms `SAFE ✅ SUCCESS` or triggers `REASSESS 🔄` if clearance is insufficient. |
| **Threat vs Resource Classifier** (`risk_engine.py`) | Innovatively classifies debris into `THREAT ☄️` (Avoid), `RECOVERABLE ♻️` (Candidate for in-orbit salvage/recycling), or `UNCERTAIN ⚠️` (Monitor). |
| **Fault Injection Suite** (`data/simulation_data.json`) | Scenarios: Normal Conjunction, Hypervelocity Crossing, Low Battery Mode, Sensor Covariance Glitch, and Ground Station Blackout. |
| **Interactive 2D Orbit Visualizer** (`static/orbit.js`) | HTML5 Canvas 2D engine displaying Earth, orbits, satellites, debris hazard halos, conjunction crosshairs, and pre vs post maneuver trajectories. |

---

## 🛠️ Project Structure
```text
ORBITGUARD_AI/
│
├── app.py                  # Flask API server & closed-loop orchestration
├── simulator.py            # Keplerian orbital mechanics & numerical propagator
├── risk_engine.py          # Explainable risk assessment & debris classification
├── maneuver_engine.py      # Physically calculated maneuver generation (A, B, C)
├── ai_engine.py            # Multi-Attribute Utility AI decision engine
├── virtual_hardware.py     # Virtual Actuator (RCS/RWA) & Virtual Sensor (IMU/Star Tracker)
├── database.py             # SQLite persistence for telemetry & mission audit logs
├── test_orbitguard.py      # Automated integration & pipeline verification test suite
│
├── templates/
│   ├── index.html          # Gateway template
│   └── dashboard.html      # Mission Control GUI dashboard
│
├── static/
│   ├── style.css           # Mission control cyber-aesthetic dark styling
│   ├── script.js           # Frontend orchestrator & REST API client
│   └── orbit.js            # HTML5 Canvas 2D orbital propagation visualizer
│
└── data/
    └── simulation_data.json# Configured orbital scenarios & fault injection models
```

---

## ⚡ Quickstart Guide

### 1. Requirements
- Python 3.9+
- Flask (`pip install flask`)
- NumPy (`pip install numpy`)

### 2. Run the Application
Open a terminal in the project directory and run:
```bash
python app.py
```

### 3. Open Mission Control
Open your web browser and navigate to:
```text
http://127.0.0.1:5000
```

---

## 🎯 Hackathon Live Demo Flow (2 Minutes)

1. **Observe Baseline Orbit**:
   - The interactive 2D orbit map displays Earth, the satellite (green), and tracked space debris (red/yellow).
   - Telemetry shows normal LEO parameters (550 km altitude, 7.59 km/s, 88.5% battery).

2. **Trigger Simulation (`[🚀 SIMULATE CONJUNCTION]`)**:
   - Numerical propagation detects an intercept trajectory with *Cosmos-2251 Fragment #92*.
   - **Risk Score** leaps to **CRITICAL** (e.g., `87.5 / 100`).
   - The **Explainable Risk Engine** displays the exact breakdown: miss distance ($180\text{ m}$), hypervelocity energy ($10.45\text{ km/s}$), and narrow reaction window ($18.4\text{ min}$).
   - Debris is classified as `THREAT ☄️: AVOID`.

3. **Evaluate AI Decision Layer**:
   - Maneuver options A, B, and C are calculated.
   - The AI Decision Engine recommends **Maneuver B ⭐ (Phasing Shift)** with an explainable technical justification:
     > *"Lowest collision risk + low maneuver cost + minimum mission impact. Reduces risk to 2.8% using only 3.8 m/s Delta-V with negligible science interruption."*

4. **Approve & Execute (`[✅ APPROVE & EXECUTE]`)**:
   - **Virtual Actuator** fires simulated thruster burn for 6.8 seconds.
   - **Virtual Sensor** cross-checks commanded pitch ($4.5^\circ$) and $\Delta V$ ($3.8\text{ m/s}$), logging `MANEUVER VERIFIED ✅`.
   - Satellite orbital coordinates shift into a deflected trajectory.

5. **Closed-Loop Safety Reassessment**:
   - The system automatically recalculates post-burn orbit and risk.
   - Collision Risk plummets from **87.5** to **3.2 / 100** (`SAFE ✅`).
   - The **BEFORE vs AFTER** comparison card visually proves the expanded separation distance ($14.2\text{ km}$).

6. **Demonstrate Fault Injection**:
   - Switch dropdown to **Low Battery Mode (Eclipse)**: The AI dynamically adapts its utility weights to strictly penalize power-intensive burns.
   - Switch to **Sensor Covariance Glitch**: The system detects measurement uncertainty expansion.

---

## 🛡️ Note on Simulation Scope
*All orbital values, thruster dynamics, and sensor telemetry are simulated demonstration values generated for collegiate hackathon research and decision-support prototype demonstration. This prototype is designed as an explainable decision-support tool and does not claim direct autonomous control of operational orbital spacecraft.*
