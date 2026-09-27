---
name: shot-timeline-planner
description: Allocate plausible action durations and split overloaded AI video scenes into generation clips without losing events.
---

# Shot and Timeline Planner

Assign each action a plausible `min_duration` in seconds. The pipeline allocates remaining requested time evenly, preserves action order, and greedily splits clips at the selected model's limit. The duration profile for H3, Seedance 2, Veo 3.1, Kling 3, Wan 2.6, LTX 2 or generic comes from `ScenePlan.model`; fixed-length models pad the final state to a valid clip duration. A `TIMING` issue reports when the requested duration cannot contain all actions; it is nonfatal only when the output explicitly splits or extends.

Review the planned `timeline` for visual legibility, geography changes, interaction complexity and multiple independent action centers. Split further upstream when one clip is still too complicated, and keep continuity constraints across the boundary. Never compress away the user's required action or transfer the staging decision to the adapter.
