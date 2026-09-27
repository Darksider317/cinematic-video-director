---
name: seedance-2-adapter
description: Adapt an approved video ScenePlan for Seedance 2 with timed actions, camera, audio and explicit @Image/@Video/@Audio reference roles.
---

# Seedance 2 Adapter

Run `python scene_pipeline.py PLAN --model seedance-2` after scene validation. This adapter uses explicit opening geography, chronological action beats, camera, continuity and any declared audio. It maps generation references to `@ImageN`, `@VideoN`, `@AudioN`; upload assets in the same order and keep image identity separate from video blocking. For a previs used only to infer blocking, set `generation_input: false` after its facts are encoded in ScenePlan. Supported profile: 2–15 second clips. Verify a specific provider or variant before making API parameter claims. See [BytePlus Seedance 2 guide](https://docs.byteplus.com/en/docs/modelark/2222480) and [enhanced video API](https://docs.byteplus.com/en/docs/byteplus_las/video_gen_enhanced).
