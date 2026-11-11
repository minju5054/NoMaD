"""Original Phase43 infer/decoder/RNG; supply captured odometry XY to NET."""
from nomad_phase43p import worker as frozen
from nomad_phase40p.launch import bind
from .localization import Localization

def make_policy(native,request_metadata):
    def factory(node_poses):
        return Localization(node_poses,position_provider=lambda:request_metadata()['observation_pose'][:2])
    return bind(frozen.make_policy,Localization=factory)(native,request_metadata)
def main():return bind(frozen.main,make_policy=make_policy)()
if __name__=='__main__':main()
