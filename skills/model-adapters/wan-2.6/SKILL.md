---
name: wan-2-6-adapter
description: Adapt an approved video ScenePlan for Alibaba Wan 2.6 using explicit characters, sequential motion, camera, audio and Image/Video references.
---

# Wan 2.6 Adapter

Run `python scene_pipeline.py PLAN --model wan-2.6`. The prompt follows character, action, scene and optional speech/sound structure. References become `Image N` or `Video N` in upload order. Keep action order and interaction targets from ScenePlan; do not let prompt extension invent events. The conservative profile pads clips to 5, 10 or 15 seconds. Wan deployments and variants differ, so verify the target endpoint before submitting generation parameters. See [Alibaba's video prompt guide](https://www.alibabacloud.com/help/en/model-studio/text-to-video-prompt) and [model specifications](https://www.alibabacloud.com/help/en/model-studio/use-video-generation/).
