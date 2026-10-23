using System.Text;
using UnityEngine;
using UnityEngine.XR;

/// <summary>
/// A small on-screen diagnostics panel for the VR path (F2 to show or hide).
///
/// It exists so the XR side of the trainer can be demonstrated and evidenced without a
/// headset: with the Mock HMD package enabled, the panel reports an active XR session,
/// stereo rendering and the eye texture size, which is exactly the information a normal
/// play session cannot show. With a real headset it shows the tracking origin and the
/// controllers that were found.
///
/// Nothing in the lesson depends on this component; it only reads state.
/// </summary>
public class VrReadinessPanel : MonoBehaviour
{
    [Tooltip("Show the panel as soon as the scene starts (F2 still toggles it).")]
    public bool showOnStart;

    [Tooltip("Panel width in pixels at the reference resolution.")]
    public int panelWidth = 560;

    public int fontSize = 15;

    bool visible;
    float smoothedDelta = 0.016f;
    GUIStyle style;
    Texture2D background;

    void Awake()
    {
        visible = showOnStart;
    }

    void Update()
    {
        if (Input.GetKeyDown(KeyCode.F2)) visible = !visible;
        smoothedDelta = Mathf.Lerp(smoothedDelta, Time.unscaledDeltaTime, 0.05f);
    }

    void OnDestroy()
    {
        if (background != null) Destroy(background);
    }

    void OnGUI()
    {
        if (!visible) return;

        EnsureStyles();

        string text = BuildText();
        float scale = Mathf.Max(0.75f, Screen.height / 900f);
        int width = Mathf.RoundToInt(panelWidth * scale);
        GUIStyle measure = style;
        measure.fontSize = Mathf.RoundToInt(fontSize * scale);

        GUIContent content = new GUIContent(text);
        float height = measure.CalcHeight(content, width - 24f) + 20f;

        Rect rect = new Rect(16f, 16f, width, height);
        GUI.DrawTexture(rect, background, ScaleMode.StretchToFill);
        GUI.Label(new Rect(rect.x + 12f, rect.y + 8f, rect.width - 24f, rect.height - 16f),
                  text, measure);
    }

    void EnsureStyles()
    {
        if (background == null)
        {
            background = new Texture2D(1, 1);
            background.SetPixel(0, 0, new Color(0.03f, 0.05f, 0.08f, 0.86f));
            background.Apply();
            background.hideFlags = HideFlags.DontSave;
        }

        if (style == null)
        {
            style = new GUIStyle(GUI.skin.label);
            style.fontSize = fontSize;
            style.wordWrap = true;
            style.richText = false;
            style.normal.textColor = new Color(0.93f, 0.95f, 0.98f, 1f);
        }
    }

    string BuildText()
    {
        PlayerController player = PlayerController.Instance;
        bool xrActive = XRSettings.isDeviceActive;

        StringBuilder builder = new StringBuilder(640);
        builder.AppendLine("VR READINESS  (F2 to hide)");
        builder.AppendLine("Unity " + Application.unityVersion + "   build: " +
                           (Application.isEditor ? "Editor" : "player"));
        builder.AppendLine();
        builder.AppendLine("XR session ....... " + (xrActive ? "ACTIVE" : "inactive (desktop branch)"));
        builder.AppendLine("XR device ........ " +
                           (string.IsNullOrEmpty(XRSettings.loadedDeviceName)
                               ? "none"
                               : XRSettings.loadedDeviceName));
        builder.AppendLine("Stereo mode ...... " + XRSettings.stereoRenderingMode);

        if (xrActive)
        {
            builder.AppendLine("Eye resolution ... scale " +
                               XRSettings.eyeTextureResolutionScale.ToString("0.0") +
                               "   graphics " + SystemInfo.graphicsDeviceType);
        }

        if (player != null)
        {
            builder.AppendLine("Head pose ........ " +
                               (player.IsHeadTracked ? "tracked" : "not reported") +
                               (xrActive && player.IsHeadTracked
                                   ? (player.HasFloorTrackingOrigin ? "  (floor origin)" : "  (device origin)")
                                   : string.Empty));
            builder.AppendLine("Tracking origin .. " +
                               (player.HasFloorTrackingOrigin ? "Floor" : "Device / default"));
        }
        else
        {
            builder.AppendLine("Head pose ........ PlayerController not found");
        }

        builder.AppendLine();
        builder.AppendLine("Controllers:");
        builder.AppendLine("  left  " + DescribeController(XRNode.LeftHand));
        builder.AppendLine("  right " + DescribeController(XRNode.RightHand));
        builder.AppendLine("  head  " + DescribeController(XRNode.Head));
        builder.AppendLine();
        builder.AppendLine("Frame ............ " +
                           (smoothedDelta > 0f ? Mathf.RoundToInt(1f / smoothedDelta) + " fps" : "-") +
                           "   " + Screen.width + " x " + Screen.height);
        builder.AppendLine();
        builder.AppendLine("Lesson: " + (LessonManager.Instance != null ? "running" : "not started") +
                           "   |   UI canvases: " +
                           (LessonUI.Instance != null ? "ready" : "missing"));
        return builder.ToString();
    }

    static string DescribeController(XRNode node)
    {
        InputDevice device = InputDevices.GetDeviceAtXRNode(node);
        if (!device.isValid) return "not reported";

        bool tracked = false;
        device.TryGetFeatureValue(CommonUsages.isTracked, out tracked);
        string label = string.IsNullOrEmpty(device.name) ? device.manufacturer : device.name;
        if (string.IsNullOrEmpty(label)) label = node.ToString();
        return label + (tracked ? "  [tracked]" : "  [idle]");
    }
}
