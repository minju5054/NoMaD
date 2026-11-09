from nomad_phase41.runtime import install as install41,run_without_oracle


def install(config):
    install41(config)
    from nomad_isaac import async_runtime
    from .odometry import ExecutionThread,Client
    async_runtime.ExecutionThread=ExecutionThread
    async_runtime.AsyncClient=Client
