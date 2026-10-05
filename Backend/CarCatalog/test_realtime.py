import asyncio,json,tempfile,threading,unittest,os
from unittest.mock import patch
from aiohttp.test_utils import TestClient,TestServer
from http.server import ThreadingHTTPServer
from matchmaking import Matchmaker,MatchError
from realtime import create_app
from server import Handler,Catalog

class RealtimeTests(unittest.IsolatedAsyncioTestCase):
 async def asyncSetUp(self):
  self.temp=tempfile.TemporaryDirectory();self.catalog=Catalog(self.temp.name,'missing')
  self.legacy=ThreadingHTTPServer(('127.0.0.1',0),Handler);self.legacy.catalog=self.catalog
  self.thread=threading.Thread(target=self.legacy.serve_forever,daemon=True);self.thread.start()
  self.matches=Matchmaker();self.client=TestClient(TestServer(create_app(self.matches,self.legacy.server_port)));await self.client.start_server()
 async def asyncTearDown(self):
  await self.client.close();self.legacy.shutdown();self.legacy.server_close();self.thread.join();self.catalog.pool.shutdown();self.temp.cleanup()
 async def join(self,n,protocol=7):
  response=await self.client.post('/v1/matchmaking/join',json=dict(protocol=protocol,version='1.5.0' if protocol==7 else '1.4.0',nonce=str(n).zfill(32)))
  self.assertEqual(response.status,200);return await response.json()
 async def test_admin_and_catalog_preserved(self):
  self.assertEqual((await self.client.get('/admin')).status,200)
  self.assertEqual((await self.client.get('/v1/catalog')).status,200)
  self.assertEqual((await self.client.get('/admin/session')).status,401)
  self.assertEqual((await (await self.client.get('/health')).json())['matchmaking'],8)
 async def test_protocols_do_not_mix(self):
  old=await self.join(0,6);new=await self.join(1);self.assertNotEqual(old['room'],new['room'])
 async def test_dedicated_worker_websocket_and_five_players(self):
  with patch.dict(os.environ,{'RACE_WORKER_KEY':'test-only-worker-secret-'*3}):
   worker=await self.client.ws_connect('/v1/matchmaking/worker')
   await worker.send_json(dict(protocol=8,version='1.6.0',key=os.environ['RACE_WORKER_KEY']))
   self.assertEqual((await worker.receive_json(timeout=2))['room'],'')
   peers=[]
   for i in range(5):
    response=await self.client.post('/v1/matchmaking/join',json=dict(protocol=8,version='1.6.0',nonce=str(i).zfill(32)))
    self.assertEqual(response.status,200);peers.append(await response.json())
   self.assertEqual(len({p['room'] for p in peers}),1);self.assertTrue(all(not p['host'] for p in peers))
   await worker.send_json({});assignment=await worker.receive_json(timeout=2)
   self.assertEqual(sum(s['active'] for s in assignment['seats']),5)
   state=json.dumps(dict(time=1,tick=30,ack=[1]*6,racers=[dict(distance=10,lane=0,speed=20)]*6))
   await worker.send_json(dict(room=assignment['room'],snapshot=state));await worker.receive_json(timeout=2)
   streams=[]
   for p in peers:
    ws=await self.client.ws_connect('/v1/matchmaking/stream');streams.append(ws)
    await ws.send_json(dict(ticket=p['ticket'],inputSeq=1,input=dict(accelerate=True)))
    self.assertEqual((await ws.receive_json(timeout=2))['snapshot'],state)
   await self.client.post('/v1/matchmaking/leave',json=dict(ticket=peers[0]['ticket']))
   self.assertEqual(self.matches.stream_state(peers[1]['ticket'])['humans'],4)
   for ws in streams:await ws.close()
   await worker.close()
 async def test_five_streams_relay_and_reject_stale_inputs(self):
  peers=[await self.join(i) for i in range(5)];self.assertEqual(len({p['room'] for p in peers}),1)
  streams=[]
  for p in peers:
   ws=await self.client.ws_connect('/v1/matchmaking/stream');await ws.send_json(dict(ticket=p['ticket'],inputSeq=1,input=dict(steer=.5)));streams.append(ws)
  state=json.dumps(dict(time=1,tick=30,ack=[1]*6,racers=[{}]*6))
  await streams[0].send_json(dict(inputSeq=2,input={},snapshot=state))
  for ws in streams:
   for _ in range(10):
    reply=await ws.receive_json(timeout=2)
    if reply['snapshot']==state:break
   self.assertEqual(reply['snapshot'],state);self.assertEqual(reply['humans'],5)
  await streams[1].send_json(dict(inputSeq=9,input=dict(steer=1)))
  await streams[1].send_json(dict(inputSeq=2,input=dict(steer=-1)))
  await asyncio.sleep(.1)
  reply=self.matches.stream_state(peers[1]['ticket']);self.assertEqual(reply['seats'][1]['inputSeq'],9);self.assertEqual(reply['seats'][1]['input']['steer'],1)
  for ws in streams:await ws.close()
