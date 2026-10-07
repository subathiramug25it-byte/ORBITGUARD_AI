"""
ORBITGUARD AI - Physics & Orbital Kinematics Simulator
Simulates Low Earth Orbit (LEO) satellite and space debris trajectories using
two-body Keplerian mechanics and numerical propagation with NumPy.

NOTE: This is a hackathon-ready software prototype simulation designed for
explainable collision avoidance and mission-support decision testing.
"""

import math
import json
import os
import numpy as np

# Physical Constants (WGS84 / Earth Gravitational Model)
EARTH_RADIUS_KM = 6371.0
MU_EARTH = 398600.4418  # km^3 / s^2 (Standard gravitational parameter)

DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "simulation_data.json")


class OrbitalSimulator:
    def __init__(self, scenario_name="normal"):
        self.scenario_name = scenario_name
        self.scenarios_data = self._load_scenarios()
        self.current_scenario = self.scenarios_data.get(scenario_name, self.scenarios_data["normal"])
        
        self.satellite = dict(self.current_scenario["satellite"])
        self.debris_list = [dict(d) for d in self.current_scenario["debris_list"]]
        
        # State indicators
        self.maneuver_applied = None
        self.simulation_step = 0
        self.time_elapsed_sec = 0.0

    def _load_scenarios(self):
        if os.path.exists(DATA_PATH):
            with open(DATA_PATH, "r") as f:
                return json.load(f)["scenarios"]
        raise FileNotFoundError(f"Scenario file not found at {DATA_PATH}")

    def load_scenario(self, scenario_name):
        """Switches current simulation scenario or fault state."""
        if scenario_name in self.scenarios_data:
            self.scenario_name = scenario_name
            self.current_scenario = self.scenarios_data[scenario_name]
            self.satellite = dict(self.current_scenario["satellite"])
            self.debris_list = [dict(d) for d in self.current_scenario["debris_list"]]
            self.maneuver_applied = None
            self.time_elapsed_sec = 0.0
            return True
        return False

    def reset(self):
        """Resets the simulation to the initial condition of current scenario."""
        self.current_scenario = self.scenarios_data.get(self.scenario_name, self.scenarios_data["normal"])
        self.satellite = dict(self.current_scenario["satellite"])
        self.debris_list = [dict(d) for d in self.current_scenario["debris_list"]]
        self.maneuver_applied = None
        self.time_elapsed_sec = 0.0

    def get_satellite_cartesian(self, true_anomaly_deg=None, alt_km=None):
        """Calculates 2D/3D orbital position and velocity vectors."""
        theta_deg = self.satellite["true_anomaly_deg"] if true_anomaly_deg is None else true_anomaly_deg
        alt = self.satellite["altitude_km"] if alt_km is None else alt_km
        r = EARTH_RADIUS_KM + alt
        theta = math.radians(theta_deg)

        # Orbital velocity in circular approximation
        v_mag = math.sqrt(MU_EARTH / r)
        
        # 2D in-plane coordinates (X, Y) in km
        x = r * math.cos(theta)
        y = r * math.sin(theta)
        
        # Velocity tangent to orbit
        vx = -v_mag * math.sin(theta)
        vy = v_mag * math.cos(theta)
        
        return {
            "x": round(x, 3),
            "y": round(y, 3),
            "vx": round(vx, 4),
            "vy": round(vy, 4),
            "radius_km": round(r, 2),
            "v_mag": round(v_mag, 3)
        }

    def get_debris_cartesian(self, debris_obj, true_anomaly_deg=None):
        theta_deg = debris_obj["true_anomaly_deg"] if true_anomaly_deg is None else true_anomaly_deg
        r = EARTH_RADIUS_KM + debris_obj["altitude_km"]
        theta = math.radians(theta_deg)
        inc = math.radians(debris_obj.get("inclination_deg", 51.6) - self.satellite.get("inclination_deg", 51.6))

        v_mag = math.sqrt(MU_EARTH / r)
        
        # Planar projection with relative crossing geometry
        x = r * math.cos(theta)
        y = r * math.sin(theta) * math.cos(inc)
        z = r * math.sin(theta) * math.sin(inc)
        
        # Velocity with relative angle
        vx = -v_mag * math.sin(theta)
        vy = v_mag * math.cos(theta) * math.cos(inc)
        vz = v_mag * math.cos(theta) * math.sin(inc)
        
        return {
            "x": round(x, 3),
            "y": round(y, 3),
            "z": round(z, 3),
            "vx": round(vx, 4),
            "vy": round(vy, 4),
            "vz": round(vz, 4),
            "radius_km": round(r, 2),
            "v_mag": round(v_mag, 3)
        }

    def propagate_trajectories(self, time_horizon_min=60, steps=60, delta_v_vector=None):
        """
        Propagates satellite and debris forward in time using NumPy.
        Returns coordinate arrays for plotting predicted trajectories.
        Optionally applies an instantaneous Delta-V to satellite at t=0.
        """
        dt_sec = (time_horizon_min * 60) / steps
        times = np.linspace(0, time_horizon_min * 60, steps)

        r_sat = EARTH_RADIUS_KM + self.satellite["altitude_km"]
        omega_sat = math.sqrt(MU_EARTH / (r_sat ** 3)) # rad/s

        # If a maneuver is applied, adjust orbital parameters
        r_sat_active = r_sat
        omega_sat_active = omega_sat
        radial_offset = 0.0
        
        if delta_v_vector:
            # dv_prograde, dv_radial, dv_normal in m/s
            dv_prog_km_s = delta_v_vector.get("dv_prograde", 0.0) / 1000.0
            dv_norm_km_s = delta_v_vector.get("dv_normal", 0.0) / 1000.0
            
            # Change in semi-major axis: da = (2 * a^2 * v / mu) * dv
            v_curr = math.sqrt(MU_EARTH / r_sat)
            da = (2 * (r_sat ** 2) * v_curr / MU_EARTH) * dv_prog_km_s
            r_sat_active = r_sat + da
            omega_sat_active = math.sqrt(MU_EARTH / (r_sat_active ** 3))
            radial_offset = dv_norm_km_s * 50.0  # Out of plane projection factor

        sat_theta_0 = math.radians(self.satellite["true_anomaly_deg"])
        sat_path = []
        for t in times:
            theta = sat_theta_0 + omega_sat_active * t
            x = r_sat_active * math.cos(theta)
            y = r_sat_active * math.sin(theta) + radial_offset
            sat_path.append({"time_min": round(t / 60.0, 2), "x": round(x, 2), "y": round(y, 2)})

        # Debris propagation
        debris_paths = {}
        for d in self.debris_list:
            r_deb = EARTH_RADIUS_KM + d["altitude_km"]
            omega_deb = math.sqrt(MU_EARTH / (r_deb ** 3))
            deb_theta_0 = math.radians(d["true_anomaly_deg"])
            inc_diff = math.radians(d.get("inclination_deg", 51.6) - self.satellite.get("inclination_deg", 51.6))
            
            d_path = []
            for t in times:
                theta = deb_theta_0 + omega_deb * t
                x = r_deb * math.cos(theta)
                y = r_deb * math.sin(theta) * math.cos(inc_diff)
                d_path.append({"time_min": round(t / 60.0, 2), "x": round(x, 2), "y": round(y, 2)})
            debris_paths[d["id"]] = d_path

        # Find closest approach with primary debris
        primary = next((d for d in self.debris_list if d.get("is_primary")), self.debris_list[0])
        primary_path = debris_paths[primary["id"]]

        distances = []
        for i in range(len(times)):
            dx = sat_path[i]["x"] - primary_path[i]["x"]
            dy = sat_path[i]["y"] - primary_path[i]["y"]
            dist_km = math.sqrt(dx * dx + dy * dy)
            distances.append(dist_km)

        min_idx = int(np.argmin(distances))
        min_dist_km = float(distances[min_idx])
        tca_min = float(times[min_idx] / 60.0)
        
        # Conjunction coordinates
        conjunction_point = {
            "x": round((sat_path[min_idx]["x"] + primary_path[min_idx]["x"]) / 2.0, 2),
            "y": round((sat_path[min_idx]["y"] + primary_path[min_idx]["y"]) / 2.0, 2),
            "tca_minutes": round(tca_min, 2),
            "min_distance_km": round(min_dist_km, 4),
            "min_distance_m": round(min_dist_km * 1000.0, 1)
        }

        return {
            "satellite_path": sat_path,
            "debris_paths": debris_paths,
            "conjunction": conjunction_point,
            "min_distance_km": min_dist_km,
            "tca_min": tca_min
        }

    def compute_relative_kinematics(self, debris_id=None):
        """Calculates instantaneous distance and relative velocity with specified debris."""
        deb = None
        if debris_id:
            deb = next((d for d in self.debris_list if d["id"] == debris_id), None)
        if not deb:
            deb = next((d for d in self.debris_list if d.get("is_primary")), self.debris_list[0])

        sat_pos = self.get_satellite_cartesian()
        deb_pos = self.get_debris_cartesian(deb)

        dx = deb_pos["x"] - sat_pos["x"]
        dy = deb_pos["y"] - sat_pos["y"]
        dz = deb_pos.get("z", 0.0)
        dist_km = math.sqrt(dx*dx + dy*dy + dz*dz)

        dvx = deb_pos["vx"] - sat_pos["vx"]
        dvy = deb_pos["vy"] - sat_pos["vy"]
        dvz = deb_pos.get("vz", 0.0)
        v_rel = math.sqrt(dvx*dvx + dvy*dvy + dvz*dvz)

        return {
            "debris_id": deb["id"],
            "debris_name": deb["name"],
            "distance_km": round(dist_km, 3),
            "distance_m": round(dist_km * 1000.0, 1),
            "relative_velocity_km_s": round(v_rel, 3),
            "is_primary": deb.get("is_primary", False)
        }

    def apply_maneuver(self, maneuver_spec):
        """
        Updates simulated satellite state upon actuator burn execution.
        maneuver_spec contains delta_v_m_s, burn_duration_s, battery_cost_pct, altitude_shift_km
        """
        delta_v = maneuver_spec.get("delta_v_m_s", 0.0)
        alt_shift = maneuver_spec.get("altitude_shift_km", 0.0)
        battery_cost = maneuver_spec.get("battery_cost_pct", 1.5)
        propellant_cost = maneuver_spec.get("propellant_kg", 0.45)
        pitch_deg = maneuver_spec.get("target_pitch_deg", 5.0)

        # Update satellite state
        self.satellite["altitude_km"] += alt_shift
        self.satellite["battery_pct"] = max(5.0, round(self.satellite["battery_pct"] - battery_cost, 2))
        self.satellite["propellant_kg"] = max(0.1, round(self.satellite["propellant_kg"] - propellant_cost, 2))
        self.satellite["max_delta_v_m_s"] = max(0.0, round(self.satellite["max_delta_v_m_s"] - delta_v, 2))
        self.satellite["orientation_deg"]["pitch"] = pitch_deg
        
        # Mark maneuver
        self.maneuver_applied = maneuver_spec
        return self.satellite

    def get_full_telemetry(self):
        """Returns comprehensive virtual telemetry for dashboard streaming."""
        sat_cart = self.get_satellite_cartesian()
        primary_deb = next((d for d in self.debris_list if d.get("is_primary")), self.debris_list[0])
        deb_cart = self.get_debris_cartesian(primary_deb)
        rel = self.compute_relative_kinematics(primary_deb["id"])

        return {
            "scenario": self.scenario_name,
            "scenario_title": self.current_scenario["name"],
            "satellite": {
                **self.satellite,
                "cartesian": sat_cart
            },
            "primary_debris": {
                **primary_deb,
                "cartesian": deb_cart,
                "relative": rel
            },
            "all_debris": self.debris_list,
            "maneuver_applied": self.maneuver_applied
        }