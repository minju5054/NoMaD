"""Observer-only stage instrumentation and the registered timing exceptions."""
import ast,copy,inspect,textwrap,threading,time
from contextlib import contextmanager
from types import FunctionType
import numpy as np
from scipy.optimize import minimize as scipy_minimize
from nomad_phase28 import graph_r1,tracking
from nomad_phase28.graph import certificate as frozen_certificate

BUDGET_S=.30
APPLY_TICKS=24
LOCAL=threading.local()

def now():return time.perf_counter_ns()
def stage(name):
    @contextmanager
    def measured():
        a=now();cpu=time.process_time_ns()
        record=getattr(LOCAL,'record',None)
        if record is not None:record.setdefault('stage_stack',[]).append(name)
        try:yield
        finally:
            record=getattr(LOCAL,'record',None)
            if record is not None:
                record['stages'].append(dict(name=name,start_ns=a,end_ns=now(),cpu_ns=time.process_time_ns()-cpu));record['stage_stack'].pop()
    return measured()

def measured_na_initial(*a,**kw):
    with stage('na_initial_72hz'):return graph_r1.na_initial(*a,**kw)

INITIAL=FunctionType(graph_r1.R1Graph.initial.__code__,dict(graph_r1.R1Graph.initial.__globals__,na_initial=measured_na_initial),graph_r1.R1Graph.initial.__name__,graph_r1.R1Graph.initial.__defaults__,graph_r1.R1Graph.initial.__closure__)

class InstrumentedGraph(graph_r1.R1Graph):
    def __init__(self,*a,**kw):
        with stage('graph_construct'):super().__init__(*a,**kw)
        LOCAL.graph=self
    def check(self):
        try:return super().check()
        except TimeoutError:
            r=getattr(LOCAL,'record',None)
            if r is not None and 'timeout_ns' not in r:
                r['timeout_ns']=now();r['timeout_stage']=(r.get('stage_stack') or ['BETWEEN_STAGES'])[-1]
            raise
    def initial(self,*a,**kw):
        with stage('initialization_total'):return INITIAL(self,*a,**kw)
    def scaled_objective(self,z):
        LOCAL.record['objective_evaluations']+=1;return super().scaled_objective(z)
    def scaled_constraints(self,z):
        LOCAL.record['constraint_evaluations']+=1;return super().scaled_constraints(z)
    def observe(self,x):
        record=LOCAL.record;t=now();previous=record.get('last_iteration_ns',record.get('slsqp_start_ns',t))
        cpu=time.process_time_ns();last_cpu=record.get('last_iteration_cpu_ns',record.get('slsqp_cpu_start_ns',cpu))
        record['iterations'].append(dict(iteration=len(record['iterations'])+1,at_ns=t,interval_ns=t-previous,cpu_ns=cpu,cpu_interval_ns=cpu-last_cpu))
        record['last_iteration_ns']=t
        record['last_iteration_cpu_ns']=cpu
        return super().observe(x)

def measured_minimize(*a,**kw):
    record=LOCAL.record;record['slsqp_start_ns']=now();record['slsqp_cpu_start_ns']=time.process_time_ns();record['in_slsqp']=True
    try:
        with stage('slsqp'):result=scipy_minimize(*a,**kw)
        record['returned_nit']=int(result.nit);record['returned_status']=int(result.status)
        return result
    finally:record['in_slsqp']=False

def measured_certificate(*a,**kw):
    record=LOCAL.record;which='initial_certificate' if 'slsqp_start_ns' not in record else 'optimized_certificate'
    with stage(which):return frozen_certificate(*a,**kw)

class BudgetOnly(ast.NodeTransformer):
    def __init__(self,budget):self.budget=budget;self.count=0
    def visit_Constant(self,node):
        if isinstance(node.value,float) and node.value==.15:
            self.count+=1;return ast.copy_location(ast.Constant(self.budget),node)
        return node

def clone_solver(budget,observed=True):
    source=textwrap.dedent(inspect.getsource(graph_r1.solve));tree=ast.parse(source);rewrite=BudgetOnly(budget);tree=rewrite.visit(tree)
    assert rewrite.count==3,'Only the deadline and two over-deadline comparisons may change'
    ns=dict(graph_r1.solve.__globals__)
    if observed:ns.update(R1Graph=InstrumentedGraph,minimize=measured_minimize,certificate=measured_certificate)
    exec(compile(ast.fix_missing_locations(tree),graph_r1.__file__+'[timing-only]','exec'),ns)
    return ns['solve'],rewrite.count

SOLVE,_=clone_solver(BUDGET_S)

def solve(B,vw,path,field,alpha,warm=None,started=None):
    record=dict(worker_solver_enter_ns=now(),stages=[],iterations=[],objective_evaluations=0,constraint_evaluations=0)
    LOCAL.record=record;LOCAL.graph=None
    try:
        result=SOLVE(B,vw,path,field,alpha,warm,started)
        record['worker_solver_return_ns']=now();record['completed_major_iterations']=len(record['iterations'])
        record['iterations_at_timeout']=len(record['iterations']) if result['disposition']=='TIMEOUT' else None
        if result['disposition']=='TIMEOUT' and 'timeout_ns' not in record:record.update(timeout_ns=now(),timeout_stage='RETURN_DEADLINE_CHECK')
        record['timeout_iteration_note']='Last completed major callback count; internal line-search/minor iteration is not exposed by SciPy'
        record['solver_started']='slsqp_start_ns' in record
        result['timing']=record
        return result
    finally:LOCAL.record=None;LOCAL.graph=None

def apply_tick(dispatch_tick):
    assert int(dispatch_tick)%8==0,'Dispatch must be an eligible9Hz tick'
    return int(dispatch_tick)+APPLY_TICKS

PREDICT=FunctionType(tracking.predict.__code__,dict(tracking.predict.__globals__,apply_tick=apply_tick),tracking.predict.__name__,tracking.predict.__defaults__,tracking.predict.__closure__)

def predict(*a,**kw):
    begin=now();r=PREDICT(*a,**kw);end=now();LOCAL.prediction=dict(start_ns=begin,end_ns=end)
    return dict(r,timing=dict(B_prediction_start_ns=begin,B_prediction_end_ns=end))

def application_certificate(*a,**kw):
    start=now();r=frozen_certificate(*a,**kw)
    return dict(r,timing=dict(application_certificate_start_ns=start,application_certificate_end_ns=now()))
