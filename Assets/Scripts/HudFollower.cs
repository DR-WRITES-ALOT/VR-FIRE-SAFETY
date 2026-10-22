using UnityEngine;

/// <summary>
/// Keeps the world-space training interface in front of the player.
///
/// A world-space canvas is used because screen-space canvases are not visible in VR.
/// With this follower the same canvas sits comfortably in front of the eyes in a headset
/// and in front of the desktop camera, and the crosshair always lines up with the buttons.
/// </summary>
public class HudFollower : MonoBehaviour
{
    public Transform target;
    public float distance = 1.55f;
    public float verticalOffset = -0.02f;
    public float followSpeed = 10f;
    public bool followRotation = true;

    void LateUpdate()
    {
        if (target == null)
        {
            if (Camera.main != null) target = Camera.main.transform;
            else return;
        }

        Vector3 desiredPosition = target.position
                                  + target.forward * distance
                                  + target.up * verticalOffset;
        Quaternion desiredRotation = followRotation ? target.rotation : Quaternion.identity;

        float t = 1f - Mathf.Exp(-followSpeed * Time.unscaledDeltaTime);
        transform.position = Vector3.Lerp(transform.position, desiredPosition, t);
        transform.rotation = Quaternion.Slerp(transform.rotation, desiredRotation, t);
    }

    /// <summary>Snap into place immediately, for example after a teleport.</summary>
    public void Snap()
    {
        if (target == null && Camera.main != null) target = Camera.main.transform;
        if (target == null) return;
        transform.position = target.position + target.forward * distance + target.up * verticalOffset;
        transform.rotation = target.rotation;
    }
}
