using System;
using System.Linq;
using System.Collections.Generic;
using System.Security.Cryptography;
using System.Text;
using UnityEngine;

// Explicit opt-in research geometry. Existing scene presets and physics are unchanged.
[Serializable]
public sealed class ClosedLoopInitialState
{
    public string schema="closed-loop-initial-v1";
    public int seed,agents,blocked;
    public bool mirrored;
    public Vector2Int[] exitCells,obstacleCells,agentCells;
    public string TemplateSHA => Hash("closed-loop-layout-v1|21x21|exit3|spawn8x8|total5|B"+blocked+"|nestedN|mirrorBySeedParity");
    public string Identity => Hash(JsonUtility.ToJson(this));
    public static string Hash(string text)
    {using(var sha=SHA256.Create())return BitConverter.ToString(sha.ComputeHash(Encoding.UTF8.GetBytes(text))).Replace("-","").ToLowerInvariant();}
    public static ClosedLoopInitialState Build(int seed,int agents,int blocked)
    {
        if((agents!=10 && agents!=30) || (blocked<0 || blocked>5 || blocked==1))throw new ArgumentException("Unsupported group cell");
        bool mirror=(seed&1)!=0;
        Func<Vector2Int,Vector2Int> reflect=p=>mirror?new Vector2Int(20-p.x,p.y):p;
        var points=new List<Vector2Int>();for(int x=6;x<14;x++)for(int y=6;y<14;y++)points.Add(new Vector2Int(x,y));
        var rng=new System.Random(seed);
        for(int i=points.Count-1;i>0;i--){int j=rng.Next(i+1);var p=points[i];points[i]=points[j];points[j]=p;}
        var obstacles=new List<Vector2Int>();
        if(blocked==2){obstacles.Add(new Vector2Int(9,1));obstacles.Add(new Vector2Int(10,1));}
        if(blocked==3)for(int x=9;x<=11;x++)obstacles.Add(new Vector2Int(x,1));
        if(blocked==4)for(int x=8;x<=11;x++)obstacles.Add(new Vector2Int(x,1));
        if(blocked==5)for(int x=8;x<=12;x++)obstacles.Add(new Vector2Int(x,1));
        var background=new[]{new Vector2Int(2,5),new Vector2Int(18,5),new Vector2Int(2,10),new Vector2Int(18,10),new Vector2Int(10,17)};
        obstacles.AddRange(background.Take(5-blocked));
        return new ClosedLoopInitialState {seed=seed,agents=agents,blocked=blocked,mirrored=mirror,
            exitCells=new[]{new Vector2Int(9,0),new Vector2Int(10,0),new Vector2Int(11,0)},
            obstacleCells=obstacles.Select(reflect).ToArray(),agentCells=points.Take(agents).Select(reflect).ToArray()};
    }
    public void Validate(int expectedAgents,int expectedSeed)
    {
        if(seed!=expectedSeed || agents!=expectedAgents || JsonUtility.ToJson(this)!=JsonUtility.ToJson(Build(seed,agents,blocked)))
            throw new ArgumentException("Initial-state manifest changed");
        var all=obstacleCells.Concat(agentCells).ToArray();
        if(all.Distinct().Count()!=all.Length || all.Any(p=>p.x<1||p.x>19||p.y<1||p.y>19))throw new ArgumentException("Invalid geometry");
    }
    public void Configure(GridWorld world)
    {
        Validate(agents,seed);
        if(world.width!=21 || world.height!=21 || !world.paperNeighborhood)throw new ArgumentException("Research geometry requires 21x21 paper grid");
        world.SetExits(true,false,false,false,3);
        foreach(var p in obstacleCells)world.SetCellType(p.x,p.y,CellType.Obstacle);
    }
}
