"""
ORBITGUARD AI - Automated Integration & Pipeline Test
Tests all simulation, risk calculation, maneuver generation, AI ranking,
virtual hardware verification, and Flask API endpoints.
"""

import unittest
import json
from app import app, simulator, risk_engine, maneuver_engine, ai_engine, virtual_actuator, virtual_sensor

class TestOrbitGuardAI(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_01_index_and_dashboard_routes(self):
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"ORBITGUARD AI", res.data)

        res_dash = self.client.get("/dashboard")
        self.assertEqual(res_dash.status_code, 200)
        self.assertIn(b"ORBITGUARD AI", res_dash.data)

    def test_02_api_state(self):
        res = self.client.get("/api/state")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertIn("satellite", data["telemetry"])
        self.assertIn("all_debris", data["telemetry"])

    def test_03_api_simulate_pipeline(self):
        res = self.client.post("/api/simulate")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertIn("risk_analysis", data)
        self.assertIn("maneuvers", data)
        self.assertIn("ai_recommendation", data)
        self.assertIn("trajectories", data)

        risk = data["risk_analysis"]
        self.assertGreater(risk["risk_score"], 0)
        self.assertIn("status", risk)
        self.assertIn("explanations", risk)
        self.assertIn("classification", risk)

        # AI Recommendation
        ai_rec = data["ai_recommendation"]
        self.assertIn("best_option_id", ai_rec)
        self.assertIn("recommendation_reason", ai_rec)

    def test_04_approve_and_reassess_loop(self):
        # 1. Simulate first
        self.client.post("/api/simulate")

        # 2. Approve Maneuver B
        res = self.client.post("/api/approve-maneuver", 
                               data=json.dumps({"maneuver_id": "B"}),
                               content_type="application/json")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertIn("actuator_telemetry", data)
        self.assertIn("sensor_telemetry", data)
        self.assertIn("post_risk_analysis", data)
        self.assertIn("post_trajectories", data)

        # Post risk must be significantly lower than initial risk!
        post_risk = data["post_risk_analysis"]["risk_score"]
        self.assertLess(post_risk, 25.0)
        self.assertEqual(data["post_risk_analysis"]["status"], "SAFE")
        self.assertEqual(data["phase"], "SAFE")

        # Virtual sensor verification must be verified
        self.assertTrue(data["sensor_telemetry"]["is_verified"])

    def test_05_fault_injection(self):
        for scenario in ["low_battery", "high_speed", "sensor_failure", "communication_loss", "normal"]:
            res = self.client.post("/api/inject-fault",
                                   data=json.dumps({"scenario": scenario}),
                                   content_type="application/json")
            self.assertEqual(res.status_code, 200)
            data = res.get_json()
            self.assertTrue(data["success"])
            self.assertEqual(data["scenario"], scenario)

    def test_06_logs_and_reset(self):
        res_logs = self.client.get("/api/logs")
        self.assertEqual(res_logs.status_code, 200)
        data_logs = res_logs.get_json()
        self.assertTrue(len(data_logs["logs"]) > 0)

        res_reset = self.client.post("/api/reset")
        self.assertEqual(res_reset.status_code, 200)
        self.assertTrue(res_reset.get_json()["success"])

if __name__ == "__main__":
    unittest.main()
