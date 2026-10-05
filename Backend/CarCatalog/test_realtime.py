import asyncio,json,tempfile,threading,unittest
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
  self.assertEqual((await (await self.client.get('/health')).json())['matchmaking'],7)
 async def test_protocols_do_not_mix(self):
  old=await self.join(0,6);new=await self.join(1);self.assertNotEqual(old['room'],new['room'])
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
