using System.Collections;
using UnityEngine;

/// <summary>
/// The single, small, contained fire used in Section B (a metal bin in the corridor).
///
/// The particle effects are built in code with the built-in particle shaders, so the
/// project needs no imported art and the scene file stays small and easy to inspect.
/// </summary>
public class FireDemo : MonoBehaviour
{
    [Header("Fire visuals (built at runtime when left empty)")]
    public ParticleSystem flames;
    public ParticleSystem embers;
    public ParticleSystem smoke;
    public Light fireLight;

    [Header("Extinguisher")]
    public ParticleSystem discharge;
    public AudioSource audioSource;
    public AudioClip fireClip;
    public AudioClip hissClip;

    [Header("Settings")]
    public float baseLightIntensity = 2.4f;
    public float flameHeight = 0.55f;

    bool burning = true;
    bool extinguished;
    bool discharging;

    public bool IsBurning => burning;
    public bool IsExtinguished => extinguished;

    void Awake()
    {
        if (flames == null) BuildFire();
        if (discharge == null) BuildDischarge();
        audioSource = AudioHelper.Ensure(gameObject, audioSource, true, 0.45f, 1.2f, 14f);
        fireClip = AudioHelper.ClipOrDefault(fireClip, "fire_crackle");
        hissClip = AudioHelper.ClipOrDefault(hissClip, "extinguisher_hiss");

        if (discharge != null)
        {
            ParticleSystem.EmissionModule emission = discharge.emission;
            emission.rateOverTime = 0f;
            discharge.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear);
        }
        if (smoke != null) smoke.Play();
    }

    void Start()
    {
        // The contained fire is already burning when the player arrives; the lesson just
        // draws attention to it later.
        BeginBurning();
    }

    void BuildFire()
    {
        // Flames
        flames = VfxUtil.CreateSystem(transform, "Flames", new Vector3(0f, 0.02f, 0f),
                                      VfxUtil.Additive(new Color(1f, 0.55f, 0.15f, 0.9f)));
        ParticleSystem.MainModule main = flames.main;
        main.startLifetime = new ParticleSystem.MinMaxCurve(0.35f, 0.75f);
        main.startSpeed = new ParticleSystem.MinMaxCurve(0.45f, 1.1f);
        main.startSize = new ParticleSystem.MinMaxCurve(0.16f, 0.34f);
        main.startColor = new ParticleSystem.MinMaxGradient(
            new Color(1f, 0.85f, 0.35f, 0.95f), new Color(1f, 0.35f, 0.05f, 0.9f));
        main.gravityModifier = -0.05f;

        ParticleSystem.EmissionModule emission = flames.emission;
        emission.rateOverTime = 55f;

        ParticleSystem.ShapeModule shape = flames.shape;
        shape.shapeType = ParticleSystemShapeType.Cone;
        shape.radius = 0.22f;
        shape.angle = 12f;
        shape.rotation = new Vector3(-90f, 0f, 0f);

        ParticleSystem.SizeOverLifetimeModule size = flames.sizeOverLifetime;
        size.enabled = true;
        size.size = new ParticleSystem.MinMaxCurve(1f, AnimationCurve.EaseInOut(0f, 1f, 1f, 0.1f));

        ParticleSystem.ColorOverLifetimeModule colour = flames.colorOverLifetime;
        colour.enabled = true;
        colour.color = new ParticleSystem.MinMaxGradient(VfxUtil.FadeGradient(
            new Color(1f, 1f, 0.6f, 1f), new Color(1f, 0.3f, 0.05f, 1f)));

        ParticleSystem.NoiseModule noise = flames.noise;
        noise.enabled = true;
        noise.strength = 0.35f;
        noise.frequency = 1.4f;
        noise.scrollSpeed = 0.6f;

        // Embers
        embers = VfxUtil.CreateSystem(transform, "Embers", new Vector3(0f, 0.15f, 0f),
                                      VfxUtil.Additive(new Color(1f, 0.6f, 0.2f, 0.8f)));
        ParticleSystem.MainModule emberMain = embers.main;
        emberMain.startLifetime = new ParticleSystem.MinMaxCurve(1.2f, 2.4f);
        emberMain.startSpeed = new ParticleSystem.MinMaxCurve(0.5f, 1.6f);
        emberMain.startSize = new ParticleSystem.MinMaxCurve(0.01f, 0.045f);
        emberMain.startColor = new ParticleSystem.MinMaxGradient(new Color(1f, 0.55f, 0.15f, 1f));
        emberMain.gravityModifier = 0.02f;

        ParticleSystem.EmissionModule emberEmission = embers.emission;
        emberEmission.rateOverTime = 10f;
        ParticleSystem.ShapeModule emberShape = embers.shape;
        emberShape.shapeType = ParticleSystemShapeType.Cone;
        emberShape.radius = 0.2f;
        emberShape.angle = 18f;
        emberShape.rotation = new Vector3(-90f, 0f, 0f);

        // Smoke rising from the fire (light, so the teaching point is visible)
        smoke = VfxUtil.CreateSystem(transform, "FireSmoke", new Vector3(0f, 0.5f, 0f),
                                     VfxUtil.Smoke(new Color(0.35f, 0.35f, 0.36f, 0.32f)));
        ParticleSystem.MainModule smokeMain = smoke.main;
        smokeMain.startLifetime = new ParticleSystem.MinMaxCurve(2.5f, 4.5f);
        smokeMain.startSpeed = new ParticleSystem.MinMaxCurve(0.25f, 0.6f);
        smokeMain.startSize = new ParticleSystem.MinMaxCurve(0.3f, 0.8f);
        smokeMain.startColor = new ParticleSystem.MinMaxGradient(new Color(0.45f, 0.45f, 0.46f, 0.28f));
        smokeMain.gravityModifier = -0.03f;

        ParticleSystem.EmissionModule smokeEmission = smoke.emission;
        smokeEmission.rateOverTime = 4f;
        ParticleSystem.ShapeModule smokeShape = smoke.shape;
        smokeShape.shapeType = ParticleSystemShapeType.Cone;
        smokeShape.radius = 0.18f;
        smokeShape.angle = 8f;
        smokeShape.rotation = new Vector3(-90f, 0f, 0f);

        ParticleSystem.SizeOverLifetimeModule smokeSize = smoke.sizeOverLifetime;
        smokeSize.enabled = true;
        smokeSize.size = new ParticleSystem.MinMaxCurve(1f, AnimationCurve.EaseInOut(0f, 0.4f, 1f, 1.5f));

        // Fire light
        GameObject lightObject = new GameObject("FireLight");
        lightObject.transform.SetParent(transform, false);
        lightObject.transform.localPosition = new Vector3(0f, 0.45f, 0f);
        fireLight = lightObject.AddComponent<Light>();
        fireLight.type = LightType.Point;
        fireLight.color = new Color(1f, 0.55f, 0.25f);
        fireLight.range = 6f;
        fireLight.intensity = baseLightIntensity;
        fireLight.shadows = LightShadows.None;
    }

    void BuildDischarge()
    {
        discharge = VfxUtil.CreateSystem(transform, "ExtinguisherSpray", new Vector3(0.35f, 0.55f, 0.1f),
                                         VfxUtil.Additive(new Color(0.85f, 0.9f, 1f, 0.55f)));
        ParticleSystem.MainModule main = discharge.main;
        main.startLifetime = new ParticleSystem.MinMaxCurve(0.25f, 0.5f);
        main.startSpeed = new ParticleSystem.MinMaxCurve(2.4f, 3.4f);
        main.startSize = new ParticleSystem.MinMaxCurve(0.12f, 0.3f);
        main.startColor = new ParticleSystem.MinMaxGradient(new Color(0.92f, 0.95f, 1f, 0.55f));

        ParticleSystem.EmissionModule emission = discharge.emission;
        emission.rateOverTime = 0f;

        ParticleSystem.ShapeModule shape = discharge.shape;
        shape.shapeType = ParticleSystemShapeType.Cone;
        shape.radius = 0.04f;
        shape.angle = 9f;
        // Aim the cone toward the fire (down and to the left of this transform).
        shape.rotation = new Vector3(0f, 0f, 0f);
        discharge.transform.localRotation = Quaternion.Euler(60f, -60f, 0f);
    }

    /// <summary>Start the contained fire (the flames are already visible).</summary>
    public void BeginBurning()
    {
        if (!burning) return;
        if (flames != null && !flames.isPlaying) flames.Play();
        if (embers != null && !embers.isPlaying) embers.Play();
        if (smoke != null && !smoke.isPlaying) smoke.Play();

        if (audioSource != null && fireClip != null && !audioSource.isPlaying)
        {
            audioSource.clip = fireClip;
            audioSource.loop = true;
            audioSource.volume = 0.45f;
            audioSource.spatialBlend = 1f;
            audioSource.minDistance = 1.5f;
            audioSource.maxDistance = 14f;
            audioSource.Play();
        }
    }

    void Update()
    {
        if (!burning || fireLight == null) return;
        float flicker = 0.75f + Mathf.PerlinNoise(Time.time * 6f, 0.3f) * 0.5f;
        fireLight.intensity = baseLightIntensity * flicker * (discharging ? 0.55f : 1f);
    }

    /// <summary>
    /// The controlled PASS demonstration: the spray hits the base of the fire, the flames
    /// shrink and go out, and the light fades.
    /// </summary>
    public void Extinguish()
    {
        if (!burning || discharging) return;
        StartCoroutine(ExtinguishRoutine());
    }

    IEnumerator ExtinguishRoutine()
    {
        discharging = true;

        if (discharge != null)
        {
            ParticleSystem.EmissionModule emission = discharge.emission;
            emission.rateOverTime = 110f;
            discharge.Play();
        }
        if (audioSource != null && hissClip != null)
            audioSource.PlayOneShot(hissClip, 0.8f);

        if (flames != null)
        {
            ParticleSystem.EmissionModule emission = flames.emission;
            emission.rateOverTime = 16f;
        }

        yield return new WaitForSeconds(1.2f);

        if (discharge != null)
        {
            ParticleSystem.EmissionModule emission = discharge.emission;
            emission.rateOverTime = 0f;
        }
        if (flames != null)
        {
            ParticleSystem.EmissionModule emission = flames.emission;
            emission.rateOverTime = 0f;
            flames.Stop(true, ParticleSystemStopBehavior.StopEmitting);
        }
        if (embers != null) embers.Stop(true, ParticleSystemStopBehavior.StopEmitting);
        if (smoke != null)
        {
            ParticleSystem.EmissionModule emission = smoke.emission;
            emission.rateOverTime = 0f;
            smoke.Stop(true, ParticleSystemStopBehavior.StopEmitting);
        }

        burning = false;

        if (fireLight != null)
        {
            float start = fireLight.intensity;
            float t = 0f;
            while (t < 1f)
            {
                t += Time.deltaTime * 2f;
                fireLight.intensity = Mathf.Lerp(start, 0f, t);
                yield return null;
            }
            fireLight.enabled = false;
        }

        if (audioSource != null) audioSource.Stop();
        discharging = false;
        extinguished = true;
    }
}
