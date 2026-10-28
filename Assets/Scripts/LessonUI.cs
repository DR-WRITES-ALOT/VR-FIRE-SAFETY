using System;
using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;
using UnityEngine.XR;

/// <summary>
/// Builds and drives the on-screen interface.
///
/// The interface is a world-space canvas locked in front of the camera, so the same buttons
/// and text work in the Unity Editor, in a desktop build and in a VR headset (a screen-space
/// canvas would not render in VR).
///
/// Everything can be operated three ways, because relying on the mouse alone left players
/// stuck when the cursor did not appear:
///   * mouse - click a button directly (the cursor is released while an overlay is open)
///   * keyboard - E, Enter or Space activates the highlighted button (arrow keys / Tab move
///     the highlight, Escape closes a help overlay)
///   * VR - look at a button and press the trigger
/// The highlight follows the mouse when the cursor is free and the screen centre otherwise.
/// </summary>
public class LessonUI : MonoBehaviour
{
    public static LessonUI Instance;

    [Header("Fonts (drag from Assets/Fonts)")]
    public Font fontRegular;
    public Font fontBold;

    [Header("Colours")]
    public Color panelColour = new Color(0.055f, 0.07f, 0.10f, 0.97f);
    public Color accentColour = new Color(1f, 0.72f, 0.25f, 1f);
    public Color bodyColour = new Color(0.93f, 0.94f, 0.96f, 1f);
    public Color dangerColour = new Color(0.72f, 0.13f, 0.10f, 0.96f);
    public Color buttonColour = new Color(0.16f, 0.24f, 0.34f, 1f);
    public Color buttonHoverColour = new Color(0.30f, 0.46f, 0.62f, 1f);

    // Layout constants for the 1600 x 900 design resolution.
    const float DesignWidth = 1600f;
    const float DesignHeight = 900f;
    const float Margin = 24f;

    // HUD
    RectTransform hudRoot;
    RectTransform sectionBandRect;
    RectTransform objectiveBoxRect;
    RectTransform hintRect;
    Text sectionText;
    Text objectiveText;
    Text promptText;
    Image promptBackground;
    Image warningBanner;
    Text warningText;
    RectTransform captionRoot;
    Text captionText;
    RectTransform crosshair;
    Image crosshairRing;

    // Overlays
    RectTransform menuRoot;
    RectTransform menuInfoRoot;
    Text menuInfoTitle;
    Text menuInfoBody;
    RectTransform pauseRoot;
    RectTransform modalRoot;
    Text modalTitle;
    Text modalBody;
    Text modalFooter;
    RectTransform buttonRow;

    bool menuOpen;
    bool pauseOpen;
    bool infoOpen;
    bool panelOpen;

    readonly List<Selectable> modalButtons = new List<Selectable>();
    readonly List<Selectable> menuButtons = new List<Selectable>();
    readonly List<Selectable> pauseButtons = new List<Selectable>();
    readonly List<Selectable> infoButtons = new List<Selectable>();
    List<Selectable> currentButtons = new List<Selectable>();
    Selectable hovered;
    int selectedIndex;
    float nextNavTime;
    Coroutine warningRoutine;
    GraphicRaycaster raycaster;
    Canvas canvas;
    CanvasScaler scaler;
    HudFollower follower;
    bool lastXrState;

    /// <summary>True while a teaching panel is showing.</summary>
    public bool PanelOpen => panelOpen;

    /// <summary>True while any overlay owns the input (panel, menu, pause or help).</summary>
    public bool AnyOverlayOpen => panelOpen || menuOpen || pauseOpen || infoOpen;

    // ------------------------------------------------------------------ //
    // Construction
    // ------------------------------------------------------------------ //

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

        canvas = GetComponent<Canvas>();
        scaler = GetComponent<CanvasScaler>();
        follower = GetComponent<HudFollower>();
        ApplyRenderMode();
    }

    /// <summary>
    /// Desktop and VR need different canvas modes, and both must guarantee that a teaching
    /// panel is visible:
    ///   * no headset - Screen Space Overlay. It is drawn over the 3D scene and can never be
    ///     hidden by a wall, which is exactly what went wrong when a panel opened at the
    ///     alarm while the player was facing the call point.
    ///   * headset - World Space (overlay canvases do not render in VR). The HudFollower then
    ///     keeps it in front of the eyes and pulls it in front of any wall in the way.
    /// Both modes use the same 1600 x 900 layout, so the training logic and the buttons are
    /// identical.
    /// </summary>
    void ApplyRenderMode()
    {
        bool xr = XRSettings.isDeviceActive;
        lastXrState = xr;
        if (canvas == null) return;

        if (xr)
        {
            if (follower != null) follower.enabled = true;
            canvas.renderMode = RenderMode.WorldSpace;
            canvas.worldCamera = Camera.main;
            if (scaler != null) scaler.uiScaleMode = CanvasScaler.ScaleMode.ConstantPixelSize;
            if (follower != null) follower.Snap();
        }
        else
        {
            if (follower != null) follower.enabled = false;
            transform.localScale = Vector3.one;
            transform.localPosition = Vector3.zero;
            transform.localRotation = Quaternion.identity;
            canvas.worldCamera = null;
            canvas.renderMode = RenderMode.ScreenSpaceOverlay;
            if (scaler != null)
            {
                scaler.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize;
                scaler.referenceResolution = new Vector2(DesignWidth, DesignHeight);
                scaler.screenMatchMode = CanvasScaler.ScreenMatchMode.MatchWidthOrHeight;
                scaler.matchWidthOrHeight = 0.5f;
            }
        }
    }

    void EnsureFonts()
    {
        if (fontRegular == null)
        {
            try { fontRegular = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf"); }
            catch { fontRegular = null; }
        }
        if (fontRegular == null) fontRegular = Font.CreateDynamicFontFromOSFont("Arial", 16);
        if (fontBold == null) fontBold = fontRegular;
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

    /// <summary>Stretch a rect to its parent with a margin on every side.</summary>
    static void Stretch(RectTransform rect, float margin)
    {
        rect.anchorMin = Vector2.zero;
        rect.anchorMax = Vector2.one;
        rect.offsetMin = new Vector2(margin, margin);
        rect.offsetMax = new Vector2(-margin, -margin);
    }

    static void Padding(RectTransform rect, float left, float bottom, float right, float top)
    {
        rect.offsetMin = new Vector2(left, bottom);
        rect.offsetMax = new Vector2(-right, -top);
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
        text.lineSpacing = 1.08f;
        text.raycastTarget = false;
        text.text = content;
        return text;
    }

    /// <summary>
    /// Picks a font size that keeps a block of text inside the space available.
    /// Unity's legacy Text silently truncates when it overflows, which would hide part of a
    /// lesson, so long bodies are shrunk instead of clipped.
    /// </summary>
    static int FitFontSize(string text, float height, float charactersPerLine, int maximum,
                           int minimum = 16)
    {
        if (string.IsNullOrEmpty(text)) return maximum;
        int lines = 0;
        string[] paragraphs = text.Split('\n');
        for (int i = 0; i < paragraphs.Length; i++)
            lines += Mathf.Max(1, Mathf.CeilToInt(paragraphs[i].Length / charactersPerLine));
        int fitted = Mathf.FloorToInt(height / (lines * 1.35f));
        return Mathf.Clamp(fitted, minimum, maximum);
    }

    Button CreateButton(string label, List<Selectable> owner, Transform parent, Vector2 position,
                        Vector2 size, Action onClick, int fontSize = 30)
    {
        Image background = CreateImage("Button_" + label, parent, buttonColour, true);
        Place(background.rectTransform, new Vector2(0.5f, 1f), new Vector2(0.5f, 1f),
              new Vector2(0.5f, 1f), position, size);

        Button button = background.gameObject.AddComponent<Button>();
        ColorBlock colours = button.colors;
        colours.normalColor = Color.white;
        colours.highlightedColor = new Color(1.18f, 1.18f, 1.18f, 1f);
        colours.pressedColor = new Color(0.82f, 0.82f, 0.82f, 1f);
        colours.selectedColor = new Color(1.18f, 1.18f, 1.18f, 1f);
        colours.fadeDuration = 0.05f;
        button.colors = colours;
        button.targetGraphic = background;
        button.transition = Selectable.Transition.ColorTint;
        if (onClick != null) button.onClick.AddListener(() => onClick());

        Text text = CreateText("Label", background.transform, label, fontSize, TextAnchor.MiddleCenter,
                               true, Color.white);
        RectTransform textRect = text.rectTransform;
        textRect.anchorMin = Vector2.zero;
        textRect.anchorMax = Vector2.one;
        textRect.pivot = new Vector2(0.5f, 0.5f);
        textRect.anchoredPosition = Vector2.zero;
        textRect.sizeDelta = Vector2.zero;
        Padding(textRect, 16f, 6f, 16f, 6f);

        owner.Add(button);
        return button;
    }

    // ------------------------------------------------------------------ //
    // HUD
    // ------------------------------------------------------------------ //

    void BuildHud()
    {
        hudRoot = CreateNode("HUD", transform);
        Stretch(hudRoot, 0f);

        // Section label: top left, compact.
        Image sectionBand = CreateImage("SectionBand", hudRoot, new Color(0.03f, 0.04f, 0.06f, 0.86f));
        Place(sectionBand.rectTransform, new Vector2(0f, 1f), new Vector2(0f, 1f), new Vector2(0f, 1f),
              new Vector2(Margin, -Margin), new Vector2(560f, 52f));
        sectionBandRect = sectionBand.rectTransform;
        Image sectionAccent = CreateImage("Accent", sectionBand.transform, accentColour);
        Place(sectionAccent.rectTransform, new Vector2(0f, 0f), new Vector2(0f, 1f), new Vector2(0f, 0.5f),
              new Vector2(0f, 0f), new Vector2(6f, 0f));
        sectionText = CreateText("Section", sectionBand.transform, "", 24, TextAnchor.MiddleLeft, true,
                                 accentColour);
        Stretch(sectionText.rectTransform, 0f);
        Padding(sectionText.rectTransform, 20f, 4f, 12f, 4f);

        // Objective box: top right, always visible, wraps onto several lines.
        Image objectiveBox = CreateImage("ObjectiveBox", hudRoot, new Color(0.03f, 0.04f, 0.06f, 0.9f));
        Place(objectiveBox.rectTransform, new Vector2(1f, 1f), new Vector2(1f, 1f), new Vector2(1f, 1f),
              new Vector2(-Margin, -Margin), new Vector2(470f, 176f));
        objectiveBoxRect = objectiveBox.rectTransform;
        Image objectiveAccent = CreateImage("Accent", objectiveBox.transform, accentColour);
        Place(objectiveAccent.rectTransform, new Vector2(0f, 1f), new Vector2(1f, 1f),
              new Vector2(0.5f, 1f), Vector2.zero, new Vector2(0f, 6f));
        Text objectiveHeader = CreateText("Header", objectiveBox.transform, "CURRENT OBJECTIVE", 20,
                                          TextAnchor.UpperLeft, true, accentColour);
        Place(objectiveHeader.rectTransform, new Vector2(0f, 1f), new Vector2(1f, 1f),
              new Vector2(0f, 1f), new Vector2(20f, -16f), new Vector2(-40f, 26f));
        objectiveText = CreateText("Objective", objectiveBox.transform, "", 24, TextAnchor.UpperLeft,
                                   false, bodyColour);
        Place(objectiveText.rectTransform, new Vector2(0f, 1f), new Vector2(1f, 1f), new Vector2(0f, 1f),
              new Vector2(20f, -52f), new Vector2(-40f, 112f));

        // Interaction prompt above the bottom edge.
        promptBackground = CreateImage("PromptBackground", hudRoot, new Color(0.05f, 0.06f, 0.09f, 0.9f));
        Place(promptBackground.rectTransform, new Vector2(0.5f, 0f), new Vector2(0.5f, 0f),
              new Vector2(0.5f, 0f), new Vector2(0f, 120f), new Vector2(920f, 66f));
        promptText = CreateText("Prompt", promptBackground.transform, "", 28, TextAnchor.MiddleCenter,
                                true, Color.white);
        Stretch(promptText.rectTransform, 0f);
        Padding(promptText.rectTransform, 20f, 6f, 20f, 6f);
        promptBackground.gameObject.SetActive(false);

        // Controls hint, bottom left so it never collides with the prompt.
        Text hint = CreateText("ControlsHint", hudRoot,
            "WASD move  |  Mouse look  |  E interact  |  Shift run  |  Esc pause", 20,
            TextAnchor.LowerLeft, false, new Color(0.86f, 0.88f, 0.92f, 0.9f));
        Place(hint.rectTransform, new Vector2(0f, 0f), new Vector2(1f, 0f), new Vector2(0f, 0f),
              new Vector2(Margin, Margin - 4f), new Vector2(-2f * Margin, 30f));
        hintRect = hint.rectTransform;

        // Demonstration caption: a large subtitle used while the PASS sequence is played.
        Image captionBand = CreateImage("CaptionBand", hudRoot, new Color(0.03f, 0.04f, 0.06f, 0.92f));
        Place(captionBand.rectTransform, new Vector2(0.5f, 0f), new Vector2(0.5f, 0f),
              new Vector2(0.5f, 0f), new Vector2(0f, 206f), new Vector2(1240f, 84f));
        Image captionAccent = CreateImage("Accent", captionBand.transform, accentColour);
        Place(captionAccent.rectTransform, new Vector2(0f, 0f), new Vector2(0f, 1f),
              new Vector2(0f, 0.5f), Vector2.zero, new Vector2(8f, 0f));
        captionText = CreateText("Caption", captionBand.transform, "", 40, TextAnchor.MiddleLeft,
                                 true, Color.white);
        Stretch(captionText.rectTransform, 0f);
        Padding(captionText.rectTransform, 30f, 6f, 20f, 6f);
        captionRoot = captionBand.rectTransform;
        captionBand.gameObject.SetActive(false);

        // Crosshair with a ring that lights up over a button.
        crosshair = CreateNode("Crosshair", hudRoot);
        Place(crosshair, new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f),
              Vector2.zero, new Vector2(26f, 26f));
        Image dot = CreateImage("Dot", crosshair, new Color(1f, 1f, 1f, 0.8f));
        Place(dot.rectTransform, new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f),
              Vector2.zero, new Vector2(7f, 7f));
        crosshairRing = CreateImage("Ring", crosshair, new Color(1f, 0.72f, 0.25f, 0.35f));
        Place(crosshairRing.rectTransform, new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f),
              new Vector2(0.5f, 0.5f), Vector2.zero, new Vector2(26f, 26f));

        // Warning banner, below the top row so it does not cover the objective box.
        warningBanner = CreateImage("WarningBanner", hudRoot, dangerColour);
        Place(warningBanner.rectTransform, new Vector2(0.5f, 1f), new Vector2(0.5f, 1f),
              new Vector2(0.5f, 1f), new Vector2(-60f, -230f), new Vector2(1000f, 84f));
        warningText = CreateText("WarningText", warningBanner.transform, "", 27, TextAnchor.MiddleCenter,
                                 true, Color.white);
        Stretch(warningText.rectTransform, 0f);
        Padding(warningText.rectTransform, 22f, 6f, 22f, 6f);
        warningBanner.gameObject.SetActive(false);
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
        if (objectiveText == null) return;
        objectiveText.text = text;
        // Keep the objective readable however long the instruction is.
        objectiveText.fontSize = FitFontSize(text, 104f, 34f, 24, 18);
    }

    public void SetPrompt(string text)
    {
        if (promptText == null) return;
        bool show = !string.IsNullOrEmpty(text);
        promptBackground.gameObject.SetActive(show);
        if (show) promptText.text = text;
    }

    /// <summary>
    /// Large subtitle shown during an animated demonstration ("1 of 4  PULL the safety pin").
    /// An empty string hides it.
    /// </summary>
    public void SetCaption(string text)
    {
        if (captionRoot == null) return;
        bool show = !string.IsNullOrEmpty(text);
        captionRoot.gameObject.SetActive(show);
        if (show) captionText.text = text;
    }

    public void SetHudVisible(bool visible)
    {
        if (hudRoot != null) hudRoot.gameObject.SetActive(visible);
        RefreshHudChrome();
    }

    /// <summary>
    /// A teaching panel covers almost the whole screen, so the section band, the objective
    /// box and the controls hint are hidden while it is open. They used to sit behind the
    /// panel and read as text printed on top of the panel title. The panel carries the same
    /// information in its own footer, so nothing is lost; the HUD comes back when it closes.
    /// </summary>
    void RefreshHudChrome()
    {
        bool chrome = hudRoot != null && hudRoot.activeSelf
                      && !panelOpen && !pauseOpen && !infoOpen;
        if (sectionBandRect != null) sectionBandRect.gameObject.SetActive(chrome);
        if (objectiveBoxRect != null) objectiveBoxRect.gameObject.SetActive(chrome);
        if (hintRect != null) hintRect.gameObject.SetActive(chrome);
        if (!chrome) SetPrompt(string.Empty);
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
        yield return new WaitForSecondsRealtime(seconds);
        warningBanner.gameObject.SetActive(false);
        warningRoutine = null;
    }

    // ------------------------------------------------------------------ //
    // Teaching panels
    // ------------------------------------------------------------------ //

    void BuildModal()
    {
        modalRoot = CreateNode("Modal", transform);
        Stretch(modalRoot, 0f);

        Image dim = CreateImage("Dim", modalRoot, new Color(0f, 0f, 0f, 0.6f), true);
        Stretch(dim.rectTransform, 0f);

        Image panel = CreateImage("Panel", modalRoot, panelColour, true);
        Place(panel.rectTransform, new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f),
              Vector2.zero, new Vector2(1440f, 830f));

        Image accent = CreateImage("Accent", panel.transform, accentColour);
        Place(accent.rectTransform, new Vector2(0f, 1f), new Vector2(1f, 1f), new Vector2(0.5f, 1f),
              Vector2.zero, new Vector2(0f, 7f));

        modalTitle = CreateText("Title", panel.transform, "", 42, TextAnchor.UpperLeft, true, accentColour);
        Place(modalTitle.rectTransform, new Vector2(0f, 1f), new Vector2(1f, 1f), new Vector2(0f, 1f),
              new Vector2(48f, -32f), new Vector2(-96f, 62f));

        modalBody = CreateText("Body", panel.transform, "", 28, TextAnchor.UpperLeft, false, bodyColour);
        Place(modalBody.rectTransform, new Vector2(0f, 1f), new Vector2(1f, 1f), new Vector2(0f, 1f),
              new Vector2(48f, -104f), new Vector2(-96f, 540f));

        modalFooter = CreateText("Footer", panel.transform, "", 22, TextAnchor.LowerLeft, false,
                                 new Color(0.72f, 0.76f, 0.82f, 1f));
        Place(modalFooter.rectTransform, new Vector2(0f, 0f), new Vector2(1f, 0f), new Vector2(0f, 0f),
              new Vector2(48f, 140f), new Vector2(-96f, 56f));

        buttonRow = CreateNode("Buttons", panel.transform);
        Place(buttonRow, new Vector2(0f, 0f), new Vector2(1f, 0f), new Vector2(0.5f, 0f),
              new Vector2(0f, 40f), new Vector2(-96f, 96f));
    }

    public void ShowPanel(string title, string body, string footer, string[] buttonLabels,
                          Action[] buttonActions)
    {
        modalTitle.text = title;
        modalBody.text = body;
        modalFooter.text = footer ?? string.Empty;
        modalBody.fontSize = FitFontSize(body, 530f, 86f, 28, 18);

        ClearModalButtons();

        int count = buttonLabels != null ? buttonLabels.Length : 0;
        if (count > 0)
        {
            const float spacing = 16f;
            const float rowWidth = 1344f;
            float buttonWidth = (rowWidth - spacing * (count - 1)) / count;
            for (int i = 0; i < count; i++)
            {
                float x = (i - (count - 1) * 0.5f) * (buttonWidth + spacing);
                Action action = (buttonActions != null && i < buttonActions.Length) ? buttonActions[i] : null;
                // Close this panel first, then run the lesson step (which may open the next panel).
                Action wrapped = () =>
                {
                    HidePanel();
                    if (action != null) action();
                };
                CreateButton(buttonLabels[i], modalButtons, buttonRow, new Vector2(x, 0f),
                             new Vector2(buttonWidth, 88f), wrapped);
            }
        }

        modalRoot.gameObject.SetActive(true);
        modalRoot.SetAsLastSibling();
        panelOpen = true;
        SetPrompt(string.Empty);
        RefreshHudChrome();
        SelectFirstButton();
        SyncFocus();
    }

    public void HidePanel()
    {
        if (modalRoot != null) modalRoot.gameObject.SetActive(false);
        panelOpen = false;
        ClearModalButtons();
        ClearHover();
        RefreshHudChrome();
        SyncFocus();
    }

    /// <summary>Buttons belonging to the overlay that is currently on top.</summary>
    List<Selectable> ButtonsForOpenOverlay()
    {
        if (infoOpen) return infoButtons;
        if (pauseOpen) return pauseButtons;
        if (panelOpen) return modalButtons;
        if (menuOpen) return menuButtons;
        return null;
    }

    void ClearModalButtons()
    {
        for (int i = 0; i < buttonRow.childCount; i++) Destroy(buttonRow.GetChild(i).gameObject);
        modalButtons.Clear();
        hovered = null;
        selectedIndex = 0;
    }

    void SelectFirstButton()
    {
        selectedIndex = 0;
        currentButtons = ButtonsForOpenOverlay() ?? new List<Selectable>();
        if (EventSystem.current == null) return;
        EventSystem.current.SetSelectedGameObject(null);
        if (currentButtons.Count > 0)
            EventSystem.current.SetSelectedGameObject(currentButtons[0].gameObject);
    }

    // ------------------------------------------------------------------ //
    // Menu
    // ------------------------------------------------------------------ //

    void BuildMenu()
    {
        menuRoot = CreateNode("MainMenu", transform);
        Stretch(menuRoot, 0f);

        Image dim = CreateImage("Dim", menuRoot, new Color(0.02f, 0.03f, 0.05f, 0.96f), true);
        Stretch(dim.rectTransform, 0f);

        // Header block: title, subtitle and tagline, each with its own band so they cannot overlap.
        Text title = CreateText("Title", menuRoot, "VR FIRE SAFETY", 68, TextAnchor.MiddleCenter, true,
                                Color.white);
        Place(title.rectTransform, new Vector2(0f, 1f), new Vector2(1f, 1f), new Vector2(0.5f, 1f),
              new Vector2(0f, -42f), new Vector2(-80f, 74f));

        Text subtitle = CreateText("Subtitle", menuRoot, "AND EVACUATION TRAINER", 34, TextAnchor.MiddleCenter,
                                   true, accentColour);
        Place(subtitle.rectTransform, new Vector2(0f, 1f), new Vector2(1f, 1f), new Vector2(0.5f, 1f),
              new Vector2(0f, -120f), new Vector2(-80f, 42f));

        Image stripe = CreateImage("Stripe", menuRoot, new Color(0.72f, 0.13f, 0.10f, 1f));
        Place(stripe.rectTransform, new Vector2(0.5f, 1f), new Vector2(0.5f, 1f), new Vector2(0.5f, 1f),
              new Vector2(0f, -168f), new Vector2(760f, 5f));

        Text tagline = CreateText("Tagline", menuRoot,
            "A short guided training experience: alarm, masks and extinguishers, evacuation, first aid.",
            22, TextAnchor.MiddleCenter, false, new Color(0.82f, 0.86f, 0.92f, 1f));
        Place(tagline.rectTransform, new Vector2(0f, 1f), new Vector2(1f, 1f), new Vector2(0.5f, 1f),
              new Vector2(0f, -186f), new Vector2(-120f, 32f));

        // Button column, centred between the tagline and the disclaimer band.
        const float buttonWidth = 560f;
        const float buttonHeight = 76f;
        const float gap = 14f;
        string[] labels = { "START TRAINING", "CONTROLS", "REFERENCES", "EXIT" };
        const float columnTop = -268f;   // offset from the top of the canvas
        for (int i = 0; i < labels.Length; i++)
        {
            string label = labels[i];
            float y = columnTop - i * (buttonHeight + gap);
            Action action = null;
            switch (label)
            {
                case "START TRAINING":
                    action = () => { if (LessonManager.Instance != null) LessonManager.Instance.StartTraining(); };
                    break;
                case "CONTROLS":
                    action = ShowControlsFromMenu;
                    break;
                case "REFERENCES":
                    action = ShowReferencesFromMenu;
                    break;
                case "EXIT":
                    action = () => { if (LessonManager.Instance != null) LessonManager.Instance.QuitApplication(); };
                    break;
            }
            CreateButton(label, menuButtons, menuRoot, new Vector2(0f, y),
                         new Vector2(buttonWidth, buttonHeight), action, 26);
        }

        // Disclaimer: its own band along the bottom edge.
        Image disclaimerBand = CreateImage("DisclaimerBand", menuRoot, new Color(0.03f, 0.04f, 0.06f, 0.9f));
        Place(disclaimerBand.rectTransform, new Vector2(0f, 0f), new Vector2(1f, 0f), new Vector2(0.5f, 0f),
              new Vector2(0f, 26f), new Vector2(-80f, 74f));
        Text disclaimer = CreateText("Disclaimer", disclaimerBand.transform, LessonContent.Disclaimer, 19,
                                     TextAnchor.MiddleCenter, false, new Color(0.72f, 0.76f, 0.82f, 1f));
        Stretch(disclaimer.rectTransform, 0f);
        Padding(disclaimer.rectTransform, 24f, 8f, 24f, 8f);

        BuildMenuInfo();
    }

    void BuildMenuInfo()
    {
        menuInfoRoot = CreateNode("MenuInfo", transform);
        Stretch(menuInfoRoot, 0f);

        Image dim = CreateImage("Dim", menuInfoRoot, new Color(0f, 0f, 0f, 0.85f), true);
        Stretch(dim.rectTransform, 0f);

        Image panel = CreateImage("Panel", menuInfoRoot, panelColour, true);
        Place(panel.rectTransform, new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f),
              Vector2.zero, new Vector2(1400f, 820f));

        menuInfoTitle = CreateText("Title", panel.transform, "", 40, TextAnchor.UpperLeft, true, accentColour);
        Place(menuInfoTitle.rectTransform, new Vector2(0f, 1f), new Vector2(1f, 1f), new Vector2(0f, 1f),
              new Vector2(52f, -30f), new Vector2(-104f, 58f));

        menuInfoBody = CreateText("Body", panel.transform, "", 24, TextAnchor.UpperLeft, false, bodyColour);
        Place(menuInfoBody.rectTransform, new Vector2(0f, 1f), new Vector2(1f, 1f), new Vector2(0f, 1f),
              new Vector2(52f, -98f), new Vector2(-104f, 610f));

        RectTransform backRow = CreateNode("Buttons", panel.transform);
        Place(backRow, new Vector2(0f, 0f), new Vector2(1f, 0f), new Vector2(0.5f, 0f),
              new Vector2(0f, 36f), new Vector2(-104f, 84f));
        CreateButton("BACK", infoButtons, backRow, new Vector2(0f, 0f), new Vector2(340f, 76f),
                     HideMenuInfo, 26);

        menuInfoRoot.gameObject.SetActive(false);
    }

    public void ShowMenu()
    {
        menuOpen = true;
        menuRoot.gameObject.SetActive(true);
        menuRoot.SetAsLastSibling();
        HideMenuInfo();
        SelectFirstButton();
        SyncFocus();
    }

    public void HideMenu()
    {
        menuOpen = false;
        if (menuRoot != null) menuRoot.gameObject.SetActive(false);
        HideMenuInfo();
        currentButtons = new List<Selectable>();
        ClearHover();
        SyncFocus();
    }

    void ShowMenuInfo(string title, string body)
    {
        infoOpen = true;
        RefreshHudChrome();
        menuInfoTitle.text = title;
        menuInfoBody.text = body;
        menuInfoBody.fontSize = FitFontSize(body, 590f, 92f, 24, 17);
        menuInfoRoot.gameObject.SetActive(true);
        menuInfoRoot.SetAsLastSibling();
        SelectFirstButton();
        SyncFocus();
    }

    void HideMenuInfo()
    {
        infoOpen = false;
        if (menuInfoRoot != null) menuInfoRoot.gameObject.SetActive(false);
        RefreshHudChrome();
        ClearHover();
        SelectFirstButton();
        SyncFocus();
    }

    void ShowControlsFromMenu()
    {
        if (LessonManager.Instance != null) LessonManager.Instance.PlayPanelSound();
        ShowMenuInfo("CONTROLS",
            "<b>Keyboard and mouse (works in the Unity Editor without a headset)</b>\n" +
            "W / A / S / D  -  move\n" +
            "Mouse  -  look around\n" +
            "Shift  -  walk faster\n" +
            "E  -  interact with the object under the crosshair\n" +
            "E / Enter / Space  -  press the highlighted button\n" +
            "Left mouse click  -  press a button with the cursor\n" +
            "Arrow keys or Tab  -  move between buttons\n" +
            "Escape  -  close this screen, or pause the training\n\n" +
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

    // ------------------------------------------------------------------ //
    // Pause
    // ------------------------------------------------------------------ //

    void BuildPause()
    {
        pauseRoot = CreateNode("PauseMenu", transform);
        Stretch(pauseRoot, 0f);

        Image dim = CreateImage("Dim", pauseRoot, new Color(0f, 0f, 0f, 0.8f), true);
        Stretch(dim.rectTransform, 0f);

        Image panel = CreateImage("Panel", pauseRoot, panelColour, true);
        Place(panel.rectTransform, new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f),
              Vector2.zero, new Vector2(820f, 660f));

        Text title = CreateText("Title", panel.transform, "PAUSED", 52, TextAnchor.MiddleCenter, true,
                                accentColour);
        Place(title.rectTransform, new Vector2(0f, 1f), new Vector2(1f, 1f), new Vector2(0.5f, 1f),
              new Vector2(0f, -32f), new Vector2(-60f, 62f));

        Text body = CreateText("Body", panel.transform,
            "The training is paused and your progress is safe.\nPress Escape or Resume to continue.",
            22, TextAnchor.UpperCenter, false, bodyColour);
        Place(body.rectTransform, new Vector2(0f, 1f), new Vector2(1f, 1f), new Vector2(0.5f, 1f),
              new Vector2(0f, -104f), new Vector2(-80f, 70f));

        const float width = 540f;
        const float height = 68f;
        const float gap = 12f;
        const float first = -206f;
        string[] labels = { "RESUME", "RESTART TRAINING", "MAIN MENU", "QUIT APPLICATION" };
        for (int i = 0; i < labels.Length; i++)
        {
            string label = labels[i];
            Action action = null;
            switch (label)
            {
                case "RESUME":
                    action = () => { if (LessonManager.Instance != null) LessonManager.Instance.Resume(); };
                    break;
                case "RESTART TRAINING":
                    action = () => { if (LessonManager.Instance != null) LessonManager.Instance.RestartTraining(); };
                    break;
                case "MAIN MENU":
                    action = () => { if (LessonManager.Instance != null) LessonManager.Instance.ReturnToMenu(); };
                    break;
                case "QUIT APPLICATION":
                    action = () => { if (LessonManager.Instance != null) LessonManager.Instance.QuitApplication(); };
                    break;
            }
            CreateButton(label, pauseButtons, panel.transform, new Vector2(0f, first - i * (height + gap)),
                         new Vector2(width, height), action, 24);
        }
    }

    public void ShowPause()
    {
        pauseOpen = true;
        pauseRoot.gameObject.SetActive(true);
        pauseRoot.SetAsLastSibling();
        RefreshHudChrome();
        SelectFirstButton();
        SyncFocus();
    }

    public void HidePause()
    {
        pauseOpen = false;
        if (pauseRoot != null) pauseRoot.gameObject.SetActive(false);
        currentButtons = new List<Selectable>();
        ClearHover();
        RefreshHudChrome();
        SyncFocus();
    }

    // ------------------------------------------------------------------ //
    // Input for the interface
    // ------------------------------------------------------------------ //

    void SyncFocus()
    {
        PlayerController player = PlayerController.Instance;
        if (player == null) return;
        player.SetUiFocus(AnyOverlayOpen);
    }

    void Update()
    {
        // A headset can be connected or dropped while the game is running; the canvas mode
        // has to follow, otherwise the interface ends up in the wrong space.
        if (XRSettings.isDeviceActive != lastXrState) ApplyRenderMode();

        if (EventSystem.current == null || raycaster == null) return;

        if (Input.GetKeyDown(KeyCode.Escape) && infoOpen) HideMenuInfo();

        bool overlay = AnyOverlayOpen;

        // Which pointer are we highlighting with? The mouse when the cursor is free,
        // otherwise the screen centre (keyboard / VR gaze).
        bool cursorFree = Cursor.lockState != CursorLockMode.Locked;
        Vector2 pointer = cursorFree ? (Vector2)Input.mousePosition
                                     : new Vector2(Screen.width * 0.5f, Screen.height * 0.5f);

        Selectable underPointer = SelectableAt(pointer);
        if (overlay && underPointer != null) SetHover(underPointer);

        if (!overlay)
        {
            ClearHover();
            if (crosshairRing != null) crosshairRing.color = new Color(1f, 0.72f, 0.25f, 0.3f);
            return;
        }

        if (crosshairRing != null)
            crosshairRing.color = hovered != null ? new Color(1f, 0.72f, 0.25f, 0.95f)
                                                  : new Color(1f, 0.72f, 0.25f, 0.3f);

        Navigate();

        bool activate = Input.GetKeyDown(KeyCode.E)
                        || Input.GetKeyDown(KeyCode.Return)
                        || Input.GetKeyDown(KeyCode.KeypadEnter)
                        || Input.GetKeyDown(KeyCode.Space)
                        || (cursorFree && Input.GetMouseButtonDown(0));

        PlayerController player = PlayerController.Instance;
        if (player != null && player.PointerClickPressed) activate = true;

        if (!activate) return;

        Selectable target = underPointer;
        if (target == null && currentButtons.Count > 0)
        {
            int index = Mathf.Clamp(selectedIndex, 0, currentButtons.Count - 1);
            target = currentButtons[index];
        }
        Activate(target);
    }

    /// <summary>Arrow keys / Tab move the highlight between the current buttons.</summary>
    void Navigate()
    {
        if (currentButtons.Count < 2) return;
        if (Time.unscaledTime < nextNavTime) return;

        int step = 0;
        if (Input.GetKeyDown(KeyCode.DownArrow) || Input.GetKeyDown(KeyCode.RightArrow) ||
            Input.GetKeyDown(KeyCode.Tab)) step = 1;
        else if (Input.GetKeyDown(KeyCode.UpArrow) || Input.GetKeyDown(KeyCode.LeftArrow)) step = -1;
        if (step == 0) return;

        nextNavTime = Time.unscaledTime + 0.12f;
        selectedIndex = (selectedIndex + step + currentButtons.Count) % currentButtons.Count;
        SetHover(currentButtons[selectedIndex]);
        if (EventSystem.current != null)
            EventSystem.current.SetSelectedGameObject(currentButtons[selectedIndex].gameObject);
    }

    Selectable SelectableAt(Vector2 screenPosition)
    {
        PointerEventData data = new PointerEventData(EventSystem.current) { position = screenPosition };
        List<RaycastResult> results = new List<RaycastResult>();
        raycaster.Raycast(data, results);
        for (int i = 0; i < results.Count; i++)
        {
            Selectable selectable = results[i].gameObject.GetComponentInParent<Selectable>();
            if (selectable != null && selectable.IsInteractable() && selectable.targetGraphic is Image)
                return selectable;
        }
        return null;
    }

    void Activate(Selectable selectable)
    {
        Button button = selectable as Button;
        if (button == null || !button.IsInteractable()) return;

        if (LessonManager.Instance != null) LessonManager.Instance.PlayPanelSound();

        // Invoking the button's own handler keeps this independent of the EventSystem's
        // input module, which is the part that stopped responding in the Editor.
        ClearHover();
        button.onClick.Invoke();
    }

    public void ClearHover()
    {
        RestoreColour(hovered);
        hovered = null;
    }

    void SetHover(Selectable selectable)
    {
        if (hovered == selectable) return;
        RestoreColour(hovered);
        hovered = selectable;
        if (hovered == null) return;

        int index = currentButtons.IndexOf(hovered);
        if (index >= 0) selectedIndex = index;

        if (hovered.targetGraphic is Image image)
            image.color = buttonHoverColour;
    }

    void RestoreColour(Selectable selectable)
    {
        if (selectable == null) return;
        if (selectable.targetGraphic is Image image)
        {
            ColorBlock colours = selectable.colors;
            image.color = buttonColour * colours.normalColor;
        }
    }
}
