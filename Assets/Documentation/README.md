# VR Fire Safety and Evacuation Trainer

A small, complete Unity VR training experience for a beginner-level college project.
One scene, one guided route, four short teaching sections:

**A** immediate response and alarm → **B** masks and extinguishers → **C** guided evacuation
→ **D** first-aid summary.

> This is a basic educational simulation. It is **not** a substitute for professional
> fire-safety training, a real evacuation drill, or certified first-aid instruction.

---

## 1. Open and run

| Step | What to do |
| --- | --- |
| Unity version | **Unity 6000.5.3f1 (Unity 6.5)**; any 6000.5.x or newer Unity 6 release works |
| Open the project | Unity Hub → *Add* → select this folder → open |
| Scene to open | `Assets/Scenes/FireSafetyTrainer.unity` |
| Run | Press **Play**. The main menu appears in front of you. |
| Shortcut | Menu bar → **Tools ▸ VR Fire Safety ▸ Open Training Scene** |

Everything (geometry, materials, signage, audio, lesson wiring) is already in the scene.
No assets need to be downloaded and no package needs to be installed to run it in the Editor.

### Project settings that matter on Unity 6.5

| Setting | Value | Why |
| --- | --- | --- |
| `ProjectSettings/ProjectVersion.txt` | `6000.5.3f1` (`c2eb47b3a2a9`) | the editor version the project is pinned to |
| Active Input Handling | **Both** | the trainer reads the legacy Input Manager (WASD/mouse/E) and the XR Interaction Toolkit needs the new Input System for its device simulator |
| Colour space | Linear | correct lighting and sign readability in a headset |
| Render pipeline | Built-in | no URP asset or material conversion needed; still supported in Unity 6.5 |
| Runtime packages | uGUI 2.5.0, XR Interaction Toolkit 3.5.1, XR Plug-in Management 4.5.4, OpenXR 1.17.1 | package versions used by public projects committed with Unity 6000.5.3f1 |

The first time the project opens, Unity may spend a minute importing and upgrading the settings
files written by the scene generator. Let it finish; nothing needs to be clicked.

### Controls

**Desktop / Editor (no headset needed)**

| Input | Action |
| --- | --- |
| `W` `A` `S` `D` | Move |
| Mouse | Look |
| `Shift` | Walk faster |
| `E` | Interact with the object under the crosshair |
| Left mouse click | Press on-screen buttons (the cursor is released while a panel is open) |
| `Esc` | Pause / resume |

While a panel is open the mouse cursor is free, so simply click a button. In VR, look at a
button and press the trigger – the crosshair acts as the pointer.

**VR headset (OpenXR)**

| Input | Action |
| --- | --- |
| Left stick | Move |
| Right stick | Snap turn (30°) |
| Trigger | Interact with objects and press interface buttons |
| Headset | Look around |

---

## 2. What the experience contains

### Environment (one continuous route)

1. **First corridor** – starting point, fire-action notice, red alarm call point, 112 emergency
   phone, mask teaching display, six labelled extinguisher models, PASS poster, one small
   contained fire in a metal bin, and a practice extinguisher stand.
2. **Stair lobby and one flight of stairs** – lift doors with a call button, "do not use the
   lift" signage, one 20-step flight with handrails on both sides.
3. **Second corridor** – exit signage, a fire door holding back a dense smoke hazard, and a
   smoke warning sign.
4. **Outdoor assembly point** – green assembly signage, marked assembly area, shelter and fence.

### Teaching flow

| Section | Player does | Lesson teaches |
| --- | --- | --- |
| A | Reads the initial briefing, raises the alarm (`E`), uses the 112 phone | Raise the alarm, alert others only if safe, call 112, evacuate promptly, avoid smoke |
| B | Studies the mask display, reviews all six extinguisher cards, makes a safe-response decision, practises PASS on the single contained fire | Mask limitations (cloth, N95, escape hood, SCBA), Indian fire classes A/B/C/D/F, extinguisher types, water and gas warnings, PASS, when to abandon firefighting and leave |
| C | Follows the EXIT signs, checks the lift (and is shown why not to use it), descends the flight of stairs, meets the dense smoke, closes the fire door, exits the building, walks to the assembly point | Safe stair use, why lifts are avoided, smoke toxicity and disorientation, "staying low is not a guarantee", stop and turn back rather than enter dense smoke, closing a fire door, what to do if trapped |
| D | Reads the two first-aid panels at the assembly point | Burn first aid (20 minutes cool running water, what not to apply, when to seek urgent care) and smoke-inhalation first aid (never re-enter, call 112, monitor breathing, follow dispatcher CPR/AED instructions) |

There is **no scoring, timer, NPC, multiplayer or combat**. The route can be completed at any pace.

---

## 3. Project structure

```
Assets/
  Scenes/FireSafetyTrainer.unity     the single training scene
  Scripts/
    LessonManager.cs                 stage machine: sections, panels, unlocking, pause/menu
    LessonContent.cs                 all teaching text + reference list (edit teaching here)
    LessonUI.cs                      builds the world-space UI: HUD, panels, menu, pause
    PlayerController.cs              desktop + VR movement, look, interaction, UI pointer
    IInteractable.cs                 tiny interface every usable object implements
    InteractableBase.cs              shared prompt text and hover feedback
    SimpleInteractable.cs            generic "press E" object (phone, displays, cards, lift)
    AlarmController.cs               alarm sound, flashing strobe, lesson event
    FireDemo.cs                      the single contained fire + PASS extinguishing sequence
    ExtinguisherStation.cs           the four PASS practice steps
    DoorController.cs                hinged doors (fire door, exit doors)
    EvacuationController.cs          checkpoints and the one smoke hazard
    CheckpointTrigger.cs             trigger volume that reports route progress
    CorridorSmoke.cs                 runtime-built smoke effect + hazard volume
    HazardZone.cs                    stops the player entering dense smoke
    VfxUtil.cs                       runtime particle helpers (no imported art)
    HudFollower.cs                   keeps the world-space canvas in front of the camera
    AudioHelper.cs                   audio source/clip helpers (falls back to Resources)
  Editor/FireSafetyProjectSetup.cs   open scene, validate scene, add to build settings
  Materials/  Textures/Signs/  Fonts/  Resources/Audio/
  Documentation/README.md            this document (inside the project)
tools/                               generators and static checks (Python 3, not part of the build)
  gen_assets.py                      sign textures, audio clips, materials, .meta files
  gen_scene.py                       the scene, lighting, wiring and build settings
  verify_scene.py                    reference / GUID / serialized-field integrity
  verify_flow.py                     lesson event, stage, content and collider checks
  verify_project.py                  Unity version, package, player-settings and API checks
  render_plan.py                     top-down plan and section images for layout review
```

### How the lesson logic works

`LessonManager` is a single linear stage machine. Each stage shows one panel and unlocks exactly
one interaction. Every interactable calls `LessonManager.Notify("event id")`, and the manager
decides whether that event belongs to the current stage. Teaching text lives in
`LessonContent.cs`, so wording can be improved without touching game logic.

---

## 4. Regenerating the project files (optional)

The scene, materials, signage textures and audio were produced by scripts so that everything is
repeatable and reviewable:

```bash
python3 tools/gen_assets.py     # sign textures, audio clips, materials, .meta files
python3 tools/gen_scene.py      # the Unity scene + build settings
python3 tools/verify_scene.py   # fileIDs, GUIDs, script fields, metas
python3 tools/verify_flow.py    # lesson events, stages, content, colliders
python3 tools/verify_project.py # Unity 6.5 version, packages, player settings, removed APIs
python3 tools/render_plan.py    # writes build/plan_*.png and build/section*.png
```

`verify_scene.py` reports broken references, missing assets, serialized fields that do not exist
in the C# classes, and parent/child transform mismatches. `verify_flow.py` checks that every event
id and checkpoint in the scene is handled by `LessonManager`, that every stage can be entered and
handled, that every `LessonContent` member used by the code exists, and that every interactable has
a collider (and every checkpoint/hazard a trigger). `render_plan.py` draws the level from the scene
file so the route can be reviewed without Unity. All three exit non-zero if they find a problem.

The scripts are development tools only; the Unity project does not need Python to run.

### Route dimensions (for review)

Single storey, 4 m wide corridors, 3.2 m ceilings, stairs descending 3.5 m:

| Part | Position |
| --- | --- |
| First corridor | z -1.8 to 21 (starts at the player spawn, exit signage throughout) |
| Stair flight | z 21 to 27, 20 steps (175 mm rise, 300 mm going), handrails both sides |
| Lower landing | z 27 to 28.5 |
| Second corridor | z 28.5 to 44 (smoke at z 37.1 to 40.7, store-room fire door at z 35.2 to 36.6) |
| Exit doors and outdoors | z 44 to 62, assembly point at z 51 |

---

## 5. Manual configuration still needed for a VR headset

Desktop play works immediately. To run in a headset, enable XR in the Editor (this is a per-project
Editor step in every Unity VR project):

1. **Edit ▸ Project Settings ▸ XR Plug-in Management** → on the **PC** tab (or **Android** for a
   standalone headset build), tick **OpenXR**. Unity installs the loader and may ask to restart.
2. **Project Settings ▸ XR Plug-in Management ▸ OpenXR ▸ Features** → enable the feature group for
   your headset (for Quest: **Meta Quest Support**; for a PC headset: **Microsoft HoloLens** or the
   vendor feature). If the feature list is empty, press *Fix All* / *Install* when Unity offers it.
3. **Project Settings ▸ Player ▸ Other Settings ▸ Active Input Handling** must stay **Both**.
   Setting it to *Input System Package (New)* silences the desktop controls, because the trainer
   reads the legacy Input Manager. (The project ships with *Both* already selected.)
4. To test without a headset: **Window ▸ Package Manager ▸ XR Interaction Toolkit ▸ Samples** →
   import **XR Device Simulator**, then drag the `XR Device Simulator` prefab into the scene and
   press Play. The trainer reads head pose, thumbsticks and trigger straight from `UnityEngine.XR`,
   so the simulator drives it with no further wiring.
5. For a standalone build: **File ▸ Build Settings** → the training scene is already listed →
   *Build And Run*. If the smoke or flames look wrong in a player (but fine in the Editor), add
   `Particles/Standard Unlit` to **Project Settings ▸ Graphics ▸ Always Included Shaders** — runtime
   particle materials fetch their shader by name, and unused shaders are stripped from builds.

The training itself does not depend on which controller model is used: it reads the head pose,
the left/right thumbsticks and the right trigger through `UnityEngine.XR` (`InputDevices` and
`CommonUsages`). These APIs are marked *Legacy* in the Unity 6.5 scripting reference but are still
supported. If a particular OpenXR runtime reports the headset but not the controllers, the trainer
logs a warning at runtime; the fix is to enable the controller interaction profile for that headset
in the OpenXR settings, or to swap the input reads in `PlayerController` for XR Interaction Toolkit
actions (the package is already installed).

> The scene does not use XR Interaction Toolkit interactors, because those need a controller rig
> that could not be verified in this environment. The XR Interaction Toolkit and OpenXR packages are
> nevertheless included in `Packages/manifest.json` so the project can be extended with grab
> interactors or teleportation later.

---

## 6. References

The fire-safety and first-aid content was checked against these sources (also available in-game:
main menu → **REFERENCES**, and on the reference posters in the corridors).

1. **Burns – Fact sheet**, World Health Organization — https://www.who.int/news-room/fact-sheets/detail/burns
2. **Burns and scalds – Treatment**, NHS (UK) — https://www.nhs.uk/conditions/burns-and-scalds/treatment/
3. **Burns: Types, Symptoms and How to Help**, American Red Cross — https://www.redcross.org/take-a-class/resources/learn-first-aid/burns
4. **General Respiratory Protection Guidance for Employers and Workers**, OSHA — https://www.osha.gov/publications/respiratory_protection_bulletin_2011
5. **Use of smoke escape hoods meeting the ANSI-ISEA standard** (interpretation letter), OSHA — https://www.osha.gov/laws-regs/standardinterpretations/2010-08-11-1
6. **Respiratory protection – wildfire respirator FAQ**, 3M — https://multimedia.3m.com/mws/media/1216501O/respiratory-protection-wildfire-faq.pdf
7. **Pamphlet on classification of fires and types of fire extinguishers**, Research Designs and Standards Organisation (Indian Railways) — https://rdso.indianrailways.gov.in/uploads/Draft%20Pamphlet%20on%20Classification%20of%20Fires%20&%20Types%20of%20Fire%20Extinguishers.pdf
8. **Types of Fire Extinguishers, Classes of Fire and How to Use (IS 15683 / IS 2190)**, National Institute of Fire Safety, India — https://nifsindia.net/blog/how-to-use-a-fire-extinguisher-your-complete-guide-to-fire-safety/
9. **Emergency Response Support System (single emergency number 112)**, Ministry of Home Affairs, Government of India — https://112.gov.in/
10. **CPR and ECC Guidelines**, American Heart Association — https://cpr.heart.org/en/resuscitation-science/cpr-and-ecc-guidelines

Key points taken from the sources:

* Indian fire classes are **A** (solid combustibles), **B** (flammable liquids), **C** (flammable
  gases), **D** (combustible metals) and **F** (cooking oils/fats). Energised electrical equipment is
  a **hazard**, not a separate Indian class, and it determines which extinguisher may be used.
* Particulate respirators (N95/KN95) filter particles, **not** carbon monoxide or other fire gases;
  cloth/surgical masks give no useful protection; certified escape hoods are short-duration escape
  aids that do not protect against oxygen-deficient atmospheres; SCBA is for trained firefighters.
  None of them is a reason to delay evacuation or enter smoke.
* Burn first aid: cool with cool running water for **20 minutes** as soon as possible, remove
  jewellery/clothing only if not stuck, never apply ice/toothpaste/oils/butter/turmeric, do not
  burst blisters, cover loosely with a clean non-fluffy dressing, seek urgent care for severe burns.
* Smoke inhalation: never enter a dangerous area to retrieve a casualty, move the person to fresh
  air only if safe, call 112, monitor responsiveness and breathing, and follow dispatcher
  instructions for CPR/AED if unresponsive and not breathing normally.

---

## 7. Testing status (honest summary)

**Verified in this environment**

* Every C# file parses (tree-sitter C# grammar) with no syntax errors.
* `tools/verify_scene.py` passes: all 1,153 scene objects resolve, every `fileID` reference exists,
  every asset GUID maps to a real `.meta` file, every serialized field exists in the matching C#
  class, and every transform parent/child link agrees.
* `tools/verify_flow.py` passes: all 10 scene event ids (including the six extinguisher cards),
  all 5 checkpoints and both door events are handled by `LessonManager`; all 30 lesson stages are
  declared, entered and (apart from the menu sentinel) handled; every `LessonContent` member used
  by the code is defined; all 14 interactables have colliders and all checkpoints/hazard zones are
  triggers; the six wall-card ids map onto the six entries in `LessonContent.Extinguishers`; every
  `LessonManager` scene reference (12 objects, 6 extinguisher cards, 2 audio clips) is assigned.
* The level layout was reviewed from `build/plan_route.png`, `build/plan_outdoor.png` and
  `build/section*.png`, generated from the scene by `tools/render_plan.py`.
* Teaching content was checked against the references listed above.
* `tools/verify_project.py` passes for Unity 6000.5.3f1: the pinned editor version and revision
  match, every runtime package version is one used by public projects committed with 6000.5.3f1,
  no Unity 2022-only package or removed module is requested, Active Input Handling is *Both*,
  colour space is Linear, the build settings list the scene with its current GUID, the uGUI
  components the interface needs are present, and no script uses an API removed in Unity 6
  (`FindObjectOfType`, `UnityEngine.VR`, `WWW`, `Application.LoadLevel`, and similar).

**Not verified here (no Unity Editor or headset is available in this environment)**

* The project has **never been opened in Unity 6000.5.3f1** (or any Unity). Package resolution,
  the settings upgrade Unity performs on first open, and script compilation were checked only
  statically and against Unity 6.5 documentation; they were not executed.
* Visual layout, lighting balance and particle appearance in the Editor.
* Actual mouse/keyboard or VR input, audio playback, and the on-screen button interactions.
* Frame rate, stereo rendering and comfort in a headset.

Open the scene and use **Tools ▸ VR Fire Safety ▸ Validate Training Scene** first: it re-checks
every reference, collider and lesson object inside Unity, reports the editor version, the active
input handling and whether an XR device is set up, and prints any problem to the Console before you
press Play. **Tools ▸ VR Fire Safety ▸ Project Setup Report** prints the same environment summary
on its own.
