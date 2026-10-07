"""
ORBITGUARD AI - Virtual Hardware Simulation Layer
Simulates 100% software-based Virtual Actuators (Reaction Wheels + RCS Thrusters)
and Virtual Sensors (Star Tracker, GNSS, 3-Axis Accelerometer/IMU) with realistic
telemetry verification and sensor noise models.
"""

import random
import time

class VirtualActuator:
    """
    Simulates satellite propulsion and attitude actuators:
    - 3-Axis Reaction Wheel Assembly (RWA)
    - Cold-Gas / Hydrazine Monopropellant Reaction Control System (RCS)
    """
    def __init__(self):
        self.state = "IDLE"
        self.last_command = None
        self.last_execution = None

    def execute_maneuver(self, maneuver_spec: dict, current_satellite: dict) -> dict:
        """
        Executes software-simulated maneuver burn sequence.
        Transitions states: IDLE -> ATTITUDE_SLEW -> THRUSTER_IGNITION -> BURNING -> POST_BURN_SETTLING
        """
        self.state = "EXECUTING"
        maneuver_id = maneuver_spec.get("id", "B")
        target_dv = maneuver_spec.get("delta_v_m_s", 3.8)
        target_pitch = maneuver_spec.get("target_pitch_deg", 4.5)
        burn_duration = maneuver_spec.get("burn_duration_s", 6.8)

        # Actuator physical modeling
        slew_rate_deg_s = 1.2  # Typical small satellite slew rate
        slew_duration = round(abs(target_pitch) / slew_rate_deg_s, 2)
        nominal_thrust_n = 10.5  # Newtons

        # Simulated slight micro-variations in actuator output (99.8% precision)
        actual_dv_delivered = round(target_dv * random.uniform(0.995, 1.003), 3)
        actual_pitch_slew = round(target_pitch * random.uniform(0.988, 1.012), 2)

        execution_record = {
            "status": "SUCCESS",
            "state": "NOMINAL_STABILIZED",
            "command": f"EXECUTE_MANEUVER_{maneuver_id}",
            "actuator_system": "Virtual RCS Micro-Thruster Array & 3-Axis Reaction Wheel",
            "target_delta_v_m_s": target_dv,
            "actual_delta_v_delivered_m_s": actual_dv_delivered,
            "target_pitch_deg": target_pitch,
            "actual_pitch_slew_deg": actual_pitch_slew,
            "burn_duration_s": burn_duration,
            "thrust_force_newtons": nominal_thrust_n,
            "chamber_pressure_bar": round(random.uniform(14.8, 15.2), 2),
            "attitude_slew_duration_s": slew_duration,
            "message": f"Virtual Actuator executed Maneuver {maneuver_id}: Fired {burn_duration}s pulse delivering {actual_dv_delivered} m/s ΔV."
        }

        self.last_command = maneuver_spec
        self.last_execution = execution_record
        self.state = "IDLE"
        return execution_record


class VirtualSensor:
    """
    Simulates on-board navigation sensors:
    - Autonomous Star Tracker (Attitude determination)
    - On-Board GNSS / GPS Space Receiver (Orbital position & velocity)
    - 3-Axis Inertial Measurement Unit (IMU Accelerometer)
    """
    def __init__(self):
        self.star_tracker_noise_deg = 0.04
        self.imu_noise_m_s = 0.02
        self.tolerance_pitch_deg = 0.35
        self.tolerance_dv_m_s = 0.15

    def verify_maneuver(self, target_spec: dict, actuator_result: dict, inject_sensor_fault: bool = False) -> dict:
        """
        Cross-checks commanded trajectory vs measured physical telemetry.
        Validates whether simulated maneuver achieved commanded state within engineering tolerances.
        """
        target_pitch = target_spec.get("target_pitch_deg", 4.5)
        target_dv = target_spec.get("delta_v_m_s", 3.8)

        actual_pitch = actuator_result.get("actual_pitch_slew_deg", target_pitch)
        actual_dv = actuator_result.get("actual_delta_v_delivered_m_s", target_dv)

        # Virtual sensor measurement with noise
        if inject_sensor_fault:
            # Simulate degraded sensor reading / high bias error
            measured_pitch = round(actual_pitch + random.uniform(1.8, 3.2), 2)
            measured_dv = round(actual_dv + random.uniform(0.6, 1.1), 3)
        else:
            measured_pitch = round(actual_pitch + random.gauss(0, self.star_tracker_noise_deg), 2)
            measured_dv = round(actual_dv + random.gauss(0, self.imu_noise_m_s), 3)

        pitch_error = abs(measured_pitch - target_pitch)
        dv_error = abs(measured_dv - target_dv)

        is_pitch_verified = pitch_error <= self.tolerance_pitch_deg
        is_dv_verified = dv_error <= self.tolerance_dv_m_s
        is_fully_verified = is_pitch_verified and is_dv_verified

        if is_fully_verified:
            verification_status = "MANEUVER VERIFIED ✅"
            verification_flag = "VERIFIED_SAFE"
            message = (
                f"Virtual Sensors confirmed trajectory change: Pitch {measured_pitch}° "
                f"(commanded {target_pitch}°, Δ={round(pitch_error, 2)}°), "
                f"ΔV {measured_dv} m/s (commanded {target_dv} m/s, Δ={round(dv_error, 3)} m/s). "
                "Orbital deflection confirmed within tolerance."
            )
        else:
            verification_status = "SENSOR DISCREPANCY ⚠️"
            verification_flag = "VERIFICATION_FAILED"
            message = (
                f"Sensor anomaly detected: Measured pitch {measured_pitch}° (Target {target_pitch}°) or "
                f"ΔV {measured_dv} m/s (Target {target_dv} m/s) exceeded tolerance envelope. "
                "Autonomous reassessment recommended."
            )

        return {
            "status_text": verification_status,
            "verification_flag": verification_flag,
            "is_verified": is_fully_verified,
            "target_pitch_deg": target_pitch,
            "measured_pitch_deg": measured_pitch,
            "pitch_error_deg": round(pitch_error, 3),
            "target_dv_m_s": target_dv,
            "measured_dv_m_s": measured_dv,
            "dv_error_m_s": round(dv_error, 3),
            "sensor_telemetry": {
                "star_tracker_status": "CALIBRATED_NOMINAL" if not inject_sensor_fault else "DEGRADED_COVARIANCE",
                "imu_accelerometer_status": "LOCKED",
                "gnss_ephemeris_lock": "3D_FIX_8_SATELLITES"
            },
            "message": message
        }
