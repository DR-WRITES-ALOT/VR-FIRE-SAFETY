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

    static Material CreateMaterial(string legacyName, Color tint, bool additive)
    {
        // The project renders with URP, but the same code should still work if a user
        // switches back to the Built-in pipeline, so try the URP particle shader first
        // and fall back through the other names Unity has shipped over the years.
        string[] candidates =
        {
            "Universal Render Pipeline/Particles/Unlit",
            "Universal Render Pipeline/Particles/Lit",
            legacyName,
            "Legacy Shaders/Particles/Additive",
            "Particles/Standard Unlit",
            "Sprites/Default",
        };

        Shader shader = null;
        for (int i = 0; i < candidates.Length && shader == null; i++)
            shader = Shader.Find(candidates[i]);
        if (shader == null)
        {
            Debug.LogWarning("[Fire Safety] No particle shader was found; particle effects may not render.");
            return null;
        }

        Material material = new Material(shader) { name = shader.name + " (runtime)" };
        Texture2D circle = SoftCircle();
        if (material.HasProperty("_BaseMap")) material.SetTexture("_BaseMap", circle);
        if (material.HasProperty("_MainTex")) material.SetTexture("_MainTex", circle);
        material.mainTexture = circle;

        // Tint: URP particle shaders use _BaseColor, the older ones use _TintColor/_Color.
        if (material.HasProperty("_BaseColor")) material.SetColor("_BaseColor", tint);
        if (material.HasProperty("_TintColor")) material.SetColor("_TintColor", tint);
        if (material.HasProperty("_Color")) material.SetColor("_Color", tint);
        // 0 = multiply vertex colour (the default for URP particle shaders)
        if (material.HasProperty("_ColorMode")) material.SetFloat("_ColorMode", 0f);

        // Explicit transparent state, so softening works with either shader family.
        if (material.HasProperty("_Surface")) material.SetFloat("_Surface", 1f);
        if (material.HasProperty("_Blend")) material.SetFloat("_Blend", 0f);
        if (material.HasProperty("_SrcBlend")) material.SetInt("_SrcBlend", (int)BlendMode.SrcAlpha);
        if (material.HasProperty("_DstBlend"))
            material.SetInt("_DstBlend", (int)(additive ? BlendMode.One : BlendMode.OneMinusSrcAlpha));
        if (material.HasProperty("_SrcBlendAlpha")) material.SetInt("_SrcBlendAlpha", (int)BlendMode.One);
        if (material.HasProperty("_DstBlendAlpha"))
            material.SetInt("_DstBlendAlpha", (int)BlendMode.OneMinusSrcAlpha);
        if (material.HasProperty("_ZWrite")) material.SetInt("_ZWrite", 0);
        if (material.HasProperty("_Cull")) material.SetInt("_Cull", (int)CullMode.Off);

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
