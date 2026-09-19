using UnityEngine;

namespace Decision
{
    public class OriginalGameTheoryVolunteerStrategy : IVolunteerDecisionStrategy
    {
        public bool ShouldVolunteer(VolunteerDecisionContext context)
        {
            float p = CalculateVolunteerProbability(context);
            return Random.value < p;
        }

        public float CalculateVolunteerProbability(VolunteerDecisionContext context)
        {
            int x = Mathf.Max(2, context.nearbyAgentCount);
            float blockageRatio = Mathf.Clamp01(context.blockageRatio);
            float omega = Mathf.Max(0.0001f, context.unwillingness);
            float failureCost = Mathf.Max(0.0001f, context.failureCost);
            float beta = Mathf.Clamp(context.volunteerCost / failureCost, 0.0001f, 1.0f);

            float left = Mathf.Pow(1.0f - Mathf.Exp(-omega * blockageRatio), 1.0f / x);
            float right = Mathf.Pow(beta, 1.0f / (x - 1));
            float q = Mathf.Clamp01(left * right);
            float pVolunteer = Mathf.Clamp01(1.0f - q);
            return pVolunteer;
        }
    }
}
