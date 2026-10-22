using UnityEngine;
using UnityEngine.Rendering;

/// <summary>
/// Small helpers that build lightweight particle effects at runtime.
/// Building them in code keeps the scene file small and means there are no imported
/// art dependencies: everything uses Unity's built-in particle shaders, with a fallback
/// chain so the effects still look right on newer editor versions.
/// </summary>
public static class VfxUtil
{
    static Texture2D softCircle;

    public static Texture2D SoftCircle()
    {
        if (softCircle != null) return softCircle;
        const int size = 64;
        softCircle = new Texture2D(size, size, TextureFormat.RGBA32, false);
        softCircle.wrapMode = TextureWrapMode.Clamp;
        Color[] pixels = new Color[size * size];
        Vector2 centre = new Vector2((size - 1) * 0.5f, (size - 1) * 0.5f);
        for (int y = 0; y < size; y++)
        {
            for (int x = 0; x < size; x++)
            {
                float distance = Vector2.Distance(new Vector2(x, y), centre) / (size * 0.5f);
                float alpha = Mathf.Clamp01(1f - distance);
                alpha = alpha * alpha;
                pixels[y * size + x] = new Color(1f, 1f, 1f, alpha);
            }
        }
        softCircle.SetPixels(pixels);
        softCircle.Apply();
        softCircle.name = "RuntimeSoftCircle";
        return softCircle;
    }

    static Material CreateMaterial(string shaderName, Color tint, bool additive)
    {
        // Shader names differ between Unity versions and between the built-in and
        // scriptable render pipelines, so try the preferred one and then fall back.
        // If the legacy particle shaders are unavailable, the standard particle shader
        // is configured explicitly so the effect still renders transparent.
        string[] candidates = additive
            ? new[] { shaderName, "Particles/Standard Unlit",
                      "Legacy Shaders/Particles/Additive", "Sprites/Default" }
            : new[] { shaderName, "Particles/Standard Unlit",
                      "Legacy Shaders/Particles/Alpha Blended", "Sprites/Default" };

        Shader shader = null;
        for (int i = 0; i < candidates.Length && shader == null; i++)
            shader = Shader.Find(candidates[i]);
        if (shader == null)
        {
            Debug.LogWarning("[Fire Safety] No particle shader was found; particle effects may not render.");
            return null;
        }

        Material material = new Material(shader) { name = shaderName + " (runtime)" };
        material.mainTexture = SoftCircle();

        if (material.HasProperty("_TintColor")) material.SetColor("_TintColor", tint);
        if (material.HasProperty("_Color")) material.SetColor("_Color", tint);

        // Explicit blend state: works for both the legacy and the standard particle shaders.
        if (material.HasProperty("_Mode")) material.SetFloat("_Mode", additive ? 4f : 2f);
        if (material.HasProperty("_SrcBlend")) material.SetInt("_SrcBlend", (int)BlendMode.SrcAlpha);
        if (material.HasProperty("_DstBlend"))
            material.SetInt("_DstBlend", (int)(additive ? BlendMode.One : BlendMode.OneMinusSrcAlpha));
        if (material.HasProperty("_ZWrite")) material.SetInt("_ZWrite", 0);
        material.EnableKeyword("_ALPHABLEND_ON");
        material.SetOverrideTag("RenderType", "Transparent");
        material.renderQueue = (int)RenderQueue.Transparent;

        return material;
    }

    public static Material Additive(Color tint)
    {
        return CreateMaterial("Legacy Shaders/Particles/Additive", tint, true);
    }

    public static Material Smoke(Color tint)
    {
        return CreateMaterial("Legacy Shaders/Particles/Alpha Blended", tint, false);
    }

    public static ParticleSystem CreateSystem(Transform parent, string name, Vector3 localPosition, Material material)
    {
        GameObject go = new GameObject(name);
        go.transform.SetParent(parent, false);
        go.transform.localPosition = localPosition;

        ParticleSystem system = go.AddComponent<ParticleSystem>();
        ParticleSystemRenderer renderer = go.GetComponent<ParticleSystemRenderer>();
        if (material != null) renderer.material = material;
        renderer.renderMode = ParticleSystemRenderMode.Billboard;
        renderer.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
        renderer.receiveShadows = false;
        renderer.sortingFudge = 0.5f;

        ParticleSystem.MainModule main = system.main;
        main.playOnAwake = false;
        main.loop = true;
        main.simulationSpace = ParticleSystemSimulationSpace.World;
        main.scalingMode = ParticleSystemScalingMode.Hierarchy;

        system.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear);
        return system;
    }

    public static Gradient FadeGradient(Color start, Color end)
    {
        Gradient gradient = new Gradient();
        gradient.SetKeys(
            new[] { new GradientColorKey(start, 0f), new GradientColorKey(end, 1f) },
            new[] { new GradientAlphaKey(start.a, 0f), new GradientAlphaKey(start.a, 0.15f), new GradientAlphaKey(0f, 1f) });
        return gradient;
    }
}
