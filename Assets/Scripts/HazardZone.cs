using UnityEngine;

/// <summary>
/// Sits inside the dense smoke. If the player walks into it, the lesson warns them,
/// tells them to turn back and places them safely outside the smoke.
/// There is no damage or death: this is a training aid, not a game.
/// </summary>
[RequireComponent(typeof(Collider))]
public class HazardZone : MonoBehaviour
{
    [Tooltip("Where the player is placed after walking into the hazard.")]
    public Transform safePoint;

    [Tooltip("Seconds before the zone can trigger again.")]
    public float cooldown = 2.5f;

    float nextAllowedTime;

    void Reset()
    {
        GetComponent<Collider>().isTrigger = true;
    }

    void OnTriggerEnter(Collider other)
    {
        if (Time.time < nextAllowedTime) return;
        if (other.GetComponentInParent<PlayerController>() == null) return;

        nextAllowedTime = Time.time + cooldown;
        Vector3 safePosition = safePoint != null ? safePoint.position : transform.position - transform.forward * 3f;

        if (LessonManager.Instance != null)
            LessonManager.Instance.OnEnteredDenseSmoke(safePosition);
    }
}
