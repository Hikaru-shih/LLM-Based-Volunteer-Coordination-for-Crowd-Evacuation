using System;
using System.Collections.Generic;
using System.Globalization;
using System.Text;
using UnityEngine;

namespace Coordination
{
    public static class LLMDispatchProtocol
    {
        public const string Version="coordination-dispatch-v1";
        [Serializable] private sealed class Decision {public string snapshotId,explanation;public Assignment[] assignments;}
        public static string Encode(Proposal proposal,string explanation) => JsonUtility.ToJson(new Decision {snapshotId=proposal.snapshotId,assignments=proposal.assignments,explanation=explanation});
        public const string Objective="Maximize the number of assigned tasks first. Among assignments with that maximum count, minimize the sum of approachCost. Use only eligible AND consented listed edges, at most one task per agent and one agent per task. Empty or partial assignments are allowed but are evaluated for coverage and cost. Costs are observable approach-field costs, not seconds or future benefits. Do not infer extra agents, edges, willingness or evacuation outcomes. Existing reservations are excluded and cannot be displaced.";
        public static string Prompt(Snapshot snapshot) => "Protocol: "+Version+"\n"+Objective+
            "\nReturn only JSON with exactly snapshotId (copy it), assignments (array of objects with integer agentId and obstacleId), and explanation (brief string).\nSnapshot:\n"+JsonUtility.ToJson(snapshot);
        public const string ResponseFormat="{\"type\":\"json_schema\",\"json_schema\":{\"name\":\"coordination_dispatch\",\"strict\":true,\"schema\":{\"type\":\"object\",\"properties\":{\"snapshotId\":{\"type\":\"string\"},\"assignments\":{\"type\":\"array\",\"items\":{\"type\":\"object\",\"properties\":{\"agentId\":{\"type\":\"integer\"},\"obstacleId\":{\"type\":\"integer\"}},\"required\":[\"agentId\",\"obstacleId\"],\"additionalProperties\":false}},\"explanation\":{\"type\":\"string\"}},\"required\":[\"snapshotId\",\"assignments\",\"explanation\"],\"additionalProperties\":false}}}";
        // JsonUtility alone accepts missing/extra fields. This parser rejects them,
        // duplicate keys, prose/fences, null arrays, coercions and trailing input.
        public static bool Parse(string json,out Proposal proposal,out string explanation,out string error)
        {
            proposal=null;explanation="";error="invalid_dispatch_json";
            if(json==null || json.Length>262144)return false;
            try
            {
                var reader=new Reader(json);var keys=new HashSet<string>();string id=null;Assignment[] pairs=null;
                reader.Take('{');
                do
                {
                    string key=reader.String();if(!keys.Add(key))throw new FormatException();reader.Take(':');
                    switch(key)
                    {
                        case "snapshotId":id=reader.String();break;
                        case "explanation":explanation=reader.String();break;
                        case "assignments":
                            var list=new List<Assignment>();reader.Take('[');
                            if(!reader.Peek(']')) do
                            {
                                var pair=new Assignment();var fields=new HashSet<string>();reader.Take('{');
                                do
                                {
                                    string name=reader.String();if(!fields.Add(name))throw new FormatException();reader.Take(':');
                                    if(name=="agentId")pair.agentId=reader.Integer();
                                    else if(name=="obstacleId")pair.obstacleId=reader.Integer();else throw new FormatException();
                                }while(reader.Maybe(','));
                                reader.Take('}');if(fields.Count!=2)throw new FormatException();list.Add(pair);
                            }while(reader.Maybe(','));
                            reader.Take(']');pairs=list.ToArray();break;
                        default:throw new FormatException();
                    }
                }while(reader.Maybe(','));
                reader.Take('}');if(!reader.End || keys.Count!=3 || string.IsNullOrEmpty(id) || pairs==null)throw new FormatException();
                proposal=new Proposal {snapshotId=id,source=Version,assignments=pairs};error="";return true;
            }
            catch(FormatException){return false;}
            catch(OverflowException){return false;}
        }
        private sealed class Reader
        {
            private readonly string text;private int at;
            public Reader(string text){this.text=text;}
            private void Space(){while(at<text.Length && (text[at]==' ' || text[at]=='\n' || text[at]=='\r' || text[at]=='\t'))at++;}
            public bool End {get{Space();return at==text.Length;}}
            public bool Peek(char c){Space();return at<text.Length && text[at]==c;}
            public bool Maybe(char c){if(!Peek(c))return false;at++;return true;}
            public void Take(char c){if(!Maybe(c))throw new FormatException();}
            public int Integer()
            {
                Space();int start=at;if(at<text.Length && text[at]=='-')at++;
                if(at==text.Length || text[at]<'0' || text[at]>'9')throw new FormatException();
                if(text[at]=='0')at++;else while(at<text.Length && text[at]>='0' && text[at]<='9')at++;
                return int.Parse(text.Substring(start,at-start),NumberStyles.AllowLeadingSign,CultureInfo.InvariantCulture);
            }
            public string String()
            {
                Take('"');var result=new StringBuilder();
                while(at<text.Length)
                {
                    char c=text[at++];if(c=='"')return result.ToString();if(c<32)throw new FormatException();
                    if(c!='\\'){result.Append(c);continue;}
                    if(at==text.Length)throw new FormatException();c=text[at++];
                    switch(c)
                    {
                        case '"':case '\\':case '/':result.Append(c);break;
                        case 'b':result.Append('\b');break;case 'f':result.Append('\f');break;
                        case 'n':result.Append('\n');break;case 'r':result.Append('\r');break;case 't':result.Append('\t');break;
                        case 'u':if(at+4>text.Length)throw new FormatException();result.Append((char)ushort.Parse(text.Substring(at,4),NumberStyles.AllowHexSpecifier,CultureInfo.InvariantCulture));at+=4;break;
                        default:throw new FormatException();
                    }
                }
                throw new FormatException();
            }
        }
    }
}
