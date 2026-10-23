using System;
using System.Collections.Generic;
using System.Reflection;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.XR;
using UnityEngine.SceneManagement;

/// <summary>
/// Editor helpers for the training project.
///
/// Tools > VR Fire Safety
///   Open Training Scene        opens the one scene used by the trainer
///   Validate Training Scene    checks every reference, collider and interface in the scene
///   Add Scene To Build Settings
///
/// Validation is deliberately thorough: it reports missing references, interactables
/// without colliders and lesson objects that are not wired together, so a broken scene
/// is obvious before you press Play.
/// </summary>
public static class FireSafetyProjectSetup
{
    const string ScenePath = "Assets/Scenes/FireSafetyTrainer.unity";

    [MenuItem("Tools/VR Fire Safety/Open Training Scene", false, 0)]
    public static void OpenTrainingScene()
    {
        if (!System.IO.File.Exists(ScenePath))
        {
            EditorUtility.DisplayDialog("Scene missing",
                "Could not find " + ScenePath + ".\n\n" +
                "Regenerate it with:  python3 tools/gen_scene.py", "OK");
            return;
        }

        if (EditorSceneManager.SaveCurrentModifiedScenesIfUserWantsTo())
        {
            EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
            Debug.Log("[Fire Safety] Opened " + ScenePath + ". Press Play, then choose Start Training.");
        }
    }

    [MenuItem("Tools/VR Fire Safety/Add Scene To Build Settings", false, 1)]
    public static void AddSceneToBuildSettings()
    {
        List<EditorBuildSettingsScene> scenes = new List<EditorBuildSettingsScene>(EditorBuildSettings.scenes);
        foreach (EditorBuildSettingsScene existing in scenes)
        {
            if (existing.path == ScenePath)
            {
                existing.enabled = true;
                EditorBuildSettings.scenes = scenes.ToArray();
                Debug.Log("[Fire Safety] The training scene is already in Build Settings.");
                return;
            }
        }

        scenes.Insert(0, new EditorBuildSettingsScene(ScenePath, true));
        EditorBuildSettings.scenes = scenes.ToArray();
        Debug.Log("[Fire Safety] Added " + ScenePath + " to Build Settings.");
    }

    [MenuItem("Tools/VR Fire Safety/Validate Training Scene", false, 2)]
    public static void ValidateTrainingScene()
    {
        Scene scene = SceneManager.GetActiveScene();
        if (scene.path != ScenePath)
        {
            if (!EditorSceneManager.SaveCurrentModifiedScenesIfUserWantsTo()) return;
            scene = EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
        }

        List<string> errors = new List<string>();
        List<string> notes = new List<string>();

        LessonManager lesson = UnityEngine.Object.FindFirstObjectByType<LessonManager>();
        if (lesson == null)
        {
            errors.Add("No LessonManager in the scene.");
        }
        else
        {
            Require(ref lesson.player, "LessonManager.player", errors);
            Require(ref lesson.alarm, "LessonManager.alarm", errors);
            Require(ref lesson.evacuation, "LessonManager.evacuation", errors);
            Require(ref lesson.extinguisherStation, "LessonManager.extinguisherStation", errors);
            Require(ref lesson.fire, "LessonManager.fire", errors);
            Require(ref lesson.phone, "LessonManager.phone", errors);
            Require(ref lesson.maskDisplay, "LessonManager.maskDisplay", errors);
            Require(ref lesson.liftCall, "LessonManager.liftCall", errors);
            Require(ref lesson.fireViewPoint, "LessonManager.fireViewPoint", errors);
            Require(ref lesson.storeDoor, "LessonManager.storeDoor", errors);
            Require(ref lesson.exitDoor, "LessonManager.exitDoor", errors);
            Require(ref lesson.startPoint, "LessonManager.startPoint", errors);

            if (lesson.extinguisherCards == null || lesson.extinguisherCards.Length != 6)
                errors.Add("LessonManager should reference exactly 6 extinguisher cards.");
        }

        PlayerController player = UnityEngine.Object.FindFirstObjectByType<PlayerController>();
        if (player == null) errors.Add("No PlayerController (player rig) in the scene.");
        else if (player.playerCamera == null) errors.Add("PlayerController.playerCamera is not assigned.");
        else if (player.playerCamera.GetComponent<AudioListener>() == null)
            notes.Add("The player camera has no AudioListener - alarm audio will be silent.");

        if (UnityEngine.Object.FindFirstObjectByType<LessonUI>() == null) errors.Add("No LessonUI in the scene.");
        if (UnityEngine.Object.FindFirstObjectByType<EventSystem>() == null) errors.Add("No EventSystem in the scene.");
        if (UnityEngine.Object.FindFirstObjectByType<AlarmController>() == null) errors.Add("No AlarmController in the scene.");
        if (UnityEngine.Object.FindFirstObjectByType<FireDemo>() == null) errors.Add("No FireDemo in the scene.");
        if (UnityEngine.Object.FindFirstObjectByType<CorridorSmoke>() == null) errors.Add("No CorridorSmoke in the scene.");

        EvacuationController evacuation = UnityEngine.Object.FindFirstObjectByType<EvacuationController>();
        if (evacuation == null) errors.Add("No EvacuationController in the scene.");
        else
        {
            if (evacuation.checkpoints == null || evacuation.checkpoints.Count < 4)
                errors.Add("EvacuationController should have at least 4 checkpoints.");
            if (evacuation.corridorSmoke == null)
                errors.Add("EvacuationController.corridorSmoke is not assigned.");
        }

        // Every interactable needs a collider, otherwise the player can never look at it.
        MonoBehaviour[] behaviours = UnityEngine.Object.FindObjectsByType<MonoBehaviour>(FindObjectsInactive.Include, FindObjectsSortMode.None);
        int interactables = 0;
        foreach (MonoBehaviour behaviour in behaviours)
        {
            if (!(behaviour is IInteractable)) continue;
            interactables++;
            if (behaviour.GetComponentInChildren<Collider>() == null)
                errors.Add(behaviour.name + " is interactable but has no collider.");
        }
        notes.Add(interactables + " interactable objects found.");

        // Checkpoints must use trigger colliders.
        foreach (CheckpointTrigger checkpoint in UnityEngine.Object.FindObjectsByType<CheckpointTrigger>(FindObjectsInactive.Include, FindObjectsSortMode.None))
        {
            Collider collider = checkpoint.GetComponent<Collider>();
            if (collider == null || !collider.isTrigger)
                errors.Add(checkpoint.name + " needs a trigger collider.");
        }

        // Editor / project environment: these are the two settings that most often make a
        // Unity 6 project look "broken" even though every object is wired correctly.
        notes.Add("Unity version: " + Application.unityVersion);
        if (PathIsRisky(out int pathLength, out int worstCase))
            errors.Add("The project folder path is " + pathLength + " characters and the longest package " +
                       "file would reach " + worstCase + ". " + PathAdvice() +
                       " Windows fails to import package files over " + WindowsPathLimit +
                       " characters (DirectoryNotFoundException, asset import worker crash).");

        int inputHandler = ActiveInputHandler();
        if (inputHandler == 1)
            errors.Add("Active Input Handling is 'Input System Package (New)'. This trainer uses the " +
                       "legacy Input Manager, so set Player Settings > Active Input Handling to 'Both' " +
                       "and let Unity restart.");
        else if (inputHandler == 2)
            notes.Add("Active Input Handling is 'Both' - keyboard, mouse and XR input are all available.");
        else if (inputHandler == 0)
            notes.Add("Active Input Handling is 'Input Manager (Old)' - desktop controls work. " +
                      "Select 'Both' if you want to use the XR Interaction Toolkit device simulator.");

        if (XRSettings.supportedDevices == null || XRSettings.supportedDevices.Length == 0)
            notes.Add("No XR device is enabled yet. Desktop play works now; to test in a headset, " +
                      "enable OpenXR in Project Settings > XR Plug-in Management (see the README).");

        OpenXrReport(notes);

        // Player spawn should be inside the first corridor.
        if (lesson != null && lesson.startPoint != null)
        {
            Vector3 start = lesson.startPoint.position;
            if (start.z < -2f || start.z > 18f)
                notes.Add("Player start is at z=" + start.z + "; expected inside the first corridor.");
        }

        string summary = errors.Count == 0
            ? "[Fire Safety] Validation passed with " + notes.Count + " note(s)."
            : "[Fire Safety] Validation found " + errors.Count + " problem(s).";

        if (errors.Count == 0) Debug.Log(summary); else Debug.LogError(summary);
        foreach (string note in notes) Debug.Log("[Fire Safety] Note: " + note);
        foreach (string error in errors) Debug.LogError("[Fire Safety] " + error);

        if (errors.Count == 0)
            EditorUtility.DisplayDialog("Validation passed",
                "All lesson objects, references and colliders are wired up.\n\n" + notes.Count +
                " note(s) were written to the Console.", "OK");
        else
            EditorUtility.DisplayDialog("Validation problems",
                errors.Count + " problem(s) were written to the Console.", "OK");
    }

    /// <summary>
    /// Reports the OpenXR configuration that decides whether a headset actually works:
    /// whether the loader is enabled for the active build target and whether at least one
    /// controller interaction profile is enabled.
    ///
    /// This uses reflection on purpose. The OpenXR package can be removed (see
    /// tools/set_xr_packages.py desktop), and a hard reference to its assembly would then stop
    /// the Editor scripts from compiling. Reflection keeps this tool usable either way.
    /// </summary>
    static void OpenXrReport(List<string> notes)
    {
        Type settingsType = Type.GetType("UnityEngine.XR.OpenXR.OpenXRSettings, Unity.XR.OpenXR");
        if (settingsType == null)
        {
            notes.Add("OpenXR package: not installed. Desktop play is unaffected; add " +
                      "com.unity.xr.openxr from the Package Manager to use a headset.");
            return;
        }

        object settings = null;
        try
        {
            PropertyInfo active = settingsType.GetProperty("ActiveBuildTargetInstance",
                BindingFlags.Public | BindingFlags.Static);
            settings = active != null ? active.GetValue(null) : null;
        }
        catch (Exception)
        {
            settings = null;
        }

        if (settings == null)
        {
            notes.Add("OpenXR: no settings asset exists yet for the active build target, which " +
                      "usually means the OpenXR loader is not ticked in Project Settings > " +
                      "XR Plug-in Management.");
            return;
        }

        MethodInfo getFeatures = settingsType.GetMethod("GetFeatures", Type.EmptyTypes);
        if (getFeatures == null)
        {
            notes.Add("OpenXR: the installed package exposes an unexpected API; check the OpenXR " +
                      "settings page manually.");
            return;
        }

        Array features = getFeatures.Invoke(settings, null) as Array;
        List<string> profiles = new List<string>();
        int enabledCount = 0;

        if (features != null)
        {
            foreach (object feature in features)
            {
                if (feature == null) continue;
                Type featureType = feature.GetType();

                bool enabled = false;
                PropertyInfo enabledProperty = featureType.GetProperty("enabled",
                    BindingFlags.Public | BindingFlags.Instance);
                if (enabledProperty != null && enabledProperty.PropertyType == typeof(bool))
                    enabled = (bool)enabledProperty.GetValue(feature, null);
                if (!enabled) continue;

                enabledCount++;
                if (IsInteractionProfile(featureType))
                    profiles.Add(ReadableName(featureType.Name));
            }
        }

        if (enabledCount == 0)
        {
            notes.Add("OpenXR: no features are enabled for " + EditorUserBuildSettings.activeBuildTarget +
                      ". Tick OpenXR in Project Settings > XR Plug-in Management.");
            return;
        }

        if (profiles.Count == 0)
        {
            notes.Add("OpenXR: no controller interaction profile is enabled, so the headset will " +
                      "track but the thumbsticks and trigger will do nothing. Open Project Settings > " +
                      "XR Plug-in Management > OpenXR > Enabled Interaction Profiles and add the " +
                      "profile for your headset (Oculus Touch for Quest/Rift, Valve Index, Vive, " +
                      "Microsoft Motion Controller for Windows MR).");
            return;
        }

        notes.Add("OpenXR interaction profiles enabled: " + string.Join(", ", profiles.ToArray()) + ".");
    }

    /// <summary>Interaction profiles all derive from OpenXRInteractionFeature.</summary>
    static bool IsInteractionProfile(Type type)
    {
        for (Type current = type; current != null; current = current.BaseType)
        {
            if (current.Name == "OpenXRInteractionFeature") return true;
        }
        return false;
    }

    /// <summary>"OculusTouchControllerProfile" -> "Oculus Touch Controller".</summary>
    static string ReadableName(string typeName)
    {
        if (typeName.EndsWith("Profile", StringComparison.Ordinal))
            typeName = typeName.Substring(0, typeName.Length - "Profile".Length);

        System.Text.StringBuilder builder = new System.Text.StringBuilder(typeName.Length + 8);
        for (int i = 0; i < typeName.Length; i++)
        {
            char c = typeName[i];
            if (i > 0 && char.IsUpper(c)) builder.Append(' ');
            builder.Append(c);
        }
        return builder.ToString();
    }

    /// <summary>
    /// Reads Player Settings > Active Input Handling: 0 = old Input Manager, 1 = new Input
    /// System, 2 = both, -1 = could not be read.
    /// </summary>
    static int ActiveInputHandler()
    {
        UnityEngine.Object[] assets = AssetDatabase.LoadAllAssetsAtPath("ProjectSettings/ProjectSettings.asset");
        if (assets == null || assets.Length == 0) return -1;
        SerializedProperty property = new SerializedObject(assets[0]).FindProperty("activeInputHandler");
        return property != null ? property.intValue : -1;
    }

    [MenuItem("Tools/VR Fire Safety/Project Setup Report", false, 3)]
    public static void ProjectSetupReport()
    {
        int handler = ActiveInputHandler();
        string handlerName = handler == 0 ? "Input Manager (Old)"
                           : handler == 1 ? "Input System Package (New)"
                           : handler == 2 ? "Both" : "unknown";

        Debug.Log("[Fire Safety] Unity " + Application.unityVersion +
                  " | active input handling: " + handlerName +
                  " | XR devices enabled at build time: " +
                  (XRSettings.supportedDevices.Length == 0 ? "none"
                      : string.Join(", ", XRSettings.supportedDevices)));

        if (handler == 1)
            Debug.LogError("[Fire Safety] Set Player Settings > Active Input Handling to 'Both' " +
                           "(or 'Input Manager (Old)') or the desktop controls will not respond.");
        if (XRSettings.supportedDevices.Length == 0)
            Debug.Log("[Fire Safety] Desktop play works. For a headset, enable OpenXR under " +
                      "Project Settings > XR Plug-in Management, then enable the feature for your device.");

        List<string> xrNotes = new List<string>();
        OpenXrReport(xrNotes);
        foreach (string note in xrNotes) Debug.Log("[Fire Safety] " + note);
    }


    // ------------------------------------------------------------------ //
    // Project location
    // ------------------------------------------------------------------ //

    // Unity resolves package files next to the project, and the deepest URP / Input System
    // editor asset paths are about 145 characters on their own. Windows refuses paths over
    // 260 characters, so a project in a long folder (for example a double-unzipped copy in
    // Downloads) makes Unity throw DirectoryNotFoundException and "Asset import failed"
    // for those files, and the asset import worker can crash.
    const int EstimatedLongestPackagePath = 145;
    const int WindowsPathLimit = 260;
    const int SafetyMargin = 15;

    static string ProjectRoot()
    {
        return System.IO.Path.GetDirectoryName(Application.dataPath);
    }

    /// <summary>True when the project sits somewhere Unity cannot reliably import from.</summary>
    static bool PathIsRisky(out int length, out int worstCase)
    {
        string root = ProjectRoot();
        length = root.Length;
        worstCase = length + EstimatedLongestPackagePath;

        if (worstCase + SafetyMargin > WindowsPathLimit) return true;
        foreach (char character in root)
        {
            if (character > 127) return true;   // non-ASCII paths also upset some importers
        }
        return false;
    }

    static string PathAdvice()
    {
        return "Move the project to a short path such as C:\\VR\\FireSafety, then delete the " +
               "Library folder and reopen the project.";
    }

    [InitializeOnLoadMethod]
    static void WarnAboutProjectPath()
    {
        if (!PathIsRisky(out int length, out int worstCase)) return;

        Debug.LogWarning("[Fire Safety] The project folder path is " + length + " characters long ("
                         + ProjectRoot() + "). The longest package files add about "
                         + EstimatedLongestPackagePath + ", which reaches " + worstCase +
                         " characters - Windows refuses paths over " + WindowsPathLimit +
                         ". Expect DirectoryNotFoundException, \"Asset import failed\" and possibly " +
                         "an asset import worker crash. " + PathAdvice());
    }

    [MenuItem("Tools/VR Fire Safety/Check Project Location", false, 4)]
    public static void CheckProjectLocation()
    {
        PathIsRisky(out int length, out int worstCase);
        Debug.Log("[Fire Safety] Project folder: " + ProjectRoot() + " (" + length +
                  " characters). The longest package file would reach about " + worstCase + ".");

        if (worstCase + SafetyMargin > WindowsPathLimit)
            Debug.LogError("[Fire Safety] This path is too long for Windows. " + PathAdvice());
        else if (worstCase + 3 * SafetyMargin > WindowsPathLimit)
            Debug.LogWarning("[Fire Safety] Close to the 260 character Windows path limit. " + PathAdvice());
        else
            Debug.Log("[Fire Safety] Project path length is fine.");
    }

    static void Require<T>(ref T reference, string label, List<string> errors) where T : UnityEngine.Object
    {
        if (reference == null) errors.Add(label + " is not assigned.");
    }

    [MenuItem("Tools/VR Fire Safety/Open Project README", false, 20)]
    public static void OpenReadme()
    {
        TextAsset readme = AssetDatabase.LoadAssetAtPath<TextAsset>("Assets/Documentation/README.md");
        if (readme != null) AssetDatabase.OpenAsset(readme);
        else Debug.Log("[Fire Safety] README is at Assets/Documentation/README.md");
    }
}
