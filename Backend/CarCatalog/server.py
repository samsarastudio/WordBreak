"""Dependency-free beta car catalog. Run with Python 3.11+ and Blender installed."""
import argparse, concurrent.futures, hashlib, hmac, json, os, re, secrets, shutil
import subprocess, sys, tempfile, threading, time, zipfile
from wheel_repair import validate_regions
from matchmaking import Matchmaker, MatchError
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit, parse_qs

HERE = Path(__file__).resolve().parent
MAX_UPLOAD = 100 * 1024 * 1024
BUILTINS = [('cinder', 'Cinder Disaster GT'), ('kenney-hatchback-sports', 'Hatchback Sports'),
            ('kenney-sedan', 'Sedan'), ('kenney-suv', 'SUV'), ('kenney-suv-luxury', 'Luxury SUV'),
            ('kenney-race-future', 'Future Racer')]

def atomic_json(path, data):
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(data, indent=2), encoding='utf-8')
    os.replace(temp, path)

def extract_model(archive, destination):
    """Only copy model/image data; never execute scripts or trust archive paths."""
    with zipfile.ZipFile(archive) as z:
        entries = z.infolist()
        if len(entries) > 2000 or sum(x.file_size for x in entries) > 400 * 1024 * 1024:
            raise ValueError('ZIP exceeds extracted size or file-count limit')
        seen = set()
        for info in entries:
            path = PurePosixPath(info.filename.replace('\\', '/'))
            if path.is_absolute() or '..' in path.parts or ':' in str(path) or (info.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError('Unsafe ZIP path')
            if str(path).lower() in seen:
                raise ValueError('Duplicate ZIP path')
            seen.add(str(path).lower())
            if info.flag_bits & 1:
                raise ValueError('Encrypted ZIP is unsupported')
            if info.is_dir():
                continue
            if path.suffix.lower() not in {'.fbx', '.glb', '.png', '.jpg', '.jpeg', '.tga', '.webp'}:
                continue
            target = destination.joinpath(*path.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            with z.open(info) as src, target.open('wb') as dst:
                shutil.copyfileobj(src, dst)
    models = [p for p in destination.rglob('*') if p.suffix.lower() in {'.fbx', '.glb'}]
    if len(models) != 1:
        raise ValueError('ZIP must contain exactly one FBX or GLB model and its textures')
    return models[0]

class Catalog:
    def __init__(self, root, blender):
        self.root = Path(root).resolve(); self.root.mkdir(parents=True, exist_ok=True)
        (self.root / 'packages').mkdir(exist_ok=True)
        self.blender = blender; self.lock = threading.RLock()
        self.pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        self.jobs = {}; self.path = self.root / 'catalog.json'
        token_path = self.root / 'admin-token.txt'
        if not token_path.exists():
            token_path.write_text(secrets.token_urlsafe(32), encoding='utf-8')
            try: token_path.chmod(0o600)
            except OSError: pass
        self.token = os.environ.get('CAR_ADMIN_TOKEN') or token_path.read_text().strip()
        if not self.path.exists():
            atomic_json(self.path, dict(schema=1, revision=1, defaultRevision=1, defaultCarId='cinder',
                forceDefault=False, cars=[dict(id=i, name=n, builtin=i, enabled=True, order=j) for j,(i,n) in enumerate(BUILTINS)]))
        self.data = json.loads(self.path.read_text(encoding='utf-8'))

    def snapshot(self):
        with self.lock: return json.loads(json.dumps(self.data))

    def previews(self):
        registry_path=self.root/'builtin-previews.json'
        registry=json.loads(registry_path.read_text()) if registry_path.exists() else {}
        result={}
        for car in self.snapshot()['cars']:
            metadata=registry.get(car.get('builtin'),{}) if car.get('builtin') else car
            digest=metadata.get('sha256')
            if not digest or not re.fullmatch('[0-9a-f]{64}',digest):continue
            images={view:f'/previews/{digest}/{view}.jpg' for view in ('hero','front','rear','left','right') if (self.root/'previews'/digest/(view+'.jpg')).exists()}
            result[car['id']]=dict(package=f'/packages/{digest}.wbcar',images=images,triangles=metadata.get('triangles'),wheelCount=metadata.get('wheelCount'),width=metadata.get('width'),height=metadata.get('height'),length=metadata.get('length'))
        return result

    def render_previews(self, package, digest):
        """Render once per immutable model; both upload and wheel repair share this path."""
        destination=self.root/'previews'/digest
        complete=lambda: all((destination/(view+'.jpg')).is_file() for view in ('hero','front','rear','left','right'))
        if complete():return True
        try:
            result=subprocess.run([self.blender,'--background','--factory-startup','--disable-autoexec','--threads','2','--python-exit-code','1',
                '--python',str(HERE/'render_preview.py'),'--',str(package),str(destination)],
                capture_output=True,text=True,timeout=240,encoding='utf-8',errors='replace')
            (self.root/'last-preview.log').write_text(result.stdout+'\n'+result.stderr,encoding='utf-8')
            return result.returncode==0 and complete()
        except (subprocess.TimeoutExpired,OSError) as error:
            (self.root/'last-preview.log').write_text(str(error),encoding='utf-8')
            return False

    def edit(self, body):
        with self.lock:
            current = self.snapshot()
            if body.get('revision') != current['revision']:
                raise ValueError('Catalog changed; refresh the admin page and retry')
            changes = body.get('cars', [])
            if not isinstance(changes, list): raise ValueError('cars must be a list')
            for patch in changes:
                car = next((x for x in current['cars'] if x['id'] == patch.get('id')), None)
                if car is None: raise ValueError('Unknown car')
                for key in ('enabled', 'name', 'order'):
                    if key in patch:
                        value = patch[key]
                        if key == 'enabled' and type(value) is not bool: raise ValueError('enabled must be boolean')
                        if key == 'name' and (not isinstance(value,str) or not value.strip() or len(value)>48): raise ValueError('Name must be 1–48 characters')
                        if key == 'order' and (type(value) is not int or not 0<=value<=999): raise ValueError('Invalid sort order')
                        car[key] = value
            default = body.get('defaultCarId', current['defaultCarId'])
            force = body.get('forceDefault', current['forceDefault'])
            if type(force) is not bool: raise ValueError('forceDefault must be boolean')
            if not any(x['id']==default and x['enabled'] for x in current['cars']):
                raise ValueError('Default must be an enabled car')
            if default != current['defaultCarId'] or force != current['forceDefault'] or body.get('applyDefaultNow'):
                current['defaultRevision'] += 1
            current.update(defaultCarId=default, forceDefault=force, revision=current['revision']+1)
            atomic_json(self.path,current); self.data=current
            return current

    def delete_car(self,body):
        with self.lock:
            if body.get('revision')!=self.data['revision']:raise ValueError('Catalog changed; refresh and retry')
            if any(j['state'] in ('queued','converting') for j in self.jobs.values()):raise ValueError('Wait for the current import or repair to finish')
            car=next((c for c in self.data['cars'] if c['id']==body.get('id')),None)
            if not car:raise ValueError('Unknown car')
            if car.get('builtin'):raise ValueError('Built-in cars can be disabled, not deleted')
            if car['id']==self.data['defaultCarId']:raise ValueError('Choose and publish another default car first')
            current=self.snapshot();current['cars']=[c for c in current['cars'] if c['id']!=car['id']]
            def hashes(value):
                result=set()
                if isinstance(value,dict):
                    for key,v in value.items():
                        if key=='sha256' and isinstance(v,str) and re.fullmatch('[0-9a-f]{64}',v):result.add(v)
                        else:result.update(hashes(v))
                elif isinstance(value,list):
                    for v in value:result.update(hashes(v))
                return result
            candidates=hashes(car)
            jobs={k:v for k,v in self.jobs.items() if v.get('carId')!=car['id']}
            for job in self.jobs.values():
                if job.get('carId')==car['id']:candidates.update(hashes(job))
            registry=self.root/'builtin-previews.json'
            protected=hashes(current)|hashes(list(jobs.values()))|hashes(json.loads(registry.read_text()) if registry.exists() else {})
            current['revision']+=1;atomic_json(self.path,current);self.data=current;self.jobs=jobs
            for digest in candidates-protected:
                (self.root/'packages'/(digest+'.wbcar')).unlink(missing_ok=True)
                folder=self.root/'previews'/digest
                if folder.exists():shutil.rmtree(folder)
            return current

    def wheel_preview(self, body):
        regions=validate_regions(body.get('regions'))
        neutral_inner=body.get('neutralInner',False)
        if type(neutral_inner) is not bool:raise ValueError('neutralInner must be boolean')
        with self.lock:
            if any(j['state'] in ('queued','converting') for j in self.jobs.values()):
                raise ValueError('Another import or wheel repair is processing')
            car=next((c for c in self.data['cars'] if c['id']==body.get('id')),None)
            if not car or car.get('builtin'):raise ValueError('Wheel repair is available for uploaded cars only')
            if body.get('sha256')!=car['sha256']:raise ValueError('Model changed; refresh before repairing')
            # Always cut the pre-repair model, avoiding cumulative cuts on adjustments.
            keys=('sha256','package','bytes','triangles','wheelCount','width','height','length','warnings')
            source=car.get('wheelRepairOriginal') or {k:car[k] for k in keys if k in car}
            source=json.loads(json.dumps(source))
            job=secrets.token_hex(12)
            self.jobs[job]=dict(id=job,kind='wheel-repair',state='queued',carId=car['id'],sourceSha=car['sha256'])
            self.pool.submit(self.cut_wheels,job,source,regions,neutral_inner)
            return self.jobs[job].copy()

    def cut_wheels(self,job,source,regions,neutral_inner=False):
        try:
            with self.lock:self.jobs[job]['state']='converting'
            with tempfile.TemporaryDirectory(prefix='wheel-repair-',dir=self.root) as directory:
                work=Path(directory);package=work/'model.wbcar';report=work/'report.json';config=work/'regions.json'
                config.write_text(json.dumps(regions))
                command=[sys.executable,str(HERE/'wheel_repair.py'),str(self.root/'packages'/(source['sha256']+'.wbcar')),str(package),str(config),str(report)]
                if neutral_inner:command.append('--neutral-inner')
                result=subprocess.run(command,capture_output=True,text=True,timeout=180,encoding='utf-8',errors='replace')
                if result.returncode:raise ValueError('Wheel cut failed: '+result.stderr.strip()[-500:])
                details=json.loads(report.read_text())
                details['warnings']=[w for w in source.get('warnings',[]) if not w.startswith('Not all four wheels')]+details['warnings']
                digest=hashlib.sha256(package.read_bytes()).hexdigest()
                target=self.root/'packages'/(digest+'.wbcar');os.replace(package,target)
                if not self.render_previews(target,digest):details['warnings'].append('Studio images unavailable; interactive preview is still available.')
                asset=dict(sha256=digest,package='/packages/'+target.name,bytes=target.stat().st_size,**details)
                with self.lock:self.jobs[job].update(state='ready',asset=asset,original=source,message='Preview ready. Test wheel movement before applying.')
        except Exception as error:
            with self.lock:self.jobs[job].update(state='failed',message=str(error))

    def wheel_apply(self,body):
        with self.lock:
            current=self.snapshot()
            if body.get('revision')!=current['revision']:raise ValueError('Catalog changed; refresh and review again')
            job=self.jobs.get(body.get('job'))
            if not job or job.get('kind')!='wheel-repair' or job['state']!='ready':raise ValueError('Wheel preview is unavailable; generate it again')
            car=next((c for c in current['cars'] if c['id']==job['carId']),None)
            if not car or car.get('builtin') or car.get('sha256')!=job['sourceSha']:raise ValueError('Model changed; generate a new preview')
            car.update(job['asset']);car['wheelRepairOriginal']=job['original']
            current['revision']+=1;atomic_json(self.path,current);self.data=current;job['state']='applied'
            return current

    def wheel_restore(self,body):
        with self.lock:
            current=self.snapshot()
            if body.get('revision')!=current['revision']:raise ValueError('Catalog changed; refresh before restoring')
            car=next((c for c in current['cars'] if c['id']==body.get('id')),None)
            if not car or car.get('builtin') or not car.get('wheelRepairOriginal'):raise ValueError('No original wheel setup to restore')
            car.update(car.pop('wheelRepairOriginal'));car.pop('wheelRegions',None);car.pop('wheelTriangleCounts',None);car.pop('wheelNeutralInner',None)
            for key in ('wheelCleanFragments','wheelCenterPivots','removedTriangles'):car.pop(key,None)
            current['revision']+=1;atomic_json(self.path,current);self.data=current
            return current

    def upload(self, path, name, car_id, yaw):
        if not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,47}',car_id): raise ValueError('Car ID: lowercase letters, numbers and hyphens, maximum 48')
        if not name.strip() or len(name)>48: raise ValueError('Name must be 1–48 characters')
        if yaw not in (0,90,180,270): raise ValueError('Rotation must be 0, 90, 180, or 270')
        with self.lock:
            if any(j['state'] in ('queued','converting') for j in self.jobs.values()): raise ValueError('An upload is already processing')
            existing=next((x for x in self.data['cars'] if x['id']==car_id),None)
            if existing and existing.get('builtin'): raise ValueError('Use a new ID; built-in IDs cannot be overwritten')
            if not existing and len(self.data['cars'])>=40: raise ValueError('Beta catalog limit: 40 cars')
            job=secrets.token_hex(12);self.jobs[job]=dict(id=job,state='queued',carId=car_id)
            self.pool.submit(self.convert,job,path,name,car_id,yaw)
            return self.jobs[job].copy()

    def convert(self,job,path,name,car_id,yaw):
        try:
            with self.lock:self.jobs[job]['state']='converting'
            with tempfile.TemporaryDirectory(prefix='car-import-',dir=self.root) as directory:
                work=Path(directory); model=extract_model(path,work/'source')
                package=work/'model.wbcar'; report=work/'report.json'
                result=subprocess.run([self.blender,'--background','--factory-startup','--disable-autoexec',
                    '--python',str(HERE/'convert.py'),'--',str(model),str(package),str(report),str(yaw),'--require-wheels'],
                    capture_output=True,text=True,timeout=180,encoding='utf-8',errors='replace')
                (self.root/'last-conversion.log').write_text(result.stdout+'\n'+result.stderr,encoding='utf-8')
                if result.returncode or not package.exists():raise ValueError('Model conversion failed. See last-conversion.log on the server.')
                if package.stat().st_size>64*1024*1024:raise ValueError('Converted package exceeds 64 MB')
                digest=hashlib.sha256(package.read_bytes()).hexdigest();filename=digest+'.wbcar'
                os.replace(package,self.root/'packages'/filename)
                details=json.loads(report.read_text())
                if not self.render_previews(self.root/'packages'/filename,digest):details.setdefault('warnings',[]).append('Studio images unavailable; interactive preview is still available.')
                with self.lock:
                    current=self.snapshot();old=next((x for x in current['cars'] if x['id']==car_id),None)
                    entry=dict(id=car_id,name=name,builtin='',enabled=old['enabled'] if old else False,
                        order=old['order'] if old else len(current['cars']),sha256=digest,
                        bytes=(self.root/'packages'/filename).stat().st_size,package='/packages/'+filename,**details)
                    current['cars']=[x for x in current['cars'] if x['id']!=car_id]+[entry]
                    current['revision']+=1;atomic_json(self.path,current);self.data=current
                    self.jobs[job].update(state='ready',car=entry,message='Ready. Enable this car to publish it to apps.')
        except Exception as error:
            with self.lock:self.jobs[job].update(state='failed',message=str(error))
        finally:Path(path).unlink(missing_ok=True)

class Handler(BaseHTTPRequestHandler):
    server_version='WorldBreakCatalog/1'
    matches=Matchmaker()
    def log_message(self,fmt,*args):print(time.strftime('%H:%M:%S'),fmt%args,flush=True)
    @property
    def catalog(self):return self.server.catalog
    def send(self,status,data,kind='application/json'):
        if not isinstance(data,bytes):data=json.dumps(data).encode()
        self.send_response(status);self.send_header('Content-Type',kind);self.send_header('Content-Length',str(len(data)))
        self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.end_headers();self.wfile.write(data)
    def authorized(self):
        return hmac.compare_digest(self.headers.get('Authorization',''),'Bearer '+self.catalog.token)
    def do_GET(self):
        path=urlsplit(self.path).path
        if path in ('/','/admin'):return self.send(200,(HERE/'admin.html').read_bytes(),'text/html; charset=utf-8')
        if path=='/health':return self.send(200,dict(ok=True,schema=1,matchmaking=6))
        if path=='/v1/matchmaking':return self.send(200,dict(protocol=6,version='1.4.0',queueSeconds=12,seats=6))
        if path=='/v1/catalog':return self.send(200,self.catalog.snapshot())
        if path=='/v1/previews':return self.send(200,self.catalog.previews())
        if re.fullmatch(r'/static/(?:[a-z0-9-]+\.(?:js|css)|vendor/(?:three\.(?:module|core)\.min\.js|THREE-LICENSE\.txt))',path):
            file=HERE/path.lstrip('/')
            if file.is_file():return self.send(200,file.read_bytes(),'text/css' if file.suffix=='.css' else 'text/javascript' if file.suffix=='.js' else 'text/plain')
        if re.fullmatch(r'/previews/[0-9a-f]{64}/(?:hero|front|rear|left|right)\.jpg',path):
            file=self.catalog.root/path.lstrip('/')
            if file.is_file():return self.send(200,file.read_bytes(),'image/jpeg')
        if path=='/admin/session':return self.send(200,dict(ok=True)) if self.authorized() else self.send(401,dict(error='Admin token required'))
        if path.startswith('/admin/jobs/'):
            if not self.authorized():return self.send(401,dict(error='Admin token required'))
            with self.catalog.lock:job=self.catalog.jobs.get(path.split('/')[-1])
            return self.send(200 if job else 404,job or dict(error='Job not found'))
        if re.fullmatch(r'/packages/[0-9a-f]{64}\.wbcar',path):
            file=self.catalog.root/path.lstrip('/')
            if file.is_file():
                self.send_response(200);self.send_header('Content-Type','application/octet-stream');self.send_header('Content-Length',str(file.stat().st_size));self.send_header('Cache-Control','public, max-age=31536000, immutable');self.end_headers()
                with file.open('rb') as stream:shutil.copyfileobj(stream,self.wfile)
                return
        self.send(404,dict(error='Not found'))
    def do_POST(self):
        if urlsplit(self.path).path.startswith('/v1/matchmaking/'):
            try:
                length=int(self.headers.get('Content-Length','0'))
                if not 0<length<=32768:raise MatchError(413,'Match request too large')
                self.connection.settimeout(8)
                body=json.loads(self.rfile.read(length))
                if not isinstance(body,dict):raise MatchError(400,'Expected an object')
                return self.send(200,self.matches.request(urlsplit(self.path).path.rsplit('/',1)[-1],body,self.client_address[0]))
            except MatchError as error:return self.send(error.status,dict(error=str(error)))
            except (ValueError,TypeError):return self.send(400,dict(error='Invalid match request'))
        if not self.authorized():return self.send(401,dict(error='Admin token required'))
        temp=None
        try:
            length=int(self.headers.get('Content-Length','0'))
            if not 0<length<=MAX_UPLOAD:raise ValueError('Invalid upload size (maximum 100 MB)')
            parsed=urlsplit(self.path)
            wheel_routes={'/admin/cars/delete':self.catalog.delete_car,'/admin/wheels/preview':self.catalog.wheel_preview,'/admin/wheels/apply':self.catalog.wheel_apply,'/admin/wheels/restore':self.catalog.wheel_restore}
            if parsed.path in wheel_routes:
                if length>65536:raise ValueError('Request too large')
                body=json.loads(self.rfile.read(length))
                if not isinstance(body,dict):raise ValueError('Expected an object')
                return self.send(200,wheel_routes[parsed.path](body))
            if parsed.path=='/admin/catalog':
                if length>65536:raise ValueError('Request too large')
                return self.send(200,self.catalog.edit(json.loads(self.rfile.read(length))))
            if parsed.path!='/admin/upload':return self.send(404,dict(error='Not found'))
            query=parse_qs(parsed.query);name=query.get('name',[''])[0];car_id=query.get('id',[''])[0];yaw=int(query.get('yaw',['0'])[0])
            fd,temp=tempfile.mkstemp(suffix='.zip',prefix='upload-',dir=self.catalog.root)
            self.connection.settimeout(60)
            with os.fdopen(fd,'wb') as file:
                remaining=length
                while remaining:
                    chunk=self.rfile.read(min(remaining,1024*1024))
                    if not chunk:raise ValueError('Incomplete upload')
                    file.write(chunk);remaining-=len(chunk)
            job=self.catalog.upload(temp,name,car_id,yaw);temp=None;self.send(202,job)
        except (ValueError,KeyError,TypeError,json.JSONDecodeError) as error:self.send(400,dict(error=str(error)))
        except Exception:self.send(500,dict(error='Server error; check service log'))
        finally:
            if temp:Path(temp).unlink(missing_ok=True)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--host',default='127.0.0.1');parser.add_argument('--port',type=int,default=8787)
    parser.add_argument('--data',default=str(HERE/'data'));parser.add_argument('--blender',default=os.environ.get('BLENDER_PATH','blender'))
    args=parser.parse_args();catalog=Catalog(args.data,args.blender)
    server=ThreadingHTTPServer((args.host,args.port),Handler);server.catalog=catalog
    print(f'Car catalog: http://{args.host}:{args.port}/admin\nAdmin token file: {catalog.root / "admin-token.txt"}',flush=True)
    try:server.serve_forever()
    finally:server.server_close();catalog.pool.shutdown(wait=True)
if __name__=='__main__':main()
