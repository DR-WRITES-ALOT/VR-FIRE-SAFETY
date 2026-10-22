using UnityEngine;

/// <summary>
/// Keeps the world-space training interface in front of the player and always visible.
///
/// A world-space canvas is used because screen-space canvas modes do not render properly
/// in a VR headset. The catch is that a world-space panel can end up on the far side of a
/// wall: stand at the alarm call point, look at the wall, and a panel placed 1.5 m ahead
/// would be buried behind it - which looks exactly like "nothing happened".
///
/// This follower therefore casts a short ray ahead of the camera and pulls the whole
/// interface in front of whatever is in the way, so a panel is never hidden by geometry.
/// It also scales the canvas to the camera's field of view and aspect ratio, so the same
/// 1600 x 900 layout fits a game view, a wide monitor and a headset.
/// </summary>
public class HudFollower : MonoBehaviour
{
    public Transform target;

    [Tooltip("Comfortable distance in front of the eyes when nothing is in the way.")]
    public float distance = 1.55f;

    [Tooltip("Never come closer than this, so the panel never clips into the near plane.")]
    public float minDistance = 0.15f;

    [Tooltip("Keep this much clear air between the panel and a wall in front of it.")]
    public float wallClearance = 0.12f;

    [Tooltip("What can hide the interface. Everything by default.")]
    public LayerMask occlusionMask = ~0;

    public float verticalOffset = -0.02f;
    public float followSpeed = 10f;
    public bool followRotation = true;

    [Header("Fit to view")]
    [Tooltip("Design size of the canvas in its own units (1600 x 900 for this project).")]
    public Vector2 designSize = new Vector2(1600f, 900f);

    [Tooltip("How much of the visible area the interface may use (0.9 = 90%).")]
    [Range(0.5f, 1f)] public float fill = 0.98f;

    public Camera sourceCamera;
    Vector3 targetScale = Vector3.one;

    // The distance actually used, smoothed so the panel does not jump when walking
    // towards and away from walls.
    float currentDistance;
    readonly RaycastHit[] occlusionHits = new RaycastHit[16];

    void Awake()
    {
        currentDistance = distance;
    }

    void Start()
    {
        // No first-frame pop: place the interface where it belongs before anything is drawn.
        Snap();
    }

    void LateUpdate()
    {
        if (!ResolveTarget()) return;

        float wanted = WantedDistance();
        float blend = 1f - Mathf.Exp(-followSpeed * Time.unscaledDeltaTime);
        // Pull in quickly (a wall must never hide the panel), ease back out slowly.
        float speed = wanted < currentDistance ? 1f : blend;
        currentDistance = Mathf.Lerp(currentDistance, wanted, speed);

        Vector3 desiredPosition = target.position
                                  + target.forward * currentDistance
                                  + target.up * verticalOffset;
        Quaternion desiredRotation = followRotation ? target.rotation : Quaternion.identity;

        UpdateScale(currentDistance);

        transform.position = Vector3.Lerp(transform.position, desiredPosition, blend);
        transform.rotation = Quaternion.Slerp(transform.rotation, desiredRotation, blend);
        transform.localScale = Vector3.Lerp(transform.localScale, targetScale, blend);
    }

    bool ResolveTarget()
    {
        if (target != null) return true;
        Camera cam = sourceCamera != null ? sourceCamera : Camera.main;
        if (cam == null) return false;
        target = cam.transform;
        return true;
    }

    /// <summary>
    /// Distance in front of the camera that is free of geometry. If a wall is closer than
    /// the comfortable distance, the interface moves in front of the wall instead of
    /// disappearing behind it.
    /// </summary>
    float WantedDistance()
    {
        float nearest = float.MaxValue;
        Vector3 origin = target.position;

        // A panel that covers most of the view can be clipped by a wall or a door jamb
        // that is not dead ahead, so sample the centre and both sides of the panel width.
        Camera cam = sourceCamera != null ? sourceCamera : Camera.main;
        float horizontalHalfAngle = 0f;
        if (cam != null)
        {
            float halfHeight = Mathf.Tan(cam.fieldOfView * 0.5f * Mathf.Deg2Rad);
            float halfWidth = halfHeight * Mathf.Max(0.2f, cam.aspect);
            // Sample about halfway out to the panel edge: close enough to catch a wall in
            // front of the text, far enough out not to drag the panel to the player's face
            // every time they walk along a side wall.
            horizontalHalfAngle = Mathf.Atan(halfWidth * fill) * Mathf.Rad2Deg * 0.5f;
        }

        for (int side = -1; side <= 1; side++)
        {
            Vector3 direction = target.forward;
            if (side != 0)
                direction = Quaternion.AngleAxis(side * horizontalHalfAngle, target.up) * direction;

            int count = Physics.RaycastNonAlloc(origin, direction, occlusionHits,
                                                distance + wallClearance,
                                                occlusionMask, QueryTriggerInteraction.Ignore);
            Transform playerRoot = target.root;
            for (int i = 0; i < count; i++)
            {
                Collider hit = occlusionHits[i].collider;
                if (hit == null) continue;
                // Ignore the player's own body and anything parented to it.
                if (playerRoot != null && hit.transform.IsChildOf(playerRoot)) continue;
                if (occlusionHits[i].distance < nearest) nearest = occlusionHits[i].distance;
            }
        }

        float wanted = distance;
        if (nearest < float.MaxValue)
            wanted = Mathf.Min(wanted, nearest - wallClearance);

        return Mathf.Max(minDistance, wanted);
    }

    /// <summary>
    /// Keeps the whole interface inside the view, whatever the window aspect or headset
    /// field of view. Without this, a 16:9 layout designed for 1600 x 900 is cropped in
    /// narrow game views and the menu elements overlap.
    /// </summary>
    void UpdateScale(float atDistance)
    {
        Camera cam = sourceCamera != null ? sourceCamera : Camera.main;
        if (cam == null || designSize.x <= 0f || designSize.y <= 0f) return;

        float halfHeight = Mathf.Tan(cam.fieldOfView * 0.5f * Mathf.Deg2Rad) * atDistance;
        float halfWidth = halfHeight * Mathf.Max(0.2f, cam.aspect);
        float scaleForWidth = (halfWidth * 2f * fill) / designSize.x;
        float scaleForHeight = (halfHeight * 2f * fill) / designSize.y;
        float scale = Mathf.Min(scaleForWidth, scaleForHeight);
        targetScale = new Vector3(scale, scale, scale);
    }

    /// <summary>Snap into place immediately, for example after a teleport or a reset.</summary>
    public void Snap()
    {
        if (!ResolveTarget()) return;
        currentDistance = WantedDistance();
        transform.position = target.position + target.forward * currentDistance
                             + target.up * verticalOffset;
        transform.rotation = target.rotation;
        UpdateScale(currentDistance);
        transform.localScale = targetScale;
    }
}
