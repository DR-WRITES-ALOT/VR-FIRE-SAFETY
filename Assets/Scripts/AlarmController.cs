using UnityEngine;

/// <summary>
/// The wall-mounted fire alarm call point.
/// Raises the alarm: sound, flashing light and the lesson event that unlocks Section A.
/// </summary>
public class AlarmController : InteractableBase
{
    [Header("Sound")]
    public AudioSource alarmAudio;

    [Header("Visuals")]
    public Light strobeLight;
    public Renderer strobeRenderer;

    [Header("Settings")]
    public float lightPulseSpeed = 6f;
    public float lightMinIntensity = 0.2f;
    public float lightMaxIntensity = 3.2f;
    public Color strobeColour = new Color(1f, 0.12f, 0.08f);

    public bool AlarmActive { get; private set; }

    MaterialPropertyBlock block;
    Color baseEmission = Color.black;

    public override string InteractionPrompt =>
        AlarmActive ? "Alarm already sounding" : "Raise the fire alarm";

    public override bool IsAvailable => !AlarmActive && base.IsAvailable;

    protected override void Awake()
    {
        base.Awake();
        if (strobeRenderer != null)
        {
            block = new MaterialPropertyBlock();
            strobeRenderer.GetPropertyBlock(block);
            if (strobeRenderer.sharedMaterial != null &&
                strobeRenderer.sharedMaterial.HasProperty("_EmissionColor"))
            {
                baseEmission = strobeRenderer.sharedMaterial.GetColor("_EmissionColor");
            }
        }
        alarmAudio = AudioHelper.Ensure(gameObject, alarmAudio, true, 0.45f, 1f, 40f, true);
        alarmAudio.clip = AudioHelper.ClipOrDefault(alarmAudio.clip, "alarm_loop");

        ApplyStrobe(0f);
        if (strobeLight != null) strobeLight.enabled = false;
    }

    public override void Interact(PlayerController player)
    {
        RaiseAlarm();
    }

    /// <summary>Starts the alarm. Safe to call more than once.</summary>
    public void RaiseAlarm()
    {
        if (AlarmActive) return;
        AlarmActive = true;

        if (alarmAudio != null && alarmAudio.clip != null)
        {
            alarmAudio.loop = true;
            alarmAudio.Play();
        }
        if (strobeLight != null)
        {
            strobeLight.enabled = true;
            strobeLight.color = strobeColour;
        }

        if (LessonUI.Instance != null)
            LessonUI.Instance.ShowWarning("FIRE ALARM ACTIVATED - EVACUATE USING THE STAIRS", 5f);

        NotifyLesson("alarm");
    }

    protected override void Update()
    {
        base.Update();
        if (!AlarmActive) return;

        float pulse = (Mathf.Sin(Time.time * lightPulseSpeed) + 1f) * 0.5f;
        ApplyStrobe(pulse);

        if (strobeLight != null)
        {
            strobeLight.intensity = Mathf.Lerp(lightMinIntensity, lightMaxIntensity, pulse);
            strobeLight.enabled = true;
        }
    }

    void ApplyStrobe(float amount)
    {
        if (strobeRenderer == null) return;
        if (block == null) block = new MaterialPropertyBlock();
        strobeRenderer.GetPropertyBlock(block);
        Color emission = Color.Lerp(baseEmission, strobeColour * 2.2f, amount);
        block.SetColor("_EmissionColor", emission);
        strobeRenderer.SetPropertyBlock(block);
    }
}
