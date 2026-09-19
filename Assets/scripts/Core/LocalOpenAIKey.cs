using System;
using System.IO;
using UnityEngine;

public static class LocalOpenAIKey
{
    // Keep credentials outside Assets so Unity does not package them in builds.
    public static string FilePath => Path.Combine(
        Application.isEditor ? Path.GetDirectoryName(Application.dataPath) : Application.persistentDataPath,
        "openai-key.local.txt");

    public static string Load()
    {
        try
        {
            return File.Exists(FilePath) ? File.ReadAllText(FilePath).Trim() : "";
        }
        catch (Exception ex) when (ex is IOException || ex is UnauthorizedAccessException)
        {
            Debug.LogWarning("Unable to read local OpenAI key file. Remote LLM decisions are disabled.");
            return "";
        }
    }

    public static void Save(string key)
    {
        try
        {
            Directory.CreateDirectory(Path.GetDirectoryName(FilePath));
            File.WriteAllText(FilePath, (key ?? "").Trim());
            PlayerPrefs.DeleteKey("sim.openAIKey");
        }
        catch (Exception ex) when (ex is IOException || ex is UnauthorizedAccessException)
        {
            Debug.LogError("Unable to save local OpenAI key file. Check directory permissions.");
        }
    }
}
