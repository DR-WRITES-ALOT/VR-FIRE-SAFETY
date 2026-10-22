using System.Collections;
using UnityEngine;

/// <summary>
/// The single smoke hazard in the second corridor.
///
/// It builds its own lightweight particle effects at runtime (no imported art) and a
/// trigger volume that stops the player from walking into dense smoke. Closing the store
/// room fire door lets the smoke clear and opens the way.
/// </summary>
public class CorridorSmoke : MonoBehaviour
{
    [Header("Volume")]
    [Tooltip("Width (x), height (y) and length (z) of the smoke block.")]
    public Vector3 size = new Vector3(3.8f, 2.6f, 4.5f);

    [Tooltip("Particles per second per emitter.")]
    public float density = 9f;

    [Header("Behaviour")]
    [Tooltip("Where the player is placed if they walk into the smoke.")]
    public Transform safePoint;

    public bool blocksPlayer = true;

    readonly System.Collections.Generic.List<ParticleSystem> systems = new System.Collections.Generic.List<ParticleSystem>();
    BoxCollider hazardCollider;
    bool cleared;

    public bool IsCleared => cleared;

    void Awake()
    {
        BuildSmoke();
        BuildHazardVolume();
    }

    void Start()
    {
        Play();
    }

    void BuildSmoke()
    {
        Material material = VfxUtil.Smoke(new Color(0.72f, 0.72f, 0.74f, 0.42f));
        material.renderQueue = 3000;

        for (int i = 0; i < 4; i++)
        {
            Vector3 offset = new Vector3(
                Random.Range(-size.x * 0.28f, size.x * 0.28f),
                Random.Range(0.2f, size.y * 0.55f),
                Random.Range(-size.z * 0.35f, size.z * 0.35f));

            ParticleSystem system = VfxUtil.CreateSystem(transform, "Smoke" + (i + 1), offset, material);
            ParticleSystem.MainModule main = system.main;
            main.startLifetime = new ParticleSystem.MinMaxCurve(3.5f, 6.5f);
            main.startSpeed = new ParticleSystem.MinMaxCurve(0.15f, 0.55f);
            main.startSize = new ParticleSystem.MinMaxCurve(size.y * 0.55f, size.y * 0.95f);
            main.startRotation = new ParticleSystem.MinMaxCurve(0f, Mathf.PI * 2f);
            main.startColor = new ParticleSystem.MinMaxGradient(
                new Color(0.70f, 0.70f, 0.72f, 0.34f), new Color(0.38f, 0.38f, 0.40f, 0.46f));
            main.gravityModifier = -0.015f;

            ParticleSystem.EmissionModule emission = system.emission;
            emission.rateOverTime = density;

            ParticleSystem.ShapeModule shape = system.shape;
            shape.enabled = true;
            shape.shapeType = ParticleSystemShapeType.Box;
            shape.scale = new Vector3(size.x * 0.75f, 0.4f, size.z * 0.7f);

            // All three axes must use the same curve mode. Setting only x and z left y in
            // the default Constant mode, which Unity reports as
            // "Particle Velocity curves must all be in the same mode".
            ParticleSystem.VelocityOverLifetimeModule velocity = system.velocityOverLifetime;
            velocity.enabled = true;
            velocity.x = new ParticleSystem.MinMaxCurve(-0.12f, 0.4f);
            velocity.y = new ParticleSystem.MinMaxCurve(-0.05f, 0.05f);
            velocity.z = new ParticleSystem.MinMaxCurve(-0.15f, 0.15f);
            velocity.space = ParticleSystemSimulationSpace.Local;

            ParticleSystem.RotationOverLifetimeModule rotation = system.rotationOverLifetime;
            rotation.enabled = true;
            rotation.x = new ParticleSystem.MinMaxCurve(0f, 0f);
            rotation.y = new ParticleSystem.MinMaxCurve(0f, 0f);
            rotation.z = new ParticleSystem.MinMaxCurve(-0.15f, 0.15f);

            ParticleSystem.ColorOverLifetimeModule colour = system.colorOverLifetime;
            colour.enabled = true;
            colour.color = new ParticleSystem.MinMaxGradient(VfxUtil.FadeGradient(
                new Color(1f, 1f, 1f, 1f), new Color(1f, 1f, 1f, 1f)));

            ParticleSystem.SizeOverLifetimeModule sizeOverLife = system.sizeOverLifetime;
            sizeOverLife.enabled = true;
            sizeOverLife.size = new ParticleSystem.MinMaxCurve(1f, AnimationCurve.EaseInOut(0f, 0.55f, 1f, 1.25f));

            systems.Add(system);
        }
    }

    void BuildHazardVolume()
    {
        if (!blocksPlayer) return;
        GameObject volume = new GameObject("SmokeHazardVolume");
        volume.transform.SetParent(transform, false);
        volume.transform.localPosition = new Vector3(0f, size.y * 0.45f, 0f);

        hazardCollider = volume.AddComponent<BoxCollider>();
        hazardCollider.isTrigger = true;
        hazardCollider.size = new Vector3(size.x, size.y * 0.9f, size.z);

        HazardZone zone = volume.AddComponent<HazardZone>();
        zone.safePoint = safePoint;
    }

    public void Play()
    {
        cleared = false;
        if (hazardCollider != null) hazardCollider.enabled = true;
        for (int i = 0; i < systems.Count; i++)
        {
            ParticleSystem.EmissionModule emission = systems[i].emission;
            emission.rateOverTime = density;
            systems[i].Play();
        }
    }

    /// <summary>Fade the smoke away and stop it blocking the player.</summary>
    public void Clear()
    {
        if (cleared) return;
        cleared = true;
        if (hazardCollider != null) hazardCollider.enabled = false;
        StopAllCoroutines();
        StartCoroutine(FadeRoutine());
    }

    IEnumerator FadeRoutine()
    {
        float t = 1f;
        while (t > 0f)
        {
            t -= Time.deltaTime / 3f;
            for (int i = 0; i < systems.Count; i++)
            {
                ParticleSystem.EmissionModule emission = systems[i].emission;
                emission.rateOverTime = 0f;
            }
            yield return null;
        }

        for (int i = 0; i < systems.Count; i++)
            systems[i].Stop(true, ParticleSystemStopBehavior.StopEmitting);
    }

    void OnDrawGizmosSelected()
    {
        Gizmos.color = new Color(0.9f, 0.3f, 0.2f, 0.25f);
        Gizmos.DrawCube(transform.position + Vector3.up * size.y * 0.45f, size);
    }
}
