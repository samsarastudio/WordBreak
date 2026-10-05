"""Small-beta HTTPS matchmaker and race relay. Physics authority is the elected game client.
Rooms live in one process; use one service replica until a shared room store is added.
"""
import math, secrets, threading, time, os, json

class MatchError(Exception):
    def __init__(self, status, message): self.status=status; super().__init__(message)

class Matchmaker:
    def __init__(self, clock=time.monotonic):
        self.clock=clock; self.lock=threading.RLock(); self.rooms={}; self.tickets={}; self.joins={}; self.rates={}; self.workers={}
    def worker_connect(self, key):
        expected=os.environ.get('RACE_WORKER_KEY','')
        if len(expected)<32 or not isinstance(key,str) or not secrets.compare_digest(key,expected):raise MatchError(401,'Worker authentication failed')
        with self.lock:
            self.cleanup(self.clock())
            if len(self.workers)>=4:raise MatchError(503,'Worker capacity reached')
            token=secrets.token_hex(24);self.workers[token]=dict(seen=self.clock(),room=None)
            return token
    def worker_disconnect(self, token):
        with self.lock:
            worker=self.workers.pop(token,None)
            if worker and worker['room'] in self.rooms:self.rooms[worker['room']]['closed']=True
    def worker_update(self, token, body):
        with self.lock:
            now=self.clock();self.cleanup(now);worker=self.workers.get(token)
            if worker is None:raise MatchError(401,'Worker session expired')
            worker['seen']=now;room=self.rooms.get(worker['room'])
            if not room:return dict(room='',wait=0,seats=[])
            snapshot=body.get('snapshot')
            if snapshot and body.get('room')==room['id']:
                if not isinstance(snapshot,str) or len(snapshot)>24000:raise MatchError(400,'Invalid snapshot')
                try:
                    state=json.loads(snapshot)
                    if len(state['racers'])!=6 or len(state['ack'])!=6 or type(state['tick']) is not int or not math.isfinite(state['time']):raise ValueError()
                    for r in state['racers']:
                        if not all(math.isfinite(r[k]) for k in ('distance','lane','speed')):raise ValueError()
                except (ValueError,TypeError,KeyError):raise MatchError(400,'Invalid snapshot')
                if state['tick']>room.get('tick',-1):
                    room['tick']=state['tick'];room['snapshot']=snapshot;room['seq']+=1;room['stateSeen']=now
            return dict(room=room['id'],wait=max(0,room['start']-now),seats=self.seats(room,now))
    def authority_alive(self, room, now):
        if room['protocol']==8:
            worker=self.workers.get(room.get('worker'))
            return worker is not None and now-worker['seen']<5 and now-room.get('stateSeen',room['created'])<8
        return 0 in room['players'] and now-room['players'][0]['seen']<10
    def cleanup(self, now):
        for token,worker in list(self.workers.items()):
            if now-worker['seen']>5:self.worker_disconnect(token)
        for key,room in list(self.rooms.items()):
            if now-room['created']>240 or room.get('closed') or (room['protocol']==8 and not any(now-p['seen']<10 for p in room['players'].values())):
                for p in room['players'].values(): self.tickets.pop(p['ticket'],None)
                worker=self.workers.get(room.get('worker'))
                if worker:worker['room']=None
                del self.rooms[key]
        self.joins={k:v for k,v in self.joins.items() if v in self.tickets}
        self.rates={k:v for k,v in self.rates.items() if now-v[0]<60}
    def request(self, action, body, ip):
        with self.lock:
            now=self.clock(); self.cleanup(now)
            if action=='join':
                if (body.get('protocol'),body.get('version')) not in ((6,'1.4.0'),(7,'1.5.0'),(8,'1.6.0')): raise MatchError(409,'Update the game to join online races.')
                nonce=body.get('nonce','')
                if not isinstance(nonce,str) or not 16<=len(nonce)<=80: raise MatchError(400,'Invalid join request')
                previous=self.joins.get((ip,nonce))
                if previous: return self.response(*self.tickets[previous],now)
                start,count=self.rates.get(ip,(now,0))
                if now-start>=60:start,count=now,0
                if count>=20:raise MatchError(429,'Too many matchmaking requests. Try again shortly.')
                self.rates[ip]=(start,count+1)
                if len(self.rooms)>=128:raise MatchError(503,'Races are busy. Try again shortly.')
                room=next((r for r in self.rooms.values() if r['protocol']==body['protocol'] and now<r['start'] and len(r['players'])<6 and self.authority_alive(r,now)),None)
                if room is None:
                    worker=None
                    if body['protocol']==8:
                        worker=next((key for key,w in self.workers.items() if w['room'] is None and now-w['seen']<2),None)
                        if worker is None:raise MatchError(503,'Racing is unavailable. Try again shortly.')
                    key=secrets.token_hex(12);room=dict(id=key,protocol=body['protocol'],created=now,start=now+12,players={},snapshot='',seq=0,closed=False);self.rooms[key]=room
                    if worker:room['worker']=worker;self.workers[worker]['room']=key
                slot=next(i for i in range(6) if i not in room['players']);ticket=secrets.token_urlsafe(32)
                player=dict(slot=slot,ticket=ticket,seen=now,input={},inputSeq=0,car='cinder')
                room['players'][slot]=player;self.tickets[ticket]=(room,player);self.joins[(ip,nonce)]=ticket
                return self.response(room,player,now)
            ticket=body.get('ticket','');entry=self.tickets.get(ticket) if isinstance(ticket,str) else None
            if not entry:raise MatchError(401,'Race session expired. Find a new race.')
            room,player=entry
            if action=='leave':
                self.tickets.pop(ticket,None);room['players'].pop(player['slot'],None)
                if player['slot']==0 and room['protocol']!=8:room['closed']=True
                return dict(ok=True)
            if action!='poll':raise MatchError(404,'Unknown matchmaking action')
            if not self.authority_alive(room,now):room['closed']=True;raise MatchError(410,'The race disconnected. Find a new race.')
            player['seen']=now
            raw=body.get('input',{})
            if not isinstance(raw,dict):raise MatchError(400,'Invalid controls')
            control={}
            for name in ('steer','throttle'):
                value=raw.get(name,0)
                if not isinstance(value,(int,float)) or not math.isfinite(value):raise MatchError(400,'Invalid controls')
                control[name]=max(-1,min(1,value))
            for name in ('accelerate','brake','reverse','reset','drift','boost'):control[name]=raw.get(name) is True
            seq=body.get('inputSeq',0)
            if type(seq) is not int or not 0<=seq<=2147483647:raise MatchError(400,'Invalid input sequence')
            if room['protocol']==6 or seq>=player['inputSeq']:
                player['input']=control;player['inputSeq']=seq
            snapshot=body.get('snapshot','')
            if snapshot:
                if player['slot']!=0 or room['protocol']==8:raise MatchError(403,'Only the race authority can publish state')
                if not isinstance(snapshot,str) or len(snapshot)>24000:raise MatchError(400,'Snapshot too large')
                import json
                try:
                    state=json.loads(snapshot)
                    if not isinstance(state,dict) or len(state.get('racers',[]))!=6 or not math.isfinite(state.get('time',float('nan'))):raise ValueError()
                except (ValueError,TypeError):raise MatchError(400,'Invalid race state')
                room['snapshot']=snapshot;room['seq']+=1
            return self.response(room,player,now)
    def seats(self,room,now):
        seats=[]
        for i in range(6):
            p=room['players'].get(i);active=p is not None and now-p['seen']<8
            seats.append(dict(slot=i,active=active,input=p['input'] if active and now-p['seen']<1 else {},inputSeq=p['inputSeq'] if p else 0))
        return seats
    def response(self,room,player,now):
        seats=self.seats(room,now)
        return dict(protocol=room['protocol'],ticket=player['ticket'],room=room['id'],slot=player['slot'],host=player['slot']==0 and room['protocol']!=8,wait=max(0,room['start']-now),humans=sum(p['active'] for p in seats),seats=seats,snapshot=room['snapshot'],seq=room['seq'])

    def stream_state(self,ticket):
        with self.lock:
            now=self.clock();self.cleanup(now)
            entry=self.tickets.get(ticket)
            if not entry:raise MatchError(401,'Race session expired')
            room,player=entry
            if not self.authority_alive(room,now):raise MatchError(410,'Race disconnected')
            if now-player['seen']>10:raise MatchError(408,'Connection timed out')
            return self.response(room,player,now)
