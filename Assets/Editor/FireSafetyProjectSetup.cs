using System.Collections.Generic;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.EventSystems;
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

        LessonManager lesson = Object.FindObjectOfType<LessonManager>();
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

        PlayerController player = Object.FindObjectOfType<PlayerController>();
        if (player == null) errors.Add("No PlayerController (player rig) in the scene.");
        else if (player.playerCamera == null) errors.Add("PlayerController.playerCamera is not assigned.");
        else if (player.playerCamera.GetComponent<AudioListener>() == null)
            notes.Add("The player camera has no AudioListener - alarm audio will be silent.");

        if (Object.FindObjectOfType<LessonUI>() == null) errors.Add("No LessonUI in the scene.");
        if (Object.FindObjectOfType<EventSystem>() == null) errors.Add("No EventSystem in the scene.");
        if (Object.FindObjectOfType<AlarmController>() == null) errors.Add("No AlarmController in the scene.");
        if (Object.FindObjectOfType<FireDemo>() == null) errors.Add("No FireDemo in the scene.");
        if (Object.FindObjectOfType<CorridorSmoke>() == null) errors.Add("No CorridorSmoke in the scene.");

        EvacuationController evacuation = Object.FindObjectOfType<EvacuationController>();
        if (evacuation == null) errors.Add("No EvacuationController in the scene.");
        else
        {
            if (evacuation.checkpoints == null || evacuation.checkpoints.Count < 4)
                errors.Add("EvacuationController should have at least 4 checkpoints.");
            if (evacuation.corridorSmoke == null)
                errors.Add("EvacuationController.corridorSmoke is not assigned.");
        }

        // Every interactable needs a collider, otherwise the player can never look at it.
        MonoBehaviour[] behaviours = Object.FindObjectsOfType<MonoBehaviour>(true);
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
        foreach (CheckpointTrigger checkpoint in Object.FindObjectsOfType<CheckpointTrigger>(true))
        {
            Collider collider = checkpoint.GetComponent<Collider>();
            if (collider == null || !collider.isTrigger)
                errors.Add(checkpoint.name + " needs a trigger collider.");
        }

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

    static void Require<T>(ref T reference, string label, List<string> errors) where T : Object
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
