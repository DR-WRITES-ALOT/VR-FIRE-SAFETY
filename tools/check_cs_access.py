#!/usr/bin/env python3
"""Cross-class C# accessibility check for the trainer scripts.

There is no C# compiler in the environment these scripts were generated in, and plain
syntax checking cannot catch accessibility mistakes. Two real compile errors slipped
through that way:

    error CS0272: 'EvacuationController.RouteComplete' cannot be used in this context
                  because the set accessor is inaccessible
    error CS0122: 'DoorController.finished' is inaccessible due to its protection level

This script parses every .cs file with tree-sitter and reports uses of another type's
private/protected members (and writes to properties whose setter is not accessible).
It is deliberately conservative: it only reports what it can resolve with confidence,
so a clean run means "no obvious accessibility errors", not "definitely compiles".

    python3 tools/check_cs_access.py [--verbose]

Exit code is non-zero when a problem is found.
"""

from __future__ import annotations

import glob
import os
import re
import sys

from tree_sitter import Language, Parser
import tree_sitter_c_sharp

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# C# keyword-ish names that look like types but never are
NOT_TYPES = {
    "var", "int", "float", "bool", "string", "double", "byte", "long", "short", "char",
    "object", "void", "Vector2", "Vector3", "Vector4", "Quaternion", "Color", "Transform",
    "GameObject", "Camera", "Light", "Material", "Texture2D", "AudioClip", "AudioSource",
    "Collider", "BoxCollider", "Renderer", "ParticleSystem", "Shader", "Gradient", "Debug",
    "Mathf", "Time", "Input", "Cursor", "Screen", "Physics", "Resources", "Application",
    "SceneManager", "Scene", "EventSystem", "PointerEventData", "RaycastResult", "Selectable",
    "GraphicRaycaster", "Image", "Text", "Button", "Canvas", "RectTransform", "Coroutine",
    "Action", "Array", "List", "Dictionary", "HashSet", "IEnumerator", "MonoBehaviour",
    "ScriptableObject", "Random", "XRSettings", "InputDevices", "InputDevice", "CommonUsages",
    "XRNode", "Object", "LayerMask", "Rect", "AnimationCurve", "ParticleSystemRenderer",
    "ShaderKeyword", "TextureFormat", "TextureWrapMode", "AudioRolloffMode", "AssetDatabase",
    "EditorBuildSettings", "EditorUtility", "EditorSceneManager", "SerializedObject",
    "SerializedProperty", "BuildPipeline", "OpenSceneMode", "EditorBuildSettingsScene",
    "GameObject", "InputButton", "Vector2Int", "CursorLockMode", "RenderQueue", "BlendMode",
    "CullMode", "ParticleSystemSimulationSpace", "ParticleSystemScalingMode", "Material",
}

ACCESS_PUBLIC = {"public"}
ACCESS_PROTECTED = {"protected", "protected internal", "private protected"}
ACCESS_PRIVATE = {"private", ""}


def read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


# --------------------------------------------------------------------------- #
# Parsing
# --------------------------------------------------------------------------- #

def parse_files():
    language = Language(tree_sitter_c_sharp.language())
    parser = Parser(language)
    files = {}
    for path in sorted(glob.glob(os.path.join(ROOT, "Assets", "**", "*.cs"), recursive=True)):
        text = read(path)
        files[path] = (text, parser.parse(text.encode("utf-8")))
    return files


def strip_comments_and_strings(text):
    """Remove comments and string contents so they cannot be mistaken for code."""
    text = re.sub(r"/\*.*?\*/", lambda m: "\n" * m.group(0).count("\n"), text, flags=re.DOTALL)
    text = re.sub(r"//[^\n]*", "", text)
    text = re.sub(r'@"(?:[^"]|"")*"', '""', text)
    text = re.sub(r'"(?:\\.|[^"\\])*"', '""', text)
    return text


def class_bodies(text):
    """Yield (class name, base name, body text, start line) for each class in a file."""
    header = re.compile(
        r"^[ \t]*(?:(?:public|internal|private|protected|static|abstract|sealed|partial)\s+)*"
        r"(?:class|struct)\s+(\w+)\s*(?::\s*([\w<>, .]+))?\s*$",
        re.MULTILINE)
    for match in header.finditer(text):
        name = match.group(1)
        bases = match.group(2) or ""
        brace = text.find("{", match.end())
        if brace < 0:
            continue
        depth = 0
        end = brace
        for i in range(brace, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    end = i
                    break
        line = text.count("\n", 0, match.start()) + 1
        yield name, bases, text[brace + 1:end], line


def members_of(body):
    """Collect declared members of one class body: name -> (kind, access, setter_access)."""
    members = {}

    # fields:  [modifiers] Type name [= ...];      (no parentheses, so not a method)
    for match in re.finditer(
            r"^[ \t]*(?P<mods>(?:(?:public|private|protected|internal|static|readonly|const|"
            r"volatile|new|\[[^\]]*\])\s+)*)"
            r"(?P<type>[A-Za-z_][\w.<>, ]*?)\s+(?P<name>\w+)\s*(?:=|;|,)", body, re.MULTILINE):
        mods = match.group("mods")
        access = _access(mods)
        kind = "const" if "const" in mods else "field"
        members.setdefault(match.group("name"), (kind, access, access))

    # properties:  [modifiers] Type Name { ... }
    for match in re.finditer(
            r"^[ \t]*(?P<mods>(?:(?:public|private|protected|internal|static|virtual|override|"
            r"sealed|abstract|new)\s+)*)"
            r"(?P<type>[A-Za-z_][\w.<>, ]*?)\s+(?P<name>\w+)\s*\{\s*(?P<acc>[^}]*)\}",
            body, re.MULTILINE):
        access = _access(match.group("mods"))
        accessors = match.group("acc")
        setter = re.search(r"(?P<mods>(?:(?:private|protected|internal)\s+)*)set\s*[;{]", accessors)
        setter_access = access
        if setter:
            setter_access = _access(setter.group("mods"))
        members[match.group("name")] = ("property", access, setter_access)

    # methods
    for match in re.finditer(
            r"^[ \t]*(?P<mods>(?:(?:public|private|protected|internal|static|virtual|override|"
            r"sealed|abstract|async|new|partial)\s+)*)"
            r"(?:[A-Za-z_][\w.<>,?\[\]]*)\s+(?P<name>\w+)\s*\(", body, re.MULTILINE):
        members.setdefault(match.group("name"), ("method", _access(match.group("mods")), None))

    return members


def _access(mods):
    words = mods.split()
    if "public" in words:
        return "public"
    if "protected" in words:
        return "protected"
    if "internal" in words:
        return "internal"
    return "private"


def variable_types(body):
    """name -> declared type for fields, parameters and locals in a class body."""
    types = {}
    patterns = [
        r"(?P<type>[A-Z][\w.]*)\s+(?P<name>\w+)\s*(?:=|;|,|\))",       # Type name = / ; / , / )
        r"(?P<type>[A-Z][\w.]*)\s+(?P<name>\w+)\s*$",                  # Type name  (end of line)
        r"\bout\s+(?P<type>[A-Z][\w.]*)\s+(?P<name>\w+)",              # out Type name
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, body, re.MULTILINE):
            name = match.group("name")
            type_name = match.group("type").split(".")[-1]
            if name in ("return", "new", "if", "else", "for", "while", "using", "namespace"):
                continue
            types.setdefault(name, type_name)
    return types


# --------------------------------------------------------------------------- #
# Analysis
# --------------------------------------------------------------------------- #

def main(argv):
    verbose = "--verbose" in argv
    parsed = parse_files()

    classes = {}          # class name -> (members, bases)
    for path, (text, _tree) in parsed.items():
        clean = strip_comments_and_strings(text)
        for name, bases, body, _line in class_bodies(clean):
            members = members_of(body)
            classes.setdefault(name, (members, bases))

    project_types = {name: members for name, (members, _bases) in classes.items()}
    parent = {name: [b.strip().split("<")[0] for b in bases.replace(",", " ").split()
                     if b.strip().split("<")[0] in classes]
              for name, (_members, bases) in classes.items()}

    def inherits(child, ancestor):
        seen, stack = set(), [child]
        while stack:
            current = stack.pop()
            if current == ancestor:
                return True
            if current in seen:
                continue
            seen.add(current)
            stack.extend(parent.get(current, []))
        return False

    def find_member(type_name, member):
        """Walk the inheritance chain for a member declaration."""
        seen = set()
        stack = [type_name]
        while stack:
            current = stack.pop()
            if current in seen:
                continue
            seen.add(current)
            members = project_types.get(current)
            if members and member in members:
                return current, members[member]
            stack.extend(parent.get(current, []))
        return None, None

    problems = []
    checked = 0
    for path, (text, _tree) in sorted(parsed.items()):
        clean = strip_comments_and_strings(text)
        rel = os.path.relpath(path, ROOT).replace(os.sep, "/")
        for class_name, _bases, body, class_line in class_bodies(clean):
            types = variable_types(body)
            body_start = clean.index(body) if body else 0
            for match in re.finditer(r"\b(?P<var>[A-Za-z_]\w*)\s*\.\s*(?P<member>\w+)", body):
                var, member = match.group("var"), match.group("member")
                if var in ("this", "base"):
                    continue
                type_name = types.get(var)
                if not type_name or type_name not in project_types or type_name in NOT_TYPES:
                    continue
                owner, declaration = find_member(type_name, member)
                if not declaration:
                    continue
                kind, access, setter_access = declaration
                if inherits(class_name, owner):
                    continue            # same class or a derived class: no restriction
                checked += 1

                # is this a write?  x.Member = / += / ++ / -- ...
                after = body[match.end():match.end() + 4]
                write = re.match(r"\s*(\+\+|--|\+=|-=|\*=|/=|=)(?!=)", after)
                if kind == "property":
                    if write and setter_access != "public":
                        problems.append(
                            "%s: %s line %d: writing %s.%s, but its setter is %s"
                            % (rel, class_name,
                               class_line + body.count("\n", 0, match.start()),
                               type_name, member, setter_access))
                    elif not write and access != "public":
                        problems.append(
                            "%s: %s line %d: reading %s.%s, which is %s"
                            % (rel, class_name,
                               class_line + body.count("\n", 0, match.start()),
                               type_name, member, access))
                elif access == "private":
                    problems.append(
                        "%s: %s line %d: %s.%s is private"
                        % (rel, class_name,
                           class_line + body.count("\n", 0, match.start()), type_name, member))
                elif access == "protected":
                    problems.append(
                        "%s: %s line %d: %s.%s is protected and %s does not derive from %s"
                        % (rel, class_name,
                           class_line + body.count("\n", 0, match.start()),
                           type_name, member, class_name, owner))

    print("classes: %d, cross-class member uses resolved: %d" % (len(classes), checked))
    if verbose:
        for name in sorted(classes):
            access_counts = {}
            for _kind, access, _setter in classes[name][0].values():
                access_counts[access] = access_counts.get(access, 0) + 1
            print("  %-24s %s" % (name, access_counts))

    if problems:
        print("\n%d problem(s):" % len(problems))
        for problem in problems:
            print("  - " + problem)
        return 1

    print("No cross-class accessibility problems found.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
