using System;
using System.Collections.Generic;
using System.Globalization;
using System.Text;

/// <summary>Bounded JSON reader. Rejects duplicate keys, coercion, comments and trailing text.</summary>
public static class StrictJson
{
    public sealed class Number
    {public readonly string text;public readonly double value;public Number(string text,double value){this.text=text;this.value=value;}}
    public static bool TryObject(string text,out Dictionary<string,object> result)
    {
        result=null;if(string.IsNullOrWhiteSpace(text) || text.Length>2097152)return false;
        try{var r=new Reader(text);result=r.Value(0) as Dictionary<string,object>;return result!=null && r.End;}
        catch(FormatException){return false;}catch(OverflowException){return false;}
    }
    private sealed class Reader
    {
        private readonly string text;private int at,nodes;
        public Reader(string text){this.text=text;}
        private void Space(){while(at<text.Length && (text[at]==' ' || text[at]=='\t' || text[at]=='\r' || text[at]=='\n'))at++;}
        public bool End {get{Space();return at==text.Length;}}
        private bool Maybe(char c){Space();if(at>=text.Length || text[at]!=c)return false;at++;return true;}
        private void Take(char c){if(!Maybe(c))throw new FormatException();}
        public object Value(int depth)
        {
            Space();if(depth>64 || ++nodes>65536 || at>=text.Length)throw new FormatException();
            char c=text[at];
            if(c=='"')return String();
            if(c=='{')
            {
                at++;var obj=new Dictionary<string,object>(StringComparer.Ordinal);
                if(Maybe('}'))return obj;
                do{string key=String();if(obj.ContainsKey(key))throw new FormatException();Take(':');obj.Add(key,Value(depth+1));}while(Maybe(','));
                Take('}');return obj;
            }
            if(c=='[')
            {
                at++;var list=new List<object>();if(Maybe(']'))return list;
                do{list.Add(Value(depth+1));}while(Maybe(','));Take(']');return list;
            }
            foreach(string word in new[]{"true","false","null"})
                if(at+word.Length<=text.Length && string.CompareOrdinal(text,at,word,0,word.Length)==0)
                {at+=word.Length;return word=="null"?null:(object)(word=="true");}
            int start=at;if(c=='-')at++;
            if(at==text.Length || text[at]<'0' || text[at]>'9')throw new FormatException();
            if(text[at]=='0')at++;else Digits();
            if(at<text.Length && text[at]=='.'){at++;Digits();}
            if(at<text.Length && (text[at]=='e' || text[at]=='E')){at++;if(at<text.Length && (text[at]=='+' || text[at]=='-'))at++;Digits();}
            string token=text.Substring(start,at-start);double number=double.Parse(token,NumberStyles.Float,CultureInfo.InvariantCulture);
            if(double.IsNaN(number) || double.IsInfinity(number))throw new FormatException();return new Number(token,number);
        }
        private void Digits()
        {int start=at;while(at<text.Length && text[at]>='0' && text[at]<='9')at++;if(at==start)throw new FormatException();}
        private string String()
        {
            Take('"');var value=new StringBuilder();
            while(at<text.Length)
            {
                char c=text[at++];if(c=='"')return value.ToString();if(c<32)throw new FormatException();
                if(c=='\\')
                {
                    if(at==text.Length)throw new FormatException();c=text[at++];
                    switch(c)
                    {
                        case '"':case '\\':case '/':break;
                        case 'b':c='\b';break;case 'f':c='\f';break;case 'n':c='\n';break;case 'r':c='\r';break;case 't':c='\t';break;
                        case 'u':c=Hex();break;default:throw new FormatException();
                    }
                }
                if(char.IsHighSurrogate(c))
                {
                    value.Append(c);
                    if(at+2<=text.Length && text[at]=='\\' && text[at+1]=='u'){at+=2;c=Hex();}
                    else if(at<text.Length)c=text[at++];else throw new FormatException();
                    if(!char.IsLowSurrogate(c))throw new FormatException();value.Append(c);
                }
                else{if(char.IsLowSurrogate(c))throw new FormatException();value.Append(c);}
            }
            throw new FormatException();
        }
        private char Hex()
        {if(at+4>text.Length)throw new FormatException();char c=(char)ushort.Parse(text.Substring(at,4),NumberStyles.AllowHexSpecifier,CultureInfo.InvariantCulture);at+=4;return c;}
    }
}
