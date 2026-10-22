#!/usr/bin/env python3
"""Static flow check for the fire-safety lesson.

Unity cannot be run in this environment, so this script cross-checks the parts of the
lesson that are easiest to break by hand:

  * every event id used by an object in the scene is handled by LessonManager
  * every checkpoint id in the scene is handled by LessonManager
  * every stage constant declared by LessonManager is entered and handled
  * every LessonContent member referenced by the scripts actually exists

Exit code is non-zero when a check fails.
"""

from __future__ import annotations

import os
import re
import sys

import yaml

from unity_common import ROOT

SCENE = os.path.join(ROOT, "Assets", "Scenes", "FireSafetyTrainer.unity")
SCRIPTS = os.path.join(ROOT, "Assets", "Scripts")
MANAGER = os.path.join(SCRIPTS, "LessonManager.cs")
CONTENT = os.path.join(SCRIPTS, "LessonContent.cs")
UNITY_TAG = re.compile(r"^--- !u!(\d+) &(-?\d+).*$")
EVENT_FIELDS = ("eventId", "eventWhenOpened", "eventWhenClosed", "checkpointId")
EVENT_PREFIXES = ("pass_step_", "ext_card_")
# StageMenu is a sentinel: the menu draws itself, so it never needs a stage case.
SENTINEL_STAGES = {"StageMenu"}


def read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def scene_field_values():
    """Pull the lesson-related serialized strings out of the scene."""
    values = {}
    current_class = None
    for line in read(SCENE).split("\n"):
        match = UNITY_TAG.match(line)
        if match:
            current_class = int(match.group(1))
            continue
        if current_class != 114:
            continue
        field = re.match(r"^  (eventId|eventWhenOpened|eventWhenClosed|checkpointId):\s*(.*)$", line)
        if not field:
            continue
        name, value = field.group(1), field.group(2).strip()
        if value:
            values.setdefault(name, set()).add(value)
    return values


def handled_event_ids():
    text = read(MANAGER)
    ids = set(re.findall(r'case\s+"([^"]+)"\s*:', text))
    # ids sent from code as well as from the scene
    ids.update(re.findall(r'Notify\(\s*"([^"]+)"', text))
    for path in os.listdir(SCRIPTS):
        if path.endswith(".cs"):
            ids.update(re.findall(r'NotifyLesson\(\s*"([^"]+)"', read(os.path.join(SCRIPTS, path))))
            ids.update(re.findall(r'Notify\(\s*"([^"]+)"', read(os.path.join(SCRIPTS, path))))
    return ids


def check_events(problems):
    values = scene_field_values()
    handled = handled_event_ids()
    for field, ids in sorted(values.items()):
        for value in sorted(ids):
            if any(value.startswith(prefix) for prefix in EVENT_PREFIXES):
                continue
            if value not in handled:
                problems.append("scene %s=%r has no handler in LessonManager" % (field, value))
    return values, handled


def stage_constants():
    text = read(MANAGER)
    return sorted(set(re.findall(r"const\s+int\s+(Stage\w+)\s*=", text))), text


def check_stages(problems):
    constants, text = stage_constants()
    cases = set(re.findall(r"case\s+(Stage\w+)\s*:", text))
    gotos = set(re.findall(r"GoTo\(\s*(Stage\w+)\s*\)", text))
    # GoTo(newStage) also lands on a stage passed by another method; treat stage = X as entry
    assigned = set(re.findall(r"\bstage\s*=\s*(Stage\w+)", text))
    enters = gotos | assigned
    for name in constants:
        if name in SENTINEL_STAGES:
            continue
        if name not in cases:
            problems.append("stage constant %s has no case in the stage switch" % name)
        if name not in enters:
            problems.append("stage constant %s is never entered" % name)
    # a case that only contains itself as the entry means an unreachable state
    for name in sorted(gotos):
        if name not in constants:
            problems.append("GoTo(%s) uses an undeclared stage" % name)
    return constants


def check_content(problems):
    text = read(CONTENT)
    members = set()
    group = None
    for line in text.split("\n"):
        group_match = re.search(r"(?:static\s+class|class)\s+(Section\w+)", line)
        if group_match:
            group = group_match.group(1)
        member = re.search(r"public\s+const\s+string\s+(\w+)", line)
        if member and group:
            members.add("%s.%s" % (group, member.group(1)))
    # top-level members of LessonContent itself
    for name in re.findall(r"^\s{4}public\s+const\s+string\s+(\w+)", text, re.MULTILINE):
        members.add(name)

    used = set()
    for path in os.listdir(SCRIPTS):
        if not path.endswith(".cs"):
            continue
        used.update(re.findall(r"LessonContent\.(?:Section\w+\.)?(\w+)", read(os.path.join(SCRIPTS, path))))

    for name in sorted(used):
        if name in ("References", "Extinguishers", "ExtinguisherInfo", "Reference", "Section"):
            continue
        if "." not in name and name not in members and not name.startswith("Section"):
            # a nested reference such as SectionA.IntroBody arrives here as "IntroBody"
            continue
    referenced = set()
    for path in os.listdir(SCRIPTS):
        if not path.endswith(".cs"):
            continue
        referenced.update(re.findall(r"LessonContent\.(Section\w+\.\w+)", read(os.path.join(SCRIPTS, path))))
    for name in sorted(referenced):
        if name not in members:
            problems.append("LessonContent.%s is referenced but not defined" % name)
    return len(members), len(referenced)


# --------------------------------------------------------------------------- #
# Collider checks
# --------------------------------------------------------------------------- #

COLLIDER_CLASSES = {64, 65, 135, 136}          # Box, Sphere, Capsule, Mesh
INTERACTABLE_BASE = "InteractableBase"


def script_guids():
    """guid -> class name, for the project scripts only."""
    mapping = {}
    for path in sorted(os.listdir(SCRIPTS)):
        if not path.endswith(".cs"):
            continue
        meta = os.path.join(SCRIPTS, path + ".meta")
        if not os.path.exists(meta):
            continue
        guid = re.search(r"^guid:\s*([0-9a-f]{32})$", read(meta), re.MULTILINE)
        classes = re.findall(r"class\s+(\w+)\s*:", read(os.path.join(SCRIPTS, path)))
        if guid and classes:
            mapping[guid.group(1)] = classes[0]
    return mapping


def object_graph():
    """fileID -> (class id, parsed body) for every document in the scene."""
    parsed, current, buffer = {}, None, []
    for line in read(SCENE).split("\n"):
        match = UNITY_TAG.match(line)
        if match:
            if current:
                parsed[current[1]] = current[0], buffer
            current, buffer = (int(match.group(1)), int(match.group(2))), []
        elif current is not None:
            buffer.append(line)
    if current:
        parsed[current[1]] = current[0], buffer

    result = {}
    for file_id, (class_id, lines) in parsed.items():
        try:
            body = yaml.safe_load("\n".join(lines))
        except yaml.YAMLError:
            body = None
        if isinstance(body, dict) and len(body) == 1:
            body = next(iter(body.values()))
        result[file_id] = (class_id, body)
    return result


def check_colliders(problems):
    parsed = object_graph()
    guids = script_guids()

    game_objects, transforms, children, components = {}, {}, {}, {}
    for file_id, (class_id, body) in parsed.items():
        if not isinstance(body, dict):
            continue
        if class_id == 1:
            game_objects[file_id] = body
            continue
        if class_id in (4, 224):
            transforms[file_id] = body
            go = (body.get("m_GameObject") or {}).get("fileID")
            for child in body.get("m_Children") or []:
                children.setdefault(go, []).append(child.get("fileID"))
            continue
        go = (body.get("m_GameObject") or {}).get("fileID")
        if go:
            components.setdefault(go, []).append((class_id, body))

    def has_collider(go_id, depth=0):
        for class_id, _ in components.get(go_id, []):
            if class_id in COLLIDER_CLASSES:
                return True
        if depth > 4:
            return False
        for child in children.get(go_id, []):
            child_go = (transforms.get(child, {}).get("m_GameObject") or {}).get("fileID")
            if child_go and has_collider(child_go, depth + 1):
                return True
        return False

    interactables = 0
    for go_id, comps in components.items():
        go = game_objects.get(go_id)
        if not go:
            continue
        name = go.get("m_Name", "?")
        class_names = []
        for class_id, body in comps:
            if class_id != 114:
                continue
            class_name = guids.get((body.get("m_Script") or {}).get("guid"))
            if class_name:
                class_names.append(class_name)

        for class_name in class_names:
            if class_name in ("SimpleInteractable", "AlarmController", "DoorController",
                              "ExtinguisherStation"):
                interactables += 1
                if not has_collider(go_id):
                    problems.append("interactable %r (%s) has no collider" % (name, class_name))
            if class_name in ("CheckpointTrigger", "HazardZone"):
                colliders = [body for class_id, body in components[go_id]
                             if class_id in COLLIDER_CLASSES]
                if not colliders:
                    problems.append("%s %r has no collider" % (class_name, name))
                for body in colliders:
                    if body.get("m_IsTrigger") != 1:
                        problems.append("%s %r is not a trigger" % (class_name, name))
    return interactables


REQUIRED_MANAGER_REFS = ("player", "alarm", "evacuation", "extinguisherStation", "fire", "phone",
                         "maskDisplay", "liftCall", "fireViewPoint", "storeDoor", "exitDoor",
                         "startPoint")


def check_manager_refs(problems):
    """The lesson is only as good as its wiring: no reference may be empty."""
    parsed = object_graph()
    for _, (class_id, body) in parsed.items():
        if class_id != 114 or not isinstance(body, dict) or "player" not in body:
            continue
        for field in REQUIRED_MANAGER_REFS:
            value = body.get(field)
            if not isinstance(value, dict) or not value.get("fileID"):
                problems.append("LessonManager.%s is not assigned" % field)
        for field in ("clickClip", "panelClip"):
            value = body.get(field)
            if not isinstance(value, dict) or not value.get("fileID"):
                problems.append("LessonManager.%s is not assigned" % field)
        cards = body.get("extinguisherCards")
        if not isinstance(cards, list) or len(cards) != 6:
            problems.append("LessonManager.extinguisherCards should hold 6 models, found %s"
                            % (len(cards) if isinstance(cards, list) else 0))
        return
    problems.append("LessonManager was not found in the scene")



def check_extinguisher_cards(problems):
    """Each wall card must map to a defined extinguisher entry, or the lesson cannot finish."""
    defined = set(re.findall(r'Id\s*=\s*"([^"]+)"', read(CONTENT)))
    scene_ids = set()
    for value in scene_field_values().get("eventId", ()):
        if value.startswith("ext_card_"):
            scene_ids.add(value[len("ext_card_"):])
    # scene cards are ext_card_water, content ids are ext_water
    scene_keys = {"ext_" + card for card in scene_ids}
    missing = scene_keys - defined
    unused = defined - scene_keys
    for card in sorted(missing):
        problems.append("card eventId %r has no matching entry in LessonContent.Extinguishers" % card)
    for card in sorted(unused):
        problems.append("LessonContent.Extinguishers defines %r but no card uses it" % card)
    if len(scene_ids) != 6:
        problems.append("expected 6 extinguisher cards in the scene, found %d" % len(scene_ids))
    return len(scene_ids)


def main():
    problems = []
    values, handled = check_events(problems)
    constants = check_stages(problems)
    member_count, referenced = check_content(problems)
    interactables = check_colliders(problems)
    check_manager_refs(problems)
    cards = check_extinguisher_cards(problems)

    print("Scene lesson fields: " + ", ".join(
        "%s=%d" % (field, len(ids)) for field, ids in sorted(values.items())))
    print("Handled event ids: %d" % len(handled))
    print("Stage constants: %d, LessonContent members: %d (%d referenced)"
          % (len(constants), member_count, referenced))
    print("Interactables with colliders: %d, extinguisher cards: %d"
          % (interactables, cards))

    if problems:
        print("\n%d problem(s):" % len(problems))
        for problem in problems:
            print("  - " + problem)
        return 1

    print("No flow problems found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
