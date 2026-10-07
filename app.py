"""
ORBITGUARD AI - Mission Control Web & API Server
Flask backend connecting the physics simulator, risk engine, maneuver engine,
AI decision optimizer, virtual hardware layer, and SQLite database.
"""

from flask import Flask, render_template, jsonify, request
import os
import json

from simulator import OrbitalSimulator
from risk_engine import RiskEngine
from maneuver_engine import ManeuverEngine
from ai_engine import AIDecisionEngine
from virtual_hardware import VirtualActuator, VirtualSensor
import database as db

app = Flask(__name__)

# Initialize singletons
simulator = OrbitalSimulator("normal")
risk_engine = RiskEngine()
maneuver_engine = ManeuverEngine(simulator, risk_engine)
ai_engine = AIDecisionEngine()
virtual_actuator = VirtualActuator()
virtual_sensor = VirtualSensor()

# Runtime simulation cache
current_simulation_state = {
    "phase": "STANDBY",  # STANDBY -> CONJUNCTION_DETECTED -> MANEUVER_RECOMMENDED -> EXECUTED -> SAFE
    "conjunction": None,
    "risk_analysis": None,
    "maneuvers": [],
    "ai_recommendation": None,
    "selected_maneuver": None,
    "actuator_telemetry": None,
    "sensor_telemetry": None,
    "post_risk_analysis": None,
    "trajectories": None,
    "post_trajectories": None
}


@app.route("/")
@app.route("/dashboard")
def dashboard():
    """Renders the main OrbitGuard AI Mission Control Dashboard."""
    return render_template("dashboard.html")


@app.route("/api/state", methods=["GET"])
def get_state():
    """Returns current telemetry, simulation phase, risk, and hardware states."""
    telemetry = simulator.get_full_telemetry()
    logs = db.get_recent_logs(limit=25)
    return jsonify({
        "success": True,
        "phase": current_simulation_state["phase"],
        "telemetry": telemetry,
        "conjunction": current_simulation_state["conjunction"],
        "risk_analysis": current_simulation_state["risk_analysis"],
        "maneuvers": current_simulation_state["maneuvers"],
        "ai_recommendation": current_simulation_state["ai_recommendation"],
        "selected_maneuver": current_simulation_state["selected_maneuver"],
        "actuator_telemetry": current_simulation_state["actuator_telemetry"],
        "sensor_telemetry": current_simulation_state["sensor_telemetry"],
        "post_risk_analysis": current_simulation_state["post_risk_analysis"],
        "trajectories": current_simulation_state["trajectories"],
        "post_trajectories": current_simulation_state["post_trajectories"],
        "logs": logs
    })


@app.route("/api/simulate", methods=["POST"])
def run_simulation():
    """
    Executes full forward trajectory propagation, collision risk assessment,
    maneuver option generation, and AI decision optimization.
    """
    # 1. Forward trajectory prediction via numerical propagator
    traj_data = simulator.propagate_trajectories(time_horizon_min=60, steps=60)
    conjunction = traj_data["conjunction"]
    
    primary_deb = next((d for d in simulator.debris_list if d.get("is_primary")), simulator.debris_list[0])
    rel_kinematics = simulator.compute_relative_kinematics(primary_deb["id"])
    
    # 2. Risk Calculation & Explainability
    inject_fault = (simulator.current_scenario.get("mission_status") == "SENSOR_DEGRADED")
    uncertainty_km = 0.85 if inject_fault else 0.18
    
    risk_result = risk_engine.evaluate_risk(
        min_distance_km=conjunction["min_distance_km"],
        relative_velocity_km_s=rel_kinematics["relative_velocity_km_s"],
        tca_minutes=conjunction["tca_minutes"],
        satellite_health=simulator.satellite,
        debris_metadata=primary_deb,
        sensor_uncertainty_km=uncertainty_km
    )

    # 3. Generate Candidate Maneuvers
    maneuvers = maneuver_engine.generate_candidate_maneuvers({
        "relative_velocity_km_s": rel_kinematics["relative_velocity_km_s"]
    })

    # 4. AI Decision Engine Optimization & Ranking
    ai_result = ai_engine.evaluate_and_rank(maneuvers, simulator.satellite)

    # Update state cache
    current_simulation_state["phase"] = "CONJUNCTION_DETECTED"
    current_simulation_state["conjunction"] = conjunction
    current_simulation_state["risk_analysis"] = risk_result
    current_simulation_state["maneuvers"] = ai_result["ranked_maneuvers"]
    current_simulation_state["ai_recommendation"] = ai_result
    current_simulation_state["trajectories"] = {
        "satellite": traj_data["satellite_path"],
        "debris": traj_data["debris_paths"],
        "conjunction_point": conjunction
    }
    current_simulation_state["post_trajectories"] = None
    current_simulation_state["actuator_telemetry"] = None
    current_simulation_state["sensor_telemetry"] = None
    current_simulation_state["post_risk_analysis"] = None

    # Audit Logging
    db.log_event("DEBRIS_DETECTED", f"Conjunction alert: {primary_deb['name']} detected on intercept course.", risk_result["risk_score"], "MONITOR")
    db.log_event("RISK_ASSESSED", f"Collision risk calculated: {risk_result['risk_score']}/100. Status: {risk_result['status']}.", risk_result["risk_score"], risk_result["status"])
    db.log_event("MANEUVER_GENERATED", f"Synthesized 3 avoidance options (A: Altitude Boost, B: Phasing, C: Cross-Track).", risk_result["risk_score"], risk_result["status"])
    db.log_event("AI_RECOMMENDATION", f"AI selected {ai_result['best_option_name']} (Utility {ai_result['best_utility_score']}/100).", risk_result["risk_score"], risk_result["status"])

    return jsonify({
        "success": True,
        "phase": current_simulation_state["phase"],
        "conjunction": conjunction,
        "risk_analysis": risk_result,
        "maneuvers": ai_result["ranked_maneuvers"],
        "ai_recommendation": ai_result,
        "trajectories": current_simulation_state["trajectories"]
    })


@app.route("/api/approve-maneuver", methods=["POST"])
def approve_and_execute_maneuver():
    """
    Executes approved maneuver via Virtual Actuator, validates telemetry via
    Virtual Sensor, and triggers the closed-loop risk recalculation.
    """
    data = request.get_json() or {}
    chosen_id = data.get("maneuver_id")

    if not current_simulation_state["maneuvers"]:
        return jsonify({"success": False, "message": "No maneuvers generated. Run simulation first."}), 400

    # Locate chosen maneuver (default to AI recommendation)
    if not chosen_id:
        chosen_id = current_simulation_state["ai_recommendation"]["best_option_id"]

    maneuver = next((m for m in current_simulation_state["maneuvers"] if m["id"] == chosen_id), None)
    if not maneuver:
        return jsonify({"success": False, "message": f"Maneuver {chosen_id} not found."}), 404

    # 1. Virtual Actuator Execution
    actuator_exec = virtual_actuator.execute_maneuver(maneuver, simulator.satellite)
    db.log_event("ACTUATOR_EXEC", f"Virtual actuator executed Maneuver {chosen_id}: Fired {maneuver['burn_duration_s']}s burn (ΔV {actuator_exec['actual_delta_v_delivered_m_s']} m/s).")

    # 2. Virtual Satellite State Update
    simulator.apply_maneuver(maneuver)

    # 3. Virtual Sensor Telemetry Verification
    is_sensor_fault = (simulator.scenario_name == "sensor_failure")
    sensor_verif = virtual_sensor.verify_maneuver(maneuver, actuator_exec, inject_sensor_fault=is_sensor_fault)
    db.log_event("SENSOR_VERIFY", f"Virtual sensor verification: {sensor_verif['status_text']} (Measured pitch {sensor_verif['measured_pitch_deg']}°, ΔV {sensor_verif['measured_dv_m_s']} m/s).")

    # 4. Closed-Loop Post-Maneuver Trajectory Recalculation
    post_traj_data = simulator.propagate_trajectories(
        time_horizon_min=60, 
        steps=60, 
        delta_v_vector=maneuver.get("delta_v_vector")
    )

    primary_deb = next((d for d in simulator.debris_list if d.get("is_primary")), simulator.debris_list[0])
    post_min_dist = maneuver["post_min_distance_km"]
    post_rel_vel = primary_deb.get("relative_velocity_km_s", 10.45)

    post_risk_result = risk_engine.evaluate_risk(
        min_distance_km=post_min_dist,
        relative_velocity_km_s=post_rel_vel,
        tca_minutes=post_traj_data["tca_min"],
        satellite_health=simulator.satellite,
        debris_metadata=primary_deb
    )

    # 5. Closed-Loop Reassessment Decision
    is_safe = (post_risk_result["risk_score"] <= 20.0 and sensor_verif["is_verified"])
    final_phase = "SAFE" if is_safe else "REASSESS_REQUIRED"

    if is_safe:
        db.log_event("REASSESSMENT_SUCCESS", f"Post-maneuver risk reduced to {post_risk_result['risk_score']}/100. STATUS: SAFE ✅", post_risk_result["risk_score"], "SAFE")
    else:
        db.log_event("REASSESSMENT_ALERT", f"Post-maneuver risk is {post_risk_result['risk_score']}/100. MANEUVER INSUFFICIENT - REASSESS 🔄", post_risk_result["risk_score"], post_risk_result["status"])

    # Update state cache
    current_simulation_state["phase"] = final_phase
    current_simulation_state["selected_maneuver"] = maneuver
    current_simulation_state["actuator_telemetry"] = actuator_exec
    current_simulation_state["sensor_telemetry"] = sensor_verif
    current_simulation_state["post_risk_analysis"] = post_risk_result
    current_simulation_state["post_trajectories"] = {
        "satellite": post_traj_data["satellite_path"],
        "conjunction_point": post_traj_data["conjunction"]
    }

    # Save to SQLite audit runs
    init_risk = current_simulation_state["risk_analysis"]["risk_score"] if current_simulation_state["risk_analysis"] else 0.0
    db.save_simulation_run(simulator.scenario_name, init_risk, post_risk_result["risk_score"], chosen_id, final_phase)

    return jsonify({
        "success": True,
        "phase": final_phase,
        "is_safe": is_safe,
        "selected_maneuver": maneuver,
        "actuator_telemetry": actuator_exec,
        "sensor_telemetry": sensor_verif,
        "post_risk_analysis": post_risk_result,
        "post_trajectories": current_simulation_state["post_trajectories"]
    })


@app.route("/api/reassess", methods=["POST"])
def reassess_orbit():
    """Triggered when user clicks [REASSESS] or if post-maneuver risk was insufficient."""
    primary_deb = next((d for d in simulator.debris_list if d.get("is_primary")), simulator.debris_list[0])
    rel = simulator.compute_relative_kinematics(primary_deb["id"])
    
    current_dist = rel["distance_km"]
    risk_result = risk_engine.evaluate_risk(
        min_distance_km=current_dist,
        relative_velocity_km_s=rel["relative_velocity_km_s"],
        tca_minutes=35.0,
        satellite_health=simulator.satellite,
        debris_metadata=primary_deb
    )

    db.log_event("REASSESS_REQUESTED", f"Reassessing orbital safety: Current distance {round(current_dist, 2)} km, Risk: {risk_result['risk_score']}/100.", risk_result["risk_score"], risk_result["status"])

    return jsonify({
        "success": True,
        "message": "Orbital geometry reassessed.",
        "risk_analysis": risk_result
    })


@app.route("/api/inject-fault", methods=["POST"])
def inject_fault():
    """Switches scenario / injects fault (normal, high_speed, low_battery, sensor_failure, communication_loss)."""
    data = request.get_json() or {}
    scenario = data.get("scenario", "normal")

    success = simulator.load_scenario(scenario)
    if not success:
        return jsonify({"success": False, "message": f"Scenario '{scenario}' not recognized."}), 400

    # Reset runtime state
    for k in current_simulation_state:
        current_simulation_state[k] = None
    current_simulation_state["phase"] = "STANDBY"

    db.log_event("SCENARIO_LOADED", f"Scenario changed to: {simulator.current_scenario['name']}. Fault/parameters updated.")

    return jsonify({
        "success": True,
        "scenario": scenario,
        "scenario_title": simulator.current_scenario["name"],
        "message": f"Scenario '{scenario}' loaded successfully."
    })


@app.route("/api/reset", methods=["POST"])
def reset_simulation():
    """Resets simulator and clears current trajectory predictions."""
    simulator.reset()
    for k in current_simulation_state:
        current_simulation_state[k] = None
    current_simulation_state["phase"] = "STANDBY"

    db.log_event("SYSTEM_RESET", "OrbitGuard simulation reset to standby initial state.")
    return jsonify({"success": True, "message": "System reset to initial state."})


@app.route("/api/logs", methods=["GET"])
def get_logs():
    return jsonify({"success": True, "logs": db.get_recent_logs(40)})


@app.route("/api/clear-logs", methods=["POST"])
def clear_logs():
    db.clear_logs()
    return jsonify({"success": True, "message": "Event logs cleared."})


if __name__ == "__main__":
    import sys
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    print("=" * 60)
    print("[*] ORBITGUARD AI - SPACE MISSION CONTROL SYSTEM")
    print("Explainable, Mission-Aware Satellite Collision Avoidance")
    print("Running on http://127.0.0.1:5000")
    print("=" * 60)
    app.run(debug=True, port=5000)