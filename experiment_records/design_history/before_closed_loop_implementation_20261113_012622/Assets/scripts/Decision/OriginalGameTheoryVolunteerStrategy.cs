using UnityEngine;

namespace Decision
{
    public class OriginalGameTheoryVolunteerStrategy : IVolunteerDecisionStrategy
    {
        private readonly System.Func<float> sample;
        public OriginalGameTheoryVolunteerStrategy(System.Func<float> sample = null)
        { this.sample = sample ?? (() => Random.value); }
        public bool ShouldVolunteer(VolunteerDecisionContext context)
        {
            float p = CalculateVolunteerProbability(context);
            return sample() < p;
        }

        public float CalculateVolunteerProbability(VolunteerDecisionContext context)
        {
            int x = context.nearbyAgentCount;
            float tau = Mathf.Clamp01(context.exitNonBlockage);
            if (x <= 0 || tau >= 1f) return 0f; // No game at an unblocked exit.
            if (x == 1) return tau <= 0f ? 1f : 0f; // Sec. II.C.2, p. 8.
            float omega = Mathf.Max(0f, context.unwillingness);
            // No artificial beta floor inside the paper's valid cost domain.
            bool paperCosts=context.volunteerCost>0 && context.volunteerCost<context.failureCost && context.failureCost<1;
            float beta=paperCosts ? context.volunteerCost/context.failureCost :
                Mathf.Clamp(context.volunteerCost/Mathf.Max(0.0001f,context.failureCost),0.0001f,1f);
            // The fallback above only preserves non-reference legacy/development inputs.
            // Calibration/FinalTest reject those inputs before starting.

            float left = Mathf.Pow(1.0f - Mathf.Exp(-omega * tau), 1.0f / x);
            float right = Mathf.Pow(beta, 1.0f / (x - 1));
            float q = Mathf.Clamp01(left * right);
            float pVolunteer = Mathf.Clamp01(1.0f - q);
            return pVolunteer;
        }
    }
}
