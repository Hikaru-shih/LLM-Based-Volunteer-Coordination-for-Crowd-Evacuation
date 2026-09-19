using UnityEngine;

namespace Decision
{
    public class MockLLMVolunteerStrategy : IVolunteerDecisionStrategy
    {
        public bool ShouldVolunteer(VolunteerDecisionContext context)
        {
            // Mock LLM tendency: high blockage/obstacle load and low active volunteers increase willingness.
            float blockageScore = Mathf.Clamp01(context.blockageRatio);
            float obstacleScore = Mathf.Clamp01(context.obstacleCount / 20.0f);
            float volunteerScarcity = 1.0f - Mathf.Clamp01(context.currentVolunteerCount / Mathf.Max(1.0f, context.nearbyAgentCount));
            float proximityScore = 1.0f - Mathf.Clamp01(context.distanceToObstacle / 6.0f);

            float pVolunteer = 0.10f
                + 0.40f * blockageScore
                + 0.20f * obstacleScore
                + 0.20f * volunteerScarcity
                + 0.10f * proximityScore;

            pVolunteer = Mathf.Clamp01(pVolunteer);
            return Random.value < pVolunteer;
        }
    }
}
