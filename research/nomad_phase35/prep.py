"""Lock the experiment before smoke, with explicit immutable source hashes."""
import json,subprocess,time
from nomad_isaac.common import sha256_file
from nomad_phase32o.evaluate import save
from .config import ROOT,HERE,OUT,METHODS,SCENES,INDICES,ORDER_SEED,registered_order

def freeze():
    from nomad_phase32.config import verify
    old=verify();assets=json.loads((ROOT/'research/nomad_phase29/protocol.json').read_text())
    frozen={**old['frozen_sources'],**old['source_sha256']}
    for package in ('nomad_phase21','nomad_phase26','nomad_phase28','nomad_phase32o'):
        for file in (ROOT/'research'/package).glob('*.py'):frozen[str(file.relative_to(ROOT))]=sha256_file(file)
    for file in ('research/nomad_phase33p/storage.py','research/nomad_storage_sdf/loader.py'):
        frozen[file]=sha256_file(ROOT/file)
    blocks,order=registered_order()
    definitions=[dict(method='OURS',source='Phase32 C0-NA+EC',change='storage v2 only'),
        dict(method='ASTAR+EC',source='OURS + Phase21 B4 A* R2/R3',change='solver wiring only; lambda4 / smoothing0'),
        dict(method='SAFE_TE',source='Phase27-R B1 / Phase21 SAFE TE',change='C0-NA departure installer only; TE steering/KEEP preserved'),
        dict(method='SAFE_RTC',source='Phase27-R B2 / Phase18 RTC-hard',change='C0-NA installer only'),
        dict(method='NOMAD_RAW',source='Phase27-R B0 sample0',change='C0-NA installer only; no depth/filter/recovery')]
    protocol=dict(status='FROZEN',phase='35',frozen_unix=time.time(),budget_start_unix=1794071828,
        base_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        methods=list(METHODS),method_definitions=definitions,indices=list(INDICES),scenes={s:assets['scenes'][s] for s in SCENES},
        checkpoint_sha256=assets['checkpoint_sha256'],order_seed=ORDER_SEED,blocks=blocks,main_order=order,planned=75,
        smoke=[dict(scene='H1',index=95,method=m) for m in METHODS[1:]],technical_retry=1,smoke_repeat_error_limit=2,
        sequential=True,disk_min_bytes=30_000_000_000,deadline_hours=6.5,publish_every_blocks=5,
        storage=dict(version=2,values_stored=False,compressed=True,loader='STORAGE_RETROFIT',live_compute_unchanged=True,
            cleanup=['portable/cache','pycache'],raw_retention='Phase26: smoke full, seed201 full, other seeds compact'),
        executor=dict(source='nomad_phase28.alignment.NoAlignment',PP_lookahead_m=.25,speed='Phase18D SP',rotation_threshold_deg=90,strict_greater=True,vmax=.3,omega_max=.4,acceleration_max=.5),
        primary=dict(BEATS_X='OURS goal > X goal AND OURS collision <= X collision; X SAFE_TE/SAFE_RTC/NOMAD_RAW',
            GRAPH_BETTER='OURS goal >= ASTAR goal AND collisions <= AND (goal > OR paired both-success goal-time median <0)',
            GRAPH_EQUAL='abs(goal difference)<=1 AND collisions equal, after BETTER',GRAPH_WORSE='otherwise',
            incomplete='pending; do not impute unknown collisions as zero',McNemar='exact two-sided binomial discordant pairs, reference only'),
        frozen_sources=frozen,source_sha256={str(f.relative_to(ROOT)):sha256_file(f) for f in HERE.glob('*.py')})
    save(HERE/'protocol.json',protocol)
    print(json.dumps(dict(protocol_sha256=sha256_file(HERE/'protocol.json'),planned=75,smokes=4)))
if __name__=='__main__':freeze()
