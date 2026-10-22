using System.Collections.Generic;
using UnityEngine;

/// <summary>
/// Manages the single guided evacuation route:
/// first corridor -> stairs -> second corridor -> assembly point.
/// It also owns the one route hazard (the dense smoke in the second corridor).
/// </summary>
public class EvacuationController : MonoBehaviour
{
    public static EvacuationController Instance;

    [System.Serializable]
    public class Checkpoint
    {
        public string id;
        public string displayName;
        [Tooltip("Trigger volume the player walks into.")]
        public CheckpointTrigger trigger;
        [HideInInspector] public bool reached;
    }

    [Header("Route")]
    public List<Checkpoint> checkpoints = new List<Checkpoint>();

    [Header("Hazard")]
    [Tooltip("Dense smoke that blocks the second corridor until the fire door is closed.")]
    public CorridorSmoke corridorSmoke;

    [Header("Feedback")]
    public AudioSource audioSource;
    public AudioClip checkpointClip;

    public bool RouteComplete { get; private set; }
    public string LastCheckpoint { get; private set; }

    void Awake()
    {
        Instance = this;
    }

    void Start()
    {
        audioSource = AudioHelper.Ensure(gameObject, audioSource, true, 0.5f, 1f, 20f);
        checkpointClip = AudioHelper.ClipOrDefault(checkpointClip, "ui_click");
        if (corridorSmoke != null) corridorSmoke.Play();
    }

    /// <summary>Clears (true) or restores (false) the smoke hazard.</summary>
    public void SetSmokeHazardActive(bool active)
    {
        if (corridorSmoke == null) return;
        if (active) corridorSmoke.Play();
        else corridorSmoke.Clear();
    }

    /// <summary>Called by checkpoint triggers.</summary>
    public void ReportCheckpoint(string id)
    {
        Checkpoint checkpoint = checkpoints.Find(c => c.id == id);
        if (checkpoint == null || checkpoint.reached) return;
        checkpoint.reached = true;
        LastCheckpoint = id;

        if (audioSource != null && checkpointClip != null)
            audioSource.PlayOneShot(checkpointClip, 0.3f);
    }

    public bool IsCheckpointReached(string id)
    {
        Checkpoint checkpoint = checkpoints.Find(c => c.id == id);
        return checkpoint != null && checkpoint.reached;
    }

    public void MarkRouteComplete()
    {
        RouteComplete = true;
    }
}
