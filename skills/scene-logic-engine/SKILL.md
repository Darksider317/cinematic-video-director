---
name: scene-logic-engine
description: Simulate AI video scene actions as preconditions and state changes; find impossible interactions, missing causes, and unexplained motion.
---

# Scene Logic Engine

For each action, name the actor, target, kind, observable description, prerequisites, minimum duration and explicit effects. Supported effects are `move` with full `path` and `to`, `transfer` with `from` and `to`, and `set` for pose, facing or an attribute. The validator computes a World State after each action. Never set `position` or `held_by` through `set`.

Interactions require reachable actor and target. Object pickup and handoff require a transfer effect that names the prior holder, including `null` for an unheld object. A held object follows its holder's movement. A state change needs an observable causal action. Check `preconditions` for attribute, pose, holder, near and unobstructed access.

If the user explicitly requests impossible physics, declare a named `world_rules` entry and attach it as `fantasy_rule` to the relevant action. The exception applies only to that action; later consequences still need explicit transitions. Use `python scene_pipeline.py PLAN --debug` to inspect computed states and repair failures before blocking or adaptation.
