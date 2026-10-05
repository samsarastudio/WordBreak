import json,os,unittest
from unittest.mock import patch
from matchmaking import Matchmaker,MatchError

class DedicatedTests(unittest.TestCase):
 def setUp(self):
  self.now=100.;self.m=Matchmaker(lambda:self.now)
  self.env=patch.dict(os.environ,{'RACE_WORKER_KEY':'test-only-worker-key-'*3});self.env.start();self.addCleanup(self.env.stop)
 def worker(self):return self.m.worker_connect(os.environ['RACE_WORKER_KEY'])
 def join(self,n=0):return self.m.request('join',dict(protocol=8,version='1.6.0',nonce=str(n).zfill(32)),'test')
 def test_no_worker_no_paid_or_player_fallback(self):
  with self.assertRaises(MatchError) as e:self.join()
  self.assertEqual(e.exception.status,503)
 def test_worker_authentication(self):
  with self.assertRaises(MatchError):self.m.worker_connect('wrong')
 def test_six_players_have_no_authority_and_cannot_publish(self):
  w=self.worker();peers=[self.join(i) for i in range(6)]
  self.assertEqual(len({p['room'] for p in peers}),1)
  for p in peers:
   self.assertFalse(p['host'])
   with self.assertRaises(MatchError) as e:self.m.request('poll',dict(ticket=p['ticket'],snapshot='{}'),'test')
   self.assertEqual(e.exception.status,403)
  with self.assertRaises(MatchError):self.join(7)
  self.assertEqual(self.m.worker_update(w,{})['room'],peers[0]['room'])
 def test_first_player_leaves_room_survives_and_worker_recycles(self):
  w=self.worker();a=self.join();b=self.join(1)
  self.m.request('leave',dict(ticket=a['ticket']),'test')
  self.assertEqual(self.m.stream_state(b['ticket'])['humans'],1)
  self.m.request('leave',dict(ticket=b['ticket']),'test')
  self.assertEqual(self.m.worker_update(w,{})['room'],'')
  self.assertNotEqual(self.join(2)['room'],a['room'])
 def test_worker_disconnect_invalidates_race(self):
  w=self.worker();p=self.join();self.m.worker_disconnect(w)
  with self.assertRaises(MatchError):self.m.stream_state(p['ticket'])
 def test_only_assigned_room_gets_snapshot_and_inputs(self):
  w=self.worker();p=self.join();self.m.request('poll',dict(ticket=p['ticket'],inputSeq=7,input=dict(steer=.5)),'test')
  state=json.dumps(dict(tick=1,time=-10,ack=[7,0,0,0,0,0],racers=[dict(distance=0,lane=0,speed=0)]*6))
  self.m.worker_update(w,dict(room='wrong',snapshot=state));self.assertEqual(self.m.stream_state(p['ticket'])['snapshot'],'')
  assignment=self.m.worker_update(w,dict(room=p['room'],snapshot=state))
  self.assertEqual(assignment['seats'][0]['inputSeq'],7)
  self.assertEqual(self.m.stream_state(p['ticket'])['snapshot'],state)
  self.m.worker_update(w,dict(room=p['room'],snapshot=state));self.assertEqual(self.m.stream_state(p['ticket'])['seq'],1)
 def test_stale_worker_rejected(self):
  self.worker();p=self.join();self.now+=6
  with self.assertRaises(MatchError):self.m.stream_state(p['ticket'])
 def test_stale_physics_rejected_even_with_heartbeat(self):
  w=self.worker();p=self.join()
  for _ in range(3):self.now+=3;self.m.worker_update(w,{})
  with self.assertRaises(MatchError):self.m.stream_state(p['ticket'])

if __name__=='__main__':unittest.main()
