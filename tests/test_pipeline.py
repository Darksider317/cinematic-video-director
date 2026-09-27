import copy
import json
import subprocess
import sys
import tempfile
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
        data["model"] = "generic"
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

    def test_target_generator_is_required(self):
        data = load("01-person-and-object.json")
        del data["model"]
        output = run(data)
        self.assertEqual(output["validation"]["status"], "FAIL")
        self.assertIn("MODEL_REQUIRED", [x["code"] for x in output["validation"]["issues"]])
        self.assertEqual(output["prompts"], [])

    def test_five_named_adapters_preserve_approved_actions(self):
        data = load("03-handoff.json")
        expected = [a["description"] for a in data["actions"]]
        formats = {"seedance-2": "Action sequence:", "veo-3.1": "The action unfolds in this order:",
                   "kling-3": "Choreography:", "wan-2.6": "Actions:", "ltx-2": "In hall,"}
        for model, marker in formats.items():
            with self.subTest(model=model):
                output = run(data, model)
                self.assertEqual(output["validation"]["status"], "PASS", output["validation"]["issues"])
                prompt = output["prompts"][0]["prompt"]
                self.assertIn(marker, prompt)
                self.assertLess(prompt.index(expected[0]), prompt.index(expected[1]))

    def test_model_duration_profiles(self):
        data = load("01-person-and-object.json")
        data["scene"]["duration"] = 7
        expected = {"seedance-2": 7, "veo-3.1": 8, "kling-3": 7, "wan-2.6": 10, "ltx-2": 7}
        for model, duration in expected.items():
            with self.subTest(model=model):
                self.assertEqual(run(data, model)["prompts"][0]["duration"], duration)

    def test_veo_reference_capability_is_checked(self):
        data = load("10-reference-previs.json")
        output = run(data, "veo-3.1")
        self.assertEqual(output["validation"]["status"], "FAIL")
        self.assertIn("REFERENCE_UNSUPPORTED", [x["code"] for x in output["validation"]["issues"]])
        data["references"][1]["generation_input"] = False
        output = run(data, "veo-3.1")
        self.assertEqual(output["validation"]["status"], "PASS", output["validation"]["issues"])
        self.assertEqual(output["prompts"][0]["duration"], 8)
        self.assertNotIn("Reference video", output["prompts"][0]["prompt"])

    def test_reference_roles_map_to_selected_generator(self):
        data = load("10-reference-previs.json")
        expected = {"seedance-2": ("@Image1", "@Video1"),
                    "kling-3": ("@Ref1", "@Ref2"),
                    "wan-2.6": ("Image 1", "Video 1")}
        for model, labels in expected.items():
            with self.subTest(model=model):
                output = run(data, model)
                self.assertEqual(output["validation"]["status"], "PASS", output["validation"]["issues"])
                prompt = output["prompts"][0]["prompt"]
                self.assertIn(labels[0], prompt)
                self.assertIn(labels[1], prompt)
                self.assertIn("character identity and clothing", prompt)
                self.assertIn("blocking, movement path and timing", prompt)

    def test_planning_only_reference_is_not_sent_to_h3(self):
        data = load("01-person-and-object.json")
        data["references"] = [{"id": "previs", "kind": "video", "label": "<Video 1>",
                               "role": "blocking", "generation_input": False,
                               "description": "offline previs"}]
        output = run(data)
        self.assertEqual(output["validation"]["status"], "PASS", output["validation"]["issues"])
        self.assertIn("integrated_multimodal_description:", output["prompts"][0]["prompt"])
        self.assertNotIn("<Video 1>", output["prompts"][0]["prompt"])

    def test_endpoint_frame_cannot_span_split_clips(self):
        data = load("09-timing-split.json")
        data["references"] = [{"id": "frame", "kind": "image", "label": "<Picture 1>",
                               "role": "first frame", "description": "opening frame"}]
        data["h3_mode"] = "I2VA"
        output = run(data)
        self.assertEqual(output["validation"]["status"], "FAIL")
        self.assertIn("global first/last frame", output["validation"]["issues"][-1]["message"])

    def test_cli_project_folder_creation_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "scene-project"
            cmd = [sys.executable, str(ROOT / "scene_pipeline.py"), str(ROOT / "examples" / "03-handoff.json"),
                   "--model", "kling-3", "--project-dir", str(project)]
            first = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertTrue((project / "scene-plan.json").exists())
            self.assertTrue((project / "validation.json").exists())
            self.assertTrue((project / "prompts" / "clip-01.txt").exists())
            manifest = json.loads((project / "project.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["model"], "kling-3")
            second = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(second.returncode, 2)
            self.assertIn("already exists", second.stderr)


if __name__ == "__main__":
    unittest.main()
