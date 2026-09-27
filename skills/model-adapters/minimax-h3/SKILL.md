---
name: minimax-h3-adapter
description: Compile an approved ScenePlan into MiniMax H3 T2VA, keyframe, or Ref2VA prompt structure while preserving staging and event order.
---

# MiniMax H3 Adapter

Use only after `scene_pipeline.py` returns `PASS`. H3 accepts 4–15 second clips. Set `h3_mode` to T2VA, I2VA, FL2VA, L2VA or Ref2VA from the supplied assets. Run `python scene_pipeline.py PLAN --model minimax-h3`; each returned clip is an independent generation prompt. For T2VA and keyframe modes it emits `integrated_multimodal_description`, `overall_soundscape`, `non_diegetic_music`; for Ref2VA it emits `subject_definitions`, `summary`, `retention_analysis`, `detailed_description`, `overall_soundscape`, `non_diegetic_music`.

Use stable `<Picture N>`, `<Video N>`, `<Audio N>` labels in `references[].label` and a precise role such as identity, environment, blocking, camera path or timing. Set `generation_input: false` for a previs consulted during planning but not attached to H3; it will not appear as a generation reference. For first/last frames, align the supplied pictures with the beginning/end of a single clip. Ref2VA reference video may carry blocking and choreography; a character image carries identity unless specified otherwise. Keep the user's dialogue and visible text in their original language.

If the prompt needs a changed position, order, interaction or camera path, repair ScenePlan first. The adapter cannot direct the scene. See [official H3 prompt skill](https://github.com/MiniMax-AI/MiniMax-H3/blob/main/skills/h3-prompt-writing/SKILL.md) and its base/ref guides for current format details; check those sources again before changing model constraints.
