# Universal Video Scene Validation Pipeline

This repository contains a reusable Agent Skill and specialist skills for turning an AI video idea into an explicitly staged and validated prompt. The executable validator and prompt compiler are in `scene_pipeline.py`; the skill instructions tell an agent how to interpret free text and repair its plan. The deterministic code does not pretend to understand arbitrary prose or inspect media by itself.

## Pipeline

`idea → interpretation → world-state simulation → blocking → continuity → timeline and clip split → model adapter → final prompt check`

The agent writes a `ScenePlan` JSON using `schemas/scene-plan.schema.json`. All positions share a ground-plane coordinate system in metres. Each action has an actor, optional target, prerequisites, minimum duration and explicit effects. The validator computes a world state after each action, tests reachability and movement paths, checks selected spatial relations and camera occlusion, and plans clips. A failed plan cannot produce a final prompt. The adapter only formats an approved plan.

## Use

Ask an agent to use `$cinematic-video-director` with a scene idea. If you have not named the target video generator, the skill asks which one to use. For direct CLI use after creating a plan:

```powershell
python scene_pipeline.py examples/01-person-and-object.json
python scene_pipeline.py examples/01-person-and-object.json --debug --output result.json
python scene_pipeline.py examples/01-person-and-object.json --model generic
python scene_pipeline.py examples/01-person-and-object.json --model veo-3.1
python scene_pipeline.py examples/01-person-and-object.json --model kling-3 --project-dir projects/my-scene
```

The default output contains only generation prompts. `--debug` includes world states, issues and timeline. An exit code of 1 means the plan or prompt failed; do not use the prompt. Repair at the named stage and rerun, at most three cycles. `strict_validation` and `creative_freedom` are agent-level choices: strict favors simpler blocking, while creative freedom may change style and camera only after the event remains intact.

`--project-dir PATH` saves `scene-plan.json`, `validation.json`, `project.json`, and one `prompts/clip-XX.txt` per passing clip. It creates the folder when absent and refuses to overwrite existing outputs. Without this option, no project folder is created. The skill asks for a destination if saved project files are needed but the user has not given one. Original reference media is never copied; `project.json` records its path and whether it is a generation input or planning-only reference.

## References

Give each reference an ID, `kind` (`image`, `video`, `audio`), role and optional H3 label such as `<Picture 1>` or `<Video 1>`. A character image should constrain appearance and identity. A Blender previs or reference video can constrain blocking, character path, camera path and timing; inspect it before encoding those facts. A first/last frame anchors the endpoint, not the entire choreography. Never silently treat an appearance image as a motion reference. Set `generation_input: false` for a reference used to build the ScenePlan but not attached to the generator.

## Adapters

The `model` field is required. Supported values are `minimax-h3`, `seedance-2`, `veo-3.1`, `kling-3`, `wan-2.6`, `ltx-2`, and `generic`. H3 supports T2VA, I2VA, FL2VA, L2VA and Ref2VA structures, 4–15 second clips and a conservative 7000-character prompt guard. Seedance 2 uses 2–15 second clips and `@Image`/`@Video` reference labels. Veo 3.1 uses 4, 6 or 8 seconds, with 8 seconds for generation reference images; it accepts up to three images. Kling 3 uses 3–15 seconds and bound elements. Wan 2.6 conservatively uses 5, 10 or 15 seconds. LTX 2 uses up to 20 seconds for text-to-video. `generic` remains model-neutral. Model versions and provider variants differ; adapters produce prompts and planning durations, not ready-to-send API requests.

To add another adapter, add a `MODEL_PROFILES` entry, implement a formatting branch in `render_other_model` or `compile_prompts`, create an adapter `SKILL.md`, and add a test showing preserved action order and reference roles. The adapter must not modify the approved ScenePlan.

## Tests and examples

`python -m unittest discover -s tests -v` runs the fixture suite. Eight valid examples cover object use, conversation, handoff, room traversal, obstacle routing, vehicle movement, animal behavior and fantasy action. Invalid fixtures exercise missing causes, impossible interaction, ownership, contradictory states, timing and occlusion. The test suite checks real state changes and compiler output, not merely the presence of text files.

## Open-source research

- [MiniMax official H3 prompt skill](https://github.com/MiniMax-AI/MiniMax-H3/blob/main/skills/h3-prompt-writing/SKILL.md) and [base](https://github.com/MiniMax-AI/MiniMax-H3/blob/main/skills/h3-prompt-writing/references/base-en.txt)/[reference](https://github.com/MiniMax-AI/MiniMax-H3/blob/main/skills/h3-prompt-writing/references/ref-en.txt) guides informed H3 field order, reference labels and duration handling.
- [Cinematic Director](https://github.com/cajias/agentic-video-skills/blob/master/plugins/cinematic-director/skills/cinematic-director/SKILL.md) informed continuity anchors and shot planning.
- [Video Storyboard](https://github.com/agentara/skills/blob/main/skills/aigc/video-storyboard/SKILL.md) informed reference role and storyboard continuity checks.
- Model profiles and prompting conventions were checked against official [Seedance 2](https://docs.byteplus.com/en/docs/byteplus_las/video_gen_enhanced), [Veo 3.1](https://ai.google.dev/gemini-api/docs/veo), [Kling 3](https://kling.ai/quickstart/klingai-video-3-model-user-guide), [Wan](https://www.alibabacloud.com/help/en/model-studio/text-to-video-prompt), and [LTX](https://docs.ltx.io/welcome) documentation.

Their prompt and storyboard guidance is useful after the scene is resolved. This pipeline adds a separate executable state-transition gate before adaptation. No source skill code is copied.

## Limits

The validator uses a 2D ground plane, circular obstacle footprints and explicit plan facts. It cannot infer actor intent from raw text, guarantee real-world physics, prove semantic equivalence of rewritten prose or inspect video frames automatically. The agent must review ambiguous meaning and complex 3D blocking. Tests validate planning and prompt compilation; they do not generate or assess actual model video.
