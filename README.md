# Universal Video Scene Validation Pipeline

This repository contains a reusable Agent Skill and seven specialist skills for turning an AI video idea into an explicitly staged and validated prompt. The executable validator and prompt compiler are in `scene_pipeline.py`; the skill instructions tell an agent how to interpret free text and repair its plan. The deterministic code does not pretend to understand arbitrary prose or inspect media by itself.

## Pipeline

`idea → interpretation → world-state simulation → blocking → continuity → timeline and clip split → model adapter → final prompt check`

The agent writes a `ScenePlan` JSON using `schemas/scene-plan.schema.json`. All positions share a ground-plane coordinate system in metres. Each action has an actor, optional target, prerequisites, minimum duration and explicit effects. The validator computes a world state after each action, tests reachability and movement paths, checks selected spatial relations and camera occlusion, and plans clips. A failed plan cannot produce a final prompt. The adapter only formats an approved plan.

## Use

Ask an agent to use `$cinematic-video-director` with a scene idea. For direct CLI use after creating a plan:

```powershell
python scene_pipeline.py examples/01-person-and-object.json
python scene_pipeline.py examples/01-person-and-object.json --debug --output result.json
python scene_pipeline.py examples/01-person-and-object.json --model generic
```

The default output contains only generation prompts. `--debug` includes world states, issues and timeline. An exit code of 1 means the plan or prompt failed; do not use the prompt. Repair at the named stage and rerun, at most three cycles. `strict_validation` and `creative_freedom` are agent-level choices: strict favors simpler blocking, while creative freedom may change style and camera only after the event remains intact.

## References

Give each reference an ID, role and optional H3 label such as `<Picture 1>` or `<Video 1>`. A character image should constrain appearance and identity. A Blender previs or reference video can constrain blocking, character path, camera path and timing; inspect it before encoding those facts. A first/last frame anchors the endpoint, not the entire choreography. Never silently treat an appearance image as a motion reference.

## Adapters

`minimax-h3` supports T2VA, I2VA, FL2VA, L2VA and Ref2VA structures, 4–15 second clips and a 7000-character prompt limit. `generic` provides a model-neutral output for testing. To add another adapter, implement a formatting branch in `compile_prompts`, add model constraints in `plan_timeline`, create an adapter `SKILL.md`, then add a fixture test showing preserved action order and roles. The adapter must not modify the approved ScenePlan.

## Tests and examples

`python -m unittest discover -s tests -v` runs the fixture suite. Eight valid examples cover object use, conversation, handoff, room traversal, obstacle routing, vehicle movement, animal behavior and fantasy action. Invalid fixtures exercise missing causes, impossible interaction, ownership, contradictory states, timing and occlusion. The test suite checks real state changes and compiler output, not merely the presence of text files.

## Open-source research

- [MiniMax official H3 prompt skill](https://github.com/MiniMax-AI/MiniMax-H3/blob/main/skills/h3-prompt-writing/SKILL.md) and [base](https://github.com/MiniMax-AI/MiniMax-H3/blob/main/skills/h3-prompt-writing/references/base-en.txt)/[reference](https://github.com/MiniMax-AI/MiniMax-H3/blob/main/skills/h3-prompt-writing/references/ref-en.txt) guides informed H3 field order, reference labels and duration handling.
- [Cinematic Director](https://github.com/cajias/agentic-video-skills/blob/master/plugins/cinematic-director/skills/cinematic-director/SKILL.md) informed continuity anchors and shot planning.
- [Video Storyboard](https://github.com/agentara/skills/blob/main/skills/aigc/video-storyboard/SKILL.md) informed reference role and storyboard continuity checks.

Their prompt and storyboard guidance is useful after the scene is resolved. This pipeline adds a separate executable state-transition gate before adaptation. No source skill code is copied.

## Limits

The validator uses a 2D ground plane, circular obstacle footprints and explicit plan facts. It cannot infer actor intent from raw text, guarantee real-world physics, prove semantic equivalence of rewritten prose or inspect video frames automatically. The agent must review ambiguous meaning and complex 3D blocking. Tests validate planning and prompt compilation; they do not generate or assess actual H3 video.
