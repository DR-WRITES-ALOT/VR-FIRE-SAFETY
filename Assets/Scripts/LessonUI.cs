using System;
using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;

/// <summary>
/// Builds and drives the on-screen interface.
///
/// The interface is a world-space canvas locked in front of the camera. That single
/// choice means the same buttons and text work in the Unity Editor, in a normal
/// desktop build, and in a VR headset (a screen-space canvas would not render in VR).
/// Buttons can be clicked with the mouse when the cursor is free, or by looking at
/// them with the crosshair and pressing the interact button / VR trigger.
/// </summary>
public class LessonUI : MonoBehaviour
{
    public static LessonUI Instance;

    [Header("Fonts (drag from Assets/Fonts)")]
    public Font fontRegular;
    public Font fontBold;

    [Header("Colours")]
    public Color panelColour = new Color(0.055f, 0.07f, 0.10f, 0.94f);
    public Color accentColour = new Color(1f, 0.72f, 0.25f, 1f);
    public Color bodyColour = new Color(0.93f, 0.94f, 0.96f, 1f);
    public Color dangerColour = new Color(0.72f, 0.13f, 0.10f, 0.96f);

    // HUD
    RectTransform hudRoot;
    Text sectionText;
    Text objectiveText;
    Text promptText;
    Image promptBackground;
    Image warningBanner;
    Text warningText;
    RectTransform crosshair;
    Coroutine warningRoutine;

    // Menu / pause
    RectTransform menuRoot;
    RectTransform menuInfoRoot;
    Text menuInfoTitle;
    Text menuInfoBody;
    RectTransform pauseRoot;

    // Modal panel
    RectTransform modalRoot;
    Text modalTitle;
    Text modalBody;
    Text modalFooter;
    RectTransform buttonRow;

    Selectable hovered;
    readonly Dictionary<Selectable, Color> originalColours = new Dictionary<Selectable, Color>();
    GraphicRaycaster raycaster;

    public bool PanelOpen { get; private set; }

    void Awake()
    {
        Instance = this;
        EnsureFonts();
        EnsureEventSystem();
        raycaster = GetComponent<GraphicRaycaster>();
        BuildHud();
        BuildModal();
        BuildPause();
        BuildMenu();
        HidePanel();
        HideMenu();
        HidePause();
    }

    // ------------------------------------------------------------------ //
    // Construction
    // ------------------------------------------------------------------ //

    void EnsureFonts()
    {
        if (fontRegular == null)
        {
            try { fontRegular = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf"); }
            catch { fontRegular = null; }
        }
        if (fontRegular == null)
            fontRegular = Font.CreateDynamicFontFromOSFont("Arial", 16);
        if (fontBold == null)
            fontBold = fontRegular;
    }

    void EnsureEventSystem()
    {
        if (EventSystem.current != null) return;
        GameObject eventSystem = new GameObject("EventSystem", typeof(EventSystem), typeof(StandaloneInputModule));
        eventSystem.transform.SetParent(transform.parent, false);
    }

    RectTransform CreateNode(string name, Transform parent)
    {
        GameObject go = new GameObject(name, typeof(RectTransform));
        go.layer = LayerMask.NameToLayer("UI");
        RectTransform rect = go.GetComponent<RectTransform>();
        rect.SetParent(parent, false);
        return rect;
    }

    static void Place(RectTransform rect, Vector2 anchorMin, Vector2 anchorMax, Vector2 pivot,
                      Vector2 position, Vector2 size)
    {
        rect.anchorMin = anchorMin;
        rect.anchorMax = anchorMax;
        rect.pivot = pivot;
        rect.anchoredPosition = position;
        rect.sizeDelta = size;
    }

    /// <summary>
    /// Picks a font size that keeps a block of text inside the space available.
    /// Unity's legacy Text silently truncates when it overflows, which would hide
    /// part of a lesson, so long bodies are shrunk instead of clipped.
    /// </summary>
    static int FitFontSize(string text, float height, float charactersPerLine, int maximum)
    {
        if (string.IsNullOrEmpty(text)) return maximum;
        int lines = 0;
        string[] paragraphs = text.Split('\n');
        for (int i = 0; i < paragraphs.Length; i++)
            lines += Mathf.Max(1, Mathf.CeilToInt(paragraphs[i].Length / charactersPerLine));
        int fitted = Mathf.FloorToInt(height / (lines * 1.4f));
        return Mathf.Clamp(fitted, 16, maximum);
    }

    Image CreateImage(string name, Transform parent, Color colour, bool raycast = false)
    {
        RectTransform rect = CreateNode(name, parent);
        Image image = rect.gameObject.AddComponent<Image>();
        image.color = colour;
        image.raycastTarget = raycast;
        return image;
    }

    Text CreateText(string name, Transform parent, string content, int size, TextAnchor anchor,
                    bool bold, Color colour)
    {
        RectTransform rect = CreateNode(name, parent);
        Text text = rect.gameObject.AddComponent<Text>();
        text.font = bold ? fontBold : fontRegular;
        text.fontSize = size;
        text.alignment = anchor;
        text.color = colour;
        text.supportRichText = true;
        text.horizontalOverflow = HorizontalWrapMode.Wrap;
        text.verticalOverflow = VerticalWrapMode.Truncate;
        text.lineSpacing = 1.1f;
        text.raycastTarget = false;
        text.text = content;
        return text;
    }

    Button CreateButton(string label, Transform parent, Vector2 position, Vector2 size, Action onClick)
    {
        Image background = CreateImage("Button_" + label, parent, new Color(0.16f, 0.24f, 0.34f, 1f), true);
        Place(background.rectTransform, new Vector2(0.5f, 0f), new Vector2(0.5f, 0f),
              new Vector2(0.5f, 0f), position, size);

        Button button = background.gameObject.AddComponent<Button>();
        ColorBlock colours = button.colors;
        colours.normalColor = Color.white;
        colours.highlightedColor = new Color(1.25f, 1.25f, 1.25f, 1f);
        colours.pressedColor = new Color(0.8f, 0.8f, 0.8f, 1f);
        colours.selectedColor = Color.white;
        colours.colorMultiplier = 1f;
        button.colors = colours;
        button.targetGraphic = background;
        if (onClick != null) button.onClick.AddListener(() => onClick());

        Text text = CreateText("Label", background.transform, label, 30, TextAnchor.MiddleCenter, true, Color.white);
        Place(text.rectTransform, Vector2.zero, Vector2.one, new Vector2(0.5f, 0.5f), Vector2.zero,
              new Vector2(-28f, -8f));
        Padding(text.rectTransform, 14, 8, 14, 8);

        originalColours[button] = background.color;
        return button;
    }

    static void Padding(RectTransform rect, float left, float bottom, float right, float top)
    {
        rect.offsetMin = new Vector2(left, bottom);
        rect.offsetMax = new Vector2(-right, -top);
    }

    void BuildHud()
    {
        hudRoot = CreateNode("HUD", transform);
        Place(hudRoot, Vector2.zero, Vector2.one, new Vector2(0.5f, 0.5f), Vector2.zero, Vector2.zero);
        Padding(hudRoot, 0, 0, 0, 0);

        // Top information bar
        Image topBar = CreateImage("TopBar", hudRoot, new Color(0.03f, 0.04f, 0.06f, 0.82f));
        Place(topBar.rectTransform, new Vector2(0f, 1f), new Vector2(1f, 1f), new Vector2(0.5f, 1f),
              Vector2.zero, new Vector2(0f, 172f));

        Image accent = CreateImage("Accent", topBar.transform, accentColour);
        Place(accent.rectTransform, new Vector2(0f, 0f), new Vector2(1f, 0f), new Vector2(0.5f, 0f),
              Vector2.zero, new Vector2(0f, 6f));

        sectionText = CreateText("Section", topBar.transform, "", 28, TextAnchor.UpperLeft, true, accentColour);
        Place(sectionText.rectTransform, new Vector2(0f, 1f), new Vector2(1f, 1f), new Vector2(0f, 1f),
              new Vector2(56f, -22f), new Vector2(-112f, 40f));

        objectiveText = CreateText("Objective", topBar.transform, "", 32, TextAnchor.UpperLeft, false, bodyColour);
        Place(objectiveText.rectTransform, new Vector2(0f, 1f), new Vector2(1f, 1f), new Vector2(0f, 1f),
              new Vector2(56f, -68f), new Vector2(-112f, 92f));

        // Interaction prompt above the bottom edge
        promptBackground = CreateImage("PromptBackground", hudRoot, new Color(0.05f, 0.06f, 0.09f, 0.88f));
        Place(promptBackground.rectTransform, new Vector2(0.5f, 0f), new Vector2(0.5f, 0f),
              new Vector2(0.5f, 0f), new Vector2(0f, 136f), new Vector2(980f, 74f));

        promptText = CreateText("Prompt", promptBackground.transform, "", 30, TextAnchor.MiddleCenter, true, Color.white);
        Place(promptText.rectTransform, Vector2.zero, Vector2.one, new Vector2(0.5f, 0.5f), Vector2.zero, Vector2.zero);
        Padding(promptText.rectTransform, 20, 6, 20, 6);
        promptBackground.gameObject.SetActive(false);

        // Controls hint
        Text hint = CreateText("ControlsHint", hudRoot,
            "WASD / left stick  move      Mouse / headset  look      E / trigger  interact      Esc pause",
            22, TextAnchor.LowerCenter, false, new Color(0.82f, 0.85f, 0.9f, 0.85f));
        Place(hint.rectTransform, new Vector2(0f, 0f), new Vector2(1f, 0f), new Vector2(0.5f, 0f),
              new Vector2(0f, 34f), new Vector2(-80f, 40f));

        // Crosshair
        crosshair = CreateNode("Crosshair", hudRoot);
        Place(crosshair, new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f),
              Vector2.zero, new Vector2(18f, 18f));
        Image dot = CreateImage("Dot", crosshair, new Color(1f, 1f, 1f, 0.75f));
        Place(dot.rectTransform, Vector2.zero, Vector2.one, new Vector2(0.5f, 0.5f), Vector2.zero,
              new Vector2(-6f, -6f));

        // Warning banner (hidden by default)
        warningBanner = CreateImage("WarningBanner", hudRoot, dangerColour);
        Place(warningBanner.rectTransform, new Vector2(0.5f, 1f), new Vector2(0.5f, 1f),
              new Vector2(0.5f, 1f), new Vector2(0f, -190f), new Vector2(1240f, 96f));
        warningText = CreateText("WarningText", warningBanner.transform, "", 30, TextAnchor.MiddleCenter, true, Color.white);
        Place(warningText.rectTransform, Vector2.zero, Vector2.one, new Vector2(0.5f, 0.5f), Vector2.zero, Vector2.zero);
        Padding(warningText.rectTransform, 24, 6, 24, 6);
        warningBanner.gameObject.SetActive(false);
    }

    void BuildModal()
    {
        modalRoot = CreateNode("Modal", transform);
        Place(modalRoot, Vector2.zero, Vector2.one, new Vector2(0.5f, 0.5f), Vector2.zero, Vector2.zero);
        Padding(modalRoot, 0, 0, 0, 0);

        Image dim = CreateImage("Dim", modalRoot, new Color(0f, 0f, 0f, 0.55f), true);
        Place(dim.rectTransform, Vector2.zero, Vector2.one, new Vector2(0.5f, 0.5f), Vector2.zero, Vector2.zero);

        Image panel = CreateImage("Panel", modalRoot, panelColour, true);
        Place(panel.rectTransform, new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f),
              Vector2.zero, new Vector2(1520f, 880f));

        Image accent = CreateImage("Accent", panel.transform, accentColour);
        Place(accent.rectTransform, new Vector2(0f, 1f), new Vector2(1f, 1f), new Vector2(0.5f, 1f),
              Vector2.zero, new Vector2(0f, 8f));

        modalTitle = CreateText("Title", panel.transform, "", 46, TextAnchor.UpperLeft, true, accentColour);
        Place(modalTitle.rectTransform, new Vector2(0f, 1f), new Vector2(1f, 1f), new Vector2(0f, 1f),
              new Vector2(64f, -34f), new Vector2(-128f, 70f));

        modalBody = CreateText("Body", panel.transform, "", 30, TextAnchor.UpperLeft, false, bodyColour);
        Place(modalBody.rectTransform, new Vector2(0f, 1f), new Vector2(1f, 1f), new Vector2(0f, 1f),
              new Vector2(64f, -118f), new Vector2(-128f, 590f));

        modalFooter = CreateText("Footer", panel.transform, "", 22, TextAnchor.LowerLeft, false,
                                 new Color(0.68f, 0.72f, 0.78f, 1f));
        Place(modalFooter.rectTransform, new Vector2(0f, 0f), new Vector2(1f, 0f), new Vector2(0f, 0f),
              new Vector2(64f, 148f), new Vector2(-128f, 60f));

        buttonRow = CreateNode("Buttons", panel.transform);
        Place(buttonRow, new Vector2(0f, 0f), new Vector2(1f, 0f), new Vector2(0.5f, 0f),
              new Vector2(0f, 42f), new Vector2(-128f, 96f));
    }

    // ------------------------------------------------------------------ //
    // HUD API
    // ------------------------------------------------------------------ //

    public void SetSection(string text)
    {
        if (sectionText != null) sectionText.text = text;
    }

    public void SetObjective(string text)
    {
        if (objectiveText != null) objectiveText.text = text;
    }

    public void SetPrompt(string text)
    {
        if (promptText == null) return;
        bool show = !string.IsNullOrEmpty(text);
        promptBackground.gameObject.SetActive(show);
        if (show) promptText.text = text;
    }

    public void SetHudVisible(bool visible)
    {
        if (hudRoot != null) hudRoot.gameObject.SetActive(visible);
    }

    public void ShowWarning(string message, float seconds = 4f)
    {
        if (warningRoutine != null) StopCoroutine(warningRoutine);
        warningRoutine = StartCoroutine(WarningRoutine(message, seconds));
    }

    IEnumerator WarningRoutine(string message, float seconds)
    {
        warningText.text = message;
        warningBanner.gameObject.SetActive(true);
        yield return new WaitForSeconds(seconds);
        warningBanner.gameObject.SetActive(false);
        warningRoutine = null;
    }

    // ------------------------------------------------------------------ //
    // Modal API
    // ------------------------------------------------------------------ //

    /// <summary>
    /// Shows a teaching panel. Pass up to four button labels with matching actions.
    /// While a panel is open the player stands still and the mouse cursor is released.
    /// </summary>
    public void ShowPanel(string title, string body, string footer, string[] buttonLabels, Action[] buttonActions)
    {
        modalTitle.text = title;
        modalBody.text = body;
        modalFooter.text = footer ?? string.Empty;
        modalBody.fontSize = FitFontSize(body, 570f, 88f, 30);

        foreach (Transform child in buttonRow) Destroy(child.gameObject);

        int count = buttonLabels != null ? buttonLabels.Length : 0;
        if (count > 0)
        {
            float spacing = 18f;
            float totalWidth = 1392f;
            float buttonWidth = (totalWidth - spacing * (count - 1)) / count;
            for (int i = 0; i < count; i++)
            {
                // Centre the whole row: buttons are anchored to the middle of the button row.
                float x = (i - (count - 1) * 0.5f) * (buttonWidth + spacing);
                Action action = (buttonActions != null && i < buttonActions.Length) ? buttonActions[i] : null;
                // Close this panel first, then run the lesson step. The step may open the next panel.
                Action wrapped = () =>
                {
                    HidePanel();
                    if (action != null) action();
                };
                CreateButton(buttonLabels[i], buttonRow, new Vector2(x, 0f), new Vector2(buttonWidth, 92f), wrapped);
            }
        }

        modalRoot.gameObject.SetActive(true);
        modalRoot.SetAsLastSibling();
        PanelOpen = true;
        SetPrompt(string.Empty);
        if (PlayerController.Instance != null) PlayerController.Instance.SetUiFocus(true);
    }

    public void HidePanel()
    {
        modalRoot.gameObject.SetActive(false);
        PanelOpen = false;
        ClearHover();
        if (PlayerController.Instance != null) PlayerController.Instance.SetUiFocus(false);
    }

    // ------------------------------------------------------------------ //
    // Crosshair / gaze clicking (desktop look mode and VR)
    // ------------------------------------------------------------------ //

    void Update()
    {
        PlayerController player = PlayerController.Instance;
        bool pointerActive = player != null && player.PointerClickActive;

        if (!pointerActive || raycaster == null || EventSystem.current == null)
        {
            ClearHover();
            return;
        }

        Vector2 centre = new Vector2(Screen.width * 0.5f, Screen.height * 0.5f);
        PointerEventData data = new PointerEventData(EventSystem.current) { position = centre };
        List<RaycastResult> results = new List<RaycastResult>();
        raycaster.Raycast(data, results);

        Selectable found = null;
        for (int i = 0; i < results.Count; i++)
        {
            Selectable selectable = results[i].gameObject.GetComponentInParent<Selectable>();
            if (selectable != null && selectable.IsInteractable() && selectable.targetGraphic is Image)
            {
                found = selectable;
                break;
            }
        }

        SetHover(found);

        if (found != null && player.PointerClickPressed)
        {
            data.pointerPress = found.gameObject;
            data.pointerCurrentRaycast = results[0];
            data.eligibleForClick = true;
            data.clickCount = 1;
            data.button = PointerEventData.InputButton.Left;
            ExecuteEvents.Execute(found.gameObject, data, ExecuteEvents.pointerClickHandler);
            ClearHover();
        }
    }

    void SetHover(Selectable selectable)
    {
        if (hovered == selectable) return;
        RestoreColour(hovered);
        hovered = selectable;
        if (hovered != null && hovered.targetGraphic is Image image)
        {
            if (!originalColours.ContainsKey(hovered)) originalColours[hovered] = image.color;
            image.color = new Color(0.30f, 0.46f, 0.62f, 1f);
        }
    }

    void ClearHover()
    {
        RestoreColour(hovered);
        hovered = null;
    }

    void RestoreColour(Selectable selectable)
    {
        if (selectable == null) return;
        if (selectable.targetGraphic is Image image && originalColours.TryGetValue(selectable, out Color original))
            image.color = original;
    }

    // ------------------------------------------------------------------ //
    // Main menu
    // ------------------------------------------------------------------ //

    void BuildMenu()
    {
        menuRoot = CreateNode("MainMenu", transform);
        Place(menuRoot, Vector2.zero, Vector2.one, new Vector2(0.5f, 0.5f), Vector2.zero, Vector2.zero);
        Padding(menuRoot, 0, 0, 0, 0);

        Image dim = CreateImage("Dim", menuRoot, new Color(0.02f, 0.03f, 0.05f, 0.97f), true);
        Place(dim.rectTransform, Vector2.zero, Vector2.one, new Vector2(0.5f, 0.5f), Vector2.zero, Vector2.zero);

        Image stripe = CreateImage("Stripe", menuRoot, new Color(0.72f, 0.13f, 0.10f, 1f));
        Place(stripe.rectTransform, new Vector2(0f, 1f), new Vector2(1f, 1f), new Vector2(0.5f, 1f),
              new Vector2(0f, -168f), new Vector2(0f, 10f));

        Text title = CreateText("Title", menuRoot, "VR FIRE SAFETY", 92, TextAnchor.MiddleCenter, true, Color.white);
        Place(title.rectTransform, new Vector2(0f, 1f), new Vector2(1f, 1f), new Vector2(0.5f, 1f),
              new Vector2(0f, -60f), new Vector2(-160f, 110f));

        Text subtitle = CreateText("Subtitle", menuRoot, "AND EVACUATION TRAINER", 56, TextAnchor.MiddleCenter, true,
                                   accentColour);
        Place(subtitle.rectTransform, new Vector2(0f, 1f), new Vector2(1f, 1f), new Vector2(0.5f, 1f),
              new Vector2(0f, -172f), new Vector2(-160f, 80f));

        Text tagline = CreateText("Tagline", menuRoot,
            "A short guided training experience: alarm, masks and extinguishers, evacuation, first aid.",
            26, TextAnchor.MiddleCenter, false, new Color(0.82f, 0.86f, 0.92f, 1f));
        Place(tagline.rectTransform, new Vector2(0f, 1f), new Vector2(1f, 1f), new Vector2(0.5f, 1f),
              new Vector2(0f, -268f), new Vector2(-240f, 70f));

        float buttonWidth = 620f;
        float buttonHeight = 92f;
        float gap = 18f;
        float startOffset = 130f;

        CreateButton("START TRAINING", menuRoot,
            new Vector2(0f, startOffset), new Vector2(buttonWidth, buttonHeight), () =>
            {
                if (LessonManager.Instance != null) LessonManager.Instance.StartTraining();
            });
        CreateButton("CONTROLS", menuRoot,
            new Vector2(0f, startOffset - (buttonHeight + gap)), new Vector2(buttonWidth, buttonHeight),
            ShowControlsFromMenu);
        CreateButton("REFERENCES", menuRoot,
            new Vector2(0f, startOffset - 2f * (buttonHeight + gap)), new Vector2(buttonWidth, buttonHeight),
            ShowReferencesFromMenu);
        CreateButton("EXIT", menuRoot,
            new Vector2(0f, startOffset - 3f * (buttonHeight + gap)), new Vector2(buttonWidth, buttonHeight),
            () => { if (LessonManager.Instance != null) LessonManager.Instance.QuitApplication(); });

        Text disclaimer = CreateText("Disclaimer", menuRoot, LessonContent.Disclaimer, 20, TextAnchor.LowerCenter,
                                     false, new Color(0.65f, 0.69f, 0.75f, 1f));
        Place(disclaimer.rectTransform, new Vector2(0f, 0f), new Vector2(1f, 0f), new Vector2(0.5f, 0f),
              new Vector2(0f, 34f), new Vector2(-260f, 70f));

        // Info overlay used by Controls and References
        menuInfoRoot = CreateNode("MenuInfo", transform);
        Place(menuInfoRoot, Vector2.zero, Vector2.one, new Vector2(0.5f, 0.5f), Vector2.zero, Vector2.zero);
        Padding(menuInfoRoot, 0, 0, 0, 0);

        Image infoDim = CreateImage("Dim", menuInfoRoot, new Color(0f, 0f, 0f, 0.7f), true);
        Place(infoDim.rectTransform, Vector2.zero, Vector2.one, new Vector2(0.5f, 0.5f), Vector2.zero, Vector2.zero);

        Image infoPanel = CreateImage("Panel", menuInfoRoot, panelColour, true);
        Place(infoPanel.rectTransform, new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f),
              Vector2.zero, new Vector2(1460f, 840f));

        menuInfoTitle = CreateText("Title", infoPanel.transform, "", 44, TextAnchor.UpperLeft, true, accentColour);
        Place(menuInfoTitle.rectTransform, new Vector2(0f, 1f), new Vector2(1f, 1f), new Vector2(0f, 1f),
              new Vector2(56f, -30f), new Vector2(-112f, 62f));

        menuInfoBody = CreateText("Body", infoPanel.transform, "", 26, TextAnchor.UpperLeft, false, bodyColour);
        Place(menuInfoBody.rectTransform, new Vector2(0f, 1f), new Vector2(1f, 1f), new Vector2(0f, 1f),
              new Vector2(56f, -104f), new Vector2(-112f, 610f));

        CreateButton("Back", infoPanel.transform, new Vector2(0f, 28f), new Vector2(300f, 76f), HideMenuInfo);

        menuInfoRoot.gameObject.SetActive(false);
    }

    public void ShowMenu()
    {
        menuRoot.gameObject.SetActive(true);
        menuRoot.SetAsLastSibling();
        HideMenuInfo();
    }

    public void HideMenu()
    {
        if (menuRoot != null) menuRoot.gameObject.SetActive(false);
        HideMenuInfo();
    }

    void ShowControlsFromMenu()
    {
        if (LessonManager.Instance != null) LessonManager.Instance.PlayPanelSound();
        ShowMenuInfo("CONTROLS",
            "<b>Keyboard and mouse (works in the Unity Editor without a headset)</b>\n" +
            "W / A / S / D  -  move\n" +
            "Mouse  -  look around\n" +
            "E  -  interact with the object under the crosshair\n" +
            "Left mouse click  -  press the on-screen buttons\n" +
            "Shift  -  walk faster\n" +
            "Escape  -  pause and resume\n\n" +
            "<b>VR headset (OpenXR, or the XR Device Simulator in the Editor)</b>\n" +
            "Left stick  -  move\n" +
            "Right stick  -  turn in 30 degree steps\n" +
            "Trigger  -  interact with objects and press buttons\n" +
            "Headset  -  look around\n\n" +
            "The training pauses while a teaching panel is open, so you never miss a step.");
    }

    void ShowReferencesFromMenu()
    {
        if (LessonManager.Instance != null) LessonManager.Instance.PlayPanelSound();
        System.Text.StringBuilder builder = new System.Text.StringBuilder();
        builder.AppendLine("The fire-safety and first-aid content was checked against these sources:\n");
        for (int i = 0; i < LessonContent.References.Length; i++)
        {
            LessonContent.Reference reference = LessonContent.References[i];
            builder.AppendLine("<b>" + (i + 1) + ". " + reference.Title + "</b>  (" + reference.Publisher + ")");
            builder.AppendLine(reference.Url);
        }
        ShowMenuInfo("REFERENCES", builder.ToString());
    }

    void ShowMenuInfo(string title, string body)
    {
        menuInfoTitle.text = title;
        menuInfoBody.text = body;
        menuInfoBody.fontSize = FitFontSize(body, 590f, 96f, 25);
        menuInfoRoot.gameObject.SetActive(true);
        menuInfoRoot.SetAsLastSibling();
    }

    void HideMenuInfo()
    {
        if (menuInfoRoot != null) menuInfoRoot.gameObject.SetActive(false);
    }

    // ------------------------------------------------------------------ //
    // Pause menu
    // ------------------------------------------------------------------ //

    void BuildPause()
    {
        pauseRoot = CreateNode("PauseMenu", transform);
        Place(pauseRoot, Vector2.zero, Vector2.one, new Vector2(0.5f, 0.5f), Vector2.zero, Vector2.zero);
        Padding(pauseRoot, 0, 0, 0, 0);

        Image dim = CreateImage("Dim", pauseRoot, new Color(0f, 0f, 0f, 0.75f), true);
        Place(dim.rectTransform, Vector2.zero, Vector2.one, new Vector2(0.5f, 0.5f), Vector2.zero, Vector2.zero);

        Image panel = CreateImage("Panel", pauseRoot, panelColour, true);
        Place(panel.rectTransform, new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f),
              Vector2.zero, new Vector2(860f, 620f));

        Text title = CreateText("Title", panel.transform, "PAUSED", 56, TextAnchor.MiddleCenter, true, accentColour);
        Place(title.rectTransform, new Vector2(0f, 1f), new Vector2(1f, 1f), new Vector2(0.5f, 1f),
              new Vector2(0f, -40f), new Vector2(-60f, 70f));

        Text body = CreateText("Body", panel.transform,
            "The training is paused.\nYour progress is safe. Continue when you are ready.",
            26, TextAnchor.UpperCenter, false, bodyColour);
        Place(body.rectTransform, new Vector2(0f, 1f), new Vector2(1f, 1f), new Vector2(0.5f, 1f),
              new Vector2(0f, -120f), new Vector2(-80f, 100f));

        float width = 560f;
        float height = 66f;
        float gap = 10f;
        float start = 26f;
        CreateButton("Resume", panel.transform, new Vector2(0f, start), new Vector2(width, height),
            () => { if (LessonManager.Instance != null) LessonManager.Instance.Resume(); });
        CreateButton("Restart training", panel.transform, new Vector2(0f, start + (height + gap)),
            new Vector2(width, height),
            () => { if (LessonManager.Instance != null) LessonManager.Instance.RestartTraining(); });
        CreateButton("Main menu", panel.transform, new Vector2(0f, start + 2f * (height + gap)),
            new Vector2(width, height),
            () => { if (LessonManager.Instance != null) LessonManager.Instance.ReturnToMenu(); });
        CreateButton("Quit application", panel.transform, new Vector2(0f, start + 3f * (height + gap)),
            new Vector2(width, height),
            () => { if (LessonManager.Instance != null) LessonManager.Instance.QuitApplication(); });
    }

    public void ShowPause()
    {
        pauseRoot.gameObject.SetActive(true);
        pauseRoot.SetAsLastSibling();
    }

    public void HidePause()
    {
        if (pauseRoot != null) pauseRoot.gameObject.SetActive(false);
    }
}
