---
name: cinematic-video-director
description: Turn an AI video idea into a spatially consistent, validated ScenePlan and model-ready prompts. Use for video scene prompting, blocking, continuity, and MiniMax H3 or generic video generation.
---

# Cinematic Video Director

Take the user's original idea through the stages below. Never jump from idea to model prompt. Keep an approved ScenePlan as the source of truth; the model adapter may only express it.

1. Read [scene-interpreter](skills/scene-interpreter/SKILL.md) and create a JSON plan matching [the schema](schemas/scene-plan.schema.json). Preserve the original idea verbatim in `idea` and give every entity and action a stable ID.
2. Read [scene-logic-engine](skills/scene-logic-engine/SKILL.md), [blocking-director](skills/blocking-director/SKILL.md), and [continuity-validator](skills/continuity-validator/SKILL.md). Resolve preconditions, paths, transfers, barriers, camera and reference roles before rendering.
3. Read [shot-timeline-planner](skills/shot-timeline-planner/SKILL.md). Use minimum durations grounded in observable motion. A requested duration may be extended only through an explicit split; do not remove required events.
4. Run `python scene_pipeline.py path/to/plan.json --debug --output path/to/result.json`. A `FAIL` prohibits final prompt delivery. Repair the indicated earlier stage and rerun, at most three iterations. If it still fails, report the concrete blocker; do not quietly rewrite the user's event.
5. On `PASS`, use the requested adapter: [MiniMax H3](skills/model-adapters/minimax-h3/SKILL.md) or [generic](skills/model-adapters/generic/SKILL.md). The script compiles the prompts from the approved plan and runs [final prompt validation](skills/prompt-validator/SKILL.md).

The CLI's default output is just copyable prompts. Use `--debug` only when the user asks for a report or when repairing. Return only the final prompts by default. If a scene splits, return one prompt per clip in order. Never claim a generated video was tested when only the planning pipeline was tested.

Priority: original intent; physical and causal consistency; continuity; clear staging; model reliability; cinematography; decoration. Ask the user only when an unresolved choice changes the event's meaning. Reasonable geometry and camera defaults are permitted if recorded in the plan.

For reference video or Blender previs, treat documented blocking, timing and camera paths as stronger spatial evidence than a textual guess. Assign each reference a distinct role. An image used for identity does not supply movement unless the user says so. Inspect a reference before claiming facts from it; an uninspected file remains a declared reference, not an observed scene fact.

Run `python -m unittest discover -s tests -v` to verify code changes. See [README](README.md) for use and adapter extension.
