"""Persistent 20 Hz race relay on the same port as the existing car service."""
import asyncio, contextlib, json, threading, time
from aiohttp import web, ClientSession, ClientTimeout, WSMsgType
from matchmaking import MatchError

def create_app(matches, catalog_port):
    app=web.Application(client_max_size=105*1024*1024)
    streams={}
    async def lifetime(app):
        async with ClientSession(timeout=ClientTimeout(total=190),auto_decompress=False) as session:
            app['http']=session
            yield
        await asyncio.gather(*(ws.close(code=1001) for ws in list(streams.values())),return_exceptions=True)
    app.cleanup_ctx.append(lifetime)
    async def metadata(request):
        return web.json_response(dict(protocol=7,version='1.5.0',protocols=[6,7],queueSeconds=12,seats=6,transport='websocket',snapshotRate=20))
    async def health(request):
        return web.json_response(dict(ok=True,schema=1,matchmaking=7,protocols=[6,7],transport='websocket'))
    async def action(request):
        try:
            if request.content_length is None or request.content_length>32768:raise MatchError(413,'Request too large')
            body=await request.json()
            if not isinstance(body,dict):raise MatchError(400,'Expected an object')
            return web.json_response(matches.request(request.match_info['action'],body,request.remote))
        except MatchError as e:return web.json_response(dict(error=str(e)),status=e.status)
        except (ValueError,TypeError):return web.json_response(dict(error='Invalid request'),status=400)
    async def stream(request):
        ws=web.WebSocketResponse(heartbeat=10,max_msg_size=32768,compress=False)
        await ws.prepare(request);ticket=None;writer=None
        try:
            hello=await asyncio.wait_for(ws.receive_json(),5)
            ticket=hello.get('ticket') if isinstance(hello,dict) else None
            if not isinstance(ticket,str):raise MatchError(401,'Race session required')
            reply=matches.request('poll',hello,request.remote)
            if reply['protocol']!=7:raise MatchError(409,'Update the game')
            old=streams.get(ticket)
            if old:await old.close(code=1000)
            streams[ticket]=ws
            async def send_states():
                while not ws.closed:
                    state=matches.stream_state(ticket)
                    # No outgoing queue: slow consumers get the newest state after each send.
                    await asyncio.wait_for(ws.send_str(json.dumps(state,separators=(',',':'))),2)
                    await asyncio.sleep(.05)
            writer=asyncio.create_task(send_states())
            async def read_inputs():
                window=time.monotonic();count=0
                async for message in ws:
                    if message.type!=WSMsgType.TEXT:break
                    now=time.monotonic()
                    if now-window>=1:window=now;count=0
                    count+=1
                    if count>90:raise MatchError(429,'Too many updates')
                    body=json.loads(message.data)
                    if not isinstance(body,dict):raise MatchError(400,'Invalid input')
                    body['ticket']=ticket
                    matches.request('poll',body,request.remote)
            reader=asyncio.create_task(read_inputs())
            done,pending=await asyncio.wait([reader,writer],return_when=asyncio.FIRST_COMPLETED)
            for task in pending:task.cancel()
            await asyncio.gather(*pending,return_exceptions=True)
            for task in done:task.result()
        except (MatchError,ValueError,TypeError,asyncio.TimeoutError,ConnectionError):
            pass
        finally:
            if writer:writer.cancel()
            if ticket and streams.get(ticket) is ws:streams.pop(ticket,None)
            await ws.close()
        return ws
    async def proxy(request):
        # The legacy admin stays unchanged, bound only to a private loopback port.
        if request.content_length is None and request.can_read_body:raise web.HTTPLengthRequired()
        if request.content_length and request.content_length>105*1024*1024:raise web.HTTPRequestEntityTooLarge(max_size=105*1024*1024,actual_size=request.content_length)
        headers={k:v for k,v in request.headers.items() if k.lower() not in ('host','connection','transfer-encoding','upgrade')}
        url=f'http://127.0.0.1:{catalog_port}'+request.raw_path
        async with app['http'].request(request.method,url,headers=headers,data=request.content if request.can_read_body else None,allow_redirects=False) as upstream:
            response=web.StreamResponse(status=upstream.status,headers={k:v for k,v in upstream.headers.items() if k.lower() not in ('connection','transfer-encoding')})
            await response.prepare(request)
            async for chunk in upstream.content.iter_chunked(65536):await response.write(chunk)
            await response.write_eof();return response
    app.router.add_get('/health',health)
    app.router.add_get('/v1/matchmaking',metadata)
    app.router.add_get('/v1/matchmaking/stream',stream)
    app.router.add_post('/v1/matchmaking/{action}',action)
    app.router.add_route('*','/{path:.*}',proxy)
    return app

def run(catalog_server,matches,host,port):
    thread=threading.Thread(target=catalog_server.serve_forever,daemon=True);thread.start()
    try:web.run_app(create_app(matches,catalog_server.server_port),host=host,port=port,access_log=None)
    finally:catalog_server.shutdown();thread.join(timeout=5)
