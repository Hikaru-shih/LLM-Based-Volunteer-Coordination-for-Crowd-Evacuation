using UnityEngine;
using System.Collections.Generic;

namespace Decision
{
    public class YielderGame
    {
        public enum Strategy
        {
            Random,
            Closest,
            FirstCome,
            Probabilistic
        }

        private Strategy currentStrategy = Strategy.Random;

        public YielderGame(Strategy strategy = Strategy.Random)
        {
            currentStrategy = strategy;
        }

        public PedestrianAgent ResolveConflict(List<PedestrianAgent> conflictingAgents)
        {
            if (conflictingAgents == null || conflictingAgents.Count == 0)
                return null;

            if (conflictingAgents.Count == 1)
                return conflictingAgents[0];

            switch (currentStrategy)
            {
                case Strategy.Random:
                    return ResolveByRandom(conflictingAgents);

                case Strategy.Closest:
                    return ResolveByClosest(conflictingAgents);

                case Strategy.FirstCome:
                    return ResolveByFirstCome(conflictingAgents);

                case Strategy.Probabilistic:
                    return ResolveByProbabilistic(conflictingAgents);

                default:
                    return ResolveByRandom(conflictingAgents);
            }
        }

        private PedestrianAgent ResolveByRandom(List<PedestrianAgent> agents)
        {
            int winnerIndex = Random.Range(0, agents.Count);
            return agents[winnerIndex];
        }

        private PedestrianAgent ResolveByClosest(List<PedestrianAgent> agents)
        {
            PedestrianAgent closest = agents[0];
            float minDistance = float.MaxValue;

            foreach (PedestrianAgent agent in agents)
            {
                if (agent.GetGridPos().y < minDistance)
                {
                    minDistance = agent.GetGridPos().y;
                    closest = agent;
                }
            }

            return closest;
        }

        private PedestrianAgent ResolveByFirstCome(List<PedestrianAgent> agents)
        {
            return agents[0];
        }

        private PedestrianAgent ResolveByProbabilistic(List<PedestrianAgent> agents)
        {
            List<float> probabilities = new List<float>();
            float totalProb = 0f;

            foreach (PedestrianAgent agent in agents)
            {
                float distToExit = agent.GetGridPos().y + 1;
                float prob = 1f / distToExit;
                probabilities.Add(prob);
                totalProb += prob;
            }

            for (int i = 0; i < probabilities.Count; i++)
            {
                probabilities[i] /= totalProb;
            }

            float randomValue = Random.value;
            float cumulativeProb = 0f;

            for (int i = 0; i < agents.Count; i++)
            {
                cumulativeProb += probabilities[i];
                if (randomValue < cumulativeProb)
                {
                    return agents[i];
                }
            }

            return agents[agents.Count - 1];
        }

        public void SetStrategy(Strategy strategy)
        {
            currentStrategy = strategy;
        }

        public string GetStrategyName()
        {
            return currentStrategy.ToString();
        }
    }
}
