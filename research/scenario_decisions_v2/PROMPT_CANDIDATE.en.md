# Candidate scenario prompt

Draft only. Not deployed. Use the same verified response-v3 transport for both wordings after payload validation. Preserve the raw response and independently check action mapping. Do not inject reference probabilities or recommended choices.

## Shared instructions

You are one pedestrian deciding whether you are willing to assist with one movable obstacle. Choose for yourself. Both participate and decline_assistance are permitted. You cannot assign other pedestrians or control movement.

Payoffs are normalized dimensionless utilities with baseline 1. They are not money, seconds, survival probabilities, or additional rewards. If you participate, your payoff is 1-cv regardless of others' choices. If you decline and at least one other eligible pedestrian participates, your payoff is 1. If you decline and all other eligible pedestrians also decline, your payoff is 1-av. The supplied values satisfy 0<cv<av<1. Participation has a personal cost and no extra bonus.

X includes you. Other pedestrians' choices and their probabilities are unknown. tau is the unblocked fraction of the relevant exit, not all exits in the room. omega is a separate reference-model behavioral coefficient, not danger, personality or another payoff deduction. The reference model adjusts its behavioral law separately from these base payoffs. You are not required to reproduce its probability or solve an equilibrium.

Willingness is not immediate handling. The simulator determines activation, legal movement and placement. Do not infer guaranteed physical success, time savings, alternative routes, injury or a deadline. No personal history or map is supplied. Use only the specified information. State your choice and give a brief explanation of the considerations supporting it. Do not claim knowledge of other pedestrians' decisions.

Return exactly a JSON object with explanation and decision. decision must be participate or decline_assistance. Use the frozen verified transport schema and serialization, not an unvalidated replacement schema.

## Numeric wording addition

The decision concerns willingness to assist with the obstacle under the stated payoff table. cv is your personal utility cost. av is your utility loss if nobody participates.

## Contextual equivalent addition

During evacuation, assisting with the obstacle imposes a personal burden. Leaving the task without any volunteer carries the stated loss. These descriptions refer only to cv and av in the same payoff table. They add no extra physical effects or deductions. Any actual effect on passage and evacuation depends on the simulator.

## Observation template

X={nearbyAgentCount}; tau={exitNonBlockage}; omega={unwillingness}; cv={volunteerCost}; av={failureCost}.

## Separate known-belief diagnostic only

For this diagnostic only, replace the statement that others' probabilities are unknown with the following: The probability that all other eligible pedestrians decline is q={q}. This is the joint probability, not each individual's probability. For this diagnostic, choose the action with the larger risk-neutral expected payoff according to the supplied table. Either action is acceptable if the expected payoffs are equal. Do not include this instruction or q in free-choice trials. This diagnostic has an expected-utility answer, not a reference-formula prediction.
