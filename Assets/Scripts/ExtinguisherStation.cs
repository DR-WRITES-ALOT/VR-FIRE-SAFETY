using System.Collections;
using UnityEngine;

/// <summary>
/// The extinguisher practice station next to the contained fire.
///
/// It does not ask the player to press "next" four times. One interaction starts a real,
/// animated PASS demonstration on the model itself:
///   1. the safety pin pulls out and drops onto the table,
///   2. the valve, hose and horn turn until the horn points at the base of the fire,
///   3. the lever is squeezed, the powder jet starts and the hiss plays,
///   4. the jet sweeps across the base of the fire until the flames go out.
/// Each step is announced on screen, so the four PASS actions are learned by watching them
/// happen, exactly as an instructor would demonstrate them.
/// </summary>
public class ExtinguisherStation : InteractableBase
{
    [Header("Scene references")]
    public FireDemo fire;

    [Tooltip("Valve, hose and horn assembly that turns to aim and sweep.")]
    public Transform head;
    public Transform lever;
    public Transform pin;
    [Tooltip("Empty at the horn mouth whose +Z axis points at the fire.")]
    public Transform sprayOrigin;

    [Header("Poses (degrees)")]
    public Vector3 headStowed = new Vector3(0f, -34f, 0f);
    public Vector3 headAimed = new Vector3(0f, 0f, -10f);
    public float sweepDegrees = 13f;
    public float leverPressedAngle = -30f;

    [Header("State")]
    [Tooltip("Only available once the lesson reaches the PASS practice step.")]
    public bool practiceActive;

    [Header("Feedback")]
    public AudioSource audioSource;
    public AudioClip hissClip;

    ParticleSystem spray;
    bool playing;
    bool sprayStopped;
    bool demoFinished;

    Vector3 pinStart;
    Quaternion pinStartRotation = Quaternion.identity;
    Quaternion leverHome = Quaternion.identity;

    public override bool IsAvailable => !playing && base.IsAvailable;

    public override string InteractionPrompt
    {
        get
        {
            if (playing) return "PASS demonstration in progress";
            if (demoFinished) return "PASS demonstration complete";
            if (practiceActive) return "Start the PASS demonstration";
            return "Extinguisher station - the PASS step comes later";
        }
    }

    protected override void Awake()
    {
        base.Awake();

        if (pin != null)
        {
            pinStart = pin.localPosition;
            pinStartRotation = pin.localRotation;
        }
        if (lever != null) leverHome = lever.localRotation;

        BuildSpray();
        if (head != null) head.localRotation = Quaternion.Euler(headStowed);
        if (lever != null) lever.localRotation = leverHome;
    }

    void Start()
    {
        audioSource = AudioHelper.Ensure(gameObject, audioSource, true, 0.5f, 1.5f, 12f);
        hissClip = AudioHelper.ClipOrDefault(hissClip, "extinguisher_hiss");
    }

    // ------------------------------------------------------------------ //
    // The demonstration
    // ------------------------------------------------------------------ //

    public override void Interact(PlayerController player)
    {
        if (playing) return;

        if (demoFinished)
        {
            if (LessonUI.Instance != null)
            {
                LessonUI.Instance.ShowPanel("PASS - what you just watched",
                    "1  <b>PULL</b> the safety pin.\n" +
                    "2  <b>AIM</b> the horn at the base of the fire - the fuel, not the flames.\n" +
                    "3  <b>SQUEEZE</b> the lever to discharge.\n" +
                    "4  <b>SWEEP</b> slowly across the base until the flames are out.\n\n" +
                    "A portable extinguisher gives only a few seconds of powder. If the fire is " +
                    "not out by then, leave immediately and let the fire service take over.",
                    "Small, contained fires only - and only with a clear exit behind you.",
                    new[] { "Close" }, new System.Action[] { null });
            }
            return;
        }

        if (!practiceActive)
        {
            // Never leave a click unanswered: explain when this unit is used.
            if (LessonUI.Instance != null)
            {
                LessonUI.Instance.ShowPanel("Extinguisher practice station",
                    "This is the single practice unit for the lesson - an ABC dry powder " +
                    "extinguisher, the most common type in Indian buildings.\n\n" +
                    "It is used later, during the PASS demonstration, after the extinguisher " +
                    "types and safety rules have been covered.",
                    "A fire extinguisher is only for small, contained fires.",
                    new[] { "Close" }, new System.Action[] { null });
            }
            return;
        }

        StartCoroutine(DemoRoutine());
    }

    IEnumerator DemoRoutine()
    {
        playing = true;
        sprayStopped = false;

        Caption("1 of 4   PULL the safety pin");
        yield return PullPinRoutine();

        Caption("2 of 4   AIM at the base of the fire");
        yield return RotateRoutine(head, Quaternion.Euler(headStowed),
                                  Quaternion.Euler(headAimed), 1.2f);

        Caption("3 of 4   SQUEEZE the lever");
        yield return RotateRoutine(lever,
                                   leverHome,
                                   leverHome * Quaternion.Euler(0f, 0f, leverPressedAngle),
                                   0.3f);
        StartSpray();
        yield return new WaitForSeconds(0.7f);

        Caption("4 of 4   SWEEP across the base");
        yield return SweepRoutine(3.2f);

        StopSpray();
        Caption("Fire out - PASS complete");

        yield return new WaitForSeconds(1.2f);

        Caption(string.Empty);
        practiceActive = false;
        demoFinished = true;
        playing = false;
        NotifyLesson("pass_complete");
    }

    IEnumerator PullPinRoutine()
    {
        if (pin == null)
        {
            yield return new WaitForSeconds(0.5f);
            yield break;
        }

        // Pull straight out of the valve, then let the pin fall onto the table top.
        Vector3 outPosition = pinStart + new Vector3(0f, 0.06f, -0.12f);
        float t = 0f;
        while (t < 1f)
        {
            t += Time.deltaTime / 0.45f;
            pin.localPosition = Vector3.Lerp(pinStart, outPosition, Mathf.SmoothStep(0f, 1f, t));
            yield return null;
        }

        // Detach so the falling pin is not carried away when the head turns to aim.
        pin.SetParent(transform, true);
        Vector3 from = pin.position;
        Vector3 to = new Vector3(from.x, transform.position.y + 0.5f, from.z);
        t = 0f;
        while (t < 1f)
        {
            t += Time.deltaTime / 0.55f;
            float ease = t * t;
            pin.position = Vector3.Lerp(from, to, Mathf.Clamp01(ease));
            pin.Rotate(0f, 0f, -220f * Time.deltaTime, Space.Self);
            yield return null;
        }
    }

    IEnumerator RotateRoutine(Transform target, Quaternion from, Quaternion to, float duration)
    {
        if (target == null)
        {
            yield return new WaitForSeconds(duration);
            yield break;
        }

        float t = 0f;
        while (t < 1f)
        {
            t += Time.deltaTime / Mathf.Max(0.01f, duration);
            target.localRotation = Quaternion.Slerp(from, to, Mathf.SmoothStep(0f, 1f, t));
            yield return null;
        }
        target.localRotation = to;
    }

    IEnumerator SweepRoutine(float duration)
    {
        if (fire != null) fire.Douse(duration * 0.75f);

        float t = 0f;
        while (t < duration)
        {
            t += Time.deltaTime;
            float phase = Mathf.Clamp01(t / duration);
            // One and a half sweeps across the base while the powder knocks the fire down.
            float yaw = Mathf.Sin(phase * Mathf.PI * 3f) * sweepDegrees;
            if (head != null)
                head.localRotation = Quaternion.Euler(headAimed.x,
                                                      headAimed.y + yaw,
                                                      headAimed.z);
            if (!sprayStopped && t > duration * 0.7f)
            {
                StopSpray();
                sprayStopped = true;
            }
            yield return null;
        }
        if (head != null) head.localRotation = Quaternion.Euler(headAimed);
    }

    // ------------------------------------------------------------------ //
    // Spray effect
    // ------------------------------------------------------------------ //

    void BuildSpray()
    {
        Transform parent = sprayOrigin != null ? sprayOrigin : transform;
        Material material = VfxUtil.Smoke(new Color(0.96f, 0.96f, 0.97f, 0.55f));
        spray = VfxUtil.CreateSystem(parent, "PASS_Spray", Vector3.zero, material);

        ParticleSystem.MainModule main = spray.main;
        main.startLifetime = new ParticleSystem.MinMaxCurve(0.55f, 0.95f);
        main.startSpeed = new ParticleSystem.MinMaxCurve(2.3f, 3.3f);
        main.startSize = new ParticleSystem.MinMaxCurve(0.05f, 0.16f);
        main.startColor = new ParticleSystem.MinMaxGradient(
            new Color(0.97f, 0.97f, 0.98f, 0.55f), new Color(0.84f, 0.86f, 0.9f, 0.35f));
        main.gravityModifier = 0.2f;

        ParticleSystem.EmissionModule emission = spray.emission;
        emission.rateOverTime = 0f;

        ParticleSystem.ShapeModule shape = spray.shape;
        shape.shapeType = ParticleSystemShapeType.Cone;
        shape.radius = 0.03f;
        shape.angle = 7f;
        shape.rotation = Vector3.zero;

        ParticleSystem.SizeOverLifetimeModule size = spray.sizeOverLifetime;
        size.enabled = true;
        size.size = new ParticleSystem.MinMaxCurve(1f, AnimationCurve.EaseInOut(0f, 0.6f, 1f, 1.9f));

        ParticleSystem.ColorOverLifetimeModule colour = spray.colorOverLifetime;
        colour.enabled = true;
        colour.color = new ParticleSystem.MinMaxGradient(
            VfxUtil.FadeGradient(Color.white, Color.white));

        spray.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear);
    }

    void StartSpray()
    {
        if (spray == null) return;
        ParticleSystem.EmissionModule emission = spray.emission;
        emission.rateOverTime = 90f;
        spray.Play();

        if (audioSource != null && hissClip != null)
            audioSource.PlayOneShot(hissClip, 0.9f);
    }

    void StopSpray()
    {
        if (spray == null) return;
        ParticleSystem.EmissionModule emission = spray.emission;
        emission.rateOverTime = 0f;
        spray.Stop(true, ParticleSystemStopBehavior.StopEmitting);
    }

    static void Caption(string text)
    {
        if (LessonUI.Instance != null) LessonUI.Instance.SetCaption(text);
    }

    // ------------------------------------------------------------------ //
    // Reset
    // ------------------------------------------------------------------ //

    /// <summary>Stop the demonstration and put every part back (used by Restart / Main menu).</summary>
    public void ResetStation()
    {
        StopAllCoroutines();
        playing = false;
        practiceActive = false;
        demoFinished = false;
        sprayStopped = false;
        StopSpray();

        if (head != null) head.localRotation = Quaternion.Euler(headStowed);
        if (lever != null) lever.localRotation = leverHome;
        if (pin != null)
        {
            if (head != null && pin.parent != head) pin.SetParent(head, false);
            pin.localPosition = pinStart;
            pin.localRotation = pinStartRotation;
        }
        if (LessonUI.Instance != null) LessonUI.Instance.SetCaption(string.Empty);
    }
}
