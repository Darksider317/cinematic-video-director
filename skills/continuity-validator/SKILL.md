---
name: continuity-validator
description: Check video ScenePlan world states for stable character, object, environment, temporal, and ownership continuity.
---

# Continuity Validator

Compare each computed state against the prior one. Every position change needs movement, every holder change a transfer, every open/closed or on/off change a causal set effect. Keep identity, appearance, wardrobe, damage, door state, lighting and geography fixed unless an action changes them. A required event must occur after its prerequisites.

Review both deterministic issues in `validation.issues` and semantic continuity that coordinates cannot decide, including identity drift, gaze and camera-axis shifts. Write important invariants in `continuity_constraints` for the model adapter to carry through. If a constraint fails, repair the earlier plan and rerun validation.
