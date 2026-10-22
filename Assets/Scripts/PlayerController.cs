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

    CharacterController controller;
    float pitch;
    float verticalVelocity;
    bool uiFocus;
    bool xrActive;
    bool triggerWasDown;

    IInteractable focused;
    float nextXrCheck;

    public bool IsXrActive => xrActive;
    public bool HasUiFocus => uiFocus;

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
        LockCursor(true);
    }

    void RefreshXrState()
    {
        bool wasActive = xrActive;
        xrActive = XRSettings.isDeviceActive;
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

        if (xrActive)
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
        if (!driveCameraFromXrDevice || playerCamera == null) return;
        InputDevice head = InputDevices.GetDeviceAtXRNode(XRNode.Head);
        if (!head.isValid) return;

        Vector3 headPosition;
        Quaternion headRotation;
        if (head.TryGetFeatureValue(CommonUsages.centerEyePosition, out headPosition))
            playerCamera.transform.localPosition = headPosition;
        if (head.TryGetFeatureValue(CommonUsages.centerEyeRotation, out headRotation))
            playerCamera.transform.localRotation = headRotation;
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

    public void SetUiFocus(bool focus)
    {
        uiFocus = focus;
        SetFocus(null);
        if (xrActive) return;
        LockCursor(!focus);
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
