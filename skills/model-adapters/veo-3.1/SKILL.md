---
name: veo-3-1-adapter
description: Adapt an approved video ScenePlan for Google Veo 3.1 with clear action order, camera and sound; check 4/6/8-second clips and image references.
---

# Veo 3.1 Adapter

Run `python scene_pipeline.py PLAN --model veo-3.1`. The prompt uses natural scene prose, explicit chronological beats, camera and audio. The planner pads clips to 4, 6 or 8 seconds; attached reference images use 8 seconds, with at most three images. Supply first and last frames separately in the Veo interface/API when their roles require it. The adapter rejects arbitrary video/audio files as generation references; use those for planning with `generation_input: false` or choose a supported extension workflow. See [official Veo documentation](https://ai.google.dev/gemini-api/docs/veo).
