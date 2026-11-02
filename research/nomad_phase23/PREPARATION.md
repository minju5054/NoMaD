# Phase23-O preparation — not evaluated

The graph, saved-input loader, timestamp replay, comparison adapters, guarded staged runner and report generator are implemented as a draft. Five unit tests and one saved-V1 timestamp-replay equality check pass. Full multiprocess/tuning/evaluation/report validation remains pending; no experimental decision has been produced.

Protocol is DRAFT_PENDING_DEFINITIONS. Do not start data solves until the user confirms rotation/stop execution, short-candidate handling and tuning criteria/kinematic normalization. Training:216static+26sudden. Evaluation:795static+34sudden. Eight proposed weight combinations; train/eval run sets are disjoint. The staged runner will commit selected weights before evaluation and supports wall-budget checkpoints.

The proposed tuning progression tie-break uses equal-weight ranks of the static and sudden group medians, so metres are not added to binary passage indicators. This is pending registration, not an executed choice.
