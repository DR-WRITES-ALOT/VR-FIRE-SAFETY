using UnityEngine;

/// <summary>
/// Small helpers that build lightweight particle effects at runtime.
/// Building them in code keeps the scene file small and means there are no imported
/// art dependencies: everything uses the built-in legacy particle shaders.
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

    static Material CreateMaterial(string shaderName, Color tint, float softness)
    {
        Shader shader = Shader.Find(shaderName);
        if (shader == null) shader = Shader.Find("Particles/Standard Unlit");
        if (shader == null) shader = Shader.Find("Sprites/Default");
        Material material = new Material(shader) { name = shaderName + " (runtime)" };
        material.mainTexture = SoftCircle();
        if (material.HasProperty("_TintColor")) material.SetColor("_TintColor", tint);
        if (material.HasProperty("_Color")) material.SetColor("_Color", tint);
        if (material.HasProperty("_SoftParticlesNearFadeDistance")) material.SetFloat("_SoftParticlesNearFadeDistance", softness);
        return material;
    }

    public static Material Additive(Color tint)
    {
        return CreateMaterial("Legacy Shaders/Particles/Additive", tint, 0f);
    }

    public static Material Smoke(Color tint)
    {
        return CreateMaterial("Legacy Shaders/Particles/Alpha Blended", tint, 0f);
    }

    public static ParticleSystem CreateSystem(Transform parent, string name, Vector3 localPosition, Material material)
    {
        GameObject go = new GameObject(name);
        go.transform.SetParent(parent, false);
        go.transform.localPosition = localPosition;

        ParticleSystem system = go.AddComponent<ParticleSystem>();
        ParticleSystemRenderer renderer = go.GetComponent<ParticleSystemRenderer>();
        renderer.material = material;
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
