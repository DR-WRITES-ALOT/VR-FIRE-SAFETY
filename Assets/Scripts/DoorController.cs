using UnityEngine;

/// <summary>
/// A hinged door that the player can open or close.
/// The whole door hangs from a pivot object so a single rotation animates the door leaf.
/// </summary>
public class DoorController : InteractableBase
{
    [Header("Hinge")]
    [Tooltip("Empty object positioned at the hinge edge of the door leaf.")]
    public Transform pivot;

    [Tooltip("Angle (degrees around the pivot's Y axis) when the door is open.")]
    public float openAngle = 95f;

    [Header("State")]
    public bool startsOpen;
    public bool locked;
    public bool closeOnce;
    public float speed = 3.5f;

    [Header("Labels")]
    public string openPrompt = "Open the door";
    public string closePrompt = "Close the door";
    public string lockedPrompt = "Locked";

    [Header("Events")]
    public string eventWhenOpened = "";
    public string eventWhenClosed = "";

    [Header("Feedback")]
    public AudioSource audioSource;
    public AudioClip openClip;
    public AudioClip closeClip;

    Quaternion closedRotation;
    Quaternion openRotation;
    bool open;
    bool finished;

    public bool IsOpen => open;
    public bool IsFinished => finished;

    public override string InteractionPrompt
    {
        get
        {
            if (locked) return lockedPrompt;
            return open ? closePrompt : openPrompt;
        }
    }

    public override bool IsAvailable => !locked && !finished && base.IsAvailable;

    protected override void Awake()
    {
        base.Awake();
        if (pivot == null) pivot = transform;
        closedRotation = pivot.localRotation;
        openRotation = closedRotation * Quaternion.Euler(0f, openAngle, 0f);
        open = startsOpen;
        pivot.localRotation = open ? openRotation : closedRotation;
    }

    public override void Interact(PlayerController player)
    {
        if (locked || finished) return;
        if (open) Close(); else Open();
    }

    public void Open()
    {
        if (open) return;
        open = true;
        PlaySound(openClip);
        if (!string.IsNullOrEmpty(eventWhenOpened)) NotifyLesson(eventWhenOpened);
    }

    public void Close()
    {
        if (!open) return;
        open = false;
        PlaySound(closeClip);
        if (!string.IsNullOrEmpty(eventWhenClosed)) NotifyLesson(eventWhenClosed);
        if (closeOnce) finished = true;
    }

    /// <summary>Close the door as part of the scripted lesson (no player interaction needed).</summary>
    public void CloseForLesson()
    {
        finished = false;
        closeOnce = true;
        Close();
        finished = true;
    }

    /// <summary>
    /// Return the door to the state the lesson expects at the start of an attempt:
    /// usable again, and locked or unlocked as requested.
    /// </summary>
    public void ResetForLesson(bool startLocked)
    {
        finished = false;
        closeOnce = true;
        locked = startLocked;
        open = startsOpen;
        if (pivot != null) pivot.localRotation = open ? openRotation : closedRotation;
    }

    public void Unlock()
    {
        locked = false;
    }

    public void Lock()
    {
        locked = true;
    }

    void PlaySound(AudioClip clip)
    {
        audioSource = AudioHelper.Ensure(gameObject, audioSource, true, 0.7f, 1f, 18f);
        audioSource.clip = AudioHelper.ClipOrDefault(clip, "door_close");
        if (audioSource.clip != null) audioSource.Play();
    }

    protected override void Update()
    {
        base.Update();
        if (pivot == null) return;
        Quaternion target = open ? openRotation : closedRotation;
        pivot.localRotation = Quaternion.Slerp(pivot.localRotation, target, Time.deltaTime * speed);
    }
}
