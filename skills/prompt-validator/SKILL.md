---
name: prompt-validator
description: Verify that an adapted video prompt preserves the approved ScenePlan events, order, roles, and model limits before delivery.
---

# Final Prompt Validator

Compare original idea, approved ScenePlan, computed states, and each candidate prompt. The executable validator checks exact action coverage and order, canonical compiler output, prompt length, and the prior plan's causal and spatial validation status. Independently review semantic fidelity: actor and recipient, result, camera geometry, reference roles, and continuity wording. Exact string coverage cannot prove that prose is semantically correct.

A `FAIL` forbids delivery as final. Send the issue to the stage named in `validation.issues`, repair that artifact, then rerun. Cap repair at three loops. If unresolved, give the user the blocker and a concrete choice.
