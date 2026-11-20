using UnityEngine;

namespace Decision
{
    public class VolunteerDecisionContext
    {
        public int nearbyAgentCount;
        public int obstacleCount;
        public float blockageRatio;
        // Paper Eq. (25): tau is the NON-blocked fraction of the relevant exit.
        public float exitNonBlockage = 1f;
        public float distanceToObstacle;
        public int currentVolunteerCount;
        public float volunteerCost;
        public float failureCost;
        public float unwillingness;
        public Vector2Int agentPosition;
    }
}
