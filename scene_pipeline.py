"""Deterministic scene-state checks and prompt compilation for Agent Skills.

The agent interprets prose into a ScenePlan. This module never guesses missing
events or changes a scene to make a prompt easier to generate.
"""

from __future__ import annotations

import argparse
import copy
import json
import math
import sys
from pathlib import Path


INTERACTION_KINDS = {"interact", "transfer", "state_change"}
H3_MODES = {"T2VA", "I2VA", "FL2VA", "L2VA", "Ref2VA"}
MODEL_PROFILES = {
    "minimax-h3": {"min": 4, "max": 15, "allowed": None},
    "seedance-2": {"min": 2, "max": 15, "allowed": None},
    "veo-3.1": {"min": 4, "max": 8, "allowed": (4, 6, 8)},
    "kling-3": {"min": 3, "max": 15, "allowed": None},
    "wan-2.6": {"min": 5, "max": 15, "allowed": (5, 10, 15)},
    "ltx-2": {"min": 0, "max": 20, "allowed": None},
    "generic": {"min": 0, "max": 15, "allowed": None},
}


def reference_kind(ref):
    """Classify a declared asset without interpreting its visual contents."""
    if ref.get("kind") in {"image", "video", "audio"}:
        return ref["kind"]
    label = ref.get("label", "").lower()
    if label.startswith(("<picture ", "@image", "image ")):
        return "image"
    if label.startswith(("<video ", "@video", "video ")):
        return "video"
    if label.startswith(("<audio ", "@audio", "audio ")):
        return "audio"
    suffix = Path(ref.get("path", "")).suffix.lower()
    if suffix in {".png", ".jpg", ".jpeg", ".webp", ".heic"}:
        return "image"
    if suffix in {".mp4", ".mov", ".webm"}:
        return "video"
    if suffix in {".wav", ".mp3", ".m4a"}:
        return "audio"
    return "unknown"


def is_endpoint_frame(ref):
    role = ref.get("role", "").lower()
    return reference_kind(ref) == "image" and ("first frame" in role or "last frame" in role)


def issue(code, message, stage, severity="major", action=None):
    return {"code": code, "message": message, "stage": stage,
            "severity": severity, "action": action, "recommended_fix": fix_for(code)}


def fix_for(code):
    fixes = {
        "TELEPORT": "Add an explicit movement action with a traversable path.",
        "OWNERSHIP": "Add a reachable transfer action from the current holder.",
        "UNREACHABLE": "Move the actor within reach before interaction.",
        "PRECONDITION": "Add the prerequisite action or correct the initial state.",
        "CONTRADICTION": "Choose one state value and show the action that changes it.",
        "OCCLUSION": "Change verified blocking or camera position before adaptation.",
        "OBSTACLE": "Route movement around the obstacle or declare a world rule.",
        "TIMING": "Split into clips or increase duration without dropping events.",
        "AMBIGUITY": "Resolve the actor, target, direction or event order in ScenePlan.",
        "PROMPT_DRIFT": "Regenerate the prompt from the approved ScenePlan.",
        "MODEL_REQUIRED": "Ask which video generator and version the prompt targets.",
        "REFERENCE_UNSUPPORTED": "Use the reference for planning only or choose a model mode that accepts it.",
        "REFERENCE_SCOPE": "Provide endpoint frames for each clip or fit the action into one generation clip.",
    }
    return fixes.get(code, "Repair the indicated stage and validate again.")


def distance(a, b):
    return math.dist(a[:2], b[:2])


def near(a, b, reach=1.5):
    return distance(a, b) <= reach + 1e-9


def segment_distance(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    t = max(0, min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) /
                    (dx * dx + dy * dy))) if dx * dx + dy * dy else 0
    return distance(p, [a[0] + t * dx, a[1] + t * dy])


def blocked(a, b, entities, ignore=()):
    for entity_id, item in entities.items():
        if entity_id in ignore or not item.get("occludes", False):
            continue
        p = item["position"]
        if distance(p, a) < 1e-6 or distance(p, b) < 1e-6:
            continue
        if segment_distance(p, a, b) <= item.get("radius", 0.35):
            return entity_id
    return None


def barrier_between(a, b, entities, ignore=()):
    for entity_id, item in entities.items():
        if entity_id in ignore or not item.get("blocks_movement", False):
            continue
        if segment_distance(item["position"], a, b) <= item.get("radius", 0.35):
            return entity_id
    return None


def check_relation(constraint, entities):
    relation = constraint["relation"]
    a = entities[constraint["subject"]]
    b = entities[constraint["target"]]
    p, q = a["position"], b["position"]
    if relation == "near":
        return near(p, q, constraint.get("distance", 1.5))
    if relation == "far":
        return not near(p, q, constraint.get("distance", 1.5))
    if relation == "left_of":
        return p[0] < q[0]
    if relation == "right_of":
        return p[0] > q[0]
    if relation == "in_front_of":
        return p[1] < q[1]
    if relation == "behind":
        return p[1] > q[1]
    if relation == "between":
        c = entities[constraint["other"]]["position"]
        return segment_distance(p, q, c) <= constraint.get("tolerance", 0.5) and distance(q, c) >= max(distance(q, p), distance(c, p))
    if relation in {"visible_to", "occluded_from"}:
        blocker = blocked(p, q, entities, (constraint["subject"], constraint["target"]))
        return (blocker is None) if relation == "visible_to" else (blocker is not None)
    if relation == "facing":
        vector = a.get("facing", [0, 0])
        direction = [q[0] - p[0], q[1] - p[1]]
        return vector[0] * direction[0] + vector[1] * direction[1] > 0
    if relation == "holding":
        return b.get("held_by") == constraint["subject"]
    raise ValueError(f"Unsupported relation: {relation}")


def validate(plan):
    problems = []
    required = ("idea", "scene", "characters", "objects", "initial_world_state", "actions", "blocking", "camera", "references")
    for key in required:
        if key not in plan:
            problems.append(issue("SCHEMA", f"Missing {key}", "scene-interpreter", "critical"))
    if problems:
        return result(problems)
    entities = copy.deepcopy(plan["initial_world_state"]["entities"])
    ids = [item["id"] for item in plan["characters"] + plan["objects"]]
    if len(ids) != len(set(ids)) or set(ids) != set(entities):
        problems.append(issue("SCHEMA", "Entity IDs must be unique and match initial world state", "scene-interpreter", "critical"))
        return result(problems)
    for entity_id, item in entities.items():
        if not isinstance(item.get("position"), list) or len(item["position"]) != 2:
            problems.append(issue("SCHEMA", f"{entity_id} needs a 2D position", "scene-interpreter", "critical"))
    if problems:
        return result(problems)
    if not isinstance(plan.get("idea"), str) or not plan["idea"].strip():
        problems.append(issue("SCHEMA", "Original idea is empty", "scene-interpreter"))
    if not plan["actions"]:
        problems.append(issue("SCHEMA", "At least one observable action is required", "scene-interpreter"))
    model = plan.get("model")
    if model not in MODEL_PROFILES:
        problems.append(issue("MODEL_REQUIRED", f"Choose a supported video generator; received {model!r}", "scene-interpreter"))
        return result(problems)
    if model not in {"minimax-h3", "generic"}:
        for ref in plan["references"]:
            if reference_kind(ref) == "unknown":
                problems.append(issue("AMBIGUITY", f"Reference {ref['id']} needs kind: image, video or audio", "scene-interpreter"))
    if model == "minimax-h3":
        generation_refs = [ref for ref in plan["references"] if ref.get("generation_input", True)]
        mode = plan.get("h3_mode", "Ref2VA" if generation_refs else "T2VA")
        labels = [ref.get("label") for ref in generation_refs]
        if mode not in H3_MODES:
            problems.append(issue("SCHEMA", f"Unknown H3 mode {mode}", "scene-interpreter"))
        if mode == "Ref2VA" and not generation_refs:
            problems.append(issue("AMBIGUITY", "Ref2VA requires a named reference", "scene-interpreter"))
        if mode in {"I2VA", "FL2VA", "L2VA"} and not any(label == "<Picture 1>" for label in labels):
            problems.append(issue("AMBIGUITY", "Keyframe mode requires <Picture 1>", "scene-interpreter"))
        if mode == "FL2VA" and "<Picture 2>" not in labels:
            problems.append(issue("AMBIGUITY", "FL2VA requires <Picture 2>", "scene-interpreter"))
        if len(labels) != len(set(labels)) or any(not label for label in labels):
            problems.append(issue("AMBIGUITY", "Reference labels must be present and unique", "scene-interpreter"))
        if mode == "T2VA" and generation_refs:
            problems.append(issue("AMBIGUITY", "T2VA cannot use supplied media references; select a reference mode", "scene-interpreter"))
        if mode != "Ref2VA" and any(label and (label.startswith("<Video ") or label.startswith("<Audio ")) for label in labels):
            problems.append(issue("AMBIGUITY", "Video/audio references require Ref2VA", "scene-interpreter"))
        if mode == "Ref2VA":
            counts = {prefix: sum(bool(label and label.startswith(f"<{prefix} ")) for label in labels) for prefix in ("Picture", "Video", "Audio")}
            if counts["Picture"] > 9 or counts["Video"] > 3 or counts["Audio"] > 3 or len(labels) > 12:
                problems.append(issue("SCHEMA", "Ref2VA exceeds official reference count limits", "scene-interpreter"))
            for ref in generation_refs:
                if ref.get("label", "").startswith(("<Video ", "<Audio ")) and "duration" in ref and not 2 <= float(ref["duration"]) <= 15:
                    problems.append(issue("SCHEMA", f"Reference {ref['id']} must last 2–15 seconds", "scene-interpreter"))
            for prefix in ("<Video ", "<Audio "):
                total = sum(float(ref.get("duration", 0)) for ref in generation_refs if ref.get("label", "").startswith(prefix))
                if total > 15:
                    problems.append(issue("SCHEMA", f"Total {prefix[1:-1].lower()} reference time exceeds 15 seconds", "scene-interpreter"))
    elif model in {"veo-3.1", "ltx-2"}:
        for ref in plan["references"]:
            kind = reference_kind(ref)
            if ref.get("generation_input", True) and kind in {"video", "audio"}:
                problems.append(issue("REFERENCE_UNSUPPORTED", f"{model} adapter cannot attach {kind} {ref['id']} as a free-form generation reference", "model-adapter"))
        if model == "veo-3.1" and sum(reference_kind(ref) == "image" and ref.get("generation_input", True) for ref in plan["references"]) > 3:
            problems.append(issue("REFERENCE_UNSUPPORTED", "Veo 3.1 accepts at most three generation reference images", "model-adapter"))
    camera_state = copy.deepcopy(plan["camera"].get("position"))
    states = [{"after": "initial", "entities": copy.deepcopy(entities), "camera_position": copy.deepcopy(camera_state)}]
    action_ids = set()
    world_rules = set(plan.get("world_rules", []))
    for index, action in enumerate(plan["actions"]):
        action_id = action.get("id", f"action-{index + 1}")
        if action_id in action_ids:
            problems.append(issue("SCHEMA", f"Duplicate action ID {action_id}", "scene-interpreter", action=action_id))
        action_ids.add(action_id)
        actor = action.get("actor")
        target = action.get("target")
        kind = action.get("kind")
        if actor not in entities or (target is not None and target not in entities):
            problems.append(issue("AMBIGUITY", "Actor or target is unresolved", "scene-interpreter", action=action_id))
            continue
        if not action.get("description") or not kind:
            problems.append(issue("AMBIGUITY", "Action needs an observable description and kind", "scene-interpreter", action=action_id))
            continue
        required_effect = {"move": ("move", actor), "transfer": ("transfer", target),
                           "state_change": ("set", target), "camera": ("camera_move", None)}.get(kind)
        if required_effect and not any(e.get("type") == required_effect[0] and
                                       (required_effect[1] is None or e.get("entity") == required_effect[1])
                                       for e in action.get("effects", [])):
            problems.append(issue("PRECONDITION", f"{kind} action needs its explicit consequence", "scene-logic-engine", action=action_id))
        if action.get("fantasy_rule") and action["fantasy_rule"] not in world_rules:
            problems.append(issue("PRECONDITION", "Fantasy exception lacks an explicit world rule", "scene-logic-engine", action=action_id))
        if kind in INTERACTION_KINDS:
            if target is None:
                problems.append(issue("AMBIGUITY", "Interaction target is missing", "scene-interpreter", action=action_id))
            elif not near(entities[actor]["position"], entities[target]["position"], action.get("reach", 1.5)) and not action.get("fantasy_rule"):
                problems.append(issue("UNREACHABLE", f"{actor} cannot reach {target}", "scene-logic-engine", action=action_id))
            elif target is not None and not action.get("fantasy_rule"):
                barrier = barrier_between(entities[actor]["position"], entities[target]["position"], entities, (actor, target))
                if barrier:
                    problems.append(issue("UNREACHABLE", f"{barrier} blocks interaction with {target}", "scene-logic-engine", action=action_id))
        for pre in action.get("preconditions", []):
            try:
                if not check_precondition(pre, entities):
                    problems.append(issue("PRECONDITION", f"Failed prerequisite: {pre}", "scene-logic-engine", action=action_id))
            except (KeyError, ValueError) as exc:
                problems.append(issue("SCHEMA", f"Invalid prerequisite: {exc}", "scene-interpreter", action=action_id))
        before = copy.deepcopy(entities)
        for effect in action.get("effects", []):
            try:
                if effect.get("type") == "camera_move":
                    path = effect.get("path", [])
                    if action.get("kind") != "camera" or len(path) < 2 or path[0] != camera_state or path[-1] != effect.get("to"):
                        problems.append(issue("TELEPORT", "Camera movement needs an explicit path from current camera position", "blocking-director", action=action_id))
                    else:
                        camera_state = effect["to"]
                else:
                    apply_effect(effect, action, entities, problems, world_rules)
            except (KeyError, ValueError, TypeError) as exc:
                problems.append(issue("SCHEMA", f"Invalid effect: {exc}", "scene-interpreter", action=action_id))
        for entity_id in entities:
            prior, current = before[entity_id], entities[entity_id]
            moved_explicitly = any(e.get("entity") == entity_id and e.get("type") in {"move", "transfer"} for e in action.get("effects", []))
            moved_with_holder = prior.get("held_by") and any(e.get("type") == "move" and e.get("entity") == prior.get("held_by") for e in action.get("effects", []))
            if prior["position"] != current["position"] and not moved_explicitly and not moved_with_holder:
                problems.append(issue("TELEPORT", f"{entity_id} changed position without movement", "continuity-validator", action=action_id))
            if prior.get("held_by") != current.get("held_by") and not any(e.get("type") == "transfer" and e.get("entity") == entity_id for e in action.get("effects", [])):
                problems.append(issue("OWNERSHIP", f"{entity_id} changed holder without transfer", "continuity-validator", action=action_id))
        states.append({"after": action_id, "entities": copy.deepcopy(entities), "camera_position": copy.deepcopy(camera_state)})
    for relation in plan["blocking"].get("constraints", []):
        try:
            at = relation.get("at", "initial")
            state = next((s for s in states if s["after"] == at), None)
            if state is None:
                raise ValueError(f"unknown state {at}")
            if not check_relation(relation, state["entities"]):
                problems.append(issue("OCCLUSION" if relation["relation"] in {"visible_to", "occluded_from"} else "BLOCKING",
                                      f"Spatial constraint fails: {relation}", "blocking-director"))
        except (KeyError, ValueError) as exc:
            problems.append(issue("SCHEMA", f"Invalid spatial relation: {exc}", "blocking-director"))
    camera = plan["camera"]
    if camera.get("position") is not None:
        for action in plan["actions"]:
            if not action.get("must_be_visible", True):
                continue
            focus = action.get("target") or action.get("actor")
            state = next((s for s in states if s["after"] == action.get("id")), None)
            if state and focus in state["entities"]:
                blocker = blocked(state["camera_position"], state["entities"][focus]["position"], state["entities"], (focus,))
                if blocker:
                    problems.append(issue("OCCLUSION", f"Camera view of {focus} blocked by {blocker}", "blocking-director", action=action["id"]))
    timeline, timing_issues = plan_timeline(plan)
    problems.extend(timing_issues)
    if len(timeline) > 1 and any(is_endpoint_frame(ref) and ref.get("generation_input", True) for ref in plan["references"]):
        problems.append(issue("REFERENCE_SCOPE", "A global first/last frame cannot anchor multiple generation clips", "shot-timeline-planner"))
    output = result(problems)
    output["world_states"] = states
    output["timeline"] = timeline
    return output


def check_precondition(pre, entities):
    kind = pre["type"]
    a = entities[pre["entity"]]
    if kind == "attribute":
        return a.get("attributes", {}).get(pre["key"]) == pre["value"]
    if kind == "held_by":
        return a.get("held_by") == pre.get("holder")
    if kind == "near":
        return near(a["position"], entities[pre["target"]]["position"], pre.get("reach", 1.5))
    if kind == "not_occluded":
        b = entities[pre["target"]]
        return blocked(a["position"], b["position"], entities, (pre["entity"], pre["target"])) is None
    if kind == "pose":
        return a.get("pose") == pre["value"]
    raise ValueError(f"Unsupported precondition {kind}")


def apply_effect(effect, action, entities, problems, world_rules):
    kind = effect["type"]
    entity_id = effect["entity"]
    item = entities[entity_id]
    action_id = action["id"]
    if kind == "move":
        path = effect.get("path", [])
        if len(path) < 2 or path[0] != item["position"] or path[-1] != effect.get("to"):
            problems.append(issue("TELEPORT", "Movement needs a path from current to destination", "scene-logic-engine", action=action_id))
            return
        if action.get("kind") != "move" and not (action.get("kind") == "interact" and action.get("target") == entity_id) and not action.get("fantasy_rule"):
            problems.append(issue("TELEPORT", "Position changed without a movement action", "scene-logic-engine", action=action_id))
        for a, b in zip(path, path[1:]):
            for other_id, other in entities.items():
                if other_id == entity_id or not other.get("blocks_movement"):
                    continue
                if segment_distance(other["position"], a, b) <= other.get("radius", 0.35) and not action.get("fantasy_rule"):
                    problems.append(issue("OBSTACLE", f"Path crosses {other_id}", "scene-logic-engine", action=action_id))
        max_speed = item.get("max_speed")
        if max_speed and sum(distance(a, b) for a, b in zip(path, path[1:])) > max_speed * float(action.get("min_duration", 1)) and not action.get("fantasy_rule"):
            problems.append(issue("TIMING", f"{entity_id} path exceeds declared maximum speed", "shot-timeline-planner", action=action_id))
        delta = [effect["to"][i] - item["position"][i] for i in range(2)]
        item["position"] = effect["to"]
        item["facing"] = effect.get("facing", delta)
        for held in entities.values():
            if held.get("held_by") == entity_id:
                held["position"] = effect["to"]
    elif kind == "transfer":
        previous = item.get("held_by")
        recipient = effect.get("to")
        if recipient is not None and recipient not in entities:
            raise ValueError(f"Unknown holder {recipient}")
        if previous != effect.get("from"):
            problems.append(issue("OWNERSHIP", f"{entity_id} is held by {previous}, not {effect.get('from')}", "scene-logic-engine", action=action_id))
        if recipient and not near(item["position"], entities[recipient]["position"], action.get("reach", 1.5)) and not action.get("fantasy_rule"):
            problems.append(issue("UNREACHABLE", f"{recipient} cannot receive {entity_id}", "scene-logic-engine", action=action_id))
        item["held_by"] = recipient
        if recipient:
            item["position"] = entities[recipient]["position"]
    elif kind == "set":
        key, value = effect["key"], effect["value"]
        if key in {"position", "held_by"}:
            problems.append(issue("TELEPORT" if key == "position" else "OWNERSHIP", f"Use move/transfer for {key}", "scene-logic-engine", action=action_id))
        elif key in {"facing", "pose"}:
            item[key] = value
        else:
            if isinstance(value, list) and len(value) > 1:
                problems.append(issue("CONTRADICTION", f"Multiple values for {entity_id}.{key}", "scene-logic-engine", action=action_id))
            item.setdefault("attributes", {})[key] = value
    else:
        raise ValueError(f"Unsupported effect {kind}")


def plan_timeline(plan):
    actions = plan["actions"]
    requested = float(plan["scene"].get("duration", 8))
    minimum = sum(float(a.get("min_duration", 1)) for a in actions)
    issues = []
    if minimum > requested + 1e-9:
        issues.append(issue("TIMING", f"Minimum action time {minimum:g}s exceeds requested {requested:g}s; split and extend", "shot-timeline-planner", "minor"))
    total = max(minimum, requested)
    spare = max(0, total - minimum)
    durations = [float(a.get("min_duration", 1)) + spare / len(actions) for a in actions] if actions else []
    model = plan["model"]
    profile = MODEL_PROFILES[model]
    max_clip = min(profile["max"], float(plan["scene"].get("max_clip_duration", profile["max"])))
    clips, current, elapsed = [], [], 0.0
    for action, duration in zip(actions, durations):
        if duration > max_clip:
            issues.append(issue("TIMING", f"Action {action['id']} exceeds model clip limit", "shot-timeline-planner"))
        if current and elapsed + duration > max_clip:
            clips.append(current)
            current, elapsed = [], 0.0
        current.append((action, duration))
        elapsed += duration
    if current:
        clips.append(current)
    timeline = []
    for clip_index, clip in enumerate(clips, 1):
        cursor = 0.0
        beats = []
        for action, duration in clip:
            beats.append({"action_id": action["id"], "start": round(cursor, 2), "end": round(cursor + duration, 2)})
            cursor += duration
        if profile["allowed"]:
            valid_lengths = [n for n in profile["allowed"] if n >= cursor - 1e-9]
            if model == "veo-3.1" and any(reference_kind(r) == "image" and r.get("generation_input", True) for r in plan["references"]):
                valid_lengths = [n for n in valid_lengths if n == 8]
            effective = valid_lengths[0] if valid_lengths else math.ceil(cursor)
        elif profile["min"]:
            effective = max(profile["min"], math.ceil(cursor - 1e-9))
        else:
            effective = round(cursor, 2)
        if effective > max_clip:
            issues.append(issue("TIMING", f"Clip {clip_index} exceeds model limit", "shot-timeline-planner"))
        timeline.append({"clip": clip_index, "duration": effective, "beats": beats})
    return timeline, issues


def result(problems):
    fatal = [p for p in problems if p["severity"] in {"major", "critical"}]
    return {"status": "FAIL" if fatal else "PASS", "severity": "critical" if any(p["severity"] == "critical" for p in problems) else "major" if fatal else "minor" if problems else "none", "issues": problems}


def reference_summary(plan, model):
    refs = [ref for ref in plan["references"] if ref.get("generation_input", True)]
    numbers = {"image": 0, "video": 0, "audio": 0}
    labels = []
    for ref in refs:
        kind = reference_kind(ref)
        numbers[kind] += 1
        n = numbers[kind]
        if model == "seedance-2":
            label = f"@{kind.title()}{n}"
        elif model == "wan-2.6":
            label = f"{kind.title()} {n}"
        elif model == "kling-3":
            label = f"@Ref{len(labels) + 1}"
        elif model == "veo-3.1":
            label = f"Reference image {n}"
        else:
            label = f"reference {kind} {n}"
        labels.append(f"{label}: {ref.get('description', ref['id'])} ({ref['role']})")
    return "; ".join(labels)


def render_other_model(plan, model, clip, opening, camera, continuity, beat_lines):
    """Format the same approved beats for a selected generator."""
    setting = plan["scene"].get("location", "unspecified location")
    style = plan["scene"].get("style", "")
    refs = reference_summary(plan, model)
    sound = plan.get("soundscape", "")
    music = plan.get("music", "")
    sequence = " ".join(beat_lines)
    if model == "seedance-2":
        return "\n".join(filter(None, [
            f"Scene: {setting}. {opening}",
            f"Reference assets: {refs}." if refs else "",
            f"Action sequence: {sequence}",
            f"Camera: {camera}.",
            f"Audio: {sound}" if sound else "",
            f"Music: {music}" if music else "",
            f"Style: {style}." if style else "",
            f"Continuity: {continuity}",
        ]))
    if model == "veo-3.1":
        return "\n".join(filter(None, [
            f"A {clip['duration']}-second video in {setting}. {opening}",
            f"Use the supplied images only for their declared roles: {refs}." if refs else "",
            f"The action unfolds in this order: {sequence}",
            f"Camera: {camera}.",
            f"Sound: {sound}" if sound else "",
            f"Music: {music}" if music else "",
            f"Visual style: {style}." if style else "",
            f"Keep continuity: {continuity}",
        ]))
    if model == "kling-3":
        return "\n".join(filter(None, [
            f"Single continuous shot, {clip['duration']} seconds. {setting}. {opening}",
            f"Bound elements: {refs}." if refs else "",
            f"Choreography: {sequence}",
            f"Camera movement and framing: {camera}.",
            f"Native audio: {sound}" if sound else "",
            f"Music: {music}" if music else "",
            f"Style: {style}." if style else "",
            f"Continuity: {continuity}",
        ]))
    if model == "wan-2.6":
        return "\n".join(filter(None, [
            f"Characters and scene: {opening} Location: {setting}.",
            f"References: {refs}." if refs else "",
            f"Actions: {sequence}",
            f"Camera: {camera}.",
            f"Sound: {sound}" if sound else "",
            f"Background music: {music}" if music else "",
            f"Style: {style}." if style else "",
            f"Continuity: {continuity}",
        ]))
    if model == "ltx-2":
        natural_opening = opening.replace("Subjects: ", "").replace("Opening geography: ", "")
        parts = [f"{style.rstrip(' .')}." if style else "", f"In {setting}, {natural_opening}",
                 f"Use {refs}." if refs else "", sequence, f"{camera}." if camera else "",
                 f"The soundscape is {sound.rstrip(' .')}." if sound else "",
                 f"Music: {music}." if music else "", continuity]
        return " ".join(part for part in parts if part)
    raise ValueError(f"Unknown adapter {model}")


def compile_prompts(plan, validation, model=None):
    if validation["status"] != "PASS":
        raise ValueError("Scene validation failed; no final prompt may be emitted")
    model = model or plan["model"]
    actions = {a["id"]: a for a in plan["actions"]}
    labels = {r["id"]: r.get("label", r["id"]) for r in plan["references"]}
    prompts = []
    cast = "; ".join(f"{e['id']}: {e['description']}" for e in plan["characters"] + plan["objects"])
    relation_text = "; ".join(f"{c['subject']} {c['relation'].replace('_', ' ')} {c['target']}" +
                              (f" and {c['other']}" if c.get("other") else "")
                              for c in plan["blocking"].get("constraints", []) if c.get("at", "initial") == "initial")
    for clip in validation["timeline"]:
        beat_lines = [f"At {b['start']:.2f}-{b['end']:.2f}s, {actions[b['action_id']]['description'].rstrip(' .')}." for b in clip["beats"]]
        if clip["beats"] and clip["duration"] > clip["beats"][-1]["end"] + 1e-9:
            beat_lines.append(f"Hold the final visible state until {clip['duration']:.2f}s.")
        opening = " ".join(filter(None, [plan["blocking"].get("description", ""), f"Subjects: {cast}." if cast else "", f"Opening geography: {relation_text}." if relation_text else ""]))
        camera = plan["camera"].get("description", "").rstrip(" .")
        continuity = " ".join(plan.get("continuity_constraints", []))
        if model == "generic":
            body = "\n".join([f"Scene: {plan['scene'].get('location', 'unspecified')}. {opening}",
                              f"Camera: {camera}", *beat_lines, f"Continuity: {continuity}"])
        elif model in {"seedance-2", "veo-3.1", "kling-3", "wan-2.6", "ltx-2"}:
            body = render_other_model(plan, model, clip, opening, camera, continuity, beat_lines)
        elif model == "minimax-h3":
            generation_refs = [r for r in plan["references"] if r.get("generation_input", True)]
            mode = plan.get("h3_mode", "Ref2VA" if generation_refs else "T2VA")
            if mode not in H3_MODES:
                raise ValueError(f"Unsupported H3 mode {mode}")
            used_refs = "\n".join(f"{labels[r['id']]} is {r.get('description', r['id'])}; it supplies {r['role']}." for r in generation_refs)
            if mode == "Ref2VA":
                body = "\n".join([
                    f"subject_definitions:\n{used_refs}",
                    f"summary: [reference generation] {plan['scene'].get('summary', plan['idea'])}",
                    "retention_analysis:\n" + "\n".join(f"{labels[r['id']]} ([Shot 1]): fully_preserved - preserve its {r['role']} role." for r in generation_refs),
                    f"detailed_description: [Shot 1] {plan['scene'].get('location', '')}. {opening} Camera: {camera}. " + " ".join(beat_lines) + f" Reference roles: {', '.join(labels[r['id']] for r in generation_refs)}. Continuity: {continuity}",
                    f"overall_soundscape: {plan.get('soundscape', 'Natural sound of the visible actions only.')}",
                    f"non_diegetic_music: {plan.get('music', 'None.')}",
                ])
            else:
                prefix = ""
                if mode == "I2VA":
                    prefix = "For the target video, at 0.00 seconds into the target video, <Picture 1> (from [Shot 1]) is fully referenced.\n\n"
                elif mode == "FL2VA":
                    prefix = f"How the reference pictures align with the target video — Picture 1 (from Shot 1) aligns with the 0.00-second mark of the target video; Picture 2 (from Shot 1) aligns with the {clip['duration']:.2f}-second mark of the target video.\n\n"
                elif mode == "L2VA":
                    prefix = f"How the reference pictures align with the target video — <Picture 1> (from [Shot 1]) aligns with the {clip['duration']:.2f}-second mark of the target video.\n\n"
                body = prefix + "\n".join([
                    f"integrated_multimodal_description: [Shot 1] {plan['scene'].get('location', '')}. {opening} Camera: {camera}. " + " ".join(beat_lines) + f" Continuity: {continuity}",
                    f"overall_soundscape: {plan.get('soundscape', 'Natural sound of the visible actions only.')}",
                    f"non_diegetic_music: {plan.get('music', 'None.')}",
                ])
            if len(body) > 7000:
                raise ValueError("H3 prompt exceeds 7000 characters; split or simplify upstream")
        else:
            raise ValueError(f"Unknown adapter {model}")
        prompts.append({"clip": clip["clip"], "duration": clip["duration"], "prompt": body,
                        "action_ids": [b["action_id"] for b in clip["beats"]]})
    return prompts


def validate_prompts(plan, validation, prompts):
    problems = []
    canonical = compile_prompts(plan, validation, plan.get("model"))
    if len(prompts) != len(canonical) or any(a.get("prompt") != b["prompt"] for a, b in zip(prompts, canonical)):
        problems.append(issue("PROMPT_DRIFT", "Prompt text differs from the approved ScenePlan compilation", "prompt-validator"))
    expected = [a["id"] for a in plan["actions"]]
    actual = [action_id for clip in prompts for action_id in clip.get("action_ids", [])]
    if actual != expected:
        problems.append(issue("PROMPT_DRIFT", "Prompt action IDs differ from approved action order", "prompt-validator"))
    by_id = {a["id"]: a for a in plan["actions"]}
    for clip in prompts:
        cursor = 0
        for action_id in clip.get("action_ids", []):
            phrase = by_id.get(action_id, {}).get("description", "").rstrip(" .")
            location = clip["prompt"].find(phrase, cursor) if phrase else -1
            if location < 0:
                problems.append(issue("PROMPT_DRIFT", f"Missing or reordered action {action_id}", "prompt-validator", action=action_id))
            else:
                cursor = location + len(phrase)
        if plan.get("model", "minimax-h3") == "minimax-h3" and len(clip["prompt"]) > 7000:
            problems.append(issue("PROMPT_DRIFT", "H3 prompt exceeds length limit", "prompt-validator"))
    return result(problems)


def run(plan, model=None):
    if model:
        plan = copy.deepcopy(plan)
        plan["model"] = model
    validation = validate(plan)
    if validation["status"] != "PASS":
        return {"validation": validation, "prompts": []}
    try:
        prompts = compile_prompts(plan, validation, model)
    except ValueError as exc:
        validation["status"] = "FAIL"
        validation["issues"].append(issue("PROMPT_DRIFT", str(exc), "model-adapter"))
        return {"validation": validation, "prompts": []}
    final = validate_prompts(plan, validation, prompts)
    if final["status"] != "PASS":
        validation["status"] = "FAIL"
        validation["issues"].extend(final["issues"])
        return {"validation": validation, "prompts": []}
    return {"validation": validation, "prompts": prompts}


def save_project(project_dir, plan, output, model):
    """Create a reviewable project package without overwriting existing files."""
    prompts_dir = project_dir / "prompts"
    prompt_files = [prompts_dir / f"clip-{item['clip']:02d}.txt" for item in output["prompts"]]
    files = [project_dir / "scene-plan.json", project_dir / "validation.json", project_dir / "project.json", *prompt_files]
    existing = [path for path in files if path.exists()]
    if existing:
        raise FileExistsError(f"Project output already exists: {existing[0]}")
    project_dir.mkdir(parents=True, exist_ok=True)
    if prompt_files:
        prompts_dir.mkdir(exist_ok=True)
    (project_dir / "scene-plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (project_dir / "validation.json").write_text(json.dumps(output["validation"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    manifest = {"model": model, "status": output["validation"]["status"],
                "references": [{"id": r["id"], "kind": reference_kind(r), "role": r["role"],
                                "generation_input": r.get("generation_input", True), "path": r.get("path")}
                               for r in plan.get("references", [])],
                "prompts": [str(path.relative_to(project_dir)).replace("\\", "/") for path in prompt_files]}
    (project_dir / "project.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for path, item in zip(prompt_files, output["prompts"]):
        path.write_text(item["prompt"] + "\n", encoding="utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Validate a ScenePlan and compile video prompts")
    parser.add_argument("plan", type=Path)
    parser.add_argument("--model", choices=list(MODEL_PROFILES))
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--project-dir", type=Path, help="Save plan, validation and clip prompts in this project folder")
    args = parser.parse_args(argv)
    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    output = run(plan, args.model)
    if args.project_dir:
        try:
            save_project(args.project_dir, {**plan, "model": args.model or plan.get("model")}, output, args.model or plan.get("model"))
        except (FileExistsError, OSError) as exc:
            parser.exit(2, f"Project folder error: {exc}\n")
    if args.output:
        args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.debug or output["validation"]["status"] != "PASS":
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        print("\n\n".join(item["prompt"] for item in output["prompts"]))
    return 0 if output["validation"]["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
