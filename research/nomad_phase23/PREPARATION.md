# Phase23-O preparation amendment — execution held

Accepted: variant(ii),8policy+available left/right starts,4workers,500ms shared deadline; feasible anytime output; predicted application pose and computation-motion rollout prefix. Factors/grid/SLSQP options and optimized.py hash remain unchanged.28/28tests pass. No tuning/evaluation records exist.

Conservative scheduling estimate: full242training snapshots×8weights +829evaluation snapshots =2h42m. Reducing evaluation uniform static sampling10→5/run (failure-window5 unchanged, deduplicated) leaves454static+34sudden evaluation snapshots and takes2h8m. Training is unchanged. Both exceed the requested2h gate; no reduction or nohup execution selected.

Two motion details remain explicitly unset pending the earlier user questions: current-speed PP prediction versus full saved executor-state reconstruction; and C0/C1 original online braking wait versus old offline fixed-B immediate application. Proposed branches have synthetic tests, but the runner refuses unset choices. The user must also choose runtime scope. FROZEN weight selection will occur only after authorized training and before evaluation.
