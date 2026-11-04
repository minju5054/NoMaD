"""Certificate-filtered anytime alternatives, preserving per-start priority."""
import time
from .safety import certificate

class CandidateBank:
    def __init__(self,B,base,strict,deadline):
        self.B=B;self.base=base;self.strict=strict;self.deadline=deadline;self.feasible={};self.tolerated={};self.seen={};self.rejected=[];self.raw_best=None;self.late_certificates=0
    def ingest(self,message):
        index=message['index']
        if 'last_candidate' in message and message['last_candidate'] is None:self.tolerated.pop(index,None)
        source=message if message['kind']=='FEASIBLE' else message.get('last_candidate')
        if source is None:return
        kind='FEASIBLE' if message['kind']=='FEASIBLE' else 'KINEMATIC_TOLERATED';candidate=dict(source,index=index,output_type=kind)
        key=(index,kind,candidate['ready_ns'])
        if key not in self.seen:self.seen[key]=certificate(candidate['path'],self.B,self.base,self.strict)
        if time.monotonic_ns()>self.deadline:self.late_certificates+=1;return
        check=self.seen[key]
        rank=lambda r:(r['output_type']!='FEASIBLE',r['cost'],r['index'])
        if self.raw_best is None or rank(candidate)<rank(self.raw_best):self.raw_best=candidate
        if not check['passed']:
            if not any(r['key']==key for r in self.rejected):self.rejected.append(dict(key=key,index=index,output_type=kind,certificate=check))
            if kind!='FEASIBLE':self.tolerated.pop(index,None)
            return
        candidate['certificate']=check
        if kind=='FEASIBLE':
            previous=self.feasible.get(index)
            if previous is None or candidate['cost']<previous['cost']:self.feasible[index]=candidate
        else:self.tolerated[index]=candidate
    def alternatives(self):
        values=list(self.feasible.values())+[r for i,r in self.tolerated.items() if i not in self.feasible]
        return sorted(values,key=lambda r:(r['output_type']!='FEASIBLE',r['cost'],r['index']))
    def statistics(self):
        alternatives=self.alternatives();chosen=alternatives[0] if alternatives else None
        return dict(certificate_rejections=len(self.rejected),certificate_rejection_details=self.rejected,
            alternative_initializer_used=bool(chosen and self.raw_best and chosen['index']!=self.raw_best['index']),raw_best_index=self.raw_best['index'] if self.raw_best else None,late_certificates=self.late_certificates)
