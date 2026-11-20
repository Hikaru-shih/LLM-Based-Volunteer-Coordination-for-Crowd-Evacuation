using System;
using System.Security.Cryptography;
using System.Text;

/// <summary>Versioned public task specification, without the benchmark probability or recommended action.</summary>
public static class PaperVolunteerPrompt
{
    public const string Version="paper-agent-v5";
    public const string Participate="participate";
    public const string Decline="decline_assistance";
    public static bool IsDecision(string value) => value==Participate || value==Decline;
    public static string Instructions(string information,AgentPromptWording wording)
    {
        string opening=wording==AgentPromptWording.Alternate
            ? "Make your own choice between declining assistance and participating in assistance for one movable obstacle.\n"
            : "Choose for yourself whether to participate in assistance or decline assistance for one movable obstacle.\n";
        string shared=information==AgentInformationCondition.SharedContext.ToString()
            ? "Additional context: distanceToObstacle is grid-cell distance, not an extra payoff deduction. obstacleCount and currentVolunteerCount are model-wide counts; active workers are not commitments by the other players in this decision. blockageRatio equals 1-exitNonBlockage. Position and distance do not establish alternative routes or handling success.\n"
            : "Core observations contain only the five game inputs below; no map, route, distance or prior decisions are supplied.\n";
        return "Task specification: "+Version+"; information condition: "+information+".\n"+opening+
            "You are one pedestrian in a volunteer's dilemma. Make a personal decision using the stated payoffs and observations. Neither action is prescribed.\n"+
            "Actions: participate means willingness to assist (C); decline_assistance means not volunteering for this obstacle (D). Declining does not mean that evacuation is currently possible or completed.\n"+
            "Payoffs are normalized, dimensionless utilities with initial value 1. Let cv=volunteerCost and av=failureCost, with 0<cv<av<1.\n"+
            "- If you choose C, your payoff is 1-cv, regardless of the other players' choices.\n"+
            "- If you choose D and at least one other player chooses C, your payoff is 1.\n"+
            "- If you choose D and every other player also chooses D, your payoff is 1-av.\n"+
            "This is the base payoff table (Eq.20), not a complete specification of the reference simulator's adjusted behavioral law. The reference adds exit-nonblockage/unwillingness adjustments separately; those adjustments are not additional utility deductions and their probability is not supplied. You are not asked to solve a Nash equilibrium or reproduce that law.\n"+
            "av is the loss from nobody volunteering. It is NOT a risk or penalty caused by your participation, and is NOT a probability of injury or unsuccessful manipulation. cv is the cost of intending to help, not an invented travel-time estimate. These are decision-game payoffs, not measured future evacuation times.\n"+
            "nearbyAgentCount is X, the number of eligible players for this obstacle, including you. Their current choices are not provided. X can equal one, in which case there are no other players. The reference model has a separate single-player behavioral branch, but that branch does not prescribe your choice. Make your own decision for the supplied state.\n"+
            "exitNonBlockage is tau, the unblocked fraction of the relevant exit (0 fully blocked, 1 unblocked). It does not identify every exit in the room. Do not invent an alternative exit, or infer that a movable obstacle cannot be moved because blockage is high.\n"+
            "unwillingness is omega, a nonnegative coefficient used by the reference model to modify participation with exit nonblockage. It is not a declaration that you refuse, a physical danger level, or a personality rating out of five. It is separate from cv and av, not another payoff deduction.\n"+
            "The simulator asks for decisions when an unhandled obstacle has no potential volunteers, eligible pedestrians are in its visibility region, and the relevant exit is blocked. If nobody participates, the same eligibility rules can trigger another decision on a later step.\n"+
            "Participation adds you to a potential-volunteer list; it does not instantly move the obstacle. An adjacent candidate can later be randomly activated if a legal placement exists. Movement, conflicts, push/pull/rotation and placement are executed by the simulator. Their completion and time benefit are not guaranteed by this decision.\n"+
            "No additional injury, accident or manipulation-failure penalty is specified in this payoff game. Do not introduce one. You cannot assign other people, control a grid move, or assume knowledge of future outcomes.\n"+shared+
            "This is a fresh individual decision with no supplied personal history. No benchmark probability or current choices by other players are supplied. Express your own choice for the stated game.\n"+
            "Return a JSON object with exactly decision and explanation. decision must be participate or decline_assistance. explanation is a brief account using only the stated rules and supplied observations.\n";
    }
    public static string Build(string observation,string information,AgentPromptWording wording)
        => Instructions(information,wording)+"Observation:\n"+observation;
    public static string Hash(string information,AgentPromptWording wording)
    {
        using(var sha=SHA256.Create())
            return BitConverter.ToString(sha.ComputeHash(Encoding.UTF8.GetBytes(Instructions(information,wording))))
                .Replace("-","").ToLowerInvariant();
    }
}
