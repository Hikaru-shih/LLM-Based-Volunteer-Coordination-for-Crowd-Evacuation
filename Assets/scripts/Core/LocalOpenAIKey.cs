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
            string key=File.Exists(FilePath) ? File.ReadAllText(FilePath).Trim().TrimStart('\uFEFF') : "";
            if(!HasValidLocalFormat(key))
            {
                Debug.LogWarning("[LLM] Local key file contains whitespace or quotes. Keep only the API key; remote decisions are disabled.");
                return "";
            }
            return key;
        }
        catch (Exception ex) when (ex is IOException || ex is UnauthorizedAccessException)
        {
            Debug.LogWarning("Unable to read local OpenAI key file. Remote LLM decisions are disabled.");
            return "";
        }
    }

    // This is a local format check, not proof that a credential is authorized.
    public static bool HasValidLocalFormat(string key)
    {
        if(string.IsNullOrEmpty(key)) return true;
        if(key.StartsWith("\"") || key.StartsWith("'") || key.EndsWith("\"") || key.EndsWith("'")) return false;
        foreach(char character in key) if(char.IsWhiteSpace(character)) return false;
        return true;
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
