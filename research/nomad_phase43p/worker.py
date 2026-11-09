"""Existing NoMaD worker, selected-condition localization replacement only."""
import json,time
from pathlib import Path
from types import FunctionType
from .localization import Localization


def make_policy(native,request_metadata):
    class Policy(native.TopomapPolicy):
        def __init__(self,manifest_path):
            super().__init__(manifest_path)
            nodes=json.loads(Path(manifest_path).read_text())['nodes']
            assert [n['node_id'] for n in nodes]==list(range(len(self.images)))
            self.localization=Localization([n['world_pose'] for n in nodes])

        def infer(self,model,observations,noise,scheduler_seed):
            start,end=self.localization.window();begin=time.monotonic_ns()
            condition,distance,obs,goals=native.encode_candidates(model,observations,self.images[start:end+1])
            values=distance.detach().flatten().cpu().numpy()
            request=request_metadata()
            selection=self.localization.select(values,request['hmm_odometry_total_m'])
            selected_id=selection['selected_subgoal_id'];sg_idx=selection.pop('selected_condition_index')
            self.closest_node=selection['closest_node'];selected=condition[sg_idx].unsqueeze(0)
            selection_time=time.monotonic_ns()
            result=native.diffuse_condition(model,selected,noise,scheduler_seed)
            native.torch.cuda.synchronize();end_ns=time.monotonic_ns()
            metadata=dict(selection,previous_subgoal_id=self.previous_subgoal,
                subgoal_changed=self.previous_subgoal!=selected_id,
                closest_moved_backward=self.closest_node<selection['previous_closest_node'],
                subgoal_moved_backward=self.previous_subgoal is not None and selected_id<self.previous_subgoal,
                selection_monotonic_ns=selection_time,selected_subgoal_image=self.hashes[selected_id],
                candidate_encoding_and_selection_ms=(selection_time-begin)/1e6,
                diffusion_and_action_ms=(end_ns-selection_time)/1e6,diffusion_passes=1,num_diffusion_steps_unchanged=True,
                diffusion_steps=native.CONFIG['num_diffusion_iters'])
            metadata['hmm']['odometry_tick']=request['hmm_odometry_tick']
            self.previous_subgoal=selected_id
            result.update(condition=selected.detach(),distance=distance.detach(),observation=obs,goal=goals[sg_idx:sg_idx+1])
            return result,metadata
    return Policy


def main():
    from nomad_isaac import worker as frozen,topomap_inference as native
    current={}
    def receive(*args,**kwargs):
        metadata,arrays=frozen.receive_packet(*args,**kwargs)
        current.clear();current.update(metadata)
        return metadata,arrays
    native.TopomapPolicy=make_policy(native,lambda:current)
    fn=frozen.main
    FunctionType(fn.__code__,dict(fn.__globals__,receive_packet=receive),fn.__name__,fn.__defaults__,fn.__closure__)()


if __name__=='__main__':main()
