"""Create varied example plans; scenarios live only in fixtures, never in runtime rules."""

import copy
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"


def entity(position, **extra):
    return {"position": position, "facing": [1, 0], "pose": "standing", "attributes": {}, **extra}


def action(id, actor, kind, description, target=None, effects=None, preconditions=None, min_duration=1, **extra):
    value = {"id": id, "actor": actor, "kind": kind, "description": description,
             "min_duration": min_duration, "effects": effects or [], "preconditions": preconditions or [], **extra}
    if target:
        value["target"] = target
    return value


DESCRIPTIONS = {
    "woman": "woman in a pale blue shirt", "cup": "ceramic cup on the counter",
    "ada": "Ada, seated on the left", "bo": "Bo, seated on the right", "table": "small café table",
    "a": "person A", "b": "person B", "key": "small metal key", "door": "wooden hinged door",
    "crate": "large wooden crate", "package": "sealed cardboard package", "car": "red compact car",
    "sign": "roadside sign", "dog": "golden dog", "ball": "red rubber ball",
    "mage": "robed mage", "stone": "loose stone on the ground",
}


def plan(name, location, duration, characters, objects, states, actions, camera=(0, -4), blocking="A stable wide view of the scene.", constraints=None, references=None):
    return {"idea": name, "model": "minimax-h3", "scene": {"location": location, "duration": duration, "summary": name},
            "characters": [{"id": x, "description": DESCRIPTIONS.get(x, x)} for x in characters],
            "objects": [{"id": x, "description": DESCRIPTIONS.get(x, x)} for x in objects],
            "initial_world_state": {"entities": states}, "actions": actions,
            "blocking": {"description": blocking, "constraints": constraints or []},
            "camera": {"position": list(camera), "description": "Locked wide shot from the near side."},
            "references": references or [], "continuity_constraints": ["Keep identities, geography and prop ownership stable."]}


def build():
    valid = {}
    valid["01-person-and-object"] = plan("A woman picks up a cup", "kitchen", 6, ["woman"], ["cup"],
        {"woman": entity([0, 0]), "cup": entity([1, 0], held_by=None)},
        [action("notice", "woman", "observe", "The woman notices the cup", "cup"),
         action("pickup", "woman", "transfer", "The woman reaches for and lifts the cup with her right hand", "cup", [{"type": "transfer", "entity": "cup", "from": None, "to": "woman"}], [{"type": "held_by", "entity": "cup", "holder": None}])],
        constraints=[{"relation": "right_of", "subject": "cup", "target": "woman"}])
    valid["02-conversation"] = plan("Two people talk across a table", "quiet café", 7, ["ada", "bo"], ["table"],
        {"ada": entity([-1, 0], facing=[1, 0]), "bo": entity([1, 0], facing=[-1, 0]), "table": entity([0, 0], radius=0.3)},
        [action("line-1", "ada", "observe", "Ada speaks while facing Bo", "bo", min_duration=2),
         action("line-2", "bo", "observe", "Bo listens then answers Ada", "ada", min_duration=2)],
        constraints=[{"relation": "between", "subject": "table", "target": "ada", "other": "bo"},
                     {"relation": "facing", "subject": "ada", "target": "bo"}])
    valid["03-handoff"] = plan("A gives B a key", "hall", 6, ["a", "b"], ["key"],
        {"a": entity([0, 0]), "b": entity([1, 0], facing=[-1, 0]), "key": entity([0, 0], held_by="a")},
        [action("offer", "a", "observe", "A extends the key toward B", "b"),
         action("handoff", "a", "transfer", "B takes the key from A's hand", "key", [{"type": "transfer", "entity": "key", "from": "a", "to": "b"}], [{"type": "held_by", "entity": "key", "holder": "a"}])])
    valid["04-room-traversal"] = plan("A opens a door and enters", "room entrance", 8, ["a"], ["door"],
        {"a": entity([0, 0]), "door": entity([2, 0], attributes={"open": False})},
        [action("approach", "a", "move", "A walks to the near side of the door", effects=[{"type": "move", "entity": "a", "path": [[0, 0], [1, 0]], "to": [1, 0]}]),
         action("open", "a", "state_change", "A turns the handle and opens the door", "door", [{"type": "set", "entity": "door", "key": "open", "value": True}], [{"type": "attribute", "entity": "door", "key": "open", "value": False}]),
         action("cross", "a", "move", "A walks through the open doorway into the room", effects=[{"type": "move", "entity": "a", "path": [[1, 0], [2, 0], [3, 0]], "to": [3, 0]}], preconditions=[{"type": "attribute", "entity": "door", "key": "open", "value": True}])])
    valid["05-obstacle"] = plan("A walks around a crate to a package", "warehouse", 9, ["a"], ["crate", "package"],
        {"a": entity([0, 0]), "crate": entity([2, 0], blocks_movement=True, radius=0.4), "package": entity([4, 0], held_by=None)},
        [action("route", "a", "move", "A walks around the far side of the crate to the package", effects=[{"type": "move", "entity": "a", "path": [[0, 0], [1, 1.2], [3, 1.2], [4, 0]], "to": [4, 0]}], min_duration=3),
         action("collect", "a", "transfer", "A picks up the package", "package", [{"type": "transfer", "entity": "package", "from": None, "to": "a"}])],
        camera=(0, -4), blocking="The crate remains between the starting point and the package.",
        constraints=[{"relation": "between", "subject": "crate", "target": "a", "other": "package"}])
    valid["06-vehicle"] = plan("A car drives from left to right", "empty road", 6, ["car"], ["sign"],
        {"car": entity([-3, 0]), "sign": entity([3, 1])},
        [action("drive", "car", "move", "The car drives steadily from screen left to screen right past the sign", effects=[{"type": "move", "entity": "car", "path": [[-3, 0], [0, 0], [3, 0]], "to": [3, 0]}], min_duration=4)],
        constraints=[{"relation": "left_of", "subject": "car", "target": "sign"}])
    valid["07-animal"] = plan("A dog noses a ball", "garden", 5, ["dog"], ["ball"],
        {"dog": entity([0, 0]), "ball": entity([1, 0])},
        [action("sniff", "dog", "interact", "The dog leans in and sniffs the ball", "ball"),
         action("nudge", "dog", "interact", "The dog nudges the ball with its nose", "ball", [{"type": "move", "entity": "ball", "path": [[1, 0], [1.5, 0]], "to": [1.5, 0]}])])
    valid["08-fantasy"] = plan("A mage levitates a stone", "courtyard", 6, ["mage"], ["stone"],
        {"mage": entity([0, 0]), "stone": entity([4, 0])},
        [action("levitate", "mage", "supernatural", "The mage raises one hand and the distant stone levitates straight up", "stone", [{"type": "move", "entity": "stone", "path": [[4, 0], [4, 2]], "to": [4, 2]}], fantasy_rule="telekinesis")])
    valid["08-fantasy"]["world_rules"] = ["telekinesis"]
    valid["08-fantasy"]["camera"]["position"] = [0, -4]
    valid["10-reference-previs"] = copy.deepcopy(valid["05-obstacle"])
    valid["10-reference-previs"]["idea"] = "Use the supplied Blender previs for the route around a crate"
    valid["10-reference-previs"]["scene"]["summary"] = valid["10-reference-previs"]["idea"]
    valid["10-reference-previs"]["h3_mode"] = "Ref2VA"
    valid["10-reference-previs"]["references"] = [
        {"id": "portrait", "label": "<Picture 1>", "role": "character identity and clothing", "description": "the supplied portrait of A"},
        {"id": "previs", "label": "<Video 1>", "role": "blocking, movement path and timing", "description": "the supplied Blender previs"},
    ]

    invalid = {}
    bad = copy.deepcopy(valid["01-person-and-object"])
    bad["actions"].append(action("jump", "woman", "move", "The woman appears across the room", effects=[{"type": "set", "entity": "woman", "key": "position", "value": [5, 0]}]))
    invalid["teleport"] = bad
    bad = copy.deepcopy(valid["03-handoff"])
    bad["actions"][1]["effects"][0]["from"] = "b"
    invalid["ownership"] = bad
    bad = copy.deepcopy(valid["01-person-and-object"])
    bad["initial_world_state"]["entities"]["cup"]["position"] = [6, 0]
    invalid["unreachable"] = bad
    bad = copy.deepcopy(valid["04-room-traversal"])
    bad["actions"][1]["effects"][0]["value"] = ["open", "closed"]
    invalid["contradiction"] = bad
    bad = copy.deepcopy(valid["04-room-traversal"])
    bad["actions"] = [bad["actions"][2]]
    invalid["missing-prerequisite"] = bad
    bad = copy.deepcopy(valid["05-obstacle"])
    bad["actions"][0]["effects"][0]["path"] = [[0, 0], [4, 0]]
    invalid["obstacle-crossing"] = bad
    bad = copy.deepcopy(valid["02-conversation"])
    bad["initial_world_state"]["entities"]["table"]["occludes"] = True
    bad["initial_world_state"]["entities"]["table"]["radius"] = 0.8
    bad["camera"]["position"] = [-2, 0]
    invalid["occlusion"] = bad
    overloaded = copy.deepcopy(valid["01-person-and-object"])
    overloaded["scene"]["duration"] = 3
    overloaded["actions"] = [action(f"beat-{n}", "woman", "observe", f"The woman performs visible beat {n}", min_duration=1) for n in range(20)]
    valid["09-timing-split"] = overloaded

    EXAMPLES.mkdir(exist_ok=True)
    (EXAMPLES / "invalid").mkdir(exist_ok=True)
    for name, data in valid.items():
        (EXAMPLES / f"{name}.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for name, data in invalid.items():
        (EXAMPLES / "invalid" / f"{name}.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    build()
