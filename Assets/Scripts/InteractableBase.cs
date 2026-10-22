using UnityEngine;

/// <summary>
/// Shared behaviour for every object the player can use.
/// Handles the prompt text and a gentle "I am looking at this" pulse, and leaves the
/// actual action to the derived class (alarm, door, extinguisher, display...).
/// </summary>
public abstract class InteractableBase : MonoBehaviour, IInteractable
{
    [Header("Interaction")]
    [Tooltip("Shown in the HUD, for example: Raise the fire alarm")]
    public string interactionName = "Interact";

    [Tooltip("Untick to make the object temporarily non-interactive.")]
    public bool available = true;

    [Tooltip("Pulse the object slightly while the player looks at it.")]
    public bool pulseOnHover = true;

    [Tooltip("Scale multiplier used for the hover pulse.")]
    public float hoverScale = 1.04f;

    Vector3 originalScale;
    bool highlighted;
    bool scaleCaptured;

    public virtual string InteractionPrompt => interactionName;

    public virtual bool IsAvailable => available && isActiveAndEnabled && gameObject.activeInHierarchy;

    protected virtual void Awake()
    {
        originalScale = transform.localScale;
        scaleCaptured = true;
    }

    public abstract void Interact(PlayerController player);

    public void SetHighlighted(bool value)
    {
        highlighted = value && pulseOnHover;
    }

    protected virtual void Update()
    {
        if (!scaleCaptured || !pulseOnHover) return;
        Vector3 target = highlighted ? originalScale * hoverScale : originalScale;
        transform.localScale = Vector3.Lerp(transform.localScale, target, Time.deltaTime * 8f);
    }

    /// <summary>Send an event id to the lesson manager if one exists.</summary>
    protected void NotifyLesson(string eventId)
    {
        if (LessonManager.Instance != null)
            LessonManager.Instance.Notify(eventId);
    }
}
