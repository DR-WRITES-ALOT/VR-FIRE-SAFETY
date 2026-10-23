using System.Collections.Generic;
using UnityEngine;
using UnityEngine.XR;

/// <summary>
/// One controller for both play modes.
///
/// Desktop: WASD to move, mouse to look, E to interact.
/// VR: the headset drives the camera pose, the left stick moves, the right stick
/// turns in 30 degree steps and the trigger interacts / clicks interface buttons.
///
/// The same interaction code is used in both modes, so the lesson works identically.
/// </summary>
[RequireComponent(typeof(CharacterController))]
public class PlayerController : MonoBehaviour
{
    public static PlayerController Instance;

    [Header("References")]
    public Camera playerCamera;

    [Header("Desktop movement")]
    public float walkSpeed = 2.4f;
    public float runSpeed = 4.2f;
    public float mouseSensitivity = 2.2f;
    public float eyeHeight = 1.62f;
    public float gravity = -18f;

    [Header("Interaction")]
    public float interactDistance = 3.2f;
    public float interactRadius = 0.22f;
    public LayerMask interactionMask = ~0;

    [Header("VR")]
    public float vrMoveSpeed = 2.0f;
    public float snapTurnDegrees = 30f;
    [Tooltip("Drive the camera from the headset pose reported by the XR runtime.")]
    public bool driveCameraFromXrDevice = true;

    [Tooltip("Ask the runtime for a floor-relative origin, so the headset reports the player's " +
             "real height. Without this the head pose is relative to wherever the headset was " +
             "when tracking started, and the eyes end up at floor level.")]
    public bool requestFloorTrackingOrigin = true;

    [Tooltip("Eye height used only when the runtime can offer a device-relative origin only.")]
    public float vrDeviceOriginEyeHeight = 1.62f;

    CharacterController controller;
    float pitch;
    float verticalVelocity;
    bool uiFocus;
    bool xrActive;
    bool triggerWasDown;

    IInteractable focused;
    float nextXrCheck;
    float xrInputWarnTime;
    bool warnedNoXrControllers;

    // VR state that has to be tracked separately from "an XR session exists":
    // a session can be active before the head pose is available, and some runtimes
    // (and the Mock HMD) render in stereo but report no head device at all.
    bool xrHeadTracked;
    TrackingOriginModeFlags trackingOrigin = TrackingOriginModeFlags.Unknown;
    readonly List<XRInputSubsystem> xrInputSubsystems = new List<XRInputSubsystem>();

    public bool IsXrActive => xrActive;
    public bool HasUiFocus => uiFocus;

    /// <summary>True when the headset itself is supplying the camera pose.</summary>
    public bool IsHeadTracked => xrActive && xrHeadTracked;

    /// <summary>Floor-relative origin confirmed by the runtime (best height accuracy).</summary>
    public bool HasFloorTrackingOrigin => trackingOrigin == TrackingOriginModeFlags.Floor;

    /// <summary>
    /// True when the crosshair should act as a pointer for interface buttons.
    /// Desktop: only while the cursor is locked (i.e. no panel is open, so real mouse clicks work).
    /// VR: always, because the headset has no mouse and the trigger is the pointer.
    /// </summary>
    public bool PointerClickActive => xrActive || (!uiFocus && Cursor.lockState == CursorLockMode.Locked);

    /// <summary>True on the frame the player asks to "click" the thing under the crosshair.</summary>
    public bool PointerClickPressed { get; private set; }

    void Awake()
    {
        Instance = this;
        controller = GetComponent<CharacterController>();
        if (playerCamera == null) playerCamera = GetComponentInChildren<Camera>();
        RefreshXrState();
        if (!xrActive && playerCamera != null)
            playerCamera.transform.localPosition = new Vector3(0f, eyeHeight, 0f);
    }

    void Start()
    {
#if !ENABLE_LEGACY_INPUT_MANAGER
        Debug.LogError("[Fire Safety] Legacy input is disabled, so WASD, the mouse and E will not work. " +
                       "Set Edit > Project Settings > Player > Other Settings > Active Input Handling to " +
                       "'Both' (or 'Input Manager (Old)') and let Unity restart.");
#endif
        LockCursor(true);
    }

    void RefreshXrState()
    {
        bool wasActive = xrActive;
        xrActive = XRSettings.isDeviceActive;

        // The tracking-origin request can only be made once the input subsystem is running,
        // which may be a few frames after the session becomes active, so keep trying.
        if (xrActive && trackingOrigin == TrackingOriginModeFlags.Unknown)
            RequestTrackingOrigin();
        if (!xrActive)
        {
            trackingOrigin = TrackingOriginModeFlags.Unknown;
            xrHeadTracked = false;
        }

        if (xrActive == wasActive || playerCamera == null) return;

        // In VR the headset supplies the eye pose, so the camera must sit on the rig origin.
        if (xrActive)
            playerCamera.transform.localPosition = Vector3.zero;
        else
            playerCamera.transform.localPosition = new Vector3(0f, eyeHeight, 0f);
    }

    void Update()
    {
        if (Time.unscaledTime > nextXrCheck)
        {
            nextXrCheck = Time.unscaledTime + 1f;
            RefreshXrState();
        }

        PointerClickPressed = false;

        // Safety net: if an overlay has closed without clearing the focus flag, movement
        // and looking would stay dead. Recover on the next frame instead.
        if (uiFocus && !OverlayIsOpen())
        {
            uiFocus = false;
            if (!xrActive) LockCursor(true);
        }

        if (xrActive)
        {
            UpdateXrHeadPose();
            ReadXrTrigger();
        }

        if (uiFocus)
        {
            SetFocus(null);
            return;
        }

        // A headset that renders but reports no head pose (for example the Mock HMD used for
        // Editor testing) would otherwise leave the camera stuck at the rig origin with no way
        // to look around. Keep the stereo rendering, but fall back to mouse/WASD control.
        if (xrActive && xrHeadTracked)
            UpdateXrInput();
        else
            UpdateDesktopInput();

        UpdateFocus();
        CheckInteractInput();
    }

    // ------------------------------------------------------------------ //
    // Desktop
    // ------------------------------------------------------------------ //

    void UpdateDesktopInput()
    {
        if (Cursor.lockState != CursorLockMode.Locked && !uiFocus)
            LockCursor(true);

        float mouseX = Input.GetAxis("Mouse X") * mouseSensitivity;
        float mouseY = Input.GetAxis("Mouse Y") * mouseSensitivity;
        transform.Rotate(0f, mouseX, 0f, Space.Self);

        pitch = Mathf.Clamp(pitch - mouseY, -85f, 85f);
        if (playerCamera != null)
        {
            playerCamera.transform.localRotation = Quaternion.Euler(pitch, 0f, 0f);
            Vector3 local = playerCamera.transform.localPosition;
            playerCamera.transform.localPosition = new Vector3(0f, eyeHeight, local.z);
        }

        Vector2 axis = new Vector2(Input.GetAxisRaw("Horizontal"), Input.GetAxisRaw("Vertical"));
        float speed = Input.GetKey(KeyCode.LeftShift) ? runSpeed : walkSpeed;
        Move(axis, speed);
    }

    // ------------------------------------------------------------------ //
    // VR
    // ------------------------------------------------------------------ //

    void UpdateXrHeadPose()
    {
        xrHeadTracked = false;
        if (!driveCameraFromXrDevice || playerCamera == null) return;
        InputDevice head = InputDevices.GetDeviceAtXRNode(XRNode.Head);
        if (!head.isValid) return;

        // With a floor origin the head pose already contains the player's real height.
        // With a device origin it does not, so add an eye height or the view starts on the floor.
        float heightOffset = trackingOrigin == TrackingOriginModeFlags.Floor
            ? 0f
            : vrDeviceOriginEyeHeight;

        Vector3 headPosition;
        Quaternion headRotation;
        if (head.TryGetFeatureValue(CommonUsages.centerEyePosition, out headPosition))
        {
            playerCamera.transform.localPosition = headPosition + new Vector3(0f, heightOffset, 0f);
            xrHeadTracked = true;
        }
        if (head.TryGetFeatureValue(CommonUsages.centerEyeRotation, out headRotation))
        {
            playerCamera.transform.localRotation = headRotation;
            xrHeadTracked = true;
        }
    }

    /// <summary>
    /// Ask XR for a floor-relative tracking origin. Without it, "head pose" is measured from
    /// wherever the headset was when tracking started, which puts the eyes at floor level in
    /// this rig (the player root sits on the floor and the camera is a child of it).
    /// </summary>
    void RequestTrackingOrigin()
    {
        xrInputSubsystems.Clear();
        SubsystemManager.GetSubsystems(xrInputSubsystems);

        for (int i = 0; i < xrInputSubsystems.Count; i++)
        {
            XRInputSubsystem subsystem = xrInputSubsystems[i];
            if (subsystem == null || !subsystem.running) continue;

            TrackingOriginModeFlags supported = subsystem.GetSupportedTrackingOriginModes();
            if (requestFloorTrackingOrigin &&
                (supported & TrackingOriginModeFlags.Floor) != 0 &&
                subsystem.TrySetTrackingOriginMode(TrackingOriginModeFlags.Floor))
            {
                trackingOrigin = TrackingOriginModeFlags.Floor;
                return;
            }

            // Device-relative only: the eye-height offset in UpdateXrHeadPose compensates.
            trackingOrigin = TrackingOriginModeFlags.Device;
        }
    }

    /// <summary>
    /// The trigger is read every frame, even while a teaching panel is open, so the player can
    /// press interface buttons from inside the headset.
    /// </summary>
    void ReadXrTrigger()
    {
        bool triggerDown = false;
        InputDevice right = InputDevices.GetDeviceAtXRNode(XRNode.RightHand);
        if (right.isValid)
            right.TryGetFeatureValue(CommonUsages.triggerButton, out triggerDown);

        if (triggerDown && !triggerWasDown) PointerClickPressed = true;
        triggerWasDown = triggerDown;
    }

    void UpdateXrInput()
    {
        Vector2 axis = Vector2.zero;
        Vector2 turnAxis = Vector2.zero;

        InputDevice left = InputDevices.GetDeviceAtXRNode(XRNode.LeftHand);
        if (left.isValid)
        {
            Vector2 value;
            if (left.TryGetFeatureValue(CommonUsages.primary2DAxis, out value)) axis = value;
        }

        InputDevice right = InputDevices.GetDeviceAtXRNode(XRNode.RightHand);
        if (right.isValid)
        {
            Vector2 value;
            if (right.TryGetFeatureValue(CommonUsages.primary2DAxis, out value)) turnAxis = value;
        }

        // A headset can run without controllers being reported (for example when the
        // OpenXR interaction profile for the device is not enabled). Say so once,
        // instead of leaving the player wondering why the sticks do nothing.
        if (!warnedNoXrControllers && !left.isValid && !right.isValid)
        {
            if (xrInputWarnTime == 0f) xrInputWarnTime = Time.unscaledTime;
            else if (Time.unscaledTime - xrInputWarnTime > 3f)
            {
                warnedNoXrControllers = true;
                Debug.LogWarning("[Fire Safety] XR is active but no controller devices were reported. " +
                                 "Check that the OpenXR runtime is running and that the controller " +
                                 "interaction profile for your headset is enabled.");
            }
        }

        if (Mathf.Abs(turnAxis.x) > 0.7f)
            transform.Rotate(0f, Mathf.Sign(turnAxis.x) * snapTurnDegrees, 0f, Space.Self);

        Move(axis, vrMoveSpeed);
    }

    // ------------------------------------------------------------------ //
    // Shared movement
    // ------------------------------------------------------------------ //

    void Move(Vector2 axis, float speed)
    {
        if (controller == null) return;

        Vector3 direction = transform.right * axis.x + transform.forward * axis.y;
        if (direction.sqrMagnitude > 1f) direction.Normalize();

        if (controller.isGrounded && verticalVelocity < 0f)
            verticalVelocity = -2f;
        else
            verticalVelocity += gravity * Time.deltaTime;

        Vector3 velocity = direction * speed;
        velocity.y = verticalVelocity;
        controller.Move(velocity * Time.deltaTime);
    }

    // ------------------------------------------------------------------ //
    // Looking at objects
    // ------------------------------------------------------------------ //

    void UpdateFocus()
    {
        IInteractable found = null;
        if (playerCamera != null)
        {
            Ray ray = new Ray(playerCamera.transform.position, playerCamera.transform.forward);
            RaycastHit[] hits = Physics.SphereCastAll(ray, interactRadius, interactDistance,
                                                      interactionMask, QueryTriggerInteraction.Collide);
            float best = float.MaxValue;
            for (int i = 0; i < hits.Length; i++)
            {
                if (hits[i].collider.transform.IsChildOf(transform)) continue;
                IInteractable candidate = hits[i].collider.GetComponentInParent<IInteractable>();
                if (candidate == null || !candidate.IsAvailable) continue;
                if (hits[i].distance < best)
                {
                    best = hits[i].distance;
                    found = candidate;
                }
            }
        }

        SetFocus(found);
    }

    void SetFocus(IInteractable target)
    {
        if (focusInteractable() == target) return;

        InteractableBase oldBase = focused as InteractableBase;
        if (oldBase != null) oldBase.SetHighlighted(false);

        focused = target;

        InteractableBase newBase = focused as InteractableBase;
        if (newBase != null) newBase.SetHighlighted(true);

        if (LessonUI.Instance != null)
        {
            if (focused == null) LessonUI.Instance.SetPrompt(string.Empty);
            else
            {
                string key = xrActive ? "Trigger" : "E";
                LessonUI.Instance.SetPrompt("[" + key + "]  " + focused.InteractionPrompt);
            }
        }
    }

    IInteractable focusInteractable() => focused;

    void CheckInteractInput()
    {
        bool pressed = Input.GetKeyDown(KeyCode.E);
        if (xrActive && PointerClickPressed) pressed = true;
        if (pressed) TryInteract();
    }

    public void TryInteract()
    {
        if (focused == null || !focused.IsAvailable) return;
        IInteractable target = focused;
        SetFocus(null);
        target.Interact(this);
    }

    // ------------------------------------------------------------------ //
    // Helpers
    // ------------------------------------------------------------------ //

    static bool OverlayIsOpen()
    {
        LessonUI ui = LessonUI.Instance;
        return ui != null && ui.AnyOverlayOpen;
    }

    public void SetUiFocus(bool focus)
    {
        uiFocus = focus;
        SetFocus(null);
        if (xrActive) return;
        LockCursor(!focus);
    }

    /// <summary>Give control back to the player (used when a panel closes or on resume).</summary>
    public void ReleaseUiFocus()
    {
        uiFocus = false;
        if (!xrActive) LockCursor(true);
    }

    public void LockCursor(bool locked)
    {
        Cursor.lockState = locked ? CursorLockMode.Locked : CursorLockMode.None;
        Cursor.visible = !locked;
    }

    /// <summary>Move the player rig to a start position and facing direction.</summary>
    public void Teleport(Vector3 position, float yaw)
    {
        if (controller != null) controller.enabled = false;
        transform.position = position;
        transform.rotation = Quaternion.Euler(0f, yaw, 0f);
        if (controller != null) controller.enabled = true;
    }
}
