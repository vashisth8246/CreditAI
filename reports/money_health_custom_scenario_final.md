# Money Health custom scenario

## Root cause and repair

The old form already recalculated standalone budget edits, but the preset label and overrides were stored separately. Editing after selecting a preset cleared the label while leaving its overrides in the calculation. There was no Apply action. Recommendations always read the baseline, which could suggest the same value the visitor had already entered. These behaviors were reproduced in Edge on the pre-change build.

The planner now keeps the mode, selected preset, overrides and confirmation state together. It opens in a baseline comparison when no change has been selected. Choosing My Own Scenario opens the prefilled editor and focuses its heading. Direct edits activate the same mode. Starting a custom scenario from a preset clears its overrides. Switching back to ready-made changes requires confirmation when custom edits exist.

The comparison, chart, recommendations and report read the same calculated scenario. Apply My Changes validates the current simulation, announces the balance and focuses the comparison heading. Changes remain live before applying. Subsequent edits clear the confirmation. Reset Changes restores the baseline comparison and leaves the custom editor available.

Recommendations use the current simulation. Completed expense reductions and suggestions that would make no change are excluded. Apply this What-If layers the recommendation over unrelated edits and asks before replacing overlapping custom inputs. Money Challenge opens a draft for review, with the existing consent flow for saving a Passport.

## Edge evidence

| Scenario | Before | After | Difference |
|---|---:|---:|---:|
| Student, direct custom expense edit | ₹1,200 | ₹1,500 | ₹300 |
| Working Professional, ₹40,000 salary and ₹1,000 extra EMI | ₹14,000 | ₹3,000 | −₹11,000 |
| Freelancer, ₹28,000 income | ₹15,000 | ₹3,000 | −₹12,000 |
| Other, zero support | ₹800 | −₹2,200 | −₹3,000 |

The Working Professional recommendations reflected ₹40,000 current income and offered a different ₹32,000 stress test. Applying that suggestion after confirmation retained the separate ₹1,000 extra EMI. The original salary remained ₹50,000. The downloaded four-page PDF showed ₹14,000 before, ₹3,000 after, and a decrease of ₹11,000. The spending draft used a ₹200 target and opening it left browser storage empty.

Edge checked 375, 390, 768 and 1440px, with no page-wide horizontal overflow or uncaught JavaScript exceptions. The run checked disabled Apply for no-change and invalid states, focus after Apply, mode switching and confirmation, reset, recommendations and the draft handoff.

[Modes](../frontend/build/custom-scenario-final/mode-selection.png) · [Editor](../frontend/build/custom-scenario-final/custom-editor.png) · [Comparison](../frontend/build/custom-scenario-final/comparison.png) · [Recommendations](../frontend/build/custom-scenario-final/recommendations.png) · [Mobile](../frontend/build/custom-scenario-final/mobile.png)

## Tests and files

Frontend tests passed 73 of 73, including combined scenario arithmetic, recommendation refresh, duplicate suggestion suppression, and preservation of unrelated inputs. TypeScript, lint, production build and Git whitespace checks passed. The build retains the existing deferred PDF size warning.

The broader Edge regression passed all four sample and personal profiles, eight direct financial PDFs, print fallback, Challenge and Passport consent, actual entries, milestone updates, backup restore, Passport PDFs, and private browser context isolation.

- `frontend/src/MoneyHealthPage.tsx` owns the modes, confirmation, live comparison and recommendation actions.
- `frontend/src/moneyHealthAnalysis.ts` derives scenario recommendations and filters repeats.
- `frontend/src/moneyHealth.css` styles the selected mode and focus targets.
- `frontend/tests/moneyHealthWhatIf.test.ts` covers recommendation arithmetic and repeat suppression.

The base was `41e3f9b7590c61b62c9222a124b695b41dbbeb47`. The rollback ZIP retained SHA-256 `ed8f4d22ee478d6f1d43f6a1ec8ba7c4257041ce70d8e2337a023b6ba389900d`. The existing predeployment audit remains separate. Verify the published change with `git log -1 -- reports/money_health_custom_scenario_final.md` and compare it with `git ls-remote origin refs/heads/visitor-money-health`.
