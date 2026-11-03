"""Mode-conditional offline report; post-passage cases never enter the gate."""
import json
from pathlib import Path
from collections import Counter
import numpy as np
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase23.report import csv_write
from nomad_phase17.report import table
from nomad_phase23o2.report import plan_passage
from .inputs import HERE,OUT,read,write

DEFINITION=r'''
## Input/output pipeline

| Stage | Inputs | Output |
|---|---|---|
| Decision D | Current8NoMaD candidates, observed depth, current execution state; depth-component history and odometry for the frozen20Fdirection rule | NORMAL reference r and sigma_r, or DETOUR u_ref |
| Single graph G | Predicted application pose/speed at+0.5s, base depth V1 SDF, r/sigma_r or u_ref | Eleven SE(2)poses, ten dt values, FEASIBLE / KINEMATIC_TOLERATED / STOP |
| Executor | Pose/dt trajectory and current pose/speed | Protected PP(.25m) steering, arclength-interpolated graph speed; graph omega for rotation segments |
| Evaluation only | Oracle boxes/walls, next-Topomap-node direction, saved source outcomes | Collision, clearance, progress and passage measurements |

| Mode | Entry/meaning | Reference |
|---|---|---|
| NORMAL | Ordinary operation | FRESHEST among native depth-safe suffixes; if none safe, FRESHEST among all8; no ALL_UNSAFE stop or R2 repair |
| DETOUR | Frozen20Ftrigger B or no NORMAL graph output within0.5s | Component-frozen preappearance u_ref and1.2m progress target; no path prior |
| Return to NORMAL | Frozen20F: no new obstacle ahead, endpoint,6s, or current depth safety failure | Next NORMAL candidate reference |
| Last resort | Registered no-output/fallback handling | Existing RECOVER_ROTATE, counted separately |

| Prior mechanism | New location |
|---|---|
| FRESHEST/depth selection | Decision D; reference and at most2alternative safe seeds |
| New-obstacle NO_PROGRESS, u_ref, handover | Decision D, frozen20Fconditions |
| Safety correction, kinematics, travel time | Graph factors in both modes |
| Mixed/Cauchy/history priors and learned F7direction | Removed |
| ALL_UNSAFE trigger and R2 repair | Removed |
| SP and start alignment | Removed from Gexecution; replaced by optimized speed/rotation |
| Rotation recovery | Decision D's last resort |
| A* | Comparison C1only; never a Gseed or fallback |

## Full graph definition

Let p0=0,theta0=0 in the predicted application-B frame; variables are (p_i,theta_i),i=1..10 and dt_i,i=0..9. The snapshot SDF already subtracts robot radius0.09m. All Ginput geometry is observed depth, not oracle geometry.

NORMAL reference: protected B-suffix projection, prepend B and arclength-resample to11positions (B+10future points). Short suffixes use the original allowed OLD supplementation; A*-derived OLD is withheld. sigma_r=clip(median_i sqrt(Var_j(x_ji)+Var_j(y_ji)),0.03,0.15), using the same prepared current8candidate dispersion as23-O.

$$J_{ref,N}=\sum_{i=1}^{10}\|p_i-r_i\|^2/\sigma_r^2+\|p_{10}-r_{10}\|^2/0.3^2.$$

DETOUR has no path or endpoint prior:
$$J_{ref,D}=[\max(0,1.2-(p_{10}-p_0)\cdot u_{ref})/0.10]^2.$$

Obstacle queries Q contain11nodes and10segment midpoints. Hard d(q)>=m(q), where m=min(0.025,max(0,d(B)-0.005)) on the first0.30m of current trajectory arclength, otherwise0.025m. Soft
$$J_{obs}=\sum_{q\in Q}[\max(0,0.15-d(q))/0.05]^2.$$
This is the inherited node/midpoint test, not a continuous collision certificate.

For segment l_i=|p_{i+1}-p_i|, v_i=l_i/dt_i and omega_i=wrap(theta_{i+1}-theta_i)/dt_i. Hard v_i<=0.3, |omega_i|<=0.4, dt_i in[0.05,1]. Initial acceleration a0=(v0-v_actual)/dt0; later a_i=2(v_i-v_{i-1})/(dt_i+dt_{i-1}). Soft acceleration, including the initial-speed boundary:
$$J_a=\sum_i[\max(0,|a_i|-0.5)/0.05]^2.$$

Frozen TEB-style soft terms, sigma_nh=0.03m:
$$r_{nh,i}=((\cos\theta_i+\cos\theta_{i+1})\delta y_i-(\sin\theta_i+\sin\theta_{i+1})\delta x_i)/0.03,$$
$$r_{back,i}=\min(0,\delta p_i\cdot[\cos\theta_i,\sin\theta_i])/0.03.$$
$$J_{motion,time}=J_a+\sum_i(r_{nh,i}^2+r_{back,i}^2)+1.0\sum_i dt_i+0.01\sum_i(\kappa_{i+1}-\kappa_i)^2.$$
The last sum uses the frozen Menger valid-chord mask (>=1cm); rotation segments are not assigned fabricated curvature. Total J=J_ref,mode+J_obs+J_motion,time. There is no max-mixture, Cauchy, memory prior or F7.

NORMAL starts: r, nonempty current OLD remainder (unless A*-derived), then the next2safe candidates ranked by remaining length/index. DETOUR starts: the unchanged1.5m straight fans at0,+30,-30,+60,-60,+90,-90degrees around u_ref, with11points. SLSQP, analytic Jacobians, maxiter100, ftol1e-8,4workers, shared0.5s. The same frozen initializer creates pose headings/time guesses; no native yaw/timing is assumed.

Output policy is exactly23-O3: choose the least-cost received feasible iterate; otherwise the least-cost last available iterate with every F2slack>=0 and v<=0.33,|omega|<=0.44,dt in[0.045,1.1]; otherwise STOP. The optimizer itself keeps the strict bounds. The executor retains v<=0.3,|omega|<=0.4,acceleration<=0.5. Translation uses PPdirection and graph speed by arclength; rotation uses graph omega. No SP/start-alignment fallback is added to G.

## Why decisions are outside the graph

The preserved23-O3registered GO_ONLINE used8already-passed snapshots. The corrected pre-passage label is PRE_PASSAGE_NO_GO: U3planned0/16, C0planned2/16, C1planned3/16. In the frozen diagnostic,13/16intent directions differed from corridor+x by>=45degrees. All5converted comparator detours cost more than U3; F7was the largest increasing term inall5. Additional seeds retained feasible passage candidates but the objective selected none. These are diagnostic findings, not evidence of improved obstacle avoidance. Phase24therefore supplies intent through Dand keeps physical trajectory generation in one graph.
'''

def summarize(rows):
    result=[]
    for group in ('STATIC','PRE_PASSAGE','PRE_SPAWN','ALREADY_PASSED'):
        for method in ('G','C0','C1','U'):
            rr=[r for r in rows if r['input_stage']==group and r['method']==method]
            if not rr:continue
            median=lambda k:float(np.median([r[k] for r in rr if r.get(k) is not None])) if any(r.get(k) is not None for r in rr) else None
            result.append(dict(group=group,method=method,n=len(rr),collisions=sum(r['oracle_collision'] for r in rr),min_clearance_median_m=median('oracle_minimum_clearance_m'),omega_saturation_median=median('omega_saturation_fraction'),
                planned_passage=sum(bool(r.get('planned_box_passage')) for r in rr),rollout_passage=sum(bool(r.get('box_passage')) for r in rr),progress_median=median('progress'),
                output_counts=dict(Counter(r['output_type'] for r in rr)),stop_fraction=sum(r['output_type']=='STOP' for r in rr)/len(rr),compute_p50_s=median('compute_s'),compute_p95_s=float(np.quantile([r['compute_s'] for r in rr],.95))))
    return result

def gate(rows,scope):
    assert scope in ('STATIC_AND_PRE_PASSAGE','PRE_PASSAGE_ONLY')
    pre=lambda method:[r for r in rows if r['method']==method and r['input_stage']=='PRE_PASSAGE']
    static=lambda method:[r for r in rows if r['method']==method and r['input_stage']=='STATIC']
    cohort=[r for r in rows if r['method']=='G' and r['input_stage'] in (('STATIC','PRE_PASSAGE') if scope=='STATIC_AND_PRE_PASSAGE' else ('PRE_PASSAGE',))]
    g,c=pre('G'),pre('C0');gs,cs=static('G'),static('C0')
    values=dict(pre_passage_n=len(g),G_planned_passage=sum(bool(r['planned_box_passage']) for r in g),C0_planned_passage=sum(bool(r['planned_box_passage']) for r in c),
        static_n=len(gs),G_static_collisions=sum(r['oracle_collision'] for r in gs),C0_static_collisions=sum(r['oracle_collision'] for r in cs),
        stop_timing_n=len(cohort),stop_fraction=sum(r['output_type']=='STOP' for r in cohort)/len(cohort),compute_p95_s=float(np.quantile([r['compute_s'] for r in cohort],.95)))
    checks=dict(passage=values['G_planned_passage']>=values['C0_planned_passage'],static_collision=values['G_static_collisions']<=values['C0_static_collisions'],stop=values['stop_fraction']<=.10,timing=values['compute_p95_s']<=.5)
    return dict(label='GO_ONLINE' if all(checks.values()) else 'NO_GO',scope=scope,conditions=checks,failed=[k for k,v in checks.items() if not v],**values)

def generate(protocol,records):
    rows=[]
    for record in records:
        for name,value in record['methods'].items():rows.append(dict(value['row'],method=name,input_stage=record['case']['input_stage']))
    summary=summarize(rows);verdict=gate(rows,protocol['gate_stop_timing_scope']);csv_write(OUT/'snapshots.csv',rows);csv_write(OUT/'summary.csv',summary);write(OUT/'gate.json',verdict)
    pictures=plots(records,protocol['figures'])
    text='# Phase24 — decision layer and one SE(2)graph\n\n'+DEFINITION+'\n## Registered offline interpretation\n\n'+str(protocol['offline_decisions'])+'\n\nMode is fixed per snapshot; this counterfactual does not replay G-induced transitions, next NoMaD inputs or recovery outcomes. The same reused training set has informed earlier designs, so this is not a held-out confirmation.\n\n'
    text+='## Offline comparisons\n\n'+table(summary)+'\n\n## Gate (post-passage excluded)\n\n'+table([dict(criterion=k,passed=v) for k,v in verdict['conditions'].items()])+'\n\n'+str({k:v for k,v in verdict.items() if k not in ('conditions',)})+'\n\n'
    for picture in pictures:text+=f'![{picture}](../research/results/phase24_offline/{picture})\n\n'
    text+='No new inference, renderer or navigation was used in this offline check. '
    text+='NO_GO: online preparation is not performed.\n' if verdict['label']=='NO_GO' else 'GO_ONLINE: permits pilot preparation/smoke only; the main24runs remain user-run.\n'
    (ROOT/'docs/PHASE24_DECISION_GRAPH.md').write_text(text);return verdict

def plots(records,identities):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon
    from nomad_phase22.drive_geometry import corners
    from nomad_phase16.geometry import centered
    from nomad_isaac.clearance import configured_obstacles
    by={r['case']['case_id']:r for r in records};colors=dict(G='seagreen',C0='darkorange',C1='steelblue',U='purple');files=[]
    for identity in identities:
        record=by[identity];c=record['case'];plan=record['methods']['G']['plan'];B=np.asarray(plan['B_pred']);points=[B[None,:2]];fig,ax=plt.subplots(figsize=(9,6),constrained_layout=True)
        for box in configured_obstacles(c['oracle_config']):q=corners(box);points.append(q);ax.add_patch(Polygon(q,color='.3',alpha=.3))
        cfg,offset=centered(c['oracle_config']);co=cfg['corridor'];wall=np.array([[co['xmin'],-co['half_width']],[co['xmax'],-co['half_width']],[co['xmax'],co['half_width']],[co['xmin'],co['half_width']],[co['xmin'],-co['half_width']]])+[0,offset];ax.plot(*wall.T,c='.4')
        if plan.get('reference') is not None:q=np.asarray(plan['reference']);points.append(q);ax.plot(*q.T,':',c='black',lw=2,label='NORMAL reference')
        if plan.get('u_ref') is not None:u=np.asarray(plan['u_ref']);ax.quiver(B[0],B[1],*.6*u,angles='xy',scale_units='xy',scale=1,color='crimson',label='D u_ref');ax.scatter(*(B[:2]+1.2*u),marker='o',facecolors='none',edgecolors='crimson',label='Progress target')
        for name,value in record['methods'].items():
            if value['plan'].get('path') is not None:q=np.asarray(value['plan']['path']);points.append(q);ax.plot(*q.T,'--',color=colors[name],alpha=.7)
            q=np.asarray(value['trace']);points.append(q[:,:2]);ax.plot(q[:,0],q[:,1],c=colors[name],lw=1.6,label=name+' rollout')
        q=np.concatenate(points);lo=q.min(axis=0)-.35;hi=q.max(axis=0)+.35;ax.set_xlim(lo[0],hi[0]);ax.set_ylim(lo[1],hi[1]);ax.set_aspect('equal');ax.scatter(*B[:2],c='black',marker='x',label='Application B');ax.legend(loc='upper left',bbox_to_anchor=(1.01,1),fontsize=8);ax.set_title(c['scene']+' '+identity+' '+plan['mode']);ax.set_xlabel('World x(m)');ax.set_ylabel('World y(m)')
        filename='example_'+identity+'.png';fig.savefig(OUT/filename,dpi=140);plt.close(fig);files.append(filename)
    return files
