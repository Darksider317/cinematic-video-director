---
name: generic-video-adapter
description: Express an approved and validated ScenePlan as model-neutral video prompts without changing scene logic.
---

# Generic Video Adapter

Use only after scene validation passes. Run `python scene_pipeline.py PLAN --model generic`. The output states setting, blocking, camera, timed events and continuity. Preserve the approved action descriptions and their order. If the generic prompt omits an essential spatial relation, add it to `blocking.description` or `continuity_constraints` and rerun validation; do not invent it here.
