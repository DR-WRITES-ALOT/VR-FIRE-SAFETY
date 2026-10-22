using UnityEngine;

/// <summary>
/// A general purpose interactable. Put it on displays, phones, the lift call button,
/// extinguisher models and so on, and give it an event id that LessonManager understands.
/// </summary>
public class SimpleInteractable : InteractableBase
{
    [Tooltip("Event id sent to LessonManager, for example mask_display or lift.")]
    public string eventId = "";

    [Tooltip("Optional prompt used while the object is not the current focus of the lesson.")]
    public string unavailablePrompt = "";

    [Header("Feedback (optional)")]
    public AudioSource audioSource;
    public AudioClip interactClip;

    public override bool IsAvailable => available && base.IsAvailable;

    public override string InteractionPrompt
    {
        get
        {
            if (!available && !string.IsNullOrEmpty(unavailablePrompt)) return unavailablePrompt;
            return interactionName;
        }
    }

    public override void Interact(PlayerController player)
    {
        if (audioSource != null && interactClip != null)
            audioSource.PlayOneShot(interactClip);

        NotifyLesson(eventId);
    }
}
