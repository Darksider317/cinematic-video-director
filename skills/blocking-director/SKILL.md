---
name: blocking-director
description: Establish stable ground-plane positions, interaction paths, barriers, screen geography, and camera visibility for a video ScenePlan.
---

# Blocking Director

Build a simple top view. Put characters, props, obstacles and camera in one coordinate system. Record positions in `initial_world_state.entities`, object radius and `occludes`/`blocks_movement` when relevant, explicit move paths, `blocking.description`, and constraints in `blocking.constraints`.

Use relations where they matter: `left_of`, `right_of`, `in_front_of`, `behind`, `between`, `near`, `far`, `facing`, `holding`, `visible_to`, `occluded_from`. A barrier that is meant to separate subjects needs a checked `between` relation. Put a camera position in the same geometry and verify the key action is visible. A camera change uses a `camera` action with a `camera_move` effect containing `path` and `to`, or a separate clip; screen-direction changes must be explained by that change.

Coordinates are a validation aid, not a claim of exact photogrammetry. Occlusion uses circular 2D footprints and is conservative. For complex 3D occlusion or perspective, inspect previs or reference frames and add a human review note.
