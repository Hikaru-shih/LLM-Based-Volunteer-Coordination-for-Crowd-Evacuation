# Worked coding examples

These are hand-authored teaching examples, not API responses, human data, or a validated semantic classifier. Context and the full supplied prompt always take precedence over keywords. Positive labels require exact quotes in actual records.

| Task and raw action | Illustrative explanation | Labels and review boundary |
|---|---|---|
| Abstract decline | The cost of helping reduces my payoff, so I decline. | personal_cost. This describes a consideration, not proof of optimality with unknown beliefs. |
| Abstract participate | If nobody helps, I face the larger loss, so I participate. | avoid_unhandled_loss, personal_cost. No unstated belief probability should be inferred. |
| Abstract participate | Helping locks in a payoff of 0.85 rather than risking 0.5 if nobody helps. | guaranteed_payoff, avoid_unhandled_loss, personal_cost, provided those numbers match the observation. |
| Abstract decline | Their choices are unknown. I think another person may help, so I decline. | reliance_on_others, uncertainty_awareness. A stated uncertain belief is not an observed commitment. |
| Any participate | There are ten people. I participate. | insufficient_reason if the full response never connects the count to its choice. Repeating X is not automatically context_use. |
| Physical calibrated participate | The supplied estimates suggest helping may shorten the others' evacuation, even though I may leave later. | shared_benefit, personal_cost, forecast_use, uncertainty_awareness if the supplied estimates support the comparison. |
| Physical calibrated decline | The table's mean own evacuation time is lower if I decline, so I decline. | forecast_use, personal_cost. Judge the comparison against the correct other-profile row, not another scenario. |
| Physical geometry-only decline | I will definitely suffer an injury if I help. | unsupported_assumption, personal_cost. No injury effect was specified. A stated motive can rely on incorrect information. |
| Physical geometry-only participate | Helping guarantees my evacuation in exactly 20 seconds. | unsupported_assumption. Consider guaranteed_payoff only if the text actually expresses certainty as its preference, not merely because the word guarantees appears. Do not use forecast_use. |
| Any raw participate | Declining gives the higher payoff. My final choice is to decline. | action_reason_conflict, personal_cost. Preserve the raw participate action. Whether the payoff comparison is correct is a separate question. |
| Abstract participate | Because 0.8 is greater than 1, helping gives the higher payoff. | personal_cost with incorrect arithmetic/comparison, supported by the exact erroneous statement. Do not repair its decision. |
| Physical calibrated decline | Dividing times by the common 301 scale preserves their order. I choose the lower estimated mean time by declining. | scale_or_normalization, forecast_use, personal_cost when the estimate comparison is supported. |

A free choice does not become incorrect simply because the coder would choose differently. Unknown beliefs, unclear wording and unsupported facts require separate treatment. These examples cannot replace reading the bound response and observation.
