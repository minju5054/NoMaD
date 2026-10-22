"""Optional seed offsets for the frozen static S0 Topomap experiment only."""
import re


def validate_seed_options(args):
    if getattr(args, "phase2_method", None):
        from nomad_phase2.config import validate_options
        validate_options(args)
        return
    if args.seed_offset < 0:
        raise ValueError("seed-offset must be nonnegative")
    if args.seed_offset or args.run_id is not None:
        from nomad_phase0.chunk_execution import validate_mode
        validate_mode(args)  # Same frozen S0/map/async/no-extra-feature gate for PD and PP.
        request_seed({"seed": 101, "seed_offset": args.seed_offset}, 240)
    if args.run_id is not None:
        if not re.fullmatch(r"S0_(0[1-9]|10)", args.run_id):
            raise ValueError("Batch run-id must be S0_01 ... S0_10")
        if args.seed_offset != int(args.run_id[3:])*10000:
            raise ValueError("Batch run-id and frozen seed offset disagree")


def request_seed(config, request_id):
    seed = config["seed"] + config.get("seed_offset", 0) + 2*request_id
    if not 0 <= seed < 2**32-1:
        raise ValueError("Inference seed and DDPM seed must fit unsigned 32-bit range")
    return seed
