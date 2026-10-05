"""Small-beta HTTPS matchmaker and race relay. Physics authority is the elected game client.
Rooms live in one process; use one service replica until a shared room store is added.
"""
import math, secrets, threading, time

class MatchError(Exception):
    def __init__(self, status, message): self.status=status; super().__init__(message)

class Matchmaker:
    def __init__(self, clock=time.monotonic):
        self.clock=clock; self.lock=threading.RLock(); self.rooms={}; self.tickets={}; self.joins={}; self.rates={}
    def cleanup(self, now):
        for key,room in list(self.rooms.items()):
            if now-room['created']>240 or room.get('closed'):
                for p in room['players'].values(): self.tickets.pop(p['ticket'],None)
                del self.rooms[key]
        self.joins={k:v for k,v in self.joins.items() if v in self.tickets}
        self.rates={k:v for k,v in self.rates.items() if now-v[0]<60}
    def request(self, action, body, ip):
        with self.lock:
            now=self.clock(); self.cleanup(now)
            if action=='join':
                if body.get('protocol')!=6 or body.get('version')!='1.4.0': raise MatchError(409,'Update the game to join online races.')
                nonce=body.get('nonce','')
                if not isinstance(nonce,str) or not 16<=len(nonce)<=80: raise MatchError(400,'Invalid join request')
                previous=self.joins.get((ip,nonce))
                if previous: return self.response(*self.tickets[previous],now)
                start,count=self.rates.get(ip,(now,0))
                if now-start>=60:start,count=now,0
                if count>=20:raise MatchError(429,'Too many matchmaking requests. Try again shortly.')
                self.rates[ip]=(start,count+1)
                if len(self.rooms)>=128:raise MatchError(503,'Races are busy. Try again shortly.')
                room=next((r for r in self.rooms.values() if now<r['start'] and len(r['players'])<6 and now-r['players'][0]['seen']<5),None)
                if room is None:
                    key=secrets.token_hex(12);room=dict(id=key,created=now,start=now+12,players={},snapshot='',seq=0,closed=False);self.rooms[key]=room
                slot=next(i for i in range(6) if i not in room['players']);ticket=secrets.token_urlsafe(32)
                player=dict(slot=slot,ticket=ticket,seen=now,input={},car='cinder')
                room['players'][slot]=player;self.tickets[ticket]=(room,player);self.joins[(ip,nonce)]=ticket
                return self.response(room,player,now)
            ticket=body.get('ticket','');entry=self.tickets.get(ticket) if isinstance(ticket,str) else None
            if not entry:raise MatchError(401,'Race session expired. Find a new race.')
            room,player=entry
            if action=='leave':
                self.tickets.pop(ticket,None);room['players'].pop(player['slot'],None)
                if player['slot']==0:room['closed']=True
                return dict(ok=True)
            if action!='poll':raise MatchError(404,'Unknown matchmaking action')
            if 0 not in room['players'] or now-room['players'][0]['seen']>10:room['closed']=True;raise MatchError(410,'The race host disconnected. Find a new race.')
            player['seen']=now
            raw=body.get('input',{})
            if not isinstance(raw,dict):raise MatchError(400,'Invalid controls')
            control={}
            for name in ('steer','throttle'):
                value=raw.get(name,0)
                if not isinstance(value,(int,float)) or not math.isfinite(value):raise MatchError(400,'Invalid controls')
                control[name]=max(-1,min(1,value))
            for name in ('accelerate','brake','reverse','reset','drift','boost'):control[name]=raw.get(name) is True
            player['input']=control
            snapshot=body.get('snapshot','')
            if snapshot:
                if player['slot']!=0:raise MatchError(403,'Only the race host can publish state')
                if not isinstance(snapshot,str) or len(snapshot)>24000:raise MatchError(400,'Snapshot too large')
                import json
                try:
                    state=json.loads(snapshot)
                    if not isinstance(state,dict) or len(state.get('racers',[]))!=6 or not math.isfinite(state.get('time',float('nan'))):raise ValueError()
                except (ValueError,TypeError):raise MatchError(400,'Invalid race state')
                room['snapshot']=snapshot;room['seq']+=1
            return self.response(room,player,now)
    def response(self,room,player,now):
        seats=[]
        for i in range(6):
            p=room['players'].get(i);active=p is not None and now-p['seen']<8
            seats.append(dict(slot=i,active=active,input=p['input'] if active and now-p['seen']<1 else {}))
        return dict(ticket=player['ticket'],room=room['id'],slot=player['slot'],host=player['slot']==0,wait=max(0,room['start']-now),humans=sum(p['active'] for p in seats),seats=seats,snapshot=room['snapshot'],seq=room['seq'])
