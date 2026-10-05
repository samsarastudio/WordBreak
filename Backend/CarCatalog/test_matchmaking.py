import json, unittest
from matchmaking import Matchmaker, MatchError
class MatchTests(unittest.TestCase):
 def setUp(self):self.now=0;self.m=Matchmaker(lambda:self.now)
 def join(self,n=0):return self.m.request('join',dict(protocol=6,version='1.4.0',nonce=str(n).zfill(32)),'test')
 def poll(self,p,**kw):return self.m.request('poll',dict(ticket=p['ticket'],**kw),'test')
 def test_queue_fill_and_start(self):
  players=[self.join(i) for i in range(6)];self.assertEqual(len({p['room'] for p in players}),1);self.assertEqual(players[-1]['humans'],6);self.assertNotEqual(self.join(7)['room'],players[0]['room'])
 def test_join_is_idempotent(self):self.assertEqual(self.join()['ticket'],self.join()['ticket'])
 def test_no_humans_still_starts(self):
  p=self.join();self.now=7;self.poll(p);self.now=13;r=self.poll(p);self.assertEqual(r['wait'],0);self.assertEqual(r['humans'],1);self.assertEqual(sum(not x['active'] for x in r['seats']),5)
 def test_locked_roster_after_countdown(self):
  p=self.join();self.now=7;self.poll(p);self.now=13;self.poll(p);self.assertNotEqual(p['room'],self.join(1)['room'])
 def test_guest_cannot_publish(self):
  self.join();p=self.join(1)
  with self.assertRaises(MatchError):self.poll(p,snapshot='{}')
 def test_tickets_and_versions(self):
  with self.assertRaises(MatchError):self.poll(dict(ticket='wrong'))
  with self.assertRaises(MatchError):self.m.request('join',dict(protocol=5),'test')
 def test_state_relay_and_input_timeout(self):
  host=self.join();guest=self.join(1);self.poll(guest,input=dict(steer=4,throttle=-2,boost=True));state=json.dumps(dict(time=1,racers=[{}]*6));r=self.poll(host,snapshot=state);self.assertEqual(r['seats'][1]['input']['steer'],1);self.assertEqual(self.poll(guest)['snapshot'],state);self.now=2;r=self.poll(host);self.assertEqual(r['seats'][1]['input'],{})
 def test_expired_session(self):
  p=self.join();self.now=241
  with self.assertRaises(MatchError):self.poll(p)
if __name__=='__main__':unittest.main()
