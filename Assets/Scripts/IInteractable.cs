using UnityEngine;

/// <summary>
/// Anything the player can use with the interact key (E on desktop / trigger in VR).
/// Keeping this to three members makes it easy for beginners to add new objects.
/// </summary>
public interface IInteractable
{
    /// <summary>Text shown in the HUD, for example "Raise the fire alarm".</summary>
    string InteractionPrompt { get; }

    /// <summary>False when the object is not part of the current lesson step.</summary>
    bool IsAvailable { get; }

    /// <summary>Called when the player presses the interact button while looking at this object.</summary>
    void Interact(PlayerController player);
}
