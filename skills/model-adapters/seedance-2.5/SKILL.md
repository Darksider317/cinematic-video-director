---
name: seedance-2-5-adapter
description: Adapt an approved ScenePlan for Seedance 2.5 video generation with a 30-second timeline and explicit multimodal reference roles. Use when the selected generator is Seedance 2.5, not Seedance 2.0.
---

# Seedance 2.5 Adapter

Run `python scene_pipeline.py PLAN --model seedance-2.5` after the scene has passed validation. This profile plans one generated clip from 4 to 30 seconds. It preserves every approved action in chronological, timestamped beats and names the opening subjects, camera, sound, style and continuity. A scene longer than 30 seconds is split upstream into clips.

Ask which service will receive the prompt when its reference tag syntax or settings are needed. For the ModelArk playground, upload generation references in their ScenePlan order. The compiler maps them by type to `@Image1`, `@Video1` and `@Audio1`. Each reference needs a precise `role` such as identity, movement, blocking, camera, voice or music. A reference used only for planning gets `generation_input: false`; its observations belong in the approved ScenePlan and it is omitted from the prompt.

The generation input budget is 30 images, 10 videos and 10 audio files, with 50 assets total. Video references together may cover at most 30 seconds, and audio references together may cover at most 30 seconds. Record `duration` for video and audio references so the validator can check those budgets. Do not infer a missing asset's duration. The target service may impose further limits.

This adapter formats **new video generation from text and references**. Editing an existing video, extending it, and first/last-frame generation use different task roles and sometimes locked aspect ratio or duration. Do not present this compiler's generated prompt or duration as a ready-to-send request for those tasks. Obtain the source assets and task type, then apply the service's task-specific rules.

The Seedance 2.5 duration and reference budget come from the [official prompt guide](https://docs.volcengine.com/docs/ark/seedance-2-5-prompt-guide?lang=zh) and [video task API](https://docs.volcengine.com/docs/ark/create-video-generation-task-api?lang=zh). BytePlus also publishes its own `sd25-pe` prompting skill in the [Seedance 2.5 tutorial](https://docs.byteplus.com/en/docs/ModelArk/2607688). This adapter keeps the universal scene-state validation before model-specific formatting.
