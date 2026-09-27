---
name: cinematic-video-director
description: Turn an AI video idea into a validated ScenePlan and prompts for MiniMax H3, Seedance 2, Veo 3.1, Kling 3, Wan 2.6, LTX 2 or a generic model. Ask which generator when unspecified and optionally save a project folder.
---

# Cinematic Video Director

Take the user's original idea through the stages below. Never jump from idea to model prompt. Keep an approved ScenePlan as the source of truth; the model adapter may only express it.

1. Read [model-selector](skills/model-selector/SKILL.md). Ask which generator the prompt is for when the user has not specified one. Record an exact `model` in the ScenePlan before timing or adaptation.
2. Read [project-workspace](skills/project-workspace/SKILL.md). Create a project folder only when the user wants saved files or the task needs a reusable multi-clip package. Ask for a destination when it matters and none was given. Otherwise deliver the prompt inline without creating a folder.
3. Read [scene-interpreter](skills/scene-interpreter/SKILL.md) and create a JSON plan matching [the schema](schemas/scene-plan.schema.json). Preserve the original idea verbatim in `idea` and give every entity and action a stable ID.
4. Read [scene-logic-engine](skills/scene-logic-engine/SKILL.md), [blocking-director](skills/blocking-director/SKILL.md), and [continuity-validator](skills/continuity-validator/SKILL.md). Resolve preconditions, paths, transfers, barriers, camera and reference roles before rendering.
5. Read [shot-timeline-planner](skills/shot-timeline-planner/SKILL.md). Use minimum durations grounded in observable motion. A requested duration may be extended only through an explicit split; do not remove required events.
6. Run `python scene_pipeline.py path/to/plan.json --debug --output path/to/result.json`. Add `--project-dir PATH` only when the user wants a saved project. A `FAIL` prohibits final prompt delivery. Repair the indicated earlier stage and rerun, at most three iterations. If it still fails, report the concrete blocker; do not quietly rewrite the user's event.
7. On `PASS`, read the selected adapter: [H3](skills/model-adapters/minimax-h3/SKILL.md), [Seedance 2](skills/model-adapters/seedance-2/SKILL.md), [Veo 3.1](skills/model-adapters/veo-3.1/SKILL.md), [Kling 3](skills/model-adapters/kling-3/SKILL.md), [Wan 2.6](skills/model-adapters/wan-2.6/SKILL.md), [LTX 2](skills/model-adapters/ltx-2/SKILL.md), or [generic](skills/model-adapters/generic/SKILL.md). The compiler verifies the final prompt with [prompt-validator](skills/prompt-validator/SKILL.md). Never allow an adapter to change approved blocking or event order.

The CLI's default output is just copyable prompts. Use `--debug` only when the user asks for a report or when repairing. Return only the final prompts by default. If a scene splits, return one prompt per clip in order. Never claim a generated video was tested when only the planning pipeline was tested.

Priority: original intent; physical and causal consistency; continuity; clear staging; model reliability; cinematography; decoration. Ask the user only when an unresolved choice changes the event's meaning. Reasonable geometry and camera defaults are permitted if recorded in the plan.

For reference video or Blender previs, treat documented blocking, timing and camera paths as stronger spatial evidence than a textual guess. Assign each reference a distinct role. An image used for identity does not supply movement unless the user says so. Inspect a reference before claiming facts from it; an uninspected file remains a declared reference, not an observed scene fact.

Run `python -m unittest discover -s tests -v` to verify code changes. See [README](README.md) for use and adapter extension.
