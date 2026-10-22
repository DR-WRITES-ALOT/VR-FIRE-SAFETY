using System;
using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.SceneManagement;

/// <summary>
/// The brain of the training experience. It walks the player through the four sections,
/// shows the teaching panels, unlocks interactions step by step and drives the evacuation.
///
/// Everything is a simple linear stage machine on purpose: a beginner project should be
/// easy to read, change and extend.
/// </summary>
public class LessonManager : MonoBehaviour
{
    public static LessonManager Instance;

    /// <summary>Set before reloading the scene so the lesson starts without the menu.</summary>
    public static bool AutoStartOnLoad;

    // Stage numbers (kept as constants so the flow below reads like a script).
    const int StageMenu = 0;
    const int StageIntroA = 10;
    const int StageAlarm = 20;
    const int StageAlarmInfo = 25;
    const int StagePhone = 30;
    const int StagePhoneInfo = 35;
    const int StageMaskIntro = 40;
    const int StageMaskDisplay = 45;
    const int StageMaskRules = 46;
    const int StageExtIntro = 50;
    const int StageExtSafety = 55;
    const int StageExtCards = 60;
    const int StagePassInfo = 65;
    const int StageFireWatch = 70;
    const int StageDecision = 75;
    const int StagePassPractice = 80;
    const int StagePassDone = 85;
    const int StageEvacIntro = 90;
    const int StageRoute = 100;
    const int StageLobby = 110;
    const int StageStairs = 120;
    const int StageCorridor2 = 130;
    const int StageHazard = 140;
    const int StageDoorClosed = 145;
    const int StageExitDoor = 150;
    const int StageOutside = 155;
    const int StageAssembly = 160;
    const int StageBurns = 165;
    const int StageSmokeInhalation = 170;
    const int StageComplete = 180;

    [Header("Scene references")]
    public PlayerController player;
    public AlarmController alarm;
    public EvacuationController evacuation;
    public ExtinguisherStation extinguisherStation;
    public FireDemo fire;
    public SimpleInteractable phone;
    public SimpleInteractable maskDisplay;
    public SimpleInteractable liftCall;
    public SimpleInteractable fireViewPoint;
    public DoorController storeDoor;
    public DoorController exitDoor;
    public Transform startPoint;

    [Header("Extinguisher models on the wall")]
    public SimpleInteractable[] extinguisherCards;

    [Header("Audio")]
    public AudioSource uiAudio;
    public AudioClip clickClip;
    public AudioClip panelClip;

    [Header("Timing")]
    public float panelOpenDelay = 0.35f;

    int stage = StageMenu;
    bool paused;
    bool busy;
    readonly HashSet<string> reviewedExtinguishers = new HashSet<string>();
    Coroutine pendingRoutine;

    LessonUI Ui => LessonUI.Instance;

    void Awake()
    {
        Instance = this;
    }

    void Start()
    {
        uiAudio = AudioHelper.Ensure(gameObject, uiAudio, false, 0.6f);
        clickClip = AudioHelper.ClipOrDefault(clickClip, "ui_click");
        panelClip = AudioHelper.ClipOrDefault(panelClip, "ui_click");

        if (AutoStartOnLoad)
        {
            AutoStartOnLoad = false;
            ShowMenu(false);
            StartTraining();
        }
        else
        {
            ShowMenu(true);
        }
    }

    void Update()
    {
        if (Input.GetKeyDown(KeyCode.Escape))
        {
            if (paused) Resume();
            else Pause();
        }
    }

    // ------------------------------------------------------------------ //
    // Menu, pause, restart
    // ------------------------------------------------------------------ //

    public void ShowMenu(bool visible)
    {
        Time.timeScale = 1f;
        paused = false;
        stage = StageMenu;
        ResetLessonState();
        if (player != null && startPoint != null)
            player.Teleport(startPoint.position, startPoint.eulerAngles.y);
        if (player != null) player.SetUiFocus(visible);

        if (Ui == null) return;
        Ui.SetHudVisible(!visible);
        if (visible) Ui.ShowMenu();
        else Ui.HideMenu();
    }

    public void StartTraining()
    {
        PlayClick();
        if (Ui != null) Ui.HideMenu();
        if (player != null) player.SetUiFocus(false);
        ResetLessonState();
        if (player != null && startPoint != null)
            player.Teleport(startPoint.position, startPoint.eulerAngles.y);
        GoTo(StageIntroA);
    }

    public void RestartTraining()
    {
        PlayClick();
        AutoStartOnLoad = true;
        Time.timeScale = 1f;
        Scene scene = SceneManager.GetActiveScene();
        SceneManager.LoadScene(scene.buildIndex >= 0 ? scene.buildIndex : 0);
    }

    public void ReturnToMenu()
    {
        PlayClick();
        AutoStartOnLoad = false;
        Time.timeScale = 1f;
        Scene scene = SceneManager.GetActiveScene();
        SceneManager.LoadScene(scene.buildIndex >= 0 ? scene.buildIndex : 0);
    }

    public void QuitApplication()
    {
        PlayClick();
#if UNITY_EDITOR
        UnityEditor.EditorApplication.isPlaying = false;
#else
        Application.Quit();
#endif
    }

    public void Pause()
    {
        if (paused || stage == StageMenu) return;
        paused = true;
        Time.timeScale = 0f;
        if (Ui != null) Ui.ShowPause();
        if (player != null) player.SetUiFocus(true);
    }

    public void Resume()
    {
        PlayClick();
        paused = false;
        Time.timeScale = 1f;
        if (Ui != null) Ui.HidePause();
        if (player != null)
        {
            player.SetUiFocus(false);
            if (Ui != null) player.SetUiFocus(Ui.PanelOpen);
        }
    }

    void ResetLessonState()
    {
        busy = false;
        reviewedExtinguishers.Clear();
        if (pendingRoutine != null)
        {
            StopCoroutine(pendingRoutine);
            pendingRoutine = null;
        }
        if (Ui != null)
        {
            Ui.HidePanel();
            Ui.HidePause();
            Ui.HideMenu();
            Ui.SetPrompt(string.Empty);
        }
        if (extinguisherStation != null)
        {
            extinguisherStation.ResetStation();
            extinguisherStation.available = true;
        }
        if (evacuation != null)
        {
            evacuation.RouteComplete = false;
            evacuation.SetSmokeHazardActive(true);
            foreach (var checkpoint in evacuation.checkpoints)
            {
                checkpoint.reached = false;
                // Triggers only fire once, so re-arm them for a fresh attempt.
                if (checkpoint.trigger != null) checkpoint.trigger.Rearm();
            }
        }
        if (storeDoor != null)
        {
            // The fire door stays locked until the evacuation reaches the smoke hazard,
            // so it cannot be closed early and leave the hazard impossible to resolve.
            storeDoor.finished = false;
            storeDoor.closeOnce = true;
            storeDoor.Lock();
        }
        if (exitDoor != null) exitDoor.Lock();
        if (liftCall != null) liftCall.available = true;
        SetExtinguisherCardsAvailable(false);
    }

    // ------------------------------------------------------------------ //
    // Stage machine
    // ------------------------------------------------------------------ //

    void GoTo(int newStage)
    {
        stage = newStage;
        switch (stage)
        {
            case StageIntroA:
                Section("Section A - Immediate response");
                Objective("Learn the correct first response to a fire.");
                ShowInfo("A1  You discover a fire", LessonContent.SectionA.IntroBody, null,
                         "I understand", BeginAlarmStep);
                break;

            case StageAlarm:
                Section("Section A - Immediate response");
                Objective(LessonContent.SectionA.AlarmObjective);
                break;

            case StageAlarmInfo:
                Section("Section A - Immediate response");
                Objective("Call 112, then evacuate.");
                ShowInfo("A2  Alarm raised", LessonContent.SectionA.AlarmRaisedBody, null,
                         "Next: call 112", BeginPhoneStep);
                break;

            case StagePhone:
                Section("Section A - Immediate response");
                Objective(LessonContent.SectionA.PhoneObjective);
                break;

            case StagePhoneInfo:
                Section("Section B - Masks and extinguishers");
                Objective("Read what masks can and cannot do.");
                ShowInfo("A3  Emergency call", LessonContent.SectionA.PhoneDoneBody, null,
                         "Next: masks", BeginMaskIntro);
                break;

            case StageMaskIntro:
                Section("Section B - Masks and extinguishers");
                Objective("Understand smoke and what masks can do.");
                ShowInfo("B1  Smoke is toxic", LessonContent.SectionB.MaskBody, null,
                         "Got it", BeginMaskStep);
                break;

            case StageMaskDisplay:
                Section("Section B - Masks and extinguishers");
                Objective(LessonContent.SectionB.MaskObjective);
                break;

            case StageMaskRules:
                Section("Section B - Masks and extinguishers");
                Objective("Learn the mask safety rules.");
                ShowInfo("B2  Never rely on a mask", LessonContent.SectionB.MaskRulesBody, null,
                         "Next: extinguisher types", (Action)ShowExtIntro);
                break;

            case StageExtIntro:
                Section("Section B - Masks and extinguishers");
                Objective("Learn the Indian fire classes.");
                ShowInfo("B3  Indian fire classes", LessonContent.SectionB.ExtIntroBody, null,
                         "Next: safety rules", (Action)ShowExtSafety);
                break;

            case StageExtSafety:
                Section("Section B - Masks and extinguishers");
                Objective("Learn the extinguisher safety rules.");
                ShowInfo("B4  Safety rules", LessonContent.SectionB.ExtSafetyBody, null,
                         "Inspect the six models", (Action)BeginExtCardStep);
                break;

            case StageExtCards:
                Section("Section B - Masks and extinguishers");
                Objective(ExtinguisherObjective());
                break;

            case StagePassInfo:
                Section("Section B - Masks and extinguishers");
                Objective("Learn the PASS technique.");
                ShowInfo("B5  PASS technique", LessonContent.SectionB.PassBody,
                         "PASS poster is on the wall next to the extinguishers.",
                         "Next: the fire demonstration", (Action)BeginFireWatch);
                break;

            case StageFireWatch:
                Section("Section B - Masks and extinguishers");
                Objective(LessonContent.SectionB.FireObjective);
                break;

            case StageDecision:
                Section("Section B - Masks and extinguishers");
                Objective("Make the safe response decision.");
                break;

            case StagePassPractice:
                Section("Section B - Masks and extinguishers");
                Objective(LessonContent.SectionB.PassPracticeObjective);
                if (extinguisherStation != null) extinguisherStation.practiceActive = true;
                break;

            case StagePassDone:
                Section("Section B - Masks and extinguishers");
                Objective("Demonstration complete.");
                ShowInfo("B6  " + LessonContent.SectionB.PassDoneTitle,
                         LessonContent.SectionB.PassDoneBody, null,
                         "Begin the evacuation exercise", (Action)BeginEvacIntro);
                break;

            case StageEvacIntro:
                Section("Section C - Evacuation exercise");
                Objective("Prepare to evacuate.");
                ShowInfo(LessonContent.SectionC.IntroTitle, LessonContent.SectionC.IntroBody,
                         "Route: corridor 1  ->  stairs  ->  corridor 2  ->  assembly point",
                         "Begin evacuation", (Action)BeginRoute);
                break;

            case StageRoute:
                Section("Section C - Evacuation exercise");
                Objective(LessonContent.SectionC.StairObjective);
                if (evacuation != null) evacuation.SetSmokeHazardActive(true);
                break;

            case StageLobby:
                Section("Section C - Evacuation exercise");
                Objective("The lifts are here. Interact with the lift call button (E) to see why not to use it.");
                break;

            case StageStairs:
                Section("Section C - Evacuation exercise");
                Objective("Walk down the stairs. Hold the handrail and keep to the right.");
                break;

            case StageCorridor2:
                Section("Section C - Evacuation exercise");
                Objective("Follow the EXIT signs along the second corridor.");
                break;

            case StageHazard:
                Section("Section C - Evacuation exercise");
                Objective(LessonContent.SectionC.HazardObjective);
                break;

            case StageDoorClosed:
                Section("Section C - Evacuation exercise");
                Objective("Continue along the corridor to the exit doors.");
                break;

            case StageExitDoor:
                Section("Section C - Evacuation exercise");
                Objective(LessonContent.SectionC.ExitObjective);
                break;

            case StageOutside:
                Section("Section C - Evacuation exercise");
                Objective(LessonContent.SectionC.OutdoorObjective);
                break;

            case StageAssembly:
                Section("Section D - First aid summary");
                Objective("Review the first aid summary at the assembly point.");
                ShowInfo(LessonContent.SectionC.AssemblyTitle, LessonContent.SectionC.AssemblyBody, null,
                         "Burns - first aid", (Action)ShowBurns);
                break;

            case StageBurns:
                Section("Section D - First aid summary");
                Objective("Burns first aid.");
                ShowInfo(LessonContent.SectionC.BurnsTitle, LessonContent.SectionC.BurnsBody,
                         "Cool first, cover later, call 112 if the burn is serious.",
                         "Next: smoke inhalation", (Action)ShowSmokeInhalation);
                break;

            case StageSmokeInhalation:
                Section("Section D - First aid summary");
                Objective("Smoke inhalation first aid.");
                ShowInfo(LessonContent.SectionC.SmokeInhalationTitle, LessonContent.SectionC.SmokeInhalationBody,
                         "Never enter a dangerous area to retrieve a casualty.",
                         "Finish training", (Action)ShowComplete);
                break;

            case StageComplete:
                Section("Training complete");
                Objective("Training complete - well done.");
                ShowInfo(LessonContent.SectionC.CompleteTitle, LessonContent.SectionC.CompleteBody,
                         LessonContent.Disclaimer,
                         null, null, new[] { "Restart training", "Main menu" },
                         new Action[] { RestartTraining, ReturnToMenu });
                break;
        }
    }

    // ------------------------------------------------------------------ //
    // Section A steps
    // ------------------------------------------------------------------ //

    void BeginAlarmStep()
    {
        GoTo(StageAlarm);
        if (alarm != null) alarm.available = true;
    }

    void BeginPhoneStep()
    {
        GoTo(StagePhone);
        if (phone != null) phone.available = true;
    }

    void BeginMaskIntro()
    {
        GoTo(StageMaskIntro);
    }

    void BeginMaskStep()
    {
        GoTo(StageMaskDisplay);
        if (maskDisplay != null) maskDisplay.available = true;
    }

    void ShowExtIntro()
    {
        GoTo(StageExtIntro);
    }

    void ShowExtSafety()
    {
        GoTo(StageExtSafety);
    }

    void BeginExtCardStep()
    {
        GoTo(StageExtCards);
        SetExtinguisherCardsAvailable(true);
    }

    void BeginFireWatch()
    {
        GoTo(StageFireWatch);
        if (fireViewPoint != null) fireViewPoint.available = true;
        if (fire != null) fire.BeginBurning();
    }

    void ShowDecisionPanel()
    {
        if (stage != StageDecision)
        {
            stage = StageDecision;
            Objective("Make the safe response decision.");
        }
        if (Ui == null) return;
        Ui.ShowPanel(LessonContent.SectionB.FireDecisionTitle, LessonContent.SectionB.FireDecisionBody,
            "The alarm is sounding. The corridor behind you is clear.",
            new[]
            {
                "Use the extinguisher",
                "Put on a cloth mask and carry on",
                "Go back for your belongings"
            },
            new Action[]
            {
                () => ChooseDecision("extinguish"),
                () => ChooseDecision("mask"),
                () => ChooseDecision("belongings")
            });
    }

    void ChooseDecision(string choice)
    {
        PlayClick();
        switch (choice)
        {
            case "extinguish":
                Ui.ShowPanel("B5  Safe response", LessonContent.SectionB.DecisionCorrectBody, null,
                    new[] { "Practise PASS now" }, new[] { (Action)BeginPassPractice });
                break;
            case "mask":
                Ui.ShowPanel("Not the safe choice", LessonContent.SectionB.DecisionWrongMaskBody, null,
                    new[] { "Try again" }, new[] { (Action)ShowDecisionPanel });
                break;
            case "belongings":
                Ui.ShowPanel("Not the safe choice", LessonContent.SectionB.DecisionWrongBelongingsBody, null,
                    new[] { "Try again" }, new[] { (Action)ShowDecisionPanel });
                break;
        }
    }

    void BeginPassPractice()
    {
        GoTo(StagePassPractice);
    }

    // ------------------------------------------------------------------ //
    // Section C steps
    // ------------------------------------------------------------------ //

    void BeginEvacIntro()
    {
        GoTo(StageEvacIntro);
    }

    void BeginRoute()
    {
        GoTo(StageRoute);
        if (evacuation != null) evacuation.SetSmokeHazardActive(true);
    }

    void BeginEvacAfterLift()
    {
        GoTo(StageStairs);
    }

    void BeginCorridor2()
    {
        GoTo(StageCorridor2);
    }

    // ------------------------------------------------------------------ //
    // Section D
    // ------------------------------------------------------------------ //

    void ShowBurns()
    {
        GoTo(StageBurns);
    }

    void ShowSmokeInhalation()
    {
        GoTo(StageSmokeInhalation);
    }

    void ShowComplete()
    {
        GoTo(StageComplete);
        if (evacuation != null) evacuation.MarkRouteComplete();
    }

    // ------------------------------------------------------------------ //
    // Events from interactables
    // ------------------------------------------------------------------ //

    /// <summary>Every interactable reports here with a short event id.</summary>
    public void Notify(string eventId)
    {
        if (string.IsNullOrEmpty(eventId) || paused || stage == StageMenu) return;

        if (eventId.StartsWith("pass_step_"))
        {
            if (stage == StagePassPractice && extinguisherStation != null)
                Objective("PASS practice: " + extinguisherStation.InteractionPrompt);
            return;
        }

        if (eventId.StartsWith("ext_card_"))
        {
            HandleExtinguisherCard(eventId.Substring("ext_card_".Length));
            return;
        }

        switch (eventId)
        {
            case "alarm":
                if (stage == StageAlarm) GoTo(StageAlarmInfo);
                break;

            case "phone":
                if (stage == StagePhone) GoTo(StagePhoneInfo);
                break;

            case "mask_display":
                if (stage == StageMaskIntro) BeginMaskStep();
                else if (stage == StageMaskDisplay) GoTo(StageMaskRules);
                break;

            case "fire_demo":
                if (stage == StageFireWatch) ShowDecisionPanel();
                break;

            case "pass_complete":
                if (stage == StagePassPractice) SchedulePassComplete();
                break;

            case "lift":
                if (stage == StageLobby) ShowLiftPanel();
                break;

            case "door_closed":
                if (stage == StageHazard || stage == StageCorridor2) OnFireDoorClosed();
                break;

            case "exit_opened":
                if (stage == StageExitDoor || stage == StageDoorClosed) GoTo(StageOutside);
                break;

            case "checkpoint_lobby":
                if (stage == StageRoute) GoTo(StageLobby);
                break;

            case "checkpoint_stairs_bottom":
                // Reaching the bottom of the stairs always keeps the lesson in step, even if
                // the player walked past the lift without using the call button.
                if (stage == StageLobby) GoTo(StageStairs);
                if (stage == StageStairs) ShowStairsPanel();
                break;

            case "checkpoint_corridor2":
                if (stage == StageLobby || stage == StageStairs) GoTo(StageCorridor2);
                if (stage == StageCorridor2) Objective("Keep going. Watch the corridor ahead.");
                break;

            case "checkpoint_smoke_approach":
                // The smoke briefing must appear even if the player skipped a panel earlier,
                // because it is the only way to unlock the fire door.
                if (stage == StageLobby || stage == StageStairs) GoTo(StageCorridor2);
                if (stage == StageCorridor2) ShowHazardPanel();
                break;

            case "checkpoint_assembly":
                if (stage != StageAssembly && stage != StageComplete)
                    GoTo(StageAssembly);
                break;
        }
    }

    void HandleExtinguisherCard(string id)
    {
        if (stage != StageExtCards)
        {
            return;
        }

        // Scene cards report "ext_card_water"; LessonContent ids are "ext_water".
        string key = id.StartsWith("ext_") ? id : "ext_" + id;
        LessonContent.ExtinguisherInfo info =
            Array.Find(LessonContent.Extinguishers, e => e.Id == key || e.Id == id);
        if (info == null) return;

        reviewedExtinguishers.Add(id);
        Objective(ExtinguisherObjective());

        if (Ui == null) return;
        Ui.ShowPanel(info.Title, info.Body, "Reviewed " + reviewedExtinguishers.Count + " of 6 models.",
            new[] { "Close" }, new[] { (Action)AfterCardReviewed });
    }

    void AfterCardReviewed()
    {
        PlayClick();
        if (Ui != null) Ui.HidePanel();
        if (reviewedExtinguishers.Count >= 6)
        {
            GoTo(StagePassInfo);
        }
        else
        {
            Objective(ExtinguisherObjective());
        }
    }

    string ExtinguisherObjective()
    {
        return "Inspect all six extinguisher models. Reviewed: " + reviewedExtinguishers.Count + " of 6.";
    }

    void ShowLiftPanel()
    {
        if (Ui == null) return;
        Ui.ShowPanel(LessonContent.SectionC.LiftTitle, LessonContent.SectionC.LiftBody,
            "Lifts are for normal use only, not for fire evacuation.",
            new[] { "Take the stairs" }, new[] { (Action)BeginEvacAfterLift });
    }

    void ShowStairsPanel()
    {
        if (Ui == null) return;
        Ui.ShowPanel(LessonContent.SectionC.StairsTitle, LessonContent.SectionC.StairsBody,
            "You are now on the ground floor.",
            new[] { "Continue to the second corridor" }, new[] { (Action)BeginCorridor2 });
    }

    void ShowHazardPanel()
    {
        if (Ui == null) return;
        Ui.ShowPanel(LessonContent.SectionC.HazardTitle, LessonContent.SectionC.HazardBody,
            "Dense smoke is toxic. Do not walk into it.",
            new[] { "Close the fire door" }, new[] { (Action)AcceptHazardTask });
    }

    void AcceptHazardTask()
    {
        PlayClick();
        GoTo(StageHazard);
        if (Ui != null) Ui.HidePanel();
        if (storeDoor != null) storeDoor.Unlock();
        Objective(LessonContent.SectionC.HazardObjective);
    }

    void OnFireDoorClosed()
    {
        if (evacuation != null) evacuation.SetSmokeHazardActive(false);
        GoTo(StageDoorClosed);
        if (Ui == null) return;
        Ui.ShowPanel(LessonContent.SectionC.DoorClosedTitle, LessonContent.SectionC.DoorClosedBody, null,
            new[] { "Continue to the exit" }, new[] { (Action)AfterDoorClosed });
    }

    void AfterDoorClosed()
    {
        PlayClick();
        if (Ui != null) Ui.HidePanel();
        if (exitDoor != null) exitDoor.Unlock();
        GoTo(StageExitDoor);
        Objective(LessonContent.SectionC.ExitObjective);
    }

    void SchedulePassComplete()
    {
        if (busy) return;
        busy = true;
        if (pendingRoutine != null) StopCoroutine(pendingRoutine);
        pendingRoutine = StartCoroutine(PassCompleteRoutine());
    }

    IEnumerator PassCompleteRoutine()
    {
        yield return new WaitForSeconds(2.2f);
        busy = false;
        pendingRoutine = null;
        GoTo(StagePassDone);
    }

    // ------------------------------------------------------------------ //
    // UI helpers
    // ------------------------------------------------------------------ //

    void Section(string text)
    {
        if (Ui != null) Ui.SetSection(text);
    }

    void Objective(string text)
    {
        if (Ui != null) Ui.SetObjective(text);
    }

    void ShowInfo(string title, string body, string footer, string primaryLabel, Action primaryAction)
    {
        ShowInfo(title, body, footer, primaryLabel, primaryAction, null, null);
    }

    void ShowInfo(string title, string body, string footer, string primaryLabel, Action primaryAction,
                  string[] labels, Action[] actions)
    {
        if (pendingRoutine != null)
        {
            StopCoroutine(pendingRoutine);
            pendingRoutine = null;
        }
        pendingRoutine = StartCoroutine(ShowInfoRoutine(title, body, footer, primaryLabel, primaryAction, labels, actions));
    }

    IEnumerator ShowInfoRoutine(string title, string body, string footer, string primaryLabel,
                                Action primaryAction, string[] labels, Action[] actions)
    {
        yield return new WaitForSeconds(panelOpenDelay);
        pendingRoutine = null;
        if (Ui == null) yield break;

        if (labels != null && labels.Length > 0)
        {
            Ui.ShowPanel(title, body, footer, labels, actions);
        }
        else if (!string.IsNullOrEmpty(primaryLabel))
        {
            Ui.ShowPanel(title, body, footer, new[] { primaryLabel },
                new[] { primaryAction ?? (Action)(() => Ui.HidePanel()) });
        }
        else
        {
            Ui.ShowPanel(title, body, footer, new string[0], new Action[0]);
        }
    }

    void SetExtinguisherCardsAvailable(bool value)
    {
        if (extinguisherCards == null) return;
        for (int i = 0; i < extinguisherCards.Length; i++)
            if (extinguisherCards[i] != null) extinguisherCards[i].available = value;
    }

    void PlayClick()
    {
        if (uiAudio != null && clickClip != null) uiAudio.PlayOneShot(clickClip, 0.6f);
    }

    public void PlayPanelSound()
    {
        if (uiAudio != null && panelClip != null) uiAudio.PlayOneShot(panelClip, 0.5f);
    }

    // ------------------------------------------------------------------ //
    // Danger handling
    // ------------------------------------------------------------------ //

    /// <summary>The player walked into dense smoke.</summary>
    public void OnEnteredDenseSmoke(Vector3 safePosition)
    {
        if (Ui != null)
            Ui.ShowWarning("DENSE SMOKE - TURN BACK. Smoke is toxic and you cannot see through it.", 5f);
        if (player != null) player.Teleport(safePosition, player.transform.eulerAngles.y);
        if (stage == StageCorridor2) ShowHazardPanel();
    }

    /// <summary>Default safe spot used when a hazard sends the player back.</summary>
    public Vector3 HazardRespawnPoint { get; set; }
}
