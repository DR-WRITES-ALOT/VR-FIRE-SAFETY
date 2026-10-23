# Proving the project is VR-headset ready without a headset

This is the evidence pack for a report, demo or viva. None of it requires a physical headset.
Every item below produces an artefact you can screenshot, paste or attach, and each one is
honest about what it does and does not prove.

Run the steps in order; steps 1–2 take about five minutes.

---

## Run sheet for a 10-minute demo

| Time | Do | They see |
| --- | --- | --- |
| 0:00 | Open the project, open `Assets/Scenes/FireSafetyTrainer.unity`, maximise the **Game** tab, press **Play** | the ordinary Unity Game tab: the main menu, then the corridor. Say: "this is the desktop branch — the same lesson code that runs in VR" |
| 0:00–3:00 | Play through section A and B (click **Start Training**, `E` at the alarm, `E` at the phone, `E` at the mask case, walk to the fire) | the teaching pop-ups, the objective box, the alarm, the animated PASS demo |
| 3:00 | Stop. Show **Tools ▸ VR Fire Safety ▸ VR Readiness Report** | a Markdown report written from the live project, with a verdict |
| 4:00 | *Package Manager ▸ + ▸ Add package by name… `com.unity.xr.mock-hmd`*; tick **Mock HMD** in XR Plug-in Management (PC tab) | the project will now run in an XR session |
| 5:00 | Press **Play**, then set the Game view render mode dropdown (top-left of the Game view) to **Both Eyes** | **the scene twice, side by side** — the same stereo image a headset receives |
| 6:00 | Press **F2** | `XR session ....... ACTIVE`, `Stereo mode ...... SinglePassInstanced`, `Head pose ... not reported` (honest: Mock HMD provides no tracking) |
| 7:00 | Stop. Untick **Mock HMD**; tick **OpenXR** on the PC tab and add your controller profile | the headset configuration screen |
| 8:00 | Show **Player ▸ Other Settings** | Active Input Handling = Both, IL2CPP, ARM64, Minimum API 29 |
| 9:00 | Say the one-sentence summary from the end of this document | — |

Mouse and keyboard keep working in the Mock HMD session: the trainer detects that the runtime
reports no head pose and keeps WASD/mouse look, while the UI switches to world space so it renders
in both eyes. That combination is the demo.



---

## Step 1 — Generate the machine-written report

**Tools ▸ VR Fire Safety ▸ VR Readiness Report**

This writes `docs/VR-Readiness-Report.md` (and opens a confirmation dialog). The file is filled
in from the live project, not typed by hand:

* Unity version and active build target
* XR package versions read from `Packages/manifest.json`
* the OpenXR loader state for the current build target
* **the enabled interaction profiles** (the setting that decides whether the controllers work)
* the XR devices enabled for the build
* Android target architecture, minimum API level, scripting backend and bundle id
* whether the scene is in Build Settings
* whether the main camera has URP's XR rendering flag set
* a **Verdict** section listing anything that is still wrong

**Screenshot:** the Verdict section and section 3 (OpenXR configuration).
**What it proves:** the project is configured for XR and for an ARM64 headset build.
**What it does not prove:** that a headset has been driven with it.

The same information is printed to the Console by **Tools ▸ VR Fire Safety ▸ Project Setup Report**.

---

## Step 2 — Show stereo rendering with the Mock HMD

This is the strongest visual evidence available without hardware: the scene is rendered twice,
once per eye, exactly as a headset receives it.

1. **Window ▸ Package Manager ▸ + ▸ Add package by name…** → `com.unity.xr.mock-hmd` → *Add*.
2. **Edit ▸ Project Settings ▸ XR Plug-in Management** → **PC** tab → tick **Mock HMD** (this is a
   separate loader from OpenXR; both may be ticked, Mock HMD wins in the Editor).
3. Press **Play**.
4. In the **Game view**, open the render-mode dropdown (top-left of the Game view toolbar, usually
   showing *Game*) and choose **Both Eyes**.

**Screenshot:** the Game view with the lesson menu drawn twice, side by side. Crop to include the
toolbar so the *Both Eyes* setting is visible.

**What it proves:** the URP camera renders in stereo, the UI is a world-space canvas that survives
stereo rendering (a screen-space overlay would be drawn once, flat, over both eyes — the giveaway),
and the lesson logic runs inside an XR session rather than beside it.
**What it does not prove:** head tracking or controller input, because Mock HMD deliberately
provides neither.

Remember to untick Mock HMD afterwards, or press Play will keep using it.

---

## Step 3 — Show the live XR state with the F2 panel

In Play mode press **F2**. A diagnostics panel appears in the top-left corner:

```
VR READINESS  (F2 to hide)
Unity 6000.5.3f1   build: Editor

XR session ....... ACTIVE
XR device ........ MockHMD
Stereo mode ...... SinglePassInstanced
Eye resolution ... scale 1.0   graphics Direct3D11

Head pose ........ not reported
Tracking origin .. Device / default

Controllers:
  left  not reported
  right not reported
  head  not reported

Frame ............ 72 fps   1600 x 900
Lesson: running   |   UI canvases: ready
```

With a real headset the same panel reports the device name, `Head pose ... tracked (floor origin)`
and the controller names.

**Screenshot:** the panel, with the scene visible behind it.
**What it proves:** the runtime really is in an XR session, stereo mode is `SinglePassInstanced`,
and the trainer knows whether the head pose and controllers are being reported — i.e. the input
code is live, not a comment.
**What it does not prove:** that a physical headset was used. Say so plainly; the panel's honesty
is the point.

---

## Step 4 — Show the settings that decide headset support

Three screenshots, taken from the real project:

| Screen | What has to be visible |
| --- | --- |
| *Project Settings ▸ XR Plug-in Management* (PC tab) | **OpenXR** ticked |
| *XR Plug-in Management ▸ OpenXR* | an **interaction profile** listed (e.g. Oculus Touch), **Render Mode = Single Pass Instanced**, a named **Play Mode OpenXR Runtime** |
| *Player ▸ Other Settings* | **Active Input Handling = Both**, **IL2CPP**, **ARM64**, **Minimum API Level 29** |

**What it proves:** the three settings that most often break a Unity VR project are correct.
**What it does not prove:** that the runtime was exercised — but combined with steps 2–3, the
whole chain is covered apart from the physical device.

---

## Step 5 — Show that it builds for a headset

**File ▸ Build Settings** → *Android* → **Switch Platform** → **Build** (not *Build And Run*),
with no device attached.

A successful APK is meaningful evidence: OpenXR, IL2CPP, ARM64, URP shaders and the runtime
particle shaders all compiled for the headset target.

**Screenshot:** the Console line *Build completed with a result of 'Succeeded'* plus the
`Builds/` folder, or the Build Settings window showing ARM64 / IL2CPP / API 29.

**What it proves:** the project compiles and links for the headset platform.
**What it does not prove:** that it runs at frame rate on the device.

---

## Step 6 — Point at the code that makes it VR (30 seconds of speaking)

Keep this short and concrete; three files do all the XR work:

| File | What to say |
| --- | --- |
| `Assets/Scripts/PlayerController.cs` | "One controller, two modes. In VR it reads the head pose, the left stick, the right stick for snap turn and the right trigger for interaction through `UnityEngine.XR`. The same interaction code runs on desktop with WASD/mouse/E." |
| `PlayerController.RequestTrackingOrigin()` | "The rig root is on the floor, so it asks the runtime for a **floor-relative** tracking origin, retried until the subsystem is running, and falls back to a 1.62 m eye offset if the runtime only offers a device origin. Without this the player would look at the floor." |
| `Assets/Scripts/LessonUI.cs` (`ApplyRenderMode`) | "The UI is a world-space canvas with a follower that keeps it in front of the eyes and out of walls — a screen-space canvas does not render properly in a headset. It switches back to screen-space when no headset is present, so the desktop experience is unaffected." |

---

## What to claim, and what not to

| Claim | Safe to say | Wording |
| --- | --- | --- |
| VR input path implemented | Yes | "Head pose, both sticks and the trigger are read through `UnityEngine.XR`." |
| Stereo rendering verified | Yes, with step 2 | "Verified in the Editor with the Mock HMD stereo runtime — the Game view renders both eyes side by side." |
| Runs on a physical headset | **No** | Do not claim this unless you have done it. Say: "The remaining step is enabling OpenXR on a machine with the headset connected; the project is configured for it." |
| Performance on device | **No** | "Not measured on device. The URP asset is tuned conservatively — MSAA 4, shadow distance 30 — and the README lists the settings to lower if needed." |
| Controller profiles | Only if step 4 shows one | "Oculus Touch / Valve Index profile enabled" only when it is actually enabled. |

A defensible one-sentence summary:

> The VR path is implemented and configuration-verified: the project targets Unity 6000.5.3f1 with
> OpenXR, URP and an ARM64 Android build, reads head and controller input through `UnityEngine.XR`,
> requests a floor-relative tracking origin, uses a world-space UI, and has been exercised in the
> Editor with the Mock HMD stereo runtime. It has not yet been run on a physical headset.

---

## Appendix — checklist

- [ ] `docs/VR-Readiness-Report.md` generated, verdict green
- [ ] Game view screenshot in **Both Eyes** mode
- [ ] F2 panel screenshot showing `XR session: ACTIVE`
- [ ] XR Plug-in Management screenshot (OpenXR ticked)
- [ ] OpenXR page screenshot (interaction profile, Single Pass Instanced, runtime named)
- [ ] Player settings screenshot (Both, IL2CPP, ARM64, API 29)
- [ ] Android build succeeded (or explicitly stated as not attempted)
- [ ] Honest wording used for anything not executed on hardware
