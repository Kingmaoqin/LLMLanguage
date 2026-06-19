# TAU_TASK_CANDIDATES — Stage-2 candidate tasks (from real tau2 tasks)

Selection rule (plan §13): real benchmark task ID + real tools + final-state evaluator + multi-call + ≥1 mutation + policy constraint + ≥5 required calls + ≥2 branch/replanning points. All candidates below are **existing tau2 tasks** (no invention); IR-MSTU adaptation = social-valence overlay + evidence/branch annotations only.

## Proposed Mini-Stage2 v1 (3 retail + 3 airline)
| IR-MSTU id | source | tau2 id | #actions | mutations | one-line |
|---|---|---|---|---|---|
| R1_retail_modify_pending | retail | **4** | 13 | `modify_pending_order_items`×2 | check tshirt options, modify all pending tshirts (color/size) — branch on availability |
| R2_retail_return_cancel_mix | retail | **30** | 13 | `return_delivered`, `cancel_pending`, `return_delivered` | damaged tablet: get tracking, then return/cancel across orders |
| R3_retail_bulk_cancel_return | retail | **55** | 13 | `cancel_pending`×2, `return_delivered`×2 | financial hardship: cancel not-yet-arrived, then return everything eligible |
| T1_airline_cancel_multi | airline | **7** | 5 | `update_reservation_flights`, `cancel_reservation`×2 | cancel upcoming flights across 2 reservation IDs |
| T2_airline_class_baggage | airline | **12** | 5 | `update_reservation_baggages` (+ class change) | change cabin class for all passengers + baggage update |
| T3_airline_conditional_cancel | airline | **44** | 19 | `update_reservation_flights`×3 | cancel future reservations whose flights >4h — agent must report durations first (strong forced-branch) |

Why these: each has multiple read→decide→mutate stages, ≥1 policy-gated irreversible action (cancel/return/modify/rebook → tau2 requires user confirmation per `policy.md`), and natural forced-replanning points (eligibility/availability/duration discovered mid-task). Retail #30/#55 and airline #44 are especially branch-rich.

## Full Stage-2 expansion pool (already qualify, ≥5 actions + mutation)
- retail (57 qualify): top by action-count include ids 4, 30, 32, 55, 3, 21 (12–13 actions) — pick 6 covering modify / return / cancel / exchange.
- airline (8 qualify): ids 44, 39, 42, 7, 12, 18 — pick 6 covering cancel / rebook / baggage / class.

## Branch / replanning annotation (to be filled in adaptation spec)
For each task, ≥2 `forced_replanning_points` will be derived from tau2's own task logic (e.g. "item not in stock → propose alternative", "order already shipped → return not cancel", "flight >4h → include in cancel set"). These are **observations of existing task structure**, not new mechanics.

> Final task IDs and the per-task evidence/branch tags are written to `data/irmstu_tasks/tau_adapted_tasks.yaml` after the architecture decision (see IMPLEMENTATION_GAP_LIST.md).
