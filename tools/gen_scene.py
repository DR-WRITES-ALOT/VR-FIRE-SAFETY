#!/usr/bin/env python3
"""Generate Assets/Scenes/FireSafetyTrainer.unity and the matching build settings.

Run from the project root:

    python3 tools/gen_scene.py

Everything is written as ordinary Unity YAML, so the scene can be regenerated at any
time and every reference can be checked in source control.

Layout (one continuous route):
    start -> first corridor -> one flight of stairs -> second corridor -> assembly point
"""

from __future__ import annotations

import glob
import math
import os

from unity_common import (
    ROOT,
    col,
    fmt,
    guid_for,
    sync_all_metas,
    v3,
    write_meta,
    write_text,
)

# --------------------------------------------------------------------------- #
# Constants
# --------------------------------------------------------------------------- #

SCENE_PATH = "Assets/Scenes/FireSafetyTrainer.unity"

HALF = 2.0           # corridor half width
WALL = 0.2           # wall thickness
CEIL = 3.2           # ceiling height above the floor
C1_START = -1.8
C1_END = 18.0
LOBBY_END = 21.0
STAIR_HALF = 1.6
RISE = 0.175
RUN = 0.30
STEPS = 20
STAIR_BOTTOM = LOBBY_END + STEPS * RUN       # 27.0
LOWER = -STEPS * RISE                        # -3.5
LANDING_END = 28.5
C2_END = 44.0
OUT_END = 62.0

# Universal Render Pipeline components (URP 17 script GUIDs, stable across versions).
URP_LIGHT_DATA = "474bcb49853aa07438625e644c072ee6"
URP_CAMERA_DATA = "a79441f348de89743a2939f4d699eac1"

URP_LIGHT_FIELDS = [
    "  m_UsePipelineSettings: 1",
    "  m_AdditionalLightsShadowResolutionTier: 2",
    "  m_CustomShadowLayers: 0",
    "  m_LightCookieSize: {x: 1, y: 1}",
    "  m_LightCookieOffset: {x: 0, y: 0}",
    "  m_SoftShadowQuality: 0",
]

URP_CAMERA_FIELDS = [
    "  m_RenderShadows: 1",
    "  m_RequiresDepthTextureOption: 2",
    "  m_RequiresOpaqueTextureOption: 2",
    "  m_CameraType: 0",
    "  m_Cameras: []",
    "  m_RendererIndex: -1",
    "  m_RenderPostProcessing: 0",
    "  m_Antialiasing: 0",
    "  m_AntialiasingQuality: 2",
    "  m_StopNaN: 0",
    "  m_Dithering: 0",
    "  m_ClearDepth: 1",
    "  m_AllowXRRendering: 1",
]

MESHES = {
    "cube": 10202,
    "sphere": 10207,
    "capsule": 10208,
    "cylinder": 10206,
    "plane": 10209,
    "quad": 10210,
}
BUILTIN_MESH_GUID = "0000000000000000e000000000000000"

MATERIALS = {}
for path in glob.glob(os.path.join(ROOT, "Assets", "Materials", "*.mat")):
    name = os.path.splitext(os.path.basename(path))[0]
    MATERIALS[name] = guid_for("Assets/Materials/%s.mat" % name)

SIGN_TEXTURES = {}
for path in glob.glob(os.path.join(ROOT, "Assets", "Textures", "Signs", "*.png")):
    name = os.path.splitext(os.path.basename(path))[0]
    SIGN_TEXTURES[name] = "Sign_" + name

SCRIPTS = {}
for path in glob.glob(os.path.join(ROOT, "Assets", "Scripts", "*.cs")):
    name = os.path.splitext(os.path.basename(path))[0]
    SCRIPTS[name] = guid_for("Assets/Scripts/%s.cs" % name)

FONTS = {
    "regular": guid_for("Assets/Fonts/DejaVuSans.ttf"),
    "bold": guid_for("Assets/Fonts/DejaVuSans-Bold.ttf"),
}

UGUI = {
    "CanvasScaler": "0cd44c1031e13a943bb63640046fad76",
    "GraphicRaycaster": "dc42784cf147c0c48a680349fa168899",
    "EventSystem": "76c392e42b5098c458856cdf6ecaaaa1",
    "StandaloneInputModule": "4f231c4fb786f3946a6b90b886c48677",
}

AUDIO_CLIPS = {
    "alarm": guid_for("Assets/Resources/Audio/alarm_loop.wav"),
    "fire": guid_for("Assets/Resources/Audio/fire_crackle.wav"),
    "hiss": guid_for("Assets/Resources/Audio/extinguisher_hiss.wav"),
    "click": guid_for("Assets/Resources/Audio/ui_click.wav"),
    "chime": guid_for("Assets/Resources/Audio/success_chime.wav"),
    "door": guid_for("Assets/Resources/Audio/door_close.wav"),
}

COMPONENT_NAMES = {
    4: "Transform",
    20: "Camera",
    23: "MeshRenderer",
    33: "MeshFilter",
    65: "BoxCollider",
    81: "AudioListener",
    82: "AudioSource",
    108: "Light",
    114: "MonoBehaviour",
    143: "CharacterController",
    223: "Canvas",
    224: "RectTransform",
    222: "CanvasRenderer",
}


def mat(name: str) -> str:
    return MATERIALS[name]


def ref(file_id: int) -> str:
    return "{fileID: %d}" % file_id


def clip(name: str) -> str:
    return "{fileID: 8300000, guid: %s, type: 3}" % AUDIO_CLIPS[name]


def font_ref(kind: str) -> str:
    return "{fileID: 12800000, guid: %s, type: 3}" % FONTS[kind]


def euler_to_quaternion(rot):
    x, y, z = [math.radians(a) for a in rot]
    cx, sx = math.cos(x / 2), math.sin(x / 2)
    cy, sy = math.cos(y / 2), math.sin(y / 2)
    cz, sz = math.cos(z / 2), math.sin(z / 2)
    qw = cx * cy * cz + sx * sy * sz
    qx = sx * cy * cz - cx * sy * sz
    qy = cx * sy * cz + sx * cy * sz
    qz = cx * cy * sz - sx * sy * cz
    return "{x: %s, y: %s, z: %s, w: %s}" % (fmt(qx), fmt(qy), fmt(qz), fmt(qw))


# --------------------------------------------------------------------------- #
# Scene graph
# --------------------------------------------------------------------------- #

class Node:
    def __init__(self, scene, name, parent=None, pos=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1),
                 layer=0, tag="Untagged", active=True, rect=False):
        self.scene = scene
        self.name = name
        self.parent = parent
        self.pos = pos
        self.rot = rot
        self.scale = scale
        self.layer = layer
        self.tag = tag
        self.active = active
        self.rect = rect
        self.children = []
        self.components = []          # extra components: (class_id, file_id, body lines)
        self.go_id = scene.new_id()
        self.tr_id = scene.new_id()
        if parent is not None:
            parent.children.append(self)
        else:
            scene.roots.append(self)
        scene.nodes.append(self)

    # -- components -------------------------------------------------------
    def add_component(self, class_id, body_lines, component_id=None):
        component_id = component_id or self.scene.new_id()
        self.components.append((class_id, component_id, body_lines))
        return component_id

    def mesh(self, mesh_name="cube", material="Concrete", shadows=True, receive=True):
        mesh_id = self.scene.new_id()
        renderer_id = self.scene.new_id()
        self.components.append((33, mesh_id, [
            "  m_GameObject: %s" % ref(self.go_id),
            "  m_Mesh: {fileID: %d, guid: %s, type: 0}" % (MESHES[mesh_name], BUILTIN_MESH_GUID),
        ]))
        self.components.append((23, renderer_id, [
            "  m_GameObject: %s" % ref(self.go_id),
            "  m_Enabled: 1",
            "  m_CastShadows: %d" % (1 if shadows else 0),
            "  m_ReceiveShadows: %d" % (1 if receive else 0),
            "  m_DynamicOccludee: 1",
            "  m_StaticShadowCaster: 0",
            "  m_MotionVectors: 1",
            "  m_LightProbeUsage: 1",
            "  m_ReflectionProbeUsage: 1",
            "  m_RayTracingMode: 2",
            "  m_RayTraceProcedural: 0",
            "  m_RenderingLayerMask: 1",
            "  m_RendererPriority: 0",
            "  m_Materials:",
            "  - {fileID: 2100000, guid: %s, type: 2}" % mat(material),
            "  m_StaticBatchInfo:",
            "    firstSubMesh: 0",
            "    subMeshCount: 0",
            "  m_StaticBatchRoot: {fileID: 0}",
            "  m_ProbeAnchor: {fileID: 0}",
            "  m_LightProbeVolumeOverride: {fileID: 0}",
            "  m_ScaleInLightmap: 1",
            "  m_ReceiveGI: 1",
            "  m_PreserveUVs: 0",
            "  m_IgnoreNormalsForChartDetection: 0",
            "  m_ImportantGI: 0",
            "  m_StitchLightmapSeams: 1",
            "  m_SelectedEditorRenderState: 3",
            "  m_MinimumChartSize: 4",
            "  m_AutoUVMaxDistance: 0.5",
            "  m_AutoUVMaxAngle: 89",
            "  m_LightmapParameters: {fileID: 0}",
            "  m_SortingLayerID: 0",
            "  m_SortingLayer: 0",
            "  m_SortingOrder: 0",
            "  m_AdditionalVertexStreams: {fileID: 0}",
        ]))
        return renderer_id

    def box_collider(self, size=(1, 1, 1), center=(0, 0, 0), trigger=False):
        collider_id = self.scene.new_id()
        self.components.append((65, collider_id, [
            "  m_GameObject: %s" % ref(self.go_id),
            "  m_Material: {fileID: 0}",
            "  m_IncludeLayers:",
            "    serializedVersion: 2",
            "    m_Bits: 0",
            "  m_ExcludeLayers:",
            "    serializedVersion: 2",
            "    m_Bits: 0",
            "  m_LayerOverridePriority: 0",
            "  m_IsTrigger: %d" % (1 if trigger else 0),
            "  m_ProvidesContacts: 0",
            "  m_Enabled: 1",
            "  serializedVersion: 3",
            "  m_Size: %s" % v3(*size),
            "  m_Center: %s" % v3(*center),
        ]))
        return collider_id

    def mono(self, script_name, fields):
        body = [
            "  m_GameObject: %s" % ref(self.go_id),
            "  m_Enabled: 1",
            "  m_EditorHideFlags: 0",
            "  m_Script: {fileID: 11500000, guid: %s, type: 3}" % SCRIPTS[script_name],
            "  m_Name: ",
            "  m_EditorClassIdentifier: ",
        ]
        body.extend(fields)
        return self.add_component(114, body)

    def script_component(self, guid, fields):
        body = [
            "  m_GameObject: %s" % ref(self.go_id),
            "  m_Enabled: 1",
            "  m_EditorHideFlags: 0",
            "  m_Script: {fileID: 11500000, guid: %s, type: 3}" % guid,
            "  m_Name: ",
            "  m_EditorClassIdentifier: ",
        ]
        body.extend(fields)
        return self.add_component(114, body)

    # -- serialisation ----------------------------------------------------
    def yaml(self, root_order):
        lines = ["--- !u!1 &%d" % self.go_id, "GameObject:", "  m_ObjectHideFlags: 0",
                 "  m_CorrespondingSourceObject: {fileID: 0}", "  m_PrefabInstance: {fileID: 0}",
                 "  m_PrefabAsset: {fileID: 0}", "  serializedVersion: 6", "  m_Component:",
                 "  - component: %s" % ref(self.tr_id)]
        for _, component_id, _ in self.components:
            lines.append("  - component: %s" % ref(component_id))
        lines += ["  m_Layer: %d" % self.layer,
                  "  m_Name: %s" % self.name,
                  "  m_TagString: %s" % self.tag,
                  "  m_Icon: {fileID: 0}",
                  "  m_NavMeshLayer: 0",
                  "  m_StaticEditorFlags: 0",
                  "  m_IsActive: %d" % (1 if self.active else 0)]

        transform_class = 224 if self.rect else 4
        lines += ["--- !u!%d &%d" % (transform_class, self.tr_id),
                  "%s:" % COMPONENT_NAMES[transform_class],
                  "  m_ObjectHideFlags: 0",
                  "  m_CorrespondingSourceObject: {fileID: 0}",
                  "  m_PrefabInstance: {fileID: 0}",
                  "  m_PrefabAsset: {fileID: 0}",
                  "  m_GameObject: %s" % ref(self.go_id),
                  "  m_LocalRotation: %s" % euler_to_quaternion(self.rot),
                  "  m_LocalPosition: %s" % v3(*self.pos),
                  "  m_LocalScale: %s" % v3(*self.scale),
                  "  m_ConstrainProportionsScale: 0"]
        if self.children:
            lines.append("  m_Children:")
            for child in self.children:
                lines.append("  - %s" % ref(child.tr_id))
        else:
            lines.append("  m_Children: []")
        lines += ["  m_Father: %s" % (ref(self.parent.tr_id) if self.parent else "{fileID: 0}"),
                  "  m_RootOrder: %d" % root_order,
                  "  m_LocalEulerAnglesHint: %s" % v3(*self.rot)]
        if self.rect:
            lines += ["  m_AnchorMin: {x: 0, y: 0}",
                      "  m_AnchorMax: {x: 0, y: 0}",
                      "  m_AnchoredPosition: {x: 0, y: 0}",
                      "  m_SizeDelta: {x: 1600, y: 900}",
                      "  m_Pivot: {x: 0.5, y: 0.5}"]

        for class_id, component_id, body in self.components:
            lines.append("--- !u!%d &%d" % (class_id, component_id))
            lines.append(COMPONENT_NAMES[class_id] + ":")
            lines += ["  m_ObjectHideFlags: 0",
                      "  m_CorrespondingSourceObject: {fileID: 0}",
                      "  m_PrefabInstance: {fileID: 0}",
                      "  m_PrefabAsset: {fileID: 0}"]
            lines += body
        return lines


class SceneBuilder:
    def __init__(self):
        self.nodes = []
        self.roots = []
        self.next = 100000

    def new_id(self):
        self.next += 1
        return self.next

    # -- helpers ----------------------------------------------------------
    def empty(self, name, parent=None, pos=(0, 0, 0), rot=(0, 0, 0), layer=0, tag="Untagged", rect=False):
        return Node(self, name, parent, pos, rot, layer=layer, tag=tag, rect=rect)

    def box(self, name, parent, pos, size, material, rot=(0, 0, 0), collider=True, trigger=False,
            shadows=True, receive=True):
        node = Node(self, name, parent, pos, rot, size)
        node.mesh("cube", material, shadows, receive)
        if collider:
            node.box_collider()
        return node

    def collider_node(self, name, parent, pos, size, center=(0, 0, 0), trigger=False):
        node = Node(self, name, parent, pos)
        node.box_collider(size=size, center=center, trigger=trigger)
        return node

    def sign(self, name, parent, pos, width, height, texture, rot=(0, 0, 0)):
        node = Node(self, name, parent, pos, rot, (width, height, 0.04))
        node.mesh("cube", SIGN_TEXTURES[texture], shadows=False, receive=False)
        return node

    def prop(self, name, parent, pos, size, material, mesh="cylinder", rot=(0, 0, 0), collider=False):
        node = Node(self, name, parent, pos, rot, size)
        node.mesh(mesh, material)
        if collider:
            node.box_collider()
        return node

    def point_light(self, name, parent, pos, colour=(1.0, 0.95, 0.86), intensity=1.5, range_=9.0,
                    shadows=False):
        node = Node(self, name, parent, pos)
        node.add_component(108, [
            "  m_GameObject: %s" % ref(node.go_id),
            "  m_Enabled: 1",
            "  serializedVersion: 10",
            "  m_Type: 2",
            "  m_Shape: 0",
            "  m_Color: %s" % col(*colour),
            "  m_Intensity: %s" % fmt(intensity),
            "  m_Range: %s" % fmt(range_),
            "  m_SpotAngle: 30",
            "  m_InnerSpotAngle: 21.80208",
            "  m_CookieSize: 10",
            "  m_Shadows:",
            "    m_Type: %d" % (2 if shadows else 0),
            "    m_Resolution: -1",
            "    m_CustomResolution: -1",
            "    m_Strength: 1",
            "    m_Bias: 0.05",
            "    m_NormalBias: 0.4",
            "    m_NearPlane: 0.2",
            "    m_CullingMatrixOverride:",
            "      e00: 1",
            "      e01: 0",
            "      e02: 0",
            "      e03: 0",
            "      e10: 0",
            "      e11: 1",
            "      e12: 0",
            "      e13: 0",
            "      e20: 0",
            "      e21: 0",
            "      e22: 1",
            "      e23: 0",
            "      e30: 0",
            "      e31: 0",
            "      e32: 0",
            "      e33: 1",
            "    m_UseCullingMatrixOverride: 0",
            "  m_Cookie: {fileID: 0}",
            "  m_DrawHalo: 0",
            "  m_Flare: {fileID: 0}",
            "  m_RenderMode: 0",
            "  m_CullingMask:",
            "    serializedVersion: 2",
            "    m_Bits: 4294967295",
            "  m_RenderingLayerMask: 1",
            "  m_Lightmapping: 4",
            "  m_LightShadowCasterMode: 0",
            "  m_AreaSize: {x: 1, y: 1}",
            "  m_BounceIntensity: 1",
            "  m_ColorTemperature: 6570",
            "  m_UseColorTemperature: 0",
            "  m_BoundingSphereOverride: {x: 0, y: 0, z: 0, w: 0}",
            "  m_UseBoundingSphereOverride: 0",
            "  m_UseViewFrustumForShadowCasterCull: 1",
            "  m_ShadowRadius: 0",
            "  m_ShadowAngle: 0",
        ])
        node.script_component(URP_LIGHT_DATA, URP_LIGHT_FIELDS)
        return node

    def yaml(self):
        lines = []
        for node in self.nodes:
            order = self.roots.index(node) if node in self.roots else node.parent.children.index(node)
            lines += node.yaml(order)
        lines += ["--- !u!1660057539 &9223372036854775807", "SceneRoots:", "  m_ObjectHideFlags: 0",
                  "  m_Roots:"]
        for node in self.roots:
            lines.append("  - %s" % ref(node.tr_id))
        return "\n".join(lines) + "\n"


scene = SceneBuilder()
refs = {}


# --------------------------------------------------------------------------- #
# Shell: corridors, stairs, outdoors
# --------------------------------------------------------------------------- #

def build_shell(b):
    env = b.empty("Environment")
    upper_len = LOBBY_END - C1_START
    upper_centre = (C1_START + LOBBY_END) / 2

    # ---- upper floor (first corridor + stair lobby) ----------------------
    b.box("Floor_Corridor1", env, (0, -0.1, upper_centre),
          (HALF * 2 + WALL * 2, 0.2, upper_len), "FloorTile")
    b.box("Ceiling_Corridor1", env, (0, CEIL + 0.1, upper_centre),
          (HALF * 2 + WALL * 2, 0.2, upper_len), "CeilingPaint")
    b.box("Wall_Left", env, (-(HALF + WALL / 2), CEIL / 2, upper_centre), (WALL, CEIL, upper_len),
          "WallPaint")
    b.box("Wall_Right", env, (HALF + WALL / 2, CEIL / 2, upper_centre), (WALL, CEIL, upper_len),
          "WallPaint")
    b.box("Wall_Back", env, (0, CEIL / 2, C1_START - WALL / 2),
          (HALF * 2 + WALL * 2, CEIL, WALL), "WallPaint")
    b.box("Band_Left", env, (-(HALF - 0.01), 0.45, upper_centre), (0.02, 0.9, upper_len),
          "WallLower", shadows=False)
    b.box("Band_Right", env, (HALF - 0.01, 0.45, upper_centre), (0.02, 0.9, upper_len),
          "WallLower", shadows=False)
    b.box("Skirting_Left", env, (-(HALF - 0.03), 0.07, upper_centre), (0.06, 0.14, upper_len),
          "Trim", shadows=False)
    b.box("Skirting_Right", env, (HALF - 0.03, 0.07, upper_centre), (0.06, 0.14, upper_len),
          "Trim", shadows=False)

    # ---- wall between the lobby and the stairwell ------------------------
    side_width = HALF + WALL - STAIR_HALF
    b.box("Wall_StairLintel", env, (0, 2.75, LOBBY_END), (STAIR_HALF * 2, 0.9, WALL), "WallPaint")
    b.box("Wall_StairLeft", env, (-(STAIR_HALF + side_width / 2), CEIL / 2, LOBBY_END),
          (side_width, CEIL, WALL), "WallPaint")
    b.box("Wall_StairRight", env, ((STAIR_HALF + side_width / 2), CEIL / 2, LOBBY_END),
          (side_width, CEIL, WALL), "WallPaint")

    # ---- stairwell ------------------------------------------------------
    stair_length = LANDING_END - LOBBY_END
    stair_height = CEIL - LOWER + 0.4
    stair_centre_y = (CEIL + LOWER) / 2 + 0.1
    b.box("Wall_StairwellLeft", env, (-(STAIR_HALF + WALL / 2), stair_centre_y,
                                     (LOBBY_END + LANDING_END) / 2),
          (WALL, stair_height, stair_length), "Concrete")
    b.box("Wall_StairwellRight", env, ((STAIR_HALF + WALL / 2), stair_centre_y,
                                      (LOBBY_END + LANDING_END) / 2),
          (WALL, stair_height, stair_length), "Concrete")
    b.box("Ceiling_Stairwell", env, (0, CEIL + 0.1, (LOBBY_END + LANDING_END) / 2),
          (STAIR_HALF * 2 + WALL * 2, 0.2, stair_length), "Concrete")

    for i in range(STEPS):
        top = -RISE * (i + 1)
        bottom = LOWER - 0.1
        b.box("Step_%02d" % (i + 1), env, (0, (top + bottom) / 2, LOBBY_END + RUN * (i + 0.5)),
              (STAIR_HALF * 2, top - bottom, RUN), "StairPaint")

    b.box("Landing_Floor", env, (0, LOWER - 0.1, (STAIR_BOTTOM + LANDING_END) / 2),
          (STAIR_HALF * 2 + WALL * 2, 0.2, LANDING_END - STAIR_BOTTOM), "FloorCorridor2")
    landing_side = HALF - STAIR_HALF
    b.box("Wall_LandingEndLeft", env, (-(STAIR_HALF + landing_side / 2), LOWER + CEIL / 2,
                                       LANDING_END), (landing_side, CEIL, WALL), "WallPaint")
    b.box("Wall_LandingEndRight", env, ((STAIR_HALF + landing_side / 2), LOWER + CEIL / 2,
                                        LANDING_END), (landing_side, CEIL, WALL), "WallPaint")
    b.box("Wall_LandingLintel", env, (0, LOWER + 2.75, LANDING_END), (STAIR_HALF * 2, 0.9, WALL),
          "WallPaint")
    # The stairwell is a full-height shaft, but the doorway into the second corridor is only
    # 2.3 m high. Without this panel the strip of wall above the doorway is missing and the
    # player looks from the stairs straight over the second corridor's ceiling into the open
    # sky, with outdoor signs apparently hanging in mid-air.
    b.box("Wall_LandingAbove", env, (0, 1.55, LANDING_END),
          (STAIR_HALF * 2 + WALL * 2, 3.7, WALL), "WallPaint")

    # handrails follow the slope of the flight
    slope = math.degrees(math.atan2(RISE, RUN))
    rail_length = math.sqrt((STEPS * RUN) ** 2 + (STEPS * RISE) ** 2)
    for side, x in (("Left", -STAIR_HALF + 0.14), ("Right", STAIR_HALF - 0.14)):
        b.box("Handrail_" + side, env,
              (x, -STEPS * RISE / 2 + 0.95, LOBBY_END + STEPS * RUN / 2),
              (0.06, 0.06, rail_length), "Handrail", rot=(slope, 0, 0), shadows=False)
        for i in range(0, STEPS, 5):
            b.box("HandrailPost_%s_%02d" % (side, i), env,
                  (x, -RISE * (i + 1) + 0.48, LOBBY_END + RUN * (i + 0.5)),
                  (0.05, 0.96, 0.05), "Handrail", shadows=False)

    # ---- second corridor ------------------------------------------------
    corridor2_centre = (LANDING_END + C2_END) / 2
    corridor2_len = C2_END - LANDING_END
    b.box("Floor_Corridor2", env, (0, LOWER - 0.1, corridor2_centre), (HALF * 2, 0.2, corridor2_len),
          "FloorCorridor2")
    b.box("Ceiling_Corridor2", env, (0, LOWER + CEIL + 0.1, corridor2_centre),
          (HALF * 2, 0.2, corridor2_len), "CeilingPaint")
    b.box("Wall_Corridor2Right", env, (HALF + WALL / 2, LOWER + CEIL / 2, corridor2_centre),
          (WALL, CEIL, corridor2_len), "WallPaint")

    door_z0, door_z1 = 35.2, 36.6
    b.box("Wall_Corridor2Left_A", env, (-(HALF + WALL / 2), LOWER + CEIL / 2,
                                        (LANDING_END + door_z0) / 2),
          (WALL, CEIL, door_z0 - LANDING_END), "WallPaint")
    b.box("Wall_Corridor2Left_B", env, (-(HALF + WALL / 2), LOWER + CEIL / 2,
                                        (door_z1 + C2_END) / 2),
          (WALL, CEIL, C2_END - door_z1), "WallPaint")
    b.box("Wall_Corridor2Left_Lintel", env, (-(HALF + WALL / 2), LOWER + 2.7,
                                             (door_z0 + door_z1) / 2),
          (WALL, 1.0, door_z1 - door_z0), "WallPaint")

    # shallow recess behind the fire door (smoke source, not a walkable room)
    b.box("StoreRoom_Floor", env, (-(HALF + 0.5), LOWER - 0.1, (door_z0 + door_z1) / 2),
          (1.0, 0.2, door_z1 - door_z0), "Concrete")
    b.box("StoreRoom_Back", env, (-(HALF + 1.0), LOWER + CEIL / 2, (door_z0 + door_z1) / 2),
          (0.1, CEIL, door_z1 - door_z0 + 0.2), "Concrete")
    b.box("StoreRoom_SideA", env, (-(HALF + 0.5), LOWER + CEIL / 2, door_z0 - 0.05),
          (1.0, CEIL, 0.1), "Concrete")
    b.box("StoreRoom_SideB", env, (-(HALF + 0.5), LOWER + CEIL / 2, door_z1 + 0.05),
          (1.0, CEIL, 0.1), "Concrete")
    b.box("StoreRoom_Ceiling", env, (-(HALF + 0.5), LOWER + 2.3, (door_z0 + door_z1) / 2),
          (1.0, 0.1, door_z1 - door_z0), "CeilingPaint")
    b.box("StoreDoor_FrameTop", env, (-(HALF - 0.02), LOWER + 2.24, (door_z0 + door_z1) / 2),
          (0.14, 0.12, door_z1 - door_z0 + 0.16), "Trim")
    b.box("StoreDoor_FrameSideA", env, (-(HALF - 0.02), LOWER + 1.1, door_z0 - 0.04),
          (0.14, 2.24, 0.1), "Trim")
    b.box("StoreDoor_FrameSideB", env, (-(HALF - 0.02), LOWER + 1.1, door_z1 + 0.04),
          (0.14, 2.24, 0.1), "Trim")

    # ---- exit wall ------------------------------------------------------
    exit_side = HALF - 1.0
    b.box("Wall_ExitLeft", env, (-(1.0 + exit_side / 2), LOWER + CEIL / 2, C2_END),
          (exit_side, CEIL, WALL), "WallPaint")
    b.box("Wall_ExitRight", env, ((1.0 + exit_side / 2), LOWER + CEIL / 2, C2_END),
          (exit_side, CEIL, WALL), "WallPaint")
    b.box("Wall_ExitLintel", env, (0, LOWER + 2.75, C2_END), (2.0, 0.9, WALL), "WallPaint")
    b.box("Exit_FrameTop", env, (0, LOWER + 2.26, C2_END - 0.02), (2.2, 0.12, 0.16), "Trim")
    b.box("Exit_FrameLeft", env, (-1.06, LOWER + 1.13, C2_END - 0.02), (0.12, 2.26, 0.16), "Trim")
    b.box("Exit_FrameRight", env, (1.06, LOWER + 1.13, C2_END - 0.02), (0.12, 2.26, 0.16), "Trim")

    # ---- outdoors -------------------------------------------------------
    b.box("Outdoor_Ground", env, (0, LOWER - 0.1, (C2_END + OUT_END) / 2),
          (22, 0.2, OUT_END - C2_END), "FloorOutdoor")
    b.box("Outdoor_Kerb", env, (0, LOWER + 0.02, C2_END + 0.6), (22, 0.04, 1.2), "Concrete",
          shadows=False)
    b.box("Facade_Left", env, (-7.5, LOWER + 3.0, C2_END + 0.15), (11, 6.0, 0.4), "Concrete")
    b.box("Facade_Right", env, (7.5, LOWER + 3.0, C2_END + 0.15), (11, 6.0, 0.4), "Concrete")
    b.box("Facade_Lintel", env, (0, LOWER + 4.0, C2_END + 0.15), (4.4, 4.0, 0.4), "Concrete")

    for ix, x in enumerate((-6.5, -2.5)):
        for iz, z in enumerate((48.5, 52.5)):
            b.box("Shelter_Post_%d%d" % (ix, iz), env, (x, LOWER + 1.3, z), (0.18, 2.6, 0.18),
                  "FenceMetal")
    b.box("Shelter_Roof", env, (-4.5, LOWER + 2.7, 50.5), (5.0, 0.16, 5.0), "Concrete")
    b.box("Shelter_BackPanel", env, (-6.9, LOWER + 1.3, 50.5), (0.1, 2.6, 4.0), "Concrete")

    for i in range(9):
        x = -10 + i * 2.5
        if abs(x) < 3.5:
            continue
        b.box("FencePost_%02d" % i, env, (x, LOWER + 0.7, OUT_END - 1.0), (0.12, 1.4, 0.12),
              "FenceMetal")
    b.box("FenceRail", env, (0, LOWER + 1.25, OUT_END - 1.0), (20, 0.08, 0.08), "FenceMetal")
    b.box("Planter_A", env, (-8.0, LOWER + 0.3, 56.0), (1.6, 0.6, 1.6), "Planter")
    b.box("Planter_B", env, (8.0, LOWER + 0.3, 56.0), (1.6, 0.6, 1.6), "Planter")
    b.prop("Planter_Bush_A", env, (-8.0, LOWER + 0.75, 56.0), (1.3, 0.5, 1.3), "GreenLeaf",
           mesh="sphere")
    b.prop("Planter_Bush_B", env, (8.0, LOWER + 0.75, 56.0), (1.3, 0.5, 1.3), "GreenLeaf",
           mesh="sphere")

    b.prop("Assembly_Marker", env, (0, LOWER + 0.02, 51.0), (3.2, 0.01, 3.2), "SafetyYellow",
           mesh="cylinder")
    b.box("Assembly_Post", env, (0, LOWER + 1.2, 53.5), (0.12, 2.4, 0.12), "FenceMetal")
    b.sign("Assembly_Sign", env, (0, LOWER + 2.15, 53.42), 2.4, 1.6, "assembly_point",
           rot=(0, 180, 0))
    for i, x in enumerate((-2.6, 2.6)):
        b.prop("Cone_%d" % i, env, (x, LOWER + 0.35, 49.0), (0.5, 0.7, 0.5), "SafetyYellow")

    return env


# --------------------------------------------------------------------------- #
# Signage, lights, decorative doors
# --------------------------------------------------------------------------- #

def build_signage(b, env):
    # left wall of the first corridor (faces +X)
    b.sign("Sign_FireAction", env, (-(HALF - 0.03), 1.8, 3.0), 1.0, 1.35, "fire_action_notice",
           rot=(0, 90, 0))
    b.sign("Sign_FirstAid", env, (-(HALF - 0.03), 1.7, 13.6), 1.1, 1.45, "first_aid_poster",
           rot=(0, 90, 0))
    b.sign("Sign_SmokeWarning", env, (-(HALF - 0.03), 1.7, 33.0), 1.2, 0.8, "smoke_warning",
           rot=(0, 90, 0))
    b.sign("Sign_FireDoor", env, (-(HALF - 0.03), 1.95, 37.5), 1.0, 0.66, "fire_door",
           rot=(0, 90, 0))
    b.sign("Sign_NoLift", env, (-(HALF - 0.03), 1.8, 20.6), 1.0, 1.3, "no_lift", rot=(0, 90, 0))

    # right wall of the first corridor (faces -X)
    b.sign("Sign_InfoBoard", env, (HALF - 0.03, 1.6, 7.4), 1.6, 1.0, "info_board", rot=(0, -90, 0))
    b.sign("Sign_StairsLobby", env, (HALF - 0.03, 1.85, 19.6), 1.3, 0.87, "stairs_sign",
           rot=(0, -90, 0))

    b.sign("Sign_ExitCorridor1", env, (0, 2.62, C1_END - 0.14), 1.6, 0.8, "exit_sign",
           rot=(0, 180, 0))
    b.sign("Sign_AssemblyDirectionLobby", env, (-(HALF - 0.03), 2.45, 18.3), 1.2, 0.38,
           "assembly_direction", rot=(0, 90, 0))

    for z in (30.5, 38.5, 42.0):
        b.sign("Sign_Exit_C2_%s" % str(z).replace(".", "_"), env, (-(HALF - 0.03), 2.5, z),
               1.1, 0.55, "exit_sign", rot=(0, 90, 0))
    b.sign("Sign_ReferencesC2", env, (HALF - 0.03, 1.6, 31.2), 1.3, 0.98, "references",
           rot=(0, -90, 0))
    b.sign("Sign_ExitAboveDoor", env, (0, LOWER + 2.62, C2_END - 0.16), 1.6, 0.8, "exit_sign",
           rot=(0, 180, 0))
    b.sign("Sign_AssemblyDirection", env, (0, LOWER + 2.25, C2_END + 0.42), 2.2, 0.7,
           "assembly_direction", rot=(0, 0, 0))
    b.sign("Sign_ReferencesOutdoor", env, (-4.5, LOWER + 1.5, 50.55), 1.6, 1.2, "references",
           rot=(0, 0, 0))


def build_lights(b, env):
    warm = (1.0, 0.95, 0.86)
    for i, z in enumerate((2.5, 8.0, 13.5, 17.2)):
        b.box("LightFixture_C1_%d" % i, env, (0, CEIL - 0.04, z), (0.7, 0.06, 1.5), "LampPanel",
              collider=False, shadows=False)
        b.point_light("Light_C1_%d" % i, env, (0, CEIL - 0.35, z), warm, 1.3, 9.5)
    b.box("LightFixture_Lobby", env, (0, CEIL - 0.04, 19.5), (0.7, 0.06, 1.3), "LampPanel",
          collider=False, shadows=False)
    b.point_light("Light_Lobby", env, (0, CEIL - 0.35, 19.5), warm, 1.2, 8.0)

    b.box("LightFixture_Stairs", env, (0, CEIL - 0.04, 23.2), (0.6, 0.06, 1.2), "LampPanel",
          collider=False, shadows=False)
    b.point_light("Light_StairsUpper", env, (0, CEIL - 0.4, 22.8), warm, 1.1, 8.0)
    b.point_light("Light_StairsLower", env, (0, LOWER + 2.0, 26.0), warm, 1.0, 7.0)

    for i, z in enumerate((30.5, 36.0, 41.5)):
        b.box("LightFixture_C2_%d" % i, env, (0, LOWER + CEIL - 0.04, z), (0.7, 0.06, 1.4),
              "LampPanel", collider=False, shadows=False)
        b.point_light("Light_C2_%d" % i, env, (0, LOWER + CEIL - 0.35, z), warm, 1.25, 9.0)

    b.box("LightFixture_Shelter", env, (-4.5, LOWER + 2.6, 50.5), (1.0, 0.06, 1.0), "LampPanel",
          collider=False, shadows=False)
    b.point_light("Light_Shelter", env, (-4.5, LOWER + 2.4, 50.5), (1.0, 0.92, 0.8), 1.3, 9.0)
    b.point_light("Light_ExitOutside", env, (0, LOWER + 2.8, C2_END + 1.6), (1.0, 0.95, 0.85),
                  1.2, 8.0)


def build_side_doors(b, env):
    for i, (side, z) in enumerate((("Left", 5.6), ("Right", 12.4), ("Left", 15.4))):
        x = -(HALF - 0.05) if side == "Left" else (HALF - 0.05)
        b.box("SideDoor_%d" % i, env, (x, 1.05, z), (0.08, 2.1, 0.95), "DoorMetal")
        b.box("SideDoorFrame_%d_Top" % i, env, (x, 2.14, z), (0.12, 0.1, 1.15), "Trim")
        b.box("SideDoorFrame_%d_A" % i, env, (x, 1.05, z - 0.52), (0.12, 2.2, 0.1), "Trim")
        b.box("SideDoorFrame_%d_B" % i, env, (x, 1.05, z + 0.52), (0.12, 2.2, 0.1), "Trim")


# --------------------------------------------------------------------------- #
# Section B props
# --------------------------------------------------------------------------- #

def build_extinguisher_model(b, parent, name, label_texture, pos, scale=1.0, body_material="ExtinguisherRed"):
    root = b.empty(name, parent, pos)
    root.scale = (scale, scale, scale)
    b.prop("Body", root, (0, 0.33, 0), (0.17, 0.33, 0.17), body_material, mesh="cylinder")
    b.prop("Base", root, (0, 0.02, 0), (0.19, 0.04, 0.19), "ExtinguisherBlack", mesh="cylinder")
    b.prop("Shoulder", root, (0, 0.66, 0), (0.15, 0.05, 0.15), body_material, mesh="cylinder")
    b.prop("Valve", root, (0, 0.72, 0), (0.06, 0.06, 0.06), "Metal", mesh="cylinder")
    b.box("Handle", root, (0.055, 0.78, 0), (0.02, 0.11, 0.07), "DarkMetal", collider=False)
    b.box("Lever", root, (-0.02, 0.8, 0), (0.14, 0.02, 0.03), "DarkMetal", collider=False)
    b.box("Hose", root, (0.09, 0.6, 0.02), (0.03, 0.3, 0.03), "Rubber", collider=False)
    b.box("Nozzle", root, (0.09, 0.45, 0.03), (0.05, 0.1, 0.05), "ExtinguisherBlack", collider=False)
    b.sign("Label", root, (0, 0.36, 0.092), 0.16, 0.14, label_texture)
    return root


def build_practice_extinguisher(b, parent, pos):
    """A small ABC powder unit with moving parts, used for the PASS demonstration.

    The parts are separate transforms so the script can animate the real actions:
      Head   - valve, hose and horn; it turns to aim and sweeps across the fire
      LeverPivot - the squeeze handle
      Pin    - the safety pin, which is pulled out and dropped onto the table
      SprayOrigin - where the powder leaves the horn, pointing at the fire
    """
    root = b.empty("PracticeExtinguisher", parent, pos)
    # Slightly larger than a real 2 kg unit so the pin, lever and horn read clearly when the
    # player watches the demonstration from a couple of metres away.
    root.scale = (1.2, 1.2, 1.2)
    b.prop("Body", root, (0, 0.33, 0), (0.17, 0.33, 0.17), "ExtinguisherRed", mesh="cylinder")
    b.prop("Base", root, (0, 0.02, 0), (0.19, 0.04, 0.19), "ExtinguisherBlack", mesh="cylinder")
    b.prop("Shoulder", root, (0, 0.66, 0), (0.15, 0.05, 0.15), "ExtinguisherRed", mesh="cylinder")
    b.sign("Label", root, (0, 0.34, 0.092), 0.2, 0.22, "ext_abc")

    # Valve, handle, hose and horn all sit on one pivot so aiming turns the whole head.
    head = b.empty("Head", root, (0, 0.72, 0), (-0.0, -34.0, 0.0))
    b.prop("Valve", head, (0, 0.0, 0), (0.06, 0.06, 0.06), "Metal", mesh="cylinder")
    b.box("HandleGrip", head, (0, 0.1, 0), (0.02, 0.13, 0.08), "DarkMetal", collider=False)

    lever = b.empty("LeverPivot", head, (-0.08, 0.06, 0))
    b.box("Lever", lever, (0.08, 0, 0), (0.16, 0.025, 0.04), "DarkMetal", collider=False)

    # Safety pin through the valve: a small stem with a ring on the end.
    pin = b.empty("Pin", head, (0.02, 0.02, 0.0))
    b.box("PinStem", pin, (0, 0, 0.0), (0.014, 0.014, 0.09), "Metal", collider=False)
    b.prop("PinRing", pin, (0, 0, 0.062), (0.055, 0.055, 0.012), "Metal", mesh="cylinder",
           rot=(90, 0, 0))

    b.box("Hose", head, (0.12, -0.09, 0), (0.18, 0.032, 0.032), "Rubber", collider=False)
    b.prop("Horn", head, (0.24, -0.11, 0), (0.14, 0.075, 0.075), "ExtinguisherBlack",
           mesh="cylinder", rot=(0, 0, 90))
    # Local +Z of this empty points along the horn, out toward the fire.
    spray = b.empty("SprayOrigin", head, (0.33, -0.13, 0), (0, 90, 0))
    return root, head, lever, pin, spray


def build_section_b(b, env):
    # ---- alarm call point (left wall) -----------------------------------
    alarm_root = b.empty("AlarmCallPoint", env, (-(HALF - 0.1), 1.35, 4.2))
    b.box("BackPlate", alarm_root, (0, 0, 0), (0.06, 0.42, 0.32), "ExtinguisherRed", collider=False)
    b.box("Housing", alarm_root, (-0.06, 0, 0), (0.14, 0.3, 0.22), "ExtinguisherRed", collider=False)
    strobe = b.prop("Strobe", alarm_root, (-0.14, 0.06, 0), (0.09, 0.06, 0.09), "AlarmStrobe",
                    mesh="sphere")
    b.box("Handle", alarm_root, (-0.13, -0.07, 0), (0.05, 0.16, 0.12), "SignWhite", collider=False)
    b.sign("AlarmSign", alarm_root, (-0.152, 0.27, 0), 0.34, 0.34, "alarm_point", rot=(0, -90, 0))
    b.collider_node("AlarmInteractBox", alarm_root, (-0.02, 0, 0), (0.3, 0.55, 0.45))
    refs["alarm"] = alarm_root

    # ---- emergency phone (right wall) -----------------------------------
    phone_root = b.empty("EmergencyPhone", env, (HALF - 0.1, 1.4, 6.4))
    b.box("Phone_BackPlate", phone_root, (0, 0, 0), (0.06, 0.62, 0.5), "ExtinguisherRed",
          collider=False)
    b.box("Phone_Body", phone_root, (0.08, -0.08, 0), (0.1, 0.34, 0.26), "DarkMetal",
          collider=False)
    b.box("Phone_Handset", phone_root, (0.15, -0.04, -0.16), (0.06, 0.28, 0.06),
          "ExtinguisherBlack", collider=False)
    b.sign("Phone_112", phone_root, (0.135, 0.06, 0), 0.2, 0.2, "call_112", rot=(0, -90, 0))
    b.collider_node("PhoneInteractBox", phone_root, (0.02, -0.05, 0), (0.34, 0.7, 0.55))
    refs["phone_root"] = phone_root

    # ---- mask teaching display (left wall) -------------------------------
    mask_root = b.empty("MaskDisplay", env, (-(HALF - 0.06), 1.3, 9.4))
    b.box("Mask_Case", mask_root, (0.1, 0, 0), (0.2, 0.95, 1.6), "DoorMetal", collider=False)
    b.box("Mask_Glass", mask_root, (0.21, 0, 0), (0.02, 0.8, 1.45), "SignWhite", collider=False,
          shadows=False)
    b.prop("Mask_Surgical", mask_root, (0.24, 0.05, -0.45), (0.06, 0.16, 0.22), "SignWhite",
           mesh="sphere")
    b.prop("Mask_N95", mask_root, (0.24, 0.05, 0), (0.09, 0.19, 0.24), "LampPanel", mesh="sphere")
    b.prop("Mask_Hood", mask_root, (0.24, 0.05, 0.48), (0.16, 0.26, 0.26), "Trim", mesh="sphere")
    b.collider_node("MaskInteractBox", mask_root, (0.12, 0, 0), (0.4, 1.1, 1.7))
    refs["mask_root"] = mask_root

    # ---- six labelled extinguisher models (right wall) -------------------
    labels = [("ext_water", "Water", "ExtinguisherRed"),
              ("ext_foam", "Foam", "ExtinguisherRed"),
              ("ext_abc", "ABC_Powder", "ExtinguisherRed"),
              ("ext_co2", "CO2", "ExtinguisherBlack"),
              ("ext_wet", "Wet_Chemical", "ExtinguisherRed"),
              ("ext_d", "Class_D", "ExtinguisherRed")]
    cards = []
    for i, (texture, name, body_material) in enumerate(labels):
        z = 10.9 + i * 0.94
        root = b.empty("ExtinguisherModel_" + name, env, (HALF - 0.45, 1.25, z))
        b.prop("Body", root, (0, 0, 0), (0.17, 0.36, 0.17), body_material, mesh="cylinder")
        b.prop("Neck", root, (0, 0.4, 0), (0.06, 0.06, 0.06), "Metal", mesh="cylinder")
        b.box("Handle", root, (0, 0.47, 0), (0.16, 0.03, 0.05), "DarkMetal", collider=False)
        b.box("Bracket", root, (0.13, 0.1, 0), (0.1, 0.4, 0.12), "DarkMetal", collider=False)
        b.sign("Label", root, (-0.09, 0.0, 0), 0.22, 0.11, texture, rot=(0, -90, 0))
        card = b.collider_node("Card_" + name, root, (0, 0.15, 0), (0.55, 0.95, 0.45))
        cards.append((card, texture))

    # ---- single contained fire demonstration ----------------------------
    fire_root = b.empty("ContainedFireDemo", env, (1.1, 0.0, 16.4))
    b.prop("Bin", fire_root, (0, 0.36, 0), (0.62, 0.72, 0.62), "Charred", mesh="cylinder",
           collider=True)
    b.prop("BinRim", fire_root, (0, 0.72, 0), (0.68, 0.05, 0.68), "DarkMetal", mesh="cylinder")
    b.prop("Ash", fire_root, (0, 0.68, 0), (0.5, 0.03, 0.5), "Ash", mesh="cylinder")
    b.sign("Fire_Sign", fire_root, (0, 1.6, 0), 0.55, 0.55, "training_fire", rot=(0, 180, 0))
    b.box("Fire_SignPost", fire_root, (0, 1.15, -0.03), (0.05, 1.0, 0.05), "FenceMetal",
          collider=False)
    fire_view = b.collider_node("FireViewPoint", fire_root, (0, 0.35, 0), (1.0, 1.2, 1.0))
    refs["fire_root"] = fire_root
    refs["fire_view"] = fire_view

    # ---- extinguisher practice station ----------------------------------
    station = b.empty("ExtinguisherStation", env, (-1.25, 0.0, 16.3))
    b.box("Station_Top", station, (0, 0.42, 0), (0.55, 0.06, 0.5), "DoorMetal", collider=False)
    b.box("Station_Leg", station, (0, 0.2, 0), (0.12, 0.4, 0.12), "DarkMetal", collider=False)
    b.box("Station_Base", station, (0, 0.02, 0), (0.5, 0.04, 0.45), "DarkMetal", collider=False)
    unit = build_practice_extinguisher(b, station, (0, 0.45, 0))
    refs["station_unit"] = unit[0]
    refs["station_head"] = unit[1]
    refs["station_lever"] = unit[2]
    refs["station_pin"] = unit[3]
    refs["station_spray"] = unit[4]
    b.collider_node("StationInteractBox", station, (0, 0.75, 0), (0.7, 1.5, 0.7))
    refs["station"] = station

    return cards


# --------------------------------------------------------------------------- #
# Section C hazard props
# --------------------------------------------------------------------------- #

def build_hazard(b, env):
    # The smoke sits just past the open store-room fire door: the player can stand
    # beside the door (and reach it with E) before the dense smoke blocks the way.
    smoke_root = b.empty("CorridorSmokeHazard", env, (0, LOWER, 38.9))
    safe = b.empty("SmokeSafePoint", env, (0, LOWER + 0.05, 32.4))
    refs["smoke_root"] = smoke_root
    refs["smoke_safe"] = safe

    door = b.empty("StoreRoomFireDoor", env, (-(HALF - 0.045), LOWER + 1.12, 36.6))
    pivot = b.empty("Pivot", door, (0, 0, 0))
    leaf = b.box("Leaf", pivot, (0, 0, -0.7), (0.07, 2.24, 1.36), "DoorGreen", collider=False)
    leaf.box_collider()
    b.box("Leaf_PushBar", pivot, (-0.07, 0, -0.7), (0.05, 0.08, 1.2), "Metal", collider=False)
    b.box("Leaf_Handle", pivot, (-0.08, -0.1, -0.15), (0.06, 0.06, 0.16), "Metal", collider=False)
    refs["store_door"] = door
    refs["store_pivot"] = pivot

    exit_doors = b.empty("ExitDoors", env, (-1.0, LOWER + 1.14, C2_END - 0.06))
    exit_pivot = b.empty("Pivot", exit_doors, (0, 0, 0))
    for i, offset in enumerate((0.5, 1.5)):
        leaf_node = b.box("Leaf_%d" % i, exit_pivot, (offset, 0, 0), (1.0, 2.24, 0.07),
                          "DoorGreen", collider=False)
        leaf_node.box_collider()
        b.box("Leaf_%d_PushBar" % i, exit_pivot, (offset, 0, -0.08), (0.8, 0.08, 0.05), "Metal",
              collider=False)
        b.box("Leaf_%d_Glass" % i, exit_pivot, (offset, 0.45, -0.05), (0.62, 0.9, 0.02),
              "SignWhite", collider=False, shadows=False)
    refs["exit_doors"] = exit_doors
    refs["exit_pivot"] = exit_pivot


def build_checkpoints(b):
    root = b.empty("Checkpoints")
    specs = [
        ("checkpoint_lobby", "Stair lobby", (0, 1.0, 19.2), (3.8, 2.2, 1.2)),
        ("checkpoint_stairs_bottom", "Bottom of the stairs", (0, LOWER + 1.0, 27.7),
         (3.0, 2.2, 1.2)),
        ("checkpoint_corridor2", "Second corridor", (0, LOWER + 1.0, 31.0), (3.8, 2.2, 1.0)),
        ("checkpoint_smoke_approach", "Smoke ahead", (0, LOWER + 1.0, 33.6), (3.8, 2.2, 1.0)),
        ("checkpoint_assembly", "Assembly point", (0, LOWER + 1.0, 50.5), (4.0, 2.2, 2.0)),
    ]
    nodes = []
    for name, display, pos, size in specs:
        node = b.empty(name, root, pos)
        node.box_collider(size=size, trigger=True)
        nodes.append((node, name, display))
    return nodes


# --------------------------------------------------------------------------- #
# Player, UI, lights, lesson
# --------------------------------------------------------------------------- #

def build_player(b):
    start = b.empty("PlayerStart", None, (0, 0.02, 0.8))
    player = b.empty("Player", None, (0, 0.02, 0.8), tag="Player")
    player.add_component(143, [
        "  m_GameObject: %s" % ref(player.go_id),
        "  m_Material: {fileID: 0}",
        "  m_IncludeLayers:",
        "    serializedVersion: 2",
        "    m_Bits: 0",
        "  m_ExcludeLayers:",
        "    serializedVersion: 2",
        "    m_Bits: 0",
        "  m_LayerOverridePriority: 0",
        "  m_IsTrigger: 0",
        "  m_ProvidesContacts: 0",
        "  m_Enabled: 1",
        "  serializedVersion: 3",
        "  m_Height: 1.75",
        "  m_Radius: 0.28",
        "  m_SlopeLimit: 50",
        "  m_StepOffset: 0.32",
        "  m_SkinWidth: 0.04",
        "  m_MinMoveDistance: 0.001",
        "  m_Center: {x: 0, y: 0.9, z: 0}",
    ])

    camera_node = b.empty("Main Camera", player, (0, 1.62, 0), tag="MainCamera")
    camera_id = camera_node.add_component(20, [
        "  m_GameObject: %s" % ref(camera_node.go_id),
        "  m_Enabled: 1",
        "  serializedVersion: 2",
        "  m_ClearFlags: 1",
        "  m_BackGroundColor: {r: 0.55, g: 0.65, b: 0.78, a: 1}",
        "  m_projectionMatrixMode: 1",
        "  m_GateFitMode: 2",
        "  m_FOVAxisMode: 0",
        "  m_Iso: 200",
        "  m_ShutterSpeed: 0.005",
        "  m_Aperture: 16",
        "  m_FocusDistance: 10",
        "  m_FocalLength: 50",
        "  m_BladeCount: 5",
        "  m_Curvature: {x: 2, y: 11}",
        "  m_BarrelClipping: 0.25",
        "  m_Anamorphism: 0",
        "  m_SensorSize: {x: 36, y: 24}",
        "  m_LensShift: {x: 0, y: 0}",
        "  m_NormalizedViewPortRect:",
        "    serializedVersion: 2",
        "    x: 0",
        "    y: 0",
        "    width: 1",
        "    height: 1",
        "  near clip plane: 0.05",
        "  far clip plane: 120",
        "  field of view: 70",
        "  orthographic: 0",
        "  orthographic size: 5",
        "  m_Depth: -1",
        "  m_CullingMask:",
        "    serializedVersion: 2",
        "    m_Bits: 4294967295",
        "  m_RenderingPath: -1",
        "  m_TargetTexture: {fileID: 0}",
        "  m_TargetDisplay: 0",
        "  m_TargetEye: 3",
        "  m_HDR: 1",
        "  m_AllowMSAA: 1",
        "  m_AllowDynamicResolution: 0",
        "  m_ForceIntoRT: 0",
        "  m_OcclusionCulling: 0",
        "  m_StereoConvergence: 10",
        "  m_StereoSeparation: 0.022",
    ])
    camera_node.script_component(URP_CAMERA_DATA, URP_CAMERA_FIELDS)
    camera_node.add_component(81, ["  m_GameObject: %s" % ref(camera_node.go_id), "  m_Enabled: 1"])

    player_script = player.mono("PlayerController", [
        "  playerCamera: {fileID: %d}" % camera_id,
        "  walkSpeed: 2.4",
        "  runSpeed: 4.2",
        "  mouseSensitivity: 2.2",
        "  eyeHeight: 1.62",
        "  gravity: -18",
        "  interactDistance: 3.2",
        "  interactRadius: 0.22",
        "  interactionMask:",
        "    serializedVersion: 2",
        "    m_Bits: 4294967295",
        "  vrMoveSpeed: 2",
        "  snapTurnDegrees: 30",
        "  driveCameraFromXrDevice: 1",
    ])
    refs["start"] = start
    refs["player"] = player
    refs["player_script"] = player_script
    refs["camera"] = camera_node
    return player


def build_ui(b):
    ui = b.empty("TrainingUI", None, (0, 1.6, 2.3), layer=5, rect=True)
    ui.scale = (0.00115, 0.00115, 0.00115)
    ui.add_component(223, [
        "  m_GameObject: %s" % ref(ui.go_id),
        "  m_Enabled: 1",
        "  serializedVersion: 3",
        "  m_RenderMode: 2",
        "  m_Camera: %s" % ref(refs["camera"].components[0][1]),
        "  m_PlaneDistance: 100",
        "  m_PixelPerfect: 0",
        "  m_ReceivesEvents: 1",
        "  m_OverrideSorting: 0",
        "  m_OverridePixelPerfect: 0",
        "  m_SortingBucketNormalizedSize: 0",
        "  m_VertexColorAlwaysGammaSpace: 0",
        "  m_AdditionalShaderChannelsFlag: 25",
        "  m_UpdateRectTransformForStandalone: 0",
        "  m_SortingLayerID: 0",
        "  m_SortingOrder: 0",
        "  m_TargetDisplay: 0",
    ])
    ui.script_component(UGUI["CanvasScaler"], [
        "  m_UiScaleMode: 0",
        "  m_ReferencePixelsPerUnit: 100",
        "  m_ScaleFactor: 1",
        "  m_ReferenceResolution: {x: 1600, y: 900}",
        "  m_ScreenMatchMode: 0",
        "  m_MatchWidthOrHeight: 0",
        "  m_PhysicalUnit: 3",
        "  m_FallbackScreenDPI: 96",
        "  m_DefaultSpriteDPI: 96",
        "  m_DynamicPixelsPerUnit: 1",
        "  m_PresetInfoIsWorld: 1",
    ])
    ui.script_component(UGUI["GraphicRaycaster"], [
        "  m_IgnoreReversedGraphics: 1",
        "  m_BlockingObjects: 0",
        "  m_BlockingMask:",
        "    serializedVersion: 2",
        "    m_Bits: 4294967295",
    ])
    ui.mono("LessonUI", [
        "  fontRegular: %s" % font_ref("regular"),
        "  fontBold: %s" % font_ref("bold"),
        "  panelColour: {r: 0.055, g: 0.07, b: 0.1, a: 0.94}",
        "  accentColour: {r: 1, g: 0.72, b: 0.25, a: 1}",
        "  bodyColour: {r: 0.93, g: 0.94, b: 0.96, a: 1}",
        "  dangerColour: {r: 0.72, g: 0.13, b: 0.1, a: 0.96}",
    ])
    ui.mono("HudFollower", [
        "  target: %s" % ref(refs["camera"].tr_id),
        "  distance: 1.55",
        "  minDistance: 0.15",
        "  wallClearance: 0.12",
        "  occlusionMask:",
        "    serializedVersion: 2",
        "    m_Bits: 4294967295",
        "  verticalOffset: -0.02",
        "  followSpeed: 10",
        "  followRotation: 1",
        "  designSize: {x: 1600, y: 900}",
        "  fill: 0.98",
        "  sourceCamera: %s" % ref(refs["camera"].components[0][1]),
    ])
    refs["ui"] = ui

    event_system = b.empty("EventSystem")
    event_system.script_component(UGUI["EventSystem"], [
        "  m_FirstSelected: {fileID: 0}",
        "  m_sendNavigationEvents: 1",
        "  m_DragThreshold: 10",
    ])
    event_system.script_component(UGUI["StandaloneInputModule"], [
        "  m_HorizontalAxis: Horizontal",
        "  m_VerticalAxis: Vertical",
        "  m_SubmitButton: Submit",
        "  m_CancelButton: Cancel",
        "  m_InputActionsPerSecond: 10",
        "  m_RepeatDelay: 0.5",
        "  m_ForceModuleActive: 0",
    ])


def build_sun(b):
    sun = b.empty("Directional Light", None, (0, 24, 10), (52, 35, 0))
    sun.add_component(108, [
        "  m_GameObject: %s" % ref(sun.go_id),
        "  m_Enabled: 1",
        "  serializedVersion: 10",
        "  m_Type: 1",
        "  m_Shape: 0",
        "  m_Color: {r: 1, g: 0.96, b: 0.9, a: 1}",
        "  m_Intensity: 1.15",
        "  m_Range: 30",
        "  m_SpotAngle: 30",
        "  m_InnerSpotAngle: 21.80208",
        "  m_CookieSize: 10",
        "  m_Shadows:",
        "    m_Type: 2",
        "    m_Resolution: -1",
        "    m_CustomResolution: -1",
        "    m_Strength: 0.85",
        "    m_Bias: 0.05",
        "    m_NormalBias: 0.4",
        "    m_NearPlane: 0.2",
        "    m_CullingMatrixOverride:",
        "      e00: 1",
        "      e01: 0",
        "      e02: 0",
        "      e03: 0",
        "      e10: 0",
        "      e11: 1",
        "      e12: 0",
        "      e13: 0",
        "      e20: 0",
        "      e21: 0",
        "      e22: 1",
        "      e23: 0",
        "      e30: 0",
        "      e31: 0",
        "      e32: 0",
        "      e33: 1",
        "    m_UseCullingMatrixOverride: 0",
        "  m_Cookie: {fileID: 0}",
        "  m_DrawHalo: 0",
        "  m_Flare: {fileID: 0}",
        "  m_RenderMode: 0",
        "  m_CullingMask:",
        "    serializedVersion: 2",
        "    m_Bits: 4294967295",
        "  m_RenderingLayerMask: 1",
        "  m_Lightmapping: 4",
        "  m_LightShadowCasterMode: 0",
        "  m_AreaSize: {x: 1, y: 1}",
        "  m_BounceIntensity: 1",
        "  m_ColorTemperature: 6570",
        "  m_UseColorTemperature: 0",
        "  m_BoundingSphereOverride: {x: 0, y: 0, z: 0, w: 0}",
        "  m_UseBoundingSphereOverride: 0",
        "  m_UseViewFrustumForShadowCasterCull: 1",
        "  m_ShadowRadius: 0",
        "  m_ShadowAngle: 0",
    ])
    sun.script_component(URP_LIGHT_DATA, URP_LIGHT_FIELDS)


SCENE_HEADER = """%YAML 1.1
%TAG !u! tag:unity3d.com,2011:
--- !u!29 &1
OcclusionCullingSettings:
  m_ObjectHideFlags: 0
  serializedVersion: 2
  m_OcclusionBakeSettings:
    smallestOccluder: 5
    smallestHole: 0.25
    backfaceThreshold: 100
  m_SceneGUID: 00000000000000000000000000000000
  m_OcclusionCullingData: {fileID: 0}
--- !u!104 &2
RenderSettings:
  m_ObjectHideFlags: 0
  serializedVersion: 9
  m_Fog: 0
  m_FogColor: {r: 0.55, g: 0.58, b: 0.62, a: 1}
  m_FogMode: 3
  m_FogDensity: 0.01
  m_LinearFogStart: 0
  m_LinearFogEnd: 300
  m_AmbientSkyColor: {r: 0.5, g: 0.52, b: 0.55, a: 1}
  m_AmbientEquatorColor: {r: 0.42, g: 0.44, b: 0.47, a: 1}
  m_AmbientGroundColor: {r: 0.28, g: 0.28, b: 0.29, a: 1}
  m_AmbientIntensity: 1
  m_AmbientMode: 3
  m_SubtractiveShadowColor: {r: 0.42, g: 0.478, b: 0.627, a: 1}
  m_SkyboxMaterial: {fileID: 10304, guid: 0000000000000000f000000000000000, type: 0}
  m_HaloStrength: 0.5
  m_FlareStrength: 1
  m_FlareFadeSpeed: 3
  m_HaloTexture: {fileID: 0}
  m_SpotCookie: {fileID: 10001, guid: 0000000000000000e000000000000000, type: 0}
  m_DefaultReflectionMode: 0
  m_DefaultReflectionResolution: 128
  m_ReflectionBounces: 1
  m_ReflectionIntensity: 1
  m_CustomReflection: {fileID: 0}
  m_Sun: {fileID: 0}
  m_IndirectSpecularColor: {r: 0.18, g: 0.22, b: 0.3, a: 1}
  m_UseRadianceAmbientProbe: 0
--- !u!157 &3
LightmapSettings:
  m_ObjectHideFlags: 0
  serializedVersion: 12
  m_GIWorkflowMode: 1
  m_GISettings:
    serializedVersion: 2
    m_BounceScale: 1
    m_IndirectOutputScale: 1
    m_AlbedoBoost: 1
    m_EnvironmentLightingMode: 0
    m_EnableBakedLightmaps: 0
    m_EnableRealtimeLightmaps: 0
  m_LightmapEditorSettings:
    serializedVersion: 12
    m_Resolution: 2
    m_BakeResolution: 40
    m_AtlasSize: 1024
    m_AO: 0
    m_AOMaxDistance: 1
    m_CompAOExponent: 1
    m_CompAOExponentDirect: 0
    m_ExtractAmbientOcclusion: 0
    m_Padding: 2
    m_LightmapParameters: {fileID: 0}
    m_LightmapsBakeMode: 1
    m_TextureCompression: 1
    m_FinalGather: 0
    m_FinalGatherFiltering: 1
    m_FinalGatherRayCount: 256
    m_ReflectionCompression: 2
    m_MixedBakeMode: 2
    m_BakeBackend: 1
    m_PVRSampling: 1
    m_PVRDirectSampleCount: 32
    m_PVRSampleCount: 512
    m_PVRBounces: 2
    m_PVREnvironmentSampleCount: 256
    m_PVREnvironmentReferencePointCount: 2048
    m_PVRFilteringMode: 1
    m_PVRDenoiserTypeDirect: 1
    m_PVRDenoiserTypeIndirect: 1
    m_PVRDenoiserTypeAO: 1
    m_PVRFilterTypeDirect: 0
    m_PVRFilterTypeIndirect: 0
    m_PVRFilterTypeAO: 0
    m_PVREnvironmentMIS: 1
    m_PVRCulling: 1
    m_PVRFilteringGaussRadiusDirect: 1
    m_PVRFilteringGaussRadiusIndirect: 5
    m_PVRFilteringGaussRadiusAO: 2
    m_PVRFilteringAtrousPositionSigmaDirect: 0.5
    m_PVRFilteringAtrousPositionSigmaIndirect: 2
    m_PVRFilteringAtrousPositionSigmaAO: 1
    m_ExportTrainingData: 0
    m_TrainingDataDestination: TrainingData
    m_LightProbeSampleCountMultiplier: 4
  m_LightingDataAsset: {fileID: 0}
  m_LightingSettings: {fileID: 0}
--- !u!196 &4
NavMeshSettings:
  serializedVersion: 2
  m_ObjectHideFlags: 0
  m_BuildSettings:
    serializedVersion: 3
    agentTypeID: 0
    agentRadius: 0.5
    agentHeight: 2
    agentSlope: 45
    agentClimb: 0.4
    ledgeDropHeight: 0
    maxJumpAcrossDistance: 0
    minRegionArea: 2
    manualCellSize: 0
    cellSize: 0.16666667
    manualTileSize: 0
    tileSize: 256
    buildHeightMesh: 0
    maxJobWorkers: 0
    preserveTilesOutsideBounds: 0
    debug:
      m_Flags: 0
  m_NavMeshData: {fileID: 0}
"""


def main():
    sync_all_metas()

    b = scene
    env = build_shell(b)
    build_signage(b, env)
    build_lights(b, env)
    build_side_doors(b, env)
    cards = build_section_b(b, env)
    build_hazard(b, env)
    build_player(b)
    build_ui(b)
    build_sun(b)

    # ---- alarm ----------------------------------------------------------
    alarm_node = refs["alarm"]
    refs["alarm_script"] = alarm_node.mono("AlarmController", [
        "  interactionName: Raise the fire alarm",
        "  available: 1",
        "  pulseOnHover: 1",
        "  hoverScale: 1.04",
        "  alarmAudio: {fileID: 0}",
        "  strobeLight: {fileID: 0}",
        "  strobeRenderer: {fileID: %d}" % alarm_node.children[2].components[1][1],
        "  lightPulseSpeed: 6",
        "  lightMinIntensity: 0.2",
        "  lightMaxIntensity: 3.2",
        "  strobeColour: {r: 1, g: 0.12, b: 0.08, a: 1}",
    ])

    # ---- phone ----------------------------------------------------------
    phone_root = refs["phone_root"]
    refs["phone_script"] = phone_root.mono("SimpleInteractable", [
        "  interactionName: Call 112 from the emergency phone",
        "  available: 0",
        "  pulseOnHover: 1",
        "  hoverScale: 1.04",
        "  eventId: phone",
        "  unavailablePrompt: Emergency phone (raise the alarm first)",
        "  audioSource: {fileID: 0}",
        "  interactClip: %s" % clip("click"),
    ])

    # ---- mask display ---------------------------------------------------
    mask_root = refs["mask_root"]
    refs["mask_script"] = mask_root.mono("SimpleInteractable", [
        "  interactionName: Inspect the three mask types",
        "  available: 1",
        "  pulseOnHover: 1",
        "  hoverScale: 1.02",
        "  eventId: mask_display",
        "  unavailablePrompt: Mask display",
        "  audioSource: {fileID: 0}",
        "  interactClip: %s" % clip("click"),
    ])

    # ---- extinguisher cards ---------------------------------------------
    refs["card_scripts"] = []
    for card, texture in cards:
        identifier = "ext_card_" + texture.replace("ext_", "")
        refs["card_scripts"].append(card.mono("SimpleInteractable", [
            "  interactionName: Inspect this extinguisher",
            "  available: 1",
            "  pulseOnHover: 1",
            "  hoverScale: 1.02",
            "  eventId: %s" % identifier,
            "  unavailablePrompt: Extinguisher information",
            "  audioSource: {fileID: 0}",
            "  interactClip: %s" % clip("click"),
        ]))

    # ---- fire -----------------------------------------------------------
    fire_root = refs["fire_root"]
    refs["fire_script"] = fire_root.mono("FireDemo", [
        "  flames: {fileID: 0}",
        "  embers: {fileID: 0}",
        "  smoke: {fileID: 0}",
        "  fireLight: {fileID: 0}",
        "  discharge: {fileID: 0}",
        "  audioSource: {fileID: 0}",
        "  fireClip: %s" % clip("fire"),
        "  hissClip: %s" % clip("hiss"),
        "  baseLightIntensity: 2.4",
        "  flameHeight: 0.55",
    ])

    fire_view = refs["fire_view"]
    refs["fireview_script"] = fire_view.mono("SimpleInteractable", [
        "  interactionName: Study the contained fire",
        "  available: 0",
        "  pulseOnHover: 1",
        "  hoverScale: 1.02",
        "  eventId: fire_demo",
        "  unavailablePrompt: Contained training fire",
        "  audioSource: {fileID: 0}",
        "  interactClip: %s" % clip("click"),
    ])

    # ---- extinguisher practice station ----------------------------------
    station = refs["station"]
    refs["station_script"] = station.mono("ExtinguisherStation", [
        "  interactionName: Start the PASS demonstration",
        "  available: 1",
        "  pulseOnHover: 1",
        "  hoverScale: 1.03",
        "  fire: %s" % ref(refs["fire_script"]),
        "  head: %s" % ref(refs["station_head"].tr_id),
        "  lever: %s" % ref(refs["station_lever"].tr_id),
        "  pin: %s" % ref(refs["station_pin"].tr_id),
        "  sprayOrigin: %s" % ref(refs["station_spray"].tr_id),
        "  headStowed: {x: 0, y: -34, z: 0}",
        "  headAimed: {x: 0, y: 0, z: -10}",
        "  sweepDegrees: 13",
        "  leverPressedAngle: -30",
        "  practiceActive: 0",
        "  audioSource: {fileID: 0}",
        "  hissClip: %s" % clip("hiss"),
    ])

    # ---- fire door ------------------------------------------------------
    store_door = refs["store_door"]
    refs["storedoor_script"] = store_door.mono("DoorController", [
        "  interactionName: Store room fire door",
        "  available: 1",
        "  pulseOnHover: 0",
        "  hoverScale: 1",
        "  pivot: %s" % ref(refs["store_pivot"].tr_id),
        "  openAngle: -95",
        "  startsOpen: 1",
        "  locked: 1",
        "  closeOnce: 1",
        "  speed: 4",
        "  openPrompt: Open the fire door",
        "  closePrompt: Close the fire door",
        "  lockedPrompt: Fire door (blocked open by debris)",
        "  eventWhenOpened: ",
        "  eventWhenClosed: door_closed",
        "  audioSource: {fileID: 0}",
        "  openClip: %s" % clip("door"),
        "  closeClip: %s" % clip("door"),
    ])

    # ---- exit doors ------------------------------------------------------
    exit_doors = refs["exit_doors"]
    refs["exitdoor_script"] = exit_doors.mono("DoorController", [
        "  interactionName: Exit doors",
        "  available: 1",
        "  pulseOnHover: 0",
        "  hoverScale: 1",
        "  pivot: %s" % ref(refs["exit_pivot"].tr_id),
        "  openAngle: -100",
        "  startsOpen: 0",
        "  locked: 1",
        "  closeOnce: 0",
        "  speed: 3.5",
        "  openPrompt: Open the exit doors",
        "  closePrompt: Close the exit doors",
        "  lockedPrompt: Exit doors - wait for the briefing",
        "  eventWhenOpened: exit_opened",
        "  eventWhenClosed: ",
        "  audioSource: {fileID: 0}",
        "  openClip: %s" % clip("door"),
        "  closeClip: %s" % clip("door"),
    ])

    # ---- lift call button -------------------------------------------------
    lift = b.empty("LiftCallButton", env, (-(HALF - 0.09), 1.25, 18.5))
    b.box("Lift_Panel", lift, (0, 0, 0), (0.06, 0.3, 0.22), "Metal", collider=False)
    b.prop("Lift_ButtonUp", lift, (-0.045, 0.05, 0), (0.05, 0.02, 0.05), "LampPanel",
           mesh="cylinder", rot=(0, 0, 90))
    b.prop("Lift_ButtonDown", lift, (-0.045, -0.05, 0), (0.05, 0.02, 0.05), "AlarmStrobe",
           mesh="cylinder", rot=(0, 0, 90))
    b.collider_node("LiftInteractBox", lift, (0, 0, 0), (0.3, 0.5, 0.4))
    lift_doors = b.empty("LiftDoors", env, (-(HALF - 0.06), 1.15, 19.7))
    b.box("Lift_DoorA", lift_doors, (0, 0, -0.55), (0.06, 2.3, 1.1), "Metal", collider=False)
    b.box("Lift_DoorB", lift_doors, (0, 0, 0.55), (0.06, 2.3, 1.1), "Metal", collider=False)
    b.box("Lift_FrameTop", lift_doors, (0, 1.2, 0), (0.1, 0.14, 2.4), "Trim", collider=False)
    refs["lift_script"] = lift.mono("SimpleInteractable", [
        "  interactionName: Look at the lift call button",
        "  available: 1",
        "  pulseOnHover: 1",
        "  hoverScale: 1.05",
        "  eventId: lift",
        "  unavailablePrompt: Lift call button",
        "  audioSource: {fileID: 0}",
        "  interactClip: %s" % clip("click"),
    ])

    # ---- smoke hazard -----------------------------------------------------
    refs["smoke_script"] = refs["smoke_root"].mono("CorridorSmoke", [
        "  size: %s" % v3(3.6, 2.8, 3.6),
        "  density: 9",
        "  safePoint: %s" % ref(refs["smoke_safe"].tr_id),
        "  blocksPlayer: 1",
    ])

    # ---- checkpoints ------------------------------------------------------
    checkpoints = build_checkpoints(b)
    refs["checkpoint_scripts"] = {}
    for node, cid, _ in checkpoints:
        refs["checkpoint_scripts"][cid] = node.mono("CheckpointTrigger", [
            "  checkpointId: %s" % cid,
            "  playerOnly: 1",
        ])

    # ---- evacuation controller -------------------------------------------
    evac = b.empty("EvacuationController", None, (0, 0, 0))
    evac_script = evac.mono("EvacuationController", ["  checkpoints:"])
    body = evac.components[-1][2]
    for node, cid, display in checkpoints:
        body += ["  - id: %s" % cid,
                 "    displayName: %s" % display,
                 "    trigger: %s" % ref(refs["checkpoint_scripts"][cid]),
                 "    reached: 0"]
    body += ["  corridorSmoke: %s" % ref(refs["smoke_script"]),
             "  audioSource: {fileID: 0}",
             "  checkpointClip: %s" % clip("click")]
    refs["evacuation_script"] = evac_script

    # ---- lesson manager --------------------------------------------------
    lesson = b.empty("LessonManager", None, (0, 0, 0))
    lesson_fields = [
        "  player: %s" % ref(refs["player_script"]),
        "  alarm: %s" % ref(refs["alarm_script"]),
        "  evacuation: %s" % ref(evac_script),
        "  extinguisherStation: %s" % ref(refs["station_script"]),
        "  fire: %s" % ref(refs["fire_script"]),
        "  phone: %s" % ref(refs["phone_script"]),
        "  maskDisplay: %s" % ref(refs["mask_script"]),
        "  liftCall: %s" % ref(refs["lift_script"]),
        "  fireViewPoint: %s" % ref(refs["fireview_script"]),
        "  storeDoor: %s" % ref(refs["storedoor_script"]),
        "  exitDoor: %s" % ref(refs["exitdoor_script"]),
        "  startPoint: %s" % ref(refs["start"].tr_id),
        "  extinguisherCards:",
    ]
    lesson_fields += ["  - %s" % ref(script) for script in refs["card_scripts"]]
    lesson_fields += [
        "  uiAudio: {fileID: 0}",
        "  clickClip: %s" % clip("click"),
        "  panelClip: %s" % clip("chime"),
        "  panelOpenDelay: 0.35",
    ]
    lesson.mono("LessonManager", lesson_fields)

    write_text(SCENE_PATH, SCENE_HEADER + scene.yaml())
    guid = write_meta(SCENE_PATH, "scene")

    build_settings = """%YAML 1.1
%TAG !u! tag:unity3d.com,2011:
--- !u!1045 &1
EditorBuildSettings:
  m_ObjectHideFlags: 0
  serializedVersion: 2
  m_Scenes:
  - enabled: 1
    path: __PATH__
    guid: __GUID__
  m_configObjects: {}
"""
    build_settings = build_settings.replace("__PATH__", SCENE_PATH).replace("__GUID__", guid)
    write_text("ProjectSettings/EditorBuildSettings.asset", build_settings)

    print("Scene written: %s (%d objects)" % (SCENE_PATH, len(scene.nodes)))


if __name__ == "__main__":
    main()
