namespace Decision
{
    /// <summary>Versioned xorshift32 stream, independent of Unity's physical RNG.</summary>
    public sealed class DecisionRandomStream
    {
        public const string Version = "decision-xorshift32-v1";
        private uint state;
        public static int SeedForRun(int runSeed) => unchecked(runSeed ^ (int)0x9E3779B9u);
        public DecisionRandomStream(int seed)
        { state=unchecked((uint)seed);if(state==0) state=0x6D2B79F5u; }
        public float NextValue()
        {
            uint value=state;
            value^=value<<13;value^=value>>17;value^=value<<5;state=value;
            return (value>>8)*(1f/16777216f);
        }
    }
}
