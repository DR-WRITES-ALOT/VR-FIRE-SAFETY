using UnityEngine;

/// <summary>
/// Small helper that creates audio sources in code and can fall back to clips stored in
/// Assets/Resources/Audio. This keeps the scene file free of fragile audio components and
/// means the project still makes sound if a reference is ever lost.
/// </summary>
public static class AudioHelper
{
    public static AudioClip Load(string clipName)
    {
        if (string.IsNullOrEmpty(clipName)) return null;
        return Resources.Load<AudioClip>("Audio/" + clipName);
    }

    public static AudioClip ClipOrDefault(AudioClip clip, string fallbackName)
    {
        return clip != null ? clip : Load(fallbackName);
    }

    public static AudioSource Ensure(GameObject host, AudioSource existing, bool spatial,
                                     float volume, float minDistance = 1.5f, float maxDistance = 22f,
                                     bool loop = false)
    {
        AudioSource source = existing;
        if (source == null)
        {
            source = host.GetComponent<AudioSource>();
            if (source == null) source = host.AddComponent<AudioSource>();
        }

        source.playOnAwake = false;
        source.loop = loop;
        source.volume = volume;
        source.spatialBlend = spatial ? 1f : 0f;
        source.rolloffMode = AudioRolloffMode.Linear;
        source.minDistance = minDistance;
        source.maxDistance = maxDistance;
        source.dopplerLevel = 0f;
        return source;
    }
}
