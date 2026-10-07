"""
ORBITGUARD AI - Explainable AI Decision Engine
Implements Multi-Attribute Utility Optimization (MAUT) & Explainable Decision Trees
to rank candidate maneuvers based on collision risk, delta-V cost, mission impact, and satellite health.
"""

from typing import List, Dict

class AIDecisionEngine:
    def __init__(self):
        # Default Multi-Objective Utility Weights
        self.w_safety = 0.50       # Collision risk reduction (highest priority)
        self.w_cost = 0.25         # Propellant & Delta-V conservation
        self.w_mission = 0.15      # Mission & payload continuity
        self.w_health = 0.10       # Battery & attitude stability preservation

    def evaluate_and_rank(self, maneuvers: List[Dict], satellite_state: dict) -> Dict:
        """
        Ranks candidate maneuvers and generates technical, human-interpretable reasoning.
        """
        battery_pct = satellite_state.get("battery_pct", 88.0)
        propellant_kg = satellite_state.get("propellant_kg", 40.0)
        mission_status = satellite_state.get("mission_status", "OPERATIONAL")

        # Dynamically adapt weights if health constraints are active
        w_safe = self.w_safety
        w_cost = self.w_cost
        w_miss = self.w_mission
        w_hlth = self.w_health

        health_alert_flag = None
        if battery_pct < 25.0:
            # Low battery: drastically increase penalty for high electrical/actuator load
            w_cost = 0.40
            w_hlth = 0.25
            w_safe = 0.30
            w_miss = 0.05
            health_alert_flag = f"LOW BATTERY CONDITION ({battery_pct}%): Energy conservation prioritized in AI optimization matrix."
        elif propellant_kg < 5.0:
            w_cost = 0.45
            w_safe = 0.40
            w_miss = 0.10
            w_hlth = 0.05
            health_alert_flag = f"PROPELLANT DEPLETION WARN ({propellant_kg} kg left): Delta-V cost given elevated weighting."

        ranked_maneuvers = []

        for m in maneuvers:
            # 1. Safety Sub-Score (0-100, where 100 is lowest post-risk)
            # post_risk_score ranges 0 - 100.
            safety_sub = max(0.0, 100.0 - m["post_risk_score"])

            # 2. Maneuver Cost Sub-Score (0-100, where 100 is lowest Delta-V)
            # Max single burn is ~20 m/s
            cost_ratio = min(1.0, m["delta_v_m_s"] / 20.0)
            cost_sub = (1.0 - cost_ratio) * 100.0

            # 3. Mission Impact Sub-Score
            if m["mission_impact"] == "LOW":
                mission_sub = 95.0
            elif m["mission_impact"] == "MEDIUM":
                mission_sub = 65.0
            else:
                mission_sub = 30.0

            # 4. Satellite Health Resilience Sub-Score
            # Considers remaining battery after maneuver
            post_battery = battery_pct - m["battery_cost_pct"]
            if post_battery < 20.0:
                health_sub = max(10.0, post_battery * 1.5)
            else:
                health_sub = min(100.0, post_battery)

            # Composite Multi-Attribute Utility Score (0 - 100)
            utility_score = (
                (w_safe * safety_sub) +
                (w_cost * cost_sub) +
                (w_miss * mission_sub) +
                (w_hlth * health_sub)
            )
            utility_score = round(utility_score, 1)

            ranked_maneuvers.append({
                **m,
                "utility_score": utility_score,
                "sub_scores": {
                    "safety": round(safety_sub, 1),
                    "cost_efficiency": round(cost_sub, 1),
                    "mission_continuity": round(mission_sub, 1),
                    "health_resilience": round(health_sub, 1)
                }
            })

        # Sort descending by utility score
        ranked_maneuvers.sort(key=lambda x: x["utility_score"], reverse=True)
        best = ranked_maneuvers[0]

        # Generate Explainable Justification
        if best["id"] == "B":
            explanation = (
                "Lowest collision risk + low maneuver cost + minimum mission impact. "
                f"Achieves post-maneuver risk of {best['post_risk_score']}% requiring only "
                f"{best['delta_v_m_s']} m/s Delta-V ({best['propellant_kg']} kg fuel) with negligible science interruption."
            )
        elif best["id"] == "A":
            explanation = (
                "Maximum separation geometry prioritized. "
                f"Altitude boost delivers {best['altitude_shift_km']} km vertical separation, "
                f"reducing risk to {best['post_risk_score']}% at higher delta-V expenditure."
            )
        else:
            explanation = (
                "Lateral cross-track deflection selected to isolate orbital plane from debris track. "
                f"Yields balanced risk reduction ({best['post_risk_score']}%) with medium thruster duty cycle."
            )

        if health_alert_flag:
            explanation += f" [Note: {health_alert_flag}]"

        return {
            "best_option_id": best["id"],
            "best_option_name": best["name"],
            "best_utility_score": best["utility_score"],
            "recommendation_reason": explanation,
            "ranked_maneuvers": ranked_maneuvers,
            "health_alert": health_alert_flag,
            "weights_applied": {
                "safety": round(w_safe, 2),
                "cost": round(w_cost, 2),
                "mission": round(w_miss, 2),
                "health": round(w_hlth, 2)
            }
        }
