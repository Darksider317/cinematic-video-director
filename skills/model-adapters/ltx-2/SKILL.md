---
name: ltx-2-adapter
description: Adapt an approved video ScenePlan for LTX 2 as a concise chronological natural-language prompt with integrated visual and audio cues.
---

# LTX 2 Adapter

Run `python scene_pipeline.py PLAN --model ltx-2`. The output is one natural-language paragraph per clip: setting, anchored subjects, observable motion in order, camera and sound. A generation image can anchor appearance or the first frame; arbitrary video/audio references are planning-only unless the user chooses LTX's separate extend, retake or audio-to-video workflow. The T2V profile caps a clip at 20 seconds. See [LTX API capabilities](https://docs.ltx.io/welcome) and the [official LTX 2 repository](https://github.com/Lightricks/LTX-2).
