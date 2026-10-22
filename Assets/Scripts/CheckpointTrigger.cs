using UnityEngine;

/// <summary>
/// Invisible volume that tells the evacuation controller (and therefore the lesson)
/// when the player reaches a point on the route.
/// The collider must have "Is Trigger" ticked.
/// </summary>
[RequireComponent(typeof(Collider))]
public class CheckpointTrigger : MonoBehaviour
{
    [Tooltip("Identifier used by LessonManager, for example checkpoint_lobby.")]
    public string checkpointId = "checkpoint";

    [Tooltip("Only react to the player, not to props.")]
    public bool playerOnly = true;

    bool fired;

    void Reset()
    {
        GetComponent<Collider>().isTrigger = true;
    }

    void OnTriggerEnter(Collider other)
    {
        if (fired) return;
        if (playerOnly && other.GetComponentInParent<PlayerController>() == null) return;
        fired = true;

        if (EvacuationController.Instance != null)
            EvacuationController.Instance.ReportCheckpoint(checkpointId);

        if (LessonManager.Instance != null)
            LessonManager.Instance.Notify(checkpointId);
    }

    /// <summary>Re-arm the trigger (used when the training is restarted without reloading).</summary>
    public void Rearm()
    {
        fired = false;
    }
}
