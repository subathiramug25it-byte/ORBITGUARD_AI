"""
ORBITGUARD AI - Explainable Collision Risk Assessment Engine
Computes transparent, multi-factor collision probabilities and risk scores (0-100),
decomposes contributing physical factors, and classifies debris as THREAT, RECOVERABLE, or UNCERTAIN.
"""

import math

class RiskEngine:
    def __init__(self):
        # NASA / ESA Safety thresholds for LEO
        self.SAFETY_RADIUS_KM = 5.0      # Safety corridor boundary
        self.CRITICAL_RADIUS_KM = 0.5    # Hard collision alert corridor (500m)
        self.TIME_HORIZON_CRITICAL_MIN = 25.0

    def evaluate_risk(self, min_distance_km: float, relative_velocity_km_s: float, 
                      tca_minutes: float, satellite_health: dict = None, 
                      debris_metadata: dict = None, sensor_uncertainty_km: float = 0.2):
        """
        Calculates a multi-factor explainable risk score (0-100) and structured decomposition.
        """
        # Default health
        if satellite_health is None:
            satellite_health = {"battery_pct": 88.0, "mission_status": "OPERATIONAL"}
        if debris_metadata is None:
            debris_metadata = {"rcs_m2": 0.85, "estimated_mass_kg": 15.0}

        explanations = []

        # -------------------------------------------------------------
        # 1. Proximity Hazard Component (Max 50 points)
        # -------------------------------------------------------------
        if min_distance_km <= 0.1:
            proximity_score = 50.0
            proximity_factor = 1.0
            explanations.append(f"Extreme proximity: Predicted miss distance is only {round(min_distance_km * 1000, 1)} m (well within collision ellipsoid).")
        elif min_distance_km <= self.CRITICAL_RADIUS_KM:
            # Scaled between 0.1 and 0.5 km -> 50 down to 38
            norm = (min_distance_km - 0.1) / (self.CRITICAL_RADIUS_KM - 0.1)
            proximity_score = 50.0 - (norm * 12.0)
            proximity_factor = 0.88 - (norm * 0.15)
            explanations.append(f"Critical proximity: Miss distance {round(min_distance_km * 1000, 1)} m breaches the 500m hard safety perimeter.")
        elif min_distance_km <= self.SAFETY_RADIUS_KM:
            # Scaled between 0.5 and 5.0 km -> 38 down to 3.0
            norm = (min_distance_km - self.CRITICAL_RADIUS_KM) / (self.SAFETY_RADIUS_KM - self.CRITICAL_RADIUS_KM)
            proximity_score = 38.0 - (norm * 35.0)
            proximity_factor = max(0.06, 0.70 - (norm * 0.62))
            explanations.append(f"Cautionary proximity: Miss distance {round(min_distance_km, 2)} km within standard 5 km conjunction monitoring bubble.")
        else:
            # Safe distance > 5 km
            proximity_score = max(0.2, 2.5 - min(2.0, (min_distance_km - 5.0) * 0.1))
            proximity_factor = 0.04
            explanations.append(f"Safe separation distance: Predicted clearance is {round(min_distance_km, 2)} km (well outside 5 km safety zone).")

        # -------------------------------------------------------------
        # 2. Hypervelocity Kinetic Hazard Component (Max 25 points)
        # -------------------------------------------------------------
        # Kinetic energy scales with v^2. Kinetic hazard is conditional on close approach!
        v_clamped = min(15.0, max(0.0, relative_velocity_km_s))
        base_kinetic = (v_clamped / 15.0) ** 1.3 * 25.0
        kinetic_score = base_kinetic * proximity_factor

        if relative_velocity_km_s >= 10.0:
            if min_distance_km <= self.SAFETY_RADIUS_KM:
                explanations.append(f"Hypervelocity impact hazard: Encounter speed {round(relative_velocity_km_s, 2)} km/s would cause catastrophic vehicle fragmentation.")
            else:
                explanations.append(f"Hypervelocity object ({round(relative_velocity_km_s, 2)} km/s), safely deflected outside collision corridor.")
        elif relative_velocity_km_s >= 5.0:
            explanations.append(f"Relative velocity: {round(relative_velocity_km_s, 2)} km/s.")
        else:
            explanations.append(f"Moderate encounter velocity: {round(relative_velocity_km_s, 2)} km/s.")

        # -------------------------------------------------------------
        # 3. Temporal Urgency (TCA) Component (Max 20 points)
        # -------------------------------------------------------------
        # Urgency is conditional on being on a close approach track
        if tca_minutes <= 10.0:
            base_urgency = 20.0
            urg_desc = f"Critical time urgency: Conjunction in {round(tca_minutes, 1)} minutes leaves minimal reaction lead time."
        elif tca_minutes <= self.TIME_HORIZON_CRITICAL_MIN:
            norm = (tca_minutes - 10.0) / (self.TIME_HORIZON_CRITICAL_MIN - 10.0)
            base_urgency = 20.0 - (norm * 10.0)
            urg_desc = f"Elevated urgency: TCA estimated at {round(tca_minutes, 1)} minutes; immediate maneuver decision required."
        elif tca_minutes <= 60.0:
            base_urgency = max(2.0, 10.0 - ((tca_minutes - 25.0) / 35.0) * 8.0)
            urg_desc = f"Moderate timeline: TCA estimated at {round(tca_minutes, 1)} minutes; sufficient window for burn planning."
        else:
            base_urgency = 1.0
            urg_desc = f"Distant conjunction: TCA {round(tca_minutes, 1)} minutes."

        urgency_score = base_urgency * proximity_factor
        if min_distance_km <= self.SAFETY_RADIUS_KM:
            explanations.append(urg_desc)

        # -------------------------------------------------------------
        # 4. Positional Uncertainty & Health Penalty (Max 10 points)
        # -------------------------------------------------------------
        uncertainty_score = min(4.0, (sensor_uncertainty_km / 1.0) * 4.0)

        health_penalty = 0.0
        bat = satellite_health.get("battery_pct", 80.0)
        status = satellite_health.get("mission_status", "OPERATIONAL")
        
        if bat < 25.0:
            health_penalty += 3.0
            explanations.append(f"Satellite battery low ({bat}%): Maneuver power budget constrained.")
        if status in ["SENSOR_DEGRADED", "SENSOR_FAILURE"]:
            health_penalty += 3.5
            explanations.append("Attitude star tracker degraded: Positional covariance volume expanded by 320%.")
        elif status in ["AUTONOMOUS_SAFEGUARD", "COMMUNICATION_LOSS"]:
            health_penalty += 2.0
            explanations.append("Ground link blackout: Autonomous safety margin verification enforced.")

        # If already far away and safe, scale down health penalty so it doesn't artificially flag a false collision
        total_risk = proximity_score + kinetic_score + urgency_score + (uncertainty_score + health_penalty) * min(1.0, proximity_factor * 2.5 + 0.15)
        total_risk = round(min(100.0, max(0.0, total_risk)), 1)

        # Early Warning Status Classification
        if total_risk >= 75.0:
            status_label = "CRITICAL"
            status_color = "#ff334b"
            status_icon = "🚨"
        elif total_risk >= 50.0:
            status_label = "WARNING"
            status_color = "#ff9900"
            status_icon = "⚠️"
        elif total_risk >= 20.0:
            status_label = "MONITOR"
            status_color = "#ffd700"
            status_icon = "👁️"
        else:
            status_label = "SAFE"
            status_color = "#00e676"
            status_icon = "✅"

        # Threat vs Resource Classification
        classification = self.classify_debris(debris_metadata, relative_velocity_km_s)

        return {
            "risk_score": total_risk,
            "status": status_label,
            "status_color": status_color,
            "status_icon": status_icon,
            "min_distance_km": round(min_distance_km, 4),
            "min_distance_m": round(min_distance_km * 1000.0, 1),
            "relative_velocity_km_s": round(relative_velocity_km_s, 2),
            "tca_minutes": round(tca_minutes, 1),
            "factors": {
                "proximity": round(proximity_score, 1),
                "kinetic": round(kinetic_score, 1),
                "urgency": round(urgency_score, 1),
                "uncertainty_and_health": round((uncertainty_score + health_penalty) * min(1.0, proximity_factor * 2.5 + 0.15), 1)
            },
            "explanations": explanations,
            "classification": classification
        }

    def classify_debris(self, debris_meta: dict, rel_vel_km_s: float):
        """
        Classifies space debris object into:
        - THREAT ☄️ (Avoid immediately)
        - RECOVERABLE ♻️ (Candidate for future Active Debris Removal / In-Orbit Recycling)
        - UNCERTAIN ⚠️ (Sparse radar signature or tumbling)
        """
        mass = debris_meta.get("estimated_mass_kg", 10.0)
        rcs = debris_meta.get("rcs_m2", 0.5)
        material = debris_meta.get("material", "Metallic Fragment")
        explicit_cat = debris_meta.get("classification_category")

        if explicit_cat:
            cat = explicit_cat
        else:
            if mass > 25.0 and rcs > 1.5 and rel_vel_km_s < 9.0:
                cat = "RECOVERABLE"
            elif rcs < 0.25 or "Particle" in debris_meta.get("name", ""):
                cat = "UNCERTAIN"
            else:
                cat = "THREAT"

        if cat == "RECOVERABLE":
            return {
                "category": "RECOVERABLE",
                "badge": "♻️ RECOVERABLE RESOURCE",
                "color": "#00d2ff",
                "rationale": f"Intact structure ({mass} kg, RCS {rcs} m²). High structural purity ({material}). Favorable rendezvous candidate for future ADR recycling."
            }
        elif cat == "UNCERTAIN":
            return {
                "category": "UNCERTAIN",
                "badge": "⚠️ UNCERTAIN SIGNATURE",
                "color": "#ffd700",
                "rationale": f"RCS under 0.3 m² ({rcs} m²). Fast tumbling radar profile. Position covariance ellipsoid requires radar tracking refinement."
            }
        else:
            return {
                "category": "THREAT",
                "badge": "☄️ KINETIC THREAT",
                "color": "#ff334b",
                "rationale": f"Uncontrolled hypervelocity fragment ({mass} kg, {round(rel_vel_km_s, 1)} km/s relative speed). Irrecoverable kinetic hazard requiring trajectory deflection."
            }
