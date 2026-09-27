---
name: scene-interpreter
description: Convert a free-form AI video idea into a structured ScenePlan with stable entities, atomic actions, references, and unresolved questions.
---

# Scene Interpreter

Record the user's idea verbatim. Extract characters, objects, location, requested duration, style, camera instructions, and any reference image/video roles. Create stable IDs; use explicit actor and target IDs in every action. Separate observable action beats at each causal dependency: reaching a prop before taking it, taking it before using it, opening a barrier before crossing it.

Use [ScenePlan schema](../../schemas/scene-plan.schema.json). Record the chosen `model`; do not infer H3 as a default. State coordinates in metres with x increasing screen right and y increasing away from a fixed ground-plan origin. Make only small, documented defaults for missing staging. If the subject, target, or outcome could change meaning, flag it for the user instead of guessing. Give each reference a `kind`, `role` and `generation_input` value. Put `h3_mode` in the plan only for H3 after classifying references as first frame, last frame or full reference.

Do not write final prompt prose or add decorative actions. Produce a plan for the logic engine.
