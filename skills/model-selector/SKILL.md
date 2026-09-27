---
name: video-model-selector
description: Choose the target video generator and exact supported version before planning or adapting a validated AI video prompt.
---

# Video Model Selector

If the user named no video generator, ask one concise question: which generator should receive the prompt? Offer the supported choices MiniMax H3, Seedance 2, Veo 3.1, Kling 3, Wan 2.6, LTX 2, or generic. Do not silently default to H3. If the user says any model, use `generic` and state that it has no vendor-specific syntax. If they name a broader family with materially different versions, ask for the version; a clearly implied version can be recorded as an explicit assumption.

Write one of `minimax-h3`, `seedance-2`, `veo-3.1`, `kling-3`, `wan-2.6`, `ltx-2`, `generic` to `ScenePlan.model`. Select timing constraints and reference semantics for that model before compiling. If the user requests an unimplemented model, use a generic prompt only with that limitation stated; never label generic output as a verified model adapter.
