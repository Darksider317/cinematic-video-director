---
name: kling-3-adapter
description: Adapt an approved video ScenePlan for Kling 3 using stable element bindings, timed choreography, camera and native audio instructions.
---

# Kling 3 Adapter

Run `python scene_pipeline.py PLAN --model kling-3`. The output describes a single continuous shot per generation clip so Kling's optional automatic multi-shot mode does not replan approved blocking. It maps supplied generation references to stable `@RefN` element names; bind them in the interface before generating. State actor, recipient, movement and camera in order, with audio only when declared. The profile uses 3–15 second clips. For a deliberate multi-shot generation, plan each shot and its duration upstream, then use Kling's custom multi-shot interface rather than delegating shot order to the model. See [Kling 3 guide](https://kling.ai/quickstart/klingai-video-3-model-user-guide) and [API capability map](https://kling.ai/document-api/guides/capability-map/video).
