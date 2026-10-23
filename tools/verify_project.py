#!/usr/bin/env python3
"""Static checks for the Unity version, packages and API level of this project.

The project targets Unity 6000.5.3f1 (Unity 6.5). Unity itself cannot be run in the
environment this project was generated in, so these checks catch the mistakes that are
easy to make by hand when moving a project between Unity versions:

  * ProjectVersion.txt points at the intended editor build
  * Packages/manifest.json asks only for packages that exist for Unity 6.5,
    with no 2022-era packages and no removed modules
  * Player Settings still suit this project (legacy input available, linear colour, 1600x900)
  * The build settings list the training scene
  * No script uses an API that Unity 6 removed or renamed
  * The UI stack the scene relies on (uGUI) is present

Exit code is non-zero when a check fails.
"""

from __future__ import annotations

import json
import os
import re
import sys

from unity_common import ROOT

EXPECTED_EDITOR = "6000.5.3f1"
EXPECTED_REVISION = "c2eb47b3a2a9"

# Versions taken from two public projects that were committed with Unity 6000.5.3f1
# (PhilippKochendoerfer/Use-the-Force-in-VR and isac-artzi/Resources-for-Game-Development-Courses).
EXPECTED_PACKAGES = {
    "com.unity.render-pipelines.universal": "17.5.0",
    "com.unity.ide.rider": "3.0.38",
    "com.unity.ide.visualstudio": "2.0.26",
    "com.unity.ugui": "2.5.0",
    "com.unity.xr.interaction.toolkit": "3.5.1",
    "com.unity.xr.management": "4.5.4",
    "com.unity.xr.openxr": "1.17.1",
}

# Package modules that ship with Unity 6.5 (list taken from the same reference project).
KNOWN_MODULES = {
    "accessibility", "adaptiveperformance", "ai", "androidjni", "animation", "assetbundle",
    "audio", "cloth", "director", "imageconversion", "imgui", "jsonserialize", "particlesystem",
    "physics", "physics2d", "physicscore2d", "screencapture", "terrain", "terrainphysics",
    "tilemap", "ui", "uielements", "umbra", "unityanalytics", "unitywebrequest",
    "unitywebrequestassetbundle", "unitywebrequestaudio", "unitywebrequesttexture",
    "unitywebrequestwww", "vectorgraphics", "vehicles", "video", "wind", "xr",
}

# Packages that only exist for Unity 2022 and would fail to resolve on Unity 6.
FORBIDDEN_PACKAGES = {
    "com.unity.modules.vr",          # removed module; UnityEngine.XR lives in modules.xr
    "com.unity.textmeshpro",         # merged into com.unity.ugui 2.x
    "com.unity.visualscripting",     # not used by this project
}

# APIs removed or renamed in Unity 6. Use the replacements noted in the message.
BANNED_APIS = {
    r"Object\.FindObjectOfType": "use Object.FindFirstObjectByType",
    r"Object\.FindObjectsOfType": "use Object.FindObjectsByType",
    r"\bFindObjectOfType<": "use FindFirstObjectByType",
    r"\bFindObjectsOfType<": "use FindObjectsByType",
    r"UnityEngine\.VR\b": "the legacy VR module was removed; use UnityEngine.XR",
    r"XRSettings\.LoadDeviceByName": "use the XR Plug-in Management loaders",
    r"Application\.LoadLevel": "use SceneManager.LoadScene",
    r"\bGUIText\b": "use a Canvas and UnityEngine.UI.Text",
    r"\bWWW\b": "use UnityWebRequest",
    r"UnityEngine\.XR\.Interaction": "this project uses UnityEngine.XR directly; XRI types "
                                     "would tie the scripts to a specific package version",
}


def read(path):
    with open(os.path.join(ROOT, path), encoding="utf-8") as handle:
        return handle.read()


def check_editor_version(problems, notes):
    text = read("ProjectSettings/ProjectVersion.txt")
    version = re.search(r"^m_EditorVersion:\s*(\S+)$", text, re.MULTILINE)
    revision = re.search(r"^m_EditorVersionWithRevision:\s*\S+\s*\(([0-9a-f]+)\)$", text,
                         re.MULTILINE)
    if not version:
        problems.append("ProjectVersion.txt has no m_EditorVersion line")
        return None
    if version.group(1) != EXPECTED_EDITOR:
        problems.append("ProjectVersion.txt is %s, expected %s" % (version.group(1), EXPECTED_EDITOR))
    if not revision:
        problems.append("ProjectVersion.txt has no m_EditorVersionWithRevision line")
    elif revision.group(1) == "0" * len(revision.group(1)):
        problems.append("ProjectVersion.txt revision is all zeros; Unity Hub cannot match the install")
    elif revision.group(1) != EXPECTED_REVISION:
        notes.append("ProjectVersion.txt revision is %s (referenced builds use %s)"
                     % (revision.group(1), EXPECTED_REVISION))
    return version.group(1)


def check_manifest(problems, notes):
    manifest = json.loads(read("Packages/manifest.json"))
    deps = manifest.get("dependencies", {})

    for package, expected in EXPECTED_PACKAGES.items():
        actual = deps.get(package)
        if actual is None:
            problems.append("manifest.json is missing %s (expected %s)" % (package, expected))
        elif actual != expected:
            notes.append("%s is %s; versions verified against Unity %s projects use %s"
                         % (package, actual, EXPECTED_EDITOR, expected))

    for package in deps:
        if package in FORBIDDEN_PACKAGES:
            problems.append("manifest.json requests %s, which is not available for Unity 6" % package)
        elif package.startswith("com.unity.modules."):
            name = package[len("com.unity.modules."):]
            if name not in KNOWN_MODULES:
                problems.append("manifest.json requests unknown module %s" % package)
        elif package not in EXPECTED_PACKAGES:
            notes.append("manifest.json also requests %s %s (not needed by the trainer)"
                         % (package, deps[package]))

    if "com.unity.render-pipelines.universal" not in deps:
        problems.append("com.unity.render-pipelines.universal is missing; the project renders with URP")
    return deps


def check_player_settings(problems, notes):
    text = read("ProjectSettings/ProjectSettings.asset")

    def value(pattern, label, default=None):
        match = re.search(pattern, text, re.MULTILINE)
        if not match:
            problems.append("ProjectSettings.asset has no %s entry" % label)
            return default
        return match.group(1).strip()

    handler = value(r"^  activeInputHandler:\s*(\d+)$", "activeInputHandler")
    if handler is not None:
        # 0 = old Input Manager, 1 = Input System package, 2 = both
        if handler == "1":
            problems.append("activeInputHandler is 1 (new Input System only); the trainer reads "
                            "the legacy Input Manager, so it must be 0 or 2")
        elif handler == "0":
            notes.append("activeInputHandler is 0 (legacy only): desktop play works, but the XR "
                         "Interaction Toolkit device simulator needs 2 (Both)")
        elif handler != "2":
            problems.append("activeInputHandler has an unexpected value: %s" % handler)

    colour_space = value(r"^  m_ActiveColorSpace:\s*(\d+)$", "m_ActiveColorSpace")
    if colour_space == "0":
        notes.append("colour space is Gamma; Linear (1) is what Unity 6 uses and looks better in VR")

    product = value(r"^  productName:\s*(.+)$", "productName")
    company = value(r"^  companyName:\s*(.+)$", "companyName")
    if not product or not company:
        problems.append("Player Settings are missing the product or company name")

    # ---- standalone headset build settings -------------------------------
    identifiers = re.findall(r"^    (Android|Standalone):\s*(\S+)$", read("ProjectSettings/ProjectSettings.asset"),
                             re.MULTILINE)
    bundle = dict(identifiers)
    if bundle.get("Android", "").startswith("com.DefaultCompany"):
        problems.append("Android bundle identifier is still the template value (%s)"
                        % bundle.get("Android"))
    if bundle.get("Standalone", "").startswith("com.DefaultCompany"):
        problems.append("Standalone bundle identifier is still the template value (%s)"
                        % bundle.get("Standalone"))

    architectures = value(r"^  AndroidTargetArchitectures:\s*(\d+)$", "AndroidTargetArchitectures")
    if architectures is not None:
        # bit 1 = ARMv7, bit 2 = ARM64; every current standalone headset is ARM64-only.
        if not (int(architectures) & 2):
            problems.append("AndroidTargetArchitectures is %s: a standalone headset build needs "
                            "ARM64 enabled" % architectures)

    min_sdk = value(r"^  AndroidMinSdkVersion:\s*(\d+)$", "AndroidMinSdkVersion")
    if min_sdk is not None and int(min_sdk) < 29:
        notes.append("AndroidMinSdkVersion is %s; Quest-class headsets need API 29 or newer "
                     "(this project ships 29)" % min_sdk)

    width = value(r"^  defaultScreenWidth:\s*(\d+)$", "defaultScreenWidth")
    height = value(r"^  defaultScreenHeight:\s*(\d+)$", "defaultScreenHeight")
    if width and height and (int(width) < 1280 or int(height) < 720):
        notes.append("default game view is %sx%s; the interface is laid out for 1600x900"
                     % (width, height))


def check_build_settings(problems):
    text = read("ProjectSettings/EditorBuildSettings.asset")
    if "Assets/Scenes/FireSafetyTrainer.unity" not in text:
        problems.append("EditorBuildSettings.asset does not list the training scene")
    if "enabled: 1" not in text:
        problems.append("the training scene is in Build Settings but is not enabled")
    scene_meta = read("Assets/Scenes/FireSafetyTrainer.unity.meta")
    guid = re.search(r"^guid: ([0-9a-f]{32})$", scene_meta, re.MULTILINE)
    if guid and guid.group(1) not in text:
        problems.append("EditorBuildSettings.asset does not use the scene's current GUID")


def check_scripts(problems, notes):
    files = []
    for folder in ("Assets/Scripts", "Assets/Editor"):
        for name in sorted(os.listdir(os.path.join(ROOT, folder))):
            if name.endswith(".cs"):
                files.append(folder + "/" + name)
    for path in files:
        text = read(path)
        for pattern, hint in BANNED_APIS.items():
            match = re.search(pattern, text)
            if match:
                problems.append("%s uses %r (%s)" % (path, match.group(0), hint))
        if "ENABLE_LEGACY_INPUT_MANAGER" in text:
            notes.append("%s guards against the legacy input backend being disabled" % path)
    return files


def check_ui_stack(problems):
    """The interface is built from uGUI at runtime, so the package must be present."""
    deps = json.loads(read("Packages/manifest.json")).get("dependencies", {})
    ugui = deps.get("com.unity.ugui", "")
    if not ugui:
        problems.append("com.unity.ugui is missing, but the whole interface is uGUI")
    elif not ugui.startswith("2."):
        problems.append("com.unity.ugui %s is a Unity 2022 version; Unity 6 needs 2.x" % ugui)

    scene = read("Assets/Scenes/FireSafetyTrainer.unity")
    for guid, label in (
        ("0cd44c1031e13a943bb63640046fad76", "CanvasScaler"),
        ("dc42784cf147c0c48a680349fa168899", "GraphicRaycaster"),
        ("76c392e42b5098c458856cdf6ecaaaa1", "EventSystem"),
        ("4f231c4fb786f3946a6b90b886c48677", "StandaloneInputModule"),
    ):
        if guid not in scene:
            problems.append("the scene has no %s component (uGUI GUID %s)" % (label, guid))



def check_script_names(problems):
    """Unity only attaches a MonoBehaviour when the class name matches the file name."""
    classes = {}
    for folder in ("Assets/Scripts", "Assets/Editor"):
        for name in sorted(os.listdir(os.path.join(ROOT, folder))):
            if not name.endswith(".cs"):
                continue
            text = read(folder + "/" + name)
            declared = []
            for line in text.split("\n"):
                stripped = line.strip()
                if stripped.startswith("//") or stripped.startswith("*") or stripped.startswith("///"):
                    continue          # prose in a comment can contain the word "class"
                match = re.match(r"^\s*(?:(?:public|internal|private|protected|static|abstract|sealed|partial)\s+)*"
                                 r"(?:class|interface)\s+(\w+)", line)
                if match:
                    declared.append(match.group(1))
            if not declared:
                continue
            classes[name] = declared[0]
            if declared[0] != name[:-3]:
                problems.append("%s/%s declares %s; Unity needs the file name to match the class name"
                                % (folder, name, declared[0]))
    return len(classes)



# --------------------------------------------------------------------------- #
# Render pipeline
# --------------------------------------------------------------------------- #

URP_PACKAGE_SCRIPTS = {
    "bf2edee5c58d82540a51f03df9d42094": "UniversalRenderPipelineAsset",
    "de640fe3d0db1804a85f9fc8f5cadab6": "UniversalRendererData",
    "2ec995e51a6e251468d2a3fd8a686257": "UniversalRenderPipelineGlobalSettings",
    "474bcb49853aa07438625e644c072ee6": "UniversalAdditionalLightData",
    "a79441f348de89743a2939f4d699eac1": "UniversalAdditionalCameraData",
}
URP_LIT_SHADER = "933532a4fcc9baf4fa0491de14d08ed7"
URP_PARTICLE_SHADER = "0406db5a14f94604a8c57ccfbc9f3b46"
BUILTIN_STANDARD_SHADER = "0000000000000000f000000000000000"


def asset_guids():
    """guid -> project-relative path for every asset with a .meta."""
    found = {}
    for root, _dirs, files in os.walk(os.path.join(ROOT, "Assets")):
        for name in files:
            if not name.endswith(".meta"):
                continue
            path = os.path.join(root, name)
            text = open(path, encoding="utf-8", errors="replace").read()
            match = re.search(r"^guid: ([0-9a-f]{32})$", text, re.MULTILINE)
            if match:
                found[match.group(1)] = os.path.relpath(path[:-5], ROOT).replace(os.sep, "/")
    return found


def check_render_pipeline(problems, notes):
    assets = asset_guids()
    graphics_path = "ProjectSettings/GraphicsSettings.asset"
    if not os.path.exists(os.path.join(ROOT, graphics_path)):
        problems.append("ProjectSettings/GraphicsSettings.asset is missing, so no pipeline asset is set")
        return
    graphics = read(graphics_path)

    match = re.search(r"m_CustomRenderPipeline: \{fileID: 11400000, guid: ([0-9a-f]{32})", graphics)
    if not match:
        problems.append("GraphicsSettings has no m_CustomRenderPipeline: the project would render "
                        "with the deprecated Built-in pipeline")
        return
    pipeline_guid = match.group(1)
    pipeline = assets.get(pipeline_guid)
    if not pipeline:
        problems.append("GraphicsSettings points at pipeline asset %s, which is not in Assets/" % pipeline_guid)
        return
    body = read(pipeline)
    if "bf2edee5c58d82540a51f03df9d42094" not in body:   # URP asset script GUID
        problems.append("%s is not a Universal Render Pipeline asset" % pipeline)
    else:
        notes.append("render pipeline: %s (URP)" % pipeline)

    renderer = re.search(r"m_RendererDataList:\n  - \{fileID: 11400000, guid: ([0-9a-f]{32})", body)
    if not renderer:
        problems.append("%s has no renderer data" % pipeline)
    elif renderer.group(1) not in assets:
        problems.append("%s references a renderer asset that is not in the project" % pipeline)

    global_settings = re.search(r"m_RenderPipelineGlobalSettingsMap:[\s\S]{0,200}?guid: ([0-9a-f]{32})",
                                graphics)
    if global_settings and global_settings.group(1) not in assets:
        problems.append("GraphicsSettings references a global settings asset that is not in the project")

    # The runtime particle material uses Shader.Find, so the shader must survive stripping.
    if URP_PARTICLE_SHADER not in graphics:
        problems.append("the URP particle shader is not in Always Included Shaders, so VfxUtil's "
                        "runtime materials would fail in a player build")

    # Quality levels must point at a pipeline that exists and use valid indices.
    quality_path = "ProjectSettings/QualitySettings.asset"
    if not os.path.exists(os.path.join(ROOT, quality_path)):
        problems.append("ProjectSettings/QualitySettings.asset is missing")
        return
    quality = read(quality_path)
    levels = re.findall(r"customRenderPipeline: \{fileID: 11400000, guid: ([0-9a-f]{32})", quality)
    level_count = len(re.findall(r"^  - serializedVersion: 2\n    name:", quality, re.MULTILINE))
    if level_count == 0:
        problems.append("QualitySettings has no quality levels")
    for guid in set(levels):
        if guid not in assets:
            problems.append("a quality level references pipeline asset %s, which is not in Assets/" % guid)
    if levels and pipeline_guid not in levels:
        problems.append("no quality level uses the pipeline asset set in GraphicsSettings")
    current = re.search(r"m_CurrentQuality: (\d+)", quality)
    if current and int(current.group(1)) >= max(1, level_count):
        problems.append("m_CurrentQuality is out of range for the number of quality levels")
    platform_block = re.search(r"m_PerPlatformDefaultQuality:\n((?:    .*\n)+)", quality)
    if platform_block:
        for platform, index in re.findall(r"^    ([\w ]+): (\d+)$", platform_block.group(1), re.MULTILINE):
            if int(index) >= max(1, level_count):
                problems.append("platform %r maps to quality level %s, but only %d level(s) exist"
                                % (platform, index, level_count))


def check_materials(problems, notes):
    """Every material must use the URP shader, or it renders magenta in Unity 6."""
    materials = []
    for root, _dirs, files in os.walk(os.path.join(ROOT, "Assets")):
        for name in files:
            if name.endswith(".mat"):
                materials.append(os.path.relpath(os.path.join(root, name), ROOT).replace(os.sep, "/"))
    for path in sorted(materials):
        text = read(path)
        shader = re.search(r"m_Shader: \{fileID: (\d+), guid: ([0-9a-f]{32})", text)
        if not shader:
            problems.append("%s has no shader reference" % path)
            continue
        guid = shader.group(2)
        if guid == URP_LIT_SHADER:
            if "_BaseColor" not in text:
                problems.append("%s uses URP/Lit but has no _BaseColor, so it would be white" % path)
        elif guid == BUILTIN_STANDARD_SHADER:
            problems.append("%s still uses the Built-in 'Standard' shader" % path)
        else:
            notes.append("%s uses shader %s" % (path, guid))
    return len(materials)



def check_guid_uniqueness(problems):
    """Duplicate GUIDs corrupt Unity's GUID table, so check them explicitly.

    A crashed asset import worker in Unity 6.5 reports its stack inside
    GuidReservations::Reserve while creating a folder, so a clean, unique GUID table is
    worth asserting: every .meta must carry a well formed, unique 32 hex GUID.
    """
    seen = {}
    duplicates = 0
    malformed = 0
    for root, _dirs, files in os.walk(os.path.join(ROOT, "Assets")):
        for name in files:
            if not name.endswith(".meta"):
                continue
            path = os.path.join(root, name)
            text = open(path, encoding="utf-8", errors="replace").read()
            match = re.search(r"^guid: (\S+)$", text, re.MULTILINE)
            rel = os.path.relpath(path, ROOT).replace(os.sep, "/")
            if not match or not re.fullmatch(r"[0-9a-f]{32}", match.group(1)):
                problems.append("%s has a malformed GUID" % rel)
                malformed += 1
                continue
            guid = match.group(1)
            if guid in seen:
                problems.append("%s and %s share GUID %s" % (seen[guid], rel, guid))
                duplicates += 1
            else:
                seen[guid] = rel

    # Every asset must have a .meta, otherwise Unity invents a GUID on import and any
    # reference to it from a scene or material breaks.
    missing = 0
    for root, dirs, files in os.walk(os.path.join(ROOT, "Assets")):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for name in dirs + [f for f in files if not f.startswith(".")]:
            path = os.path.join(root, name)
            if name.endswith(".meta"):
                continue
            if not os.path.exists(path + ".meta"):
                problems.append("%s has no .meta file" % os.path.relpath(path, ROOT).replace(os.sep, "/"))
                missing += 1
    return len(seen), duplicates, missing


def main():
    problems, notes = [], []
    editor = check_editor_version(problems, notes)
    deps = check_manifest(problems, notes)
    check_player_settings(problems, notes)
    check_build_settings(problems)
    files = check_scripts(problems, notes)
    check_script_names(problems)
    check_render_pipeline(problems, notes)
    materials = check_materials(problems, notes)
    guids, dupes, missing_meta = check_guid_uniqueness(problems)
    check_ui_stack(problems)

    print("Editor: %s" % editor)
    print("Packages: %d (%d required, %d modules)"
          % (len(deps), len(EXPECTED_PACKAGES),
             sum(1 for key in deps if key.startswith("com.unity.modules."))))
    print("Scripts checked: %d, materials checked: %d" % (len(files), materials))
    print("GUIDs: %d unique, %d duplicate, %d assets without .meta" % (guids, dupes, missing_meta))

    for note in notes:
        print("  note: " + note)

    if problems:
        print("\n%d problem(s):" % len(problems))
        for problem in problems:
            print("  - " + problem)
        return 1

    print("Project is consistent with Unity %s." % EXPECTED_EDITOR)
    return 0


if __name__ == "__main__":
    sys.exit(main())
