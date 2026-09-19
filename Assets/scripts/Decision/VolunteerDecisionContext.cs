using UnityEngine;

namespace Decision
{
    public class VolunteerDecisionContext
    {
        public int nearbyAgentCount;
        public int obstacleCount;
        public float blockageRatio;
        public float distanceToObstacle;
        public int currentVolunteerCount;
        public float volunteerCost;
        public float failureCost;
        public float unwillingness;
        public Vector2Int agentPosition;
    }
}
