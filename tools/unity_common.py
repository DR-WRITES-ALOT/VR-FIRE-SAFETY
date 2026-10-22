"""Small helper library shared by the asset/scene generators.

The generated files are ordinary Unity YAML assets; this module only makes it
easy to produce stable GUIDs and the small amount of YAML scaffolding that
Unity expects for .meta files.
"""

from __future__ import annotations

import hashlib
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def guid_for(rel_path: str) -> str:
    """Deterministic 32 hex character GUID for a project relative path."""
    normalized = rel_path.replace(os.sep, "/")
    return hashlib.md5(("vr-fire-safety/" + normalized).encode("utf-8")).hexdigest()


def project_path(rel_path: str) -> str:
    return os.path.join(ROOT, rel_path)


def write_text(rel_path: str, text: str) -> None:
    path = project_path(rel_path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


# --------------------------------------------------------------------------- #
# .meta files
# --------------------------------------------------------------------------- #

FOLDER_META = """fileFormatVersion: 2
guid: {guid}
folderAsset: yes
DefaultImporter:
  externalObjects: {{}}
  userData: 
  assetBundleName: 
  assetBundleVariant: 
"""

DEFAULT_META = """fileFormatVersion: 2
guid: {guid}
DefaultImporter:
  externalObjects: {{}}
  userData: 
  assetBundleName: 
  assetBundleVariant: 
"""

SCRIPT_META = """fileFormatVersion: 2
guid: {guid}
MonoImporter:
  externalObjects: {{}}
  serializedVersion: 2
  defaultReferences: []
  executionOrder: 0
  icon: {{instanceID: 0}}
  userData: 
  assetBundleName: 
  assetBundleVariant: 
"""

MATERIAL_META = """fileFormatVersion: 2
guid: {guid}
NativeFormatImporter:
  externalObjects: {{}}
  mainObjectFileID: 2100000
  userData: 
  assetBundleName: 
  assetBundleVariant: 
"""

SCENE_META = """fileFormatVersion: 2
guid: {guid}
DefaultImporter:
  externalObjects: {{}}
  userData: 
  assetBundleName: 
  assetBundleVariant: 
"""

FONT_META = """fileFormatVersion: 2
guid: {guid}
TrueTypeFontImporter:
  externalObjects: {{}}
  serializedVersion: 4
  fontSize: 16
  forceTextureCase: -2
  characterSpacing: 0
  characterPadding: 1
  includeFontData: 1
  fontNames:
  - DejaVu Sans
  fallbackFontReferences: []
  customCharacters: 
  fontRenderingMode: 0
  ascentCalculationMode: 1
  useLegacyBoundsCalculation: 0
  shouldRoundAdvanceValue: 1
  userData: 
  assetBundleName: 
  assetBundleVariant: 
"""

TEXTURE_META = """fileFormatVersion: 2
guid: {guid}
TextureImporter:
  internalIDToNameTable: []
  externalObjects: {{}}
  serializedVersion: 12
  mipmaps:
    mipMapMode: 0
    enableMipMap: 1
    sRGBTexture: 1
    linearTexture: 0
    fadeOut: 0
    borderMipMap: 0
    mipMapsPreserveCoverage: 0
    alphaTestReferenceValue: 0.5
    mipMapFadeDistanceStart: 1
    mipMapFadeDistanceEnd: 3
  bumpmap:
    convertToNormalMap: 0
    externalNormalMap: 0
    heightScale: 0.25
    normalMapFilter: 0
    flipGreenChannel: 0
  isReadable: 0
  streamingMipmaps: 0
  streamingMipmapsPriority: 0
  vTOnly: 0
  ignoreMipmapLimit: 0
  grayScaleToAlpha: 0
  generateCubemap: 6
  cubemapConvolution: 0
  seamlessCubemap: 0
  textureFormat: 1
  maxTextureSize: 2048
  textureSettings:
    serializedVersion: 2
    filterMode: 1
    aniso: 2
    mipBias: 0
    wrapU: 1
    wrapV: 1
    wrapW: 1
  nPOTScale: 0
  lightmap: 0
  compressionQuality: 50
  spriteMode: 0
  spriteExtrude: 1
  spriteMeshType: 1
  alignment: 0
  spritePivot: {{x: 0.5, y: 0.5}}
  spritePixelsToUnits: 100
  spriteBorder: {{x: 0, y: 0, z: 0, w: 0}}
  spriteGenerateFallbackPhysicsShape: 1
  alphaUsage: 1
  alphaIsTransparency: 0
  spriteTessellationDetail: -1
  textureType: 0
  textureShape: 1
  singleChannelComponent: 0
  flipbookRows: 1
  flipbookColumns: 1
  maxTextureSizeSet: 0
  compressionQualitySet: 0
  textureFormatSet: 0
  ignorePngGamma: 0
  applyGammaDecoding: 0
  swizzle: 50462976
  cookieLightType: 0
  platformSettings:
  - serializedVersion: 3
    buildTarget: DefaultTexturePlatform
    maxTextureSize: 2048
    resizeAlgorithm: 0
    textureFormat: -1
    textureCompression: 1
    compressionQuality: 50
    crunchedCompression: 0
    allowsAlphaSplitting: 0
    overridden: 0
    ignorePlatformSupport: 0
    androidETC2FallbackOverride: 0
    forceMaximumCompressionQuality_BC6H_BC7: 0
  spriteSheet:
    serializedVersion: 2
    sprites: []
    outline: []
    physicsShape: []
    bones: []
    spriteID: 
    internalID: 0
    vertices: []
    indices: 
    edges: []
    weights: []
    secondaryTextures: []
    nameFileIdTable: {{}}
  mipmapLimitGroupName: 
  pSDRemoveMatte: 0
  userData: 
  assetBundleName: 
  assetBundleVariant: 
"""

AUDIO_META = """fileFormatVersion: 2
guid: {guid}
AudioImporter:
  externalObjects: {{}}
  serializedVersion: 7
  defaultSettings:
    serializedVersion: 2
    loadType: 0
    sampleRateSetting: 0
    sampleRateOverride: 44100
    compressionFormat: 1
    quality: 0.7
    conversionMode: 0
    preloadAudioData: 1
  platformSettingOverrides: {{}}
  forceToMono: 0
  normalize: 1
  loadInBackground: 0
  ambisonic: 0
  3D: 1
  userData: 
  assetBundleName: 
  assetBundleVariant: 
"""


def write_meta(rel_path: str, kind: str = "default") -> str:
    """Create a .meta file next to rel_path and return the GUID."""
    guid = guid_for(rel_path)
    template = {
        "folder": FOLDER_META,
        "default": DEFAULT_META,
        "script": SCRIPT_META,
        "material": MATERIAL_META,
        "scene": SCENE_META,
        "font": FONT_META,
        "texture": TEXTURE_META,
        "audio": AUDIO_META,
    }[kind]
    write_text(rel_path + ".meta", template.format(guid=guid))
    return guid


def ensure_folder_meta(rel_dir: str) -> None:
    """Meta files are needed for folders too."""
    if rel_dir in ("Assets", ""):
        return
    meta_rel = rel_dir.rstrip("/") + ".meta"
    if not os.path.exists(project_path(meta_rel)):
        write_meta(rel_dir, "folder")


def sync_all_metas() -> None:
    """Create any missing .meta file for files/folders below Assets/."""
    assets_root = project_path("Assets")
    for current, dirs, files in os.walk(assets_root):
        rel_dir = os.path.relpath(current, ROOT).replace(os.sep, "/")
        if rel_dir != "Assets":
            ensure_folder_meta(rel_dir)
        for name in dirs:
            ensure_folder_meta(rel_dir + "/" + name)
        for name in files:
            if name.endswith(".meta") or name.startswith("."):
                continue
            rel = rel_dir + "/" + name
            if os.path.exists(project_path(rel + ".meta")):
                continue
            ext = os.path.splitext(name)[1].lower()
            kind = {
                ".cs": "script",
                ".mat": "material",
                ".unity": "scene",
                ".ttf": "font",
                ".png": "texture",
                ".wav": "audio",
            }.get(ext, "default")
            write_meta(rel, kind)


# --------------------------------------------------------------------------- #
# YAML helpers
# --------------------------------------------------------------------------- #

def ystr(value: str) -> str:
    """Quote a string for Unity's YAML dialect (plain where it is safe)."""
    if value == "":
        return ""
    safe = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 _-.,()[]&/:%+*?<>|=!@#$")
    if all(ch in safe for ch in value) and not value[0] in "-?:,[]{}#&*!|>'\"%@`":
        return value
    return "'" + value.replace("'", "''") + "'"


def v3(x: float, y: float, z: float) -> str:
    return "{x: %s, y: %s, z: %s}" % (fmt(x), fmt(y), fmt(z))


def v2(x: float, y: float) -> str:
    return "{x: %s, y: %s}" % (fmt(x), fmt(y))


def quat(x: float, y: float, z: float, w: float) -> str:
    return "{x: %s, y: %s, z: %s, w: %s}" % (fmt(x), fmt(y), fmt(z), fmt(w))


def col(r: float, g: float, b: float, a: float = 1.0) -> str:
    return "{r: %s, g: %s, b: %s, a: %s}" % (fmt(r), fmt(g), fmt(b), fmt(a))


def fmt(value: float) -> str:
    if isinstance(value, int):
        return str(value)
    text = ("%.6f" % float(value)).rstrip("0").rstrip(".")
    return text if text not in ("", "-0") else "0"
