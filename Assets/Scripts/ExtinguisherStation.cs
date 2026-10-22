using System.Collections.Generic;
using UnityEngine;

/// <summary>
/// The single extinguisher practice station next to the contained fire.
/// It walks the player through PASS, one interaction per step, then discharges the unit.
///
/// There is deliberately only one practice station: the six labelled models on the wall
/// are for reading, not for six separate fires.
/// </summary>
public class ExtinguisherStation : InteractableBase
{
    [Header("References")]
    public FireDemo fire;

    [Header("State")]
    [Tooltip("Only available once the lesson reaches the PASS practice step.")]
    public bool practiceActive;

    [Tooltip("Optional renderer tinted while the station can be used.")]
    public Renderer highlightRenderer;

    public string[] stepPrompts =
    {
        "PULL the safety pin",
        "AIM the nozzle at the base of the fire",
        "SQUEEZE the handle",
        "SWEEP across the base of the fire"
    };

    int step;

    public override bool IsAvailable => practiceActive && base.IsAvailable;

    public override string InteractionPrompt
    {
        get
        {
            if (!practiceActive) return "Extinguisher - follow the PASS poster first";
            if (step < stepPrompts.Length) return "Step " + (step + 1) + " of 4: " + stepPrompts[step];
            return "Demonstration complete";
        }
    }

    public override void Interact(PlayerController player)
    {
        if (!practiceActive) return;

        string key = PlayerController.Instance != null && PlayerController.Instance.IsXrActive
            ? "Trigger" : "E";
        if (step == 0 && LessonUI.Instance != null)
            LessonUI.Instance.SetPrompt("[" + key + "]  Pin pulled - now " + stepPrompts[1].ToLowerInvariant());
        else if (step == 1 && LessonUI.Instance != null)
            LessonUI.Instance.SetPrompt("[" + key + "]  Aimed at the base - now " + stepPrompts[2].ToLowerInvariant());

        step++;
        NotifyLesson("pass_step_" + step);

        if (step >= stepPrompts.Length)
        {
            practiceActive = false;
            if (fire != null) fire.Extinguish();
            NotifyLesson("pass_complete");
        }
    }

    /// <summary>Reset the station to step 1 (used by the in-game reset button).</summary>
    public void ResetStation()
    {
        step = 0;
        practiceActive = false;
    }
}
