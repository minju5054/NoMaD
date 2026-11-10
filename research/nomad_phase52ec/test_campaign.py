"""Real completed-cache validation; no graph solve is invoked."""
import json,unittest
from .campaign import inputs,cache,status,HEARTBEAT_S

class Tests(unittest.TestCase):
    def test_real_cache_reused_and_no_pending_recomputation(self):
        jobs=inputs();results,pending=cache(jobs)
        self.assertEqual(len(jobs),420);self.assertEqual(len(results),420);self.assertEqual(pending,[])
        self.assertEqual(sum(r['found'] for r in results),398)
        s=status(jobs,results,pending);self.assertEqual(s['remaining'],0);self.assertEqual(s['simulations_started'],0)
        self.assertEqual(HEARTBEAT_S,60.);json.dumps(s)

if __name__=='__main__':unittest.main()
