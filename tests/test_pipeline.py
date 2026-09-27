import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scene_pipeline import run, validate, validate_prompts  # noqa: E402


def load(path):
    return json.loads((ROOT / "examples" / path).read_text(encoding="utf-8"))


class PipelineTests(unittest.TestCase):
    def test_eight_scene_types_compile(self):
        cases = sorted((ROOT / "examples").glob("0[1-8]-*.json"))
        self.assertEqual(len(cases), 8)
        for path in cases:
            with self.subTest(path=path.name):
                output = run(json.loads(path.read_text(encoding="utf-8")))
                self.assertEqual(output["validation"]["status"], "PASS", output["validation"]["issues"])
                self.assertEqual(len(output["validation"]["world_states"]), len(load(path.name)["actions"]) + 1)
                self.assertTrue(output["prompts"])

    def test_invalid_scenes_fail_for_expected_reason(self):
        expected = {"teleport": "TELEPORT", "ownership": "OWNERSHIP", "unreachable": "UNREACHABLE",
                    "contradiction": "CONTRADICTION", "missing-prerequisite": "PRECONDITION",
                    "obstacle-crossing": "OBSTACLE", "occlusion": "OCCLUSION"}
        for name, code in expected.items():
            with self.subTest(name=name):
                output = run(load(f"invalid/{name}.json"))
                self.assertEqual(output["validation"]["status"], "FAIL")
                self.assertIn(code, [item["code"] for item in output["validation"]["issues"]])
                self.assertEqual(output["prompts"], [])

    def test_handoff_changes_owner_and_location(self):
        output = run(load("03-handoff.json"))
        end = output["validation"]["world_states"][-1]["entities"]
        self.assertEqual(end["key"]["held_by"], "b")
        self.assertEqual(end["key"]["position"], end["b"]["position"])

    def test_timing_overload_splits_without_losing_events(self):
        data = load("09-timing-split.json")
        output = run(data)
        self.assertEqual(output["validation"]["status"], "PASS", output["validation"]["issues"])
        self.assertGreater(len(output["prompts"]), 1)
        self.assertIn("TIMING", [x["code"] for x in output["validation"]["issues"]])
        self.assertEqual([x for clip in output["prompts"] for x in clip["action_ids"]], [a["id"] for a in data["actions"]])

    def test_fantasy_needs_declared_rule(self):
        data = load("08-fantasy.json")
        self.assertEqual(run(data)["validation"]["status"], "PASS")
        data["world_rules"] = []
        self.assertEqual(run(data)["validation"]["status"], "FAIL")

    def test_generic_adapter_and_final_prompt_tamper(self):
        data = load("01-person-and-object.json")
        output = run(data, "generic")
        self.assertEqual(output["validation"]["status"], "PASS")
        altered = copy.deepcopy(output["prompts"])
        altered[0]["prompt"] = altered[0]["prompt"].replace("The woman notices the cup", "The woman notices a vase")
        self.assertEqual(validate_prompts(data, output["validation"], altered)["status"], "FAIL")
        altered = copy.deepcopy(output["prompts"])
        altered[0]["prompt"] += " A second unseen person takes the cup."
        self.assertEqual(validate_prompts(data, output["validation"], altered)["status"], "FAIL")

    def test_obstacle_route_is_real_path(self):
        data = load("05-obstacle.json")
        self.assertEqual(validate(data)["status"], "PASS")
        data["actions"][0]["effects"][0]["path"] = [[0, 0], [4, 0]]
        self.assertIn("OBSTACLE", [x["code"] for x in validate(data)["issues"]])

    def test_reference_previs_roles_and_h3_format(self):
        output = run(load("10-reference-previs.json"))
        self.assertEqual(output["validation"]["status"], "PASS")
        prompt = output["prompts"][0]["prompt"]
        self.assertLess(prompt.index("subject_definitions:"), prompt.index("retention_analysis:"))
        self.assertLess(prompt.index("retention_analysis:"), prompt.index("detailed_description:"))
        self.assertIn("<Picture 1>", prompt)
        self.assertIn("<Video 1>", prompt)
        self.assertIn("blocking, movement path and timing", prompt)

    def test_keyframe_mode_requires_picture(self):
        data = load("01-person-and-object.json")
        data["h3_mode"] = "I2VA"
        self.assertEqual(run(data)["validation"]["status"], "FAIL")
        data["references"] = [{"id": "first", "label": "<Picture 1>", "role": "first frame", "description": "supplied first frame"}]
        self.assertEqual(run(data)["validation"]["status"], "PASS")

    def test_camera_move_updates_world_state(self):
        data = load("01-person-and-object.json")
        data["actions"].insert(0, {"id": "reframe", "actor": "woman", "kind": "camera", "description": "The camera tracks one metre right", "min_duration": 1,
                                   "effects": [{"type": "camera_move", "path": [[0, -4], [1, -4]], "to": [1, -4]}]})
        output = run(data)
        self.assertEqual(output["validation"]["status"], "PASS", output["validation"]["issues"])
        self.assertEqual(output["validation"]["world_states"][1]["camera_position"], [1, -4])

    def test_declared_speed_prevents_implausible_timing(self):
        data = load("06-vehicle.json")
        data["initial_world_state"]["entities"]["car"]["max_speed"] = 1
        self.assertIn("TIMING", [x["code"] for x in validate(data)["issues"]])

    def test_h3_duration_is_integer(self):
        data = load("01-person-and-object.json")
        data["scene"]["duration"] = 6.5
        output = run(data)
        self.assertEqual(output["prompts"][0]["duration"], 7)

    def test_state_change_requires_world_state_effect(self):
        data = load("04-room-traversal.json")
        data["actions"][1]["effects"] = []
        output = run(data)
        self.assertEqual(output["validation"]["status"], "FAIL")
        self.assertIn("PRECONDITION", [x["code"] for x in output["validation"]["issues"]])


if __name__ == "__main__":
    unittest.main()
