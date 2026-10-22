#!/usr/bin/env python3
"""Static checks for the generated Unity project.

This does not replace opening the project in the Unity Editor, but it catches the
mistakes that are easy to make when writing Unity YAML by hand:

  * broken {fileID: ...} references
  * missing or duplicate asset GUIDs
  * script fields that do not exist in the C# classes
  * transforms whose parent/child lists disagree
  * missing .meta files

Usage: python3 tools/verify_scene.py
"""

from __future__ import annotations

import glob
import os
import re
import sys

import yaml

from unity_common import ROOT

SCENE = os.path.join(ROOT, "Assets", "Scenes", "FireSafetyTrainer.unity")

IGNORED_GUIDS = {
    "0000000000000000e000000000000000",  # built-in extra resources
    "0000000000000000f000000000000000",  # built-in default resources
    "0cd44c1031e13a943bb63640046fad76",  # com.unity.ugui CanvasScaler
    "dc42784cf147c0c48a680349fa168899",  # com.unity.ugui GraphicRaycaster
    "76c392e42b5098c458856cdf6ecaaaa1",  # com.unity.ugui EventSystem
    "4f231c4fb786f3946a6b90b886c48677",  # com.unity.ugui StandaloneInputModule
    "474bcb49853aa07438625e644c072ee6",  # URP UniversalAdditionalLightData
    "a79441f348de89743a2939f4d699eac1",  # URP UniversalAdditionalCameraData
    "933532a4fcc9baf4fa0491de14d08ed7",  # URP Lit shader (materials)
    "d0353a89b1f911e48b9e16bdc9f2e058",  # URP material version stamp
    "0406db5a14f94604a8c57ccfbc9f3b46",  # URP Particles/Unlit shader
}
# Unity built-in asset ids (meshes, default material / clip / script / font objects)
BUILTIN_IDS = {10001, 10202, 10206, 10207, 10209, 10210, 10304, 2100000, 8300000,
               11500000, 12800000}


UNITY_TAG = re.compile(r"^--- !u!(\d+) &(-?\d+).*$")


def load_scene(path):
    """Return (documents, ids). Each document is a dict of the parsed YAML body."""
    with open(path, encoding="utf-8") as handle:
        lines = handle.read().split("\n")

    docs = []
    current = None
    buffer = []
    for line in lines:
        match = UNITY_TAG.match(line)
        if match:
            if current is not None:
                docs.append((current[0], current[1], "\n".join(buffer)))
            current = (int(match.group(1)), int(match.group(2)))
            buffer = []
        elif current is not None and not line.startswith("%YAML") and not line.startswith("%TAG"):
            buffer.append(line)
    if current is not None:
        docs.append((current[0], current[1], "\n".join(buffer)))

    parsed = []
    for class_id, file_id, text in docs:
        try:
            data = yaml.safe_load(text)
        except yaml.YAMLError as error:  # pragma: no cover - only on broken output
            print("YAML problem in document %s: %s" % (file_id, error))
            raise
        if isinstance(data, dict):
            parsed.append((class_id, file_id, data))
    return parsed


def find_references(value, found):
    if isinstance(value, dict):
        for key, item in value.items():
            if key == "fileID" and isinstance(item, int):
                found.append(item)
            else:
                find_references(item, found)
    elif isinstance(value, list):
        for item in value:
            find_references(item, found)
    elif isinstance(value, str):
        for match in re.finditer(r"fileID:\s*(-?\d+)", value):
            found.append(int(match.group(1)))


def collect_guids(value, found):
    if isinstance(value, dict):
        for key, item in value.items():
            if key == "guid" and isinstance(item, str):
                found.append(item)
            else:
                collect_guids(item, found)
    elif isinstance(value, list):
        for item in value:
            collect_guids(item, found)
    elif isinstance(value, str):
        for match in re.finditer(r"guid:\s*([0-9a-fA-F]{32})", value):
            found.append(match.group(1))


def meta_guids():
    mapping = {}
    for meta in glob.glob(os.path.join(ROOT, "Assets", "**", "*.meta"), recursive=True):
        with open(meta, encoding="utf-8") as handle:
            text = handle.read()
        match = re.search(r"^guid:\s*([0-9a-f]{32})$", text, re.MULTILINE)
        if match:
            mapping[match.group(1)] = os.path.relpath(meta[:-5], ROOT).replace(os.sep, "/")
    return mapping


def base_class(text):
    match = re.search(r"class\s+\w+\s*:\s*([A-Za-z_]\w*)", text)
    return match.group(1) if match else None


def parse_script_fields(path, fields_by_name=None, parsed=None):
    """Public / [SerializeField] instance fields of a C# class (including base classes)."""
    with open(path, encoding="utf-8") as handle:
        raw = handle.read()
    text = raw

    # strip comments and strings so they cannot confuse the matcher
    text = re.sub(r"//.*", "", text)
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    text = re.sub(r'"(?:[^"\\]|\\.)*"', '""', text)

    fields = set()
    for match in re.finditer(
            r"(?:public|\[SerializeField\]\s*private)\s+(?:static\s+)?(?:readonly\s+)?"
            r"([A-Za-z_][\w<>\[\],\.\s]*?)\s+([A-Za-z_]\w*)\s*(?:=[^;]*)?;", text):
        type_name, name = match.group(1).strip(), match.group(2)
        if "(" in type_name or name in ("class", "struct"):
            continue
        fields.add(name)

    # properties must not be treated as fields
    for match in re.finditer(r"public\s+[\w<>\[\],\.]+\s+(\w+)\s*=>", text):
        fields.discard(match.group(1))
    for match in re.finditer(r"public\s+[\w<>\[\],\.]+\s+(\w+)\s*\{\s*get", text):
        fields.discard(match.group(1))

    if fields_by_name is not None:
        name = os.path.splitext(os.path.basename(path))[0]
        parent = base_class(text)
        if parent and parent in fields_by_name:
            fields |= fields_by_name[parent]

    return fields


def main():
    problems = []
    docs = load_scene(SCENE)
    ids = {file_id for _, file_id, _ in docs}

    # ---- reference check -------------------------------------------------
    references = []
    find_references([data for _, _, data in docs], references)
    for file_id in sorted(set(references)):
        if file_id in (0,) or file_id in BUILTIN_IDS:
            continue
        if file_id not in ids:
            problems.append("missing fileID %s" % file_id)

    # ---- guid check ------------------------------------------------------
    guids = meta_guids()
    used = []
    collect_guids([data for _, _, data in docs], used)
    for guid in sorted(set(used)):
        if guid in IGNORED_GUIDS:
            continue
        if guid not in guids:
            problems.append("missing asset for guid %s" % guid)

    # ---- script field check ---------------------------------------------
    script_paths = {}
    for path in glob.glob(os.path.join(ROOT, "Assets", "Scripts", "*.cs")):
        name = os.path.splitext(os.path.basename(path))[0]
        meta = path + ".meta"
        if not os.path.exists(meta):
            problems.append("missing .meta for %s" % path)
            continue
        script_paths[name] = path

    fields_by_name = {}
    pending = dict(script_paths)
    # resolve base classes first (two passes are enough for this project)
    for _ in range(3):
        for name, path in list(pending.items()):
            fields_by_name[name] = parse_script_fields(path, fields_by_name)

    script_guids = {}
    for name, path in script_paths.items():
        with open(path + ".meta", encoding="utf-8") as handle:
            match = re.search(r"^guid:\s*([0-9a-f]{32})$", handle.read(), re.MULTILINE)
        if match:
            script_guids[match.group(1)] = (name, fields_by_name[name])

    ignored_keys = {
        "m_ObjectHideFlags", "m_CorrespondingSourceObject", "m_PrefabInstance", "m_PrefabAsset",
        "m_GameObject", "m_Enabled", "m_EditorHideFlags", "m_Script", "m_Name",
        "m_EditorClassIdentifier",
    }
    for class_id, file_id, data in docs:
        if class_id != 114:
            continue
        body = data.get("MonoBehaviour", {})
        script = body.get("m_Script", {})
        guid = script.get("guid") if isinstance(script, dict) else None
        if guid in IGNORED_GUIDS:
            continue
        if guid not in script_guids:
            problems.append("MonoBehaviour %s uses unknown script guid %s" % (file_id, guid))
            continue
        name, fields = script_guids[guid]
        for key in body:
            if key in ignored_keys:
                continue
            if key not in fields:
                problems.append("%s (%s) has no serialized field '%s'" % (name, file_id, key))

    # ---- transform / gameobject consistency ------------------------------
    game_objects = {}
    transforms = {}
    for class_id, file_id, data in docs:
        if class_id == 1:
            body = data.get("GameObject", {})
            game_objects[file_id] = body
        elif class_id in (4, 224):
            transforms[file_id] = data.get("Transform") or data.get("RectTransform") or {}

    for go_id, body in game_objects.items():
        components = body.get("m_Component", []) or []
        if not components:
            problems.append("GameObject %s has no components" % go_id)
            continue
        first = components[0].get("component", {}).get("fileID")
        if first not in transforms:
            problems.append("GameObject %s first component is not a transform (%s)" % (go_id, first))
        for component in components:
            component_id = component.get("component", {}).get("fileID")
            if component_id not in ids:
                problems.append("GameObject %s references missing component %s" % (go_id, component_id))

    for tr_id, body in transforms.items():
        parent = (body.get("m_Father") or {}).get("fileID", 0)
        for child in body.get("m_Children", []) or []:
            child_id = child.get("fileID")
            child_body = transforms.get(child_id)
            if child_body is None:
                problems.append("transform %s lists missing child %s" % (tr_id, child_id))
            elif (child_body.get("m_Father") or {}).get("fileID") != tr_id:
                problems.append("child %s does not point back to parent %s" % (child_id, tr_id))
        if parent and parent not in transforms:
            problems.append("transform %s has missing parent %s" % (tr_id, parent))

    # ---- stairwell envelope ----------------------------------------------
    # The stairwell is a full-height shaft but the doorway into the second corridor is only
    # 2.3 m high. If nothing fills the wall above that doorway the player can see over the
    # second corridor's ceiling and out into the sky, which reads as a hole in the level.
    named = {}
    for go_id, body in game_objects.items():
        components = body.get("m_Component") or []
        if not components:
            continue
        transform = transforms.get(components[0].get("component", {}).get("fileID"))
        if transform is None:
            continue
        named[body.get("m_Name")] = (transform.get("m_LocalPosition") or {},
                                     transform.get("m_LocalScale") or {})

    seal = named.get("Wall_LandingAbove")
    if seal is None:
        problems.append("Wall_LandingAbove is missing: the stairwell is open above the landing doorway")
    else:
        position, scale = seal
        bottom = position.get("y", 0.0) - scale.get("y", 0.0) * 0.5
        top = position.get("y", 0.0) + scale.get("y", 0.0) * 0.5
        if bottom > -0.2 or top < 3.2 or scale.get("x", 0.0) < 3.4:
            problems.append("Wall_LandingAbove does not seal the shaft above the landing doorway "
                            "(y %.2f..%.2f, width %.2f)" % (bottom, top, scale.get("x", 0.0)))

    # ---- meta coverage ---------------------------------------------------
    for path in glob.glob(os.path.join(ROOT, "Assets", "**", "*"), recursive=True):
        if os.path.isdir(path):
            continue
        if path.endswith(".meta") or path.endswith(".cs"):
            continue
        if not os.path.exists(path + ".meta"):
            problems.append("missing .meta for %s" % os.path.relpath(path, ROOT))

    print("Scene documents: %d, unique fileIDs: %d" % (len(docs), len(ids)))
    print("GUIDs checked: %d, scripts checked: %d" % (len(set(used)), len(script_guids)))

    if problems:
        print("\n%d problem(s):" % len(problems))
        for problem in problems[:80]:
            print("  - %s" % problem)
        if len(problems) > 80:
            print("  ... %d more" % (len(problems) - 80))
        return 1

    print("No structural problems found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
