using System;
using System.IO;
using UnityEngine;

/// <summary>Synthetic export checks only. No network or evacuation stepping.</summary>
public static class AutomaticExperimentLogValidation
{
    public static void Run()
    {
        string root=Path.Combine(Path.GetTempPath(),"notebook-contract-"+Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(root);
        SimulationManager manager=null;
        try
        {
            string records=Path.Combine(root,"records"),stage=Path.Combine(root,"stage");
            Directory.CreateDirectory(records);
            File.WriteAllText(Path.Combine(records,"EXPERIMENT_LOG.md"),"# Existing notebook\n\nHandwritten observation.\n");
            var data=new SimulationData("test",1,stage,"synthetic-not-a-research-run",records,"Check automatic recording");
            data.SetRunMetadata(JsonUtility.ToJson(new ResearchRunConfiguration {scenario="OpenRoom",volunteerPolicy="NoVolunteers",
                actualAgents=1,maxSteps=10,seed=123,conditionKey="synthetic"}));
            data.SetSimulationParameters(3,1,5,1,1,0);
            data.SetTermination("timeout");data.SetSimulationStats(10,3);
            data.ExportData();data.ExportData();
            string notebook=File.ReadAllText(Path.Combine(records,"EXPERIMENT_LOG.md"));
            if(!notebook.Contains("Handwritten observation.") || !notebook.Contains("T100 not observed") || !notebook.Contains("Check automatic recording"))
                throw new Exception("Notebook content/preservation failed");
            if(Directory.GetFiles(Path.Combine(records,"entries"),"*.json").Length!=1 ||
                File.ReadAllLines(Path.Combine(records,"RUN_CATALOG.csv")).Length!=2)
                throw new Exception("Repeated export duplicated notebook/index entries");
            var entry=JsonUtility.FromJson<AutomaticExperimentRecord>(File.ReadAllText(Directory.GetFiles(Path.Combine(records,"entries"),"*.json")[0]));
            if(Directory.GetFiles(Path.Combine(records,entry.dataDirectory),"*_global.csv").Length!=1)
                throw new Exception("Raw artifacts were not archived");
            var pending=new SimulationData("test",1,null,"synthetic-pending-test",records,"Check pending-entry recovery");
            pending.SetRunMetadata(JsonUtility.ToJson(new ResearchRunConfiguration {scenario="OpenRoom",volunteerPolicy="NoVolunteers",actualAgents=1}));
            pending.SetSimulationParameters(3,1,5,1,1,0);pending.SetTermination("interrupted_test");
            using(var locked=new FileStream(Path.Combine(records,".notebook.lock"),FileMode.Open,FileAccess.ReadWrite,FileShare.None))
                pending.ExportData();
            if(AutomaticExperimentLog.RecoverPending(records)!=1 ||
                Directory.GetFiles(Path.Combine(records,"data","auto"),"*_notebook_pending.json",SearchOption.AllDirectories).Length!=0)
                throw new Exception("Pending notebook entry was not recovered");
            manager=ResearchValidation.CreateManager(Path.Combine(root,"interrupted-stage"));
            manager.recordExperimentsAutomatically=true;manager.experimentRecordsRootOverride=records;
            manager.experimentPurpose="Check interruption recording";
            ResearchValidation.Begin(manager);manager.ResetSimulation();
            notebook=File.ReadAllText(Path.Combine(records,"EXPERIMENT_LOG.md"));
            if(!notebook.Contains("interrupted_manual_reset") || Directory.GetFiles(Path.Combine(records,"entries"),"*.json").Length!=3)
                throw new Exception("Interrupted execution missing from notebook");
            Debug.Log("AUTOMATIC_EXPERIMENT_LOG_VALIDATION_PASSED: archive, English notebook, catalog, idempotency, manual notes, interruption; no API or evacuation steps");
        }
        finally
        {
            if(manager!=null) manager.ResetSimulation();ResearchValidation.Cleanup();
            if(Directory.Exists(root)) Directory.Delete(root,true);
        }
    }
}
