"""Backfill previews for the current catalog and the bundled Unity vehicles."""
import argparse, hashlib, json, subprocess, tempfile
from pathlib import Path
from server import atomic_json
HERE=Path(__file__).resolve().parent
def main():
 p=argparse.ArgumentParser();p.add_argument('--blender',required=True);p.add_argument('--data',default=str(HERE/'data'));a=p.parse_args();root=Path(a.data);project=HERE.parent.parent
 models={'cinder':project/'ArtSource/Model7071/Model7071.fbx'}
 for name in ('hatchback-sports','sedan','suv','suv-luxury','race-future'):models['kenney-'+name]=project/('ArtSource/KenneyCarKit/Source/Models/GLB format/'+name+'.glb')
 registry={}
 def run(script,*args):
  result=subprocess.run([a.blender,'-b','--factory-startup','--disable-autoexec','--python',str(HERE/script),'--',*map(str,args)],capture_output=True,text=True,timeout=240)
  if result.returncode:raise RuntimeError(result.stdout[-2000:]+result.stderr[-2000:])
 for id,model in models.items():
  with tempfile.TemporaryDirectory() as temp:
   package=Path(temp)/'car.wbcar';report=Path(temp)/'report.json';run('convert.py',model,package,report,0)
   digest=hashlib.sha256(package.read_bytes()).hexdigest();target=root/'packages'/(digest+'.wbcar');target.write_bytes(package.read_bytes());registry[id]={'sha256':digest,**json.loads(report.read_text())}
  print('Prepared '+id,flush=True)
 atomic_json(root/'builtin-previews.json',registry)
 hashes={c['sha256'] for c in json.loads((root/'catalog.json').read_text())['cars'] if c.get('sha256')}|{c['sha256'] for c in registry.values()}
 for digest in hashes:
  destination=root/'previews'/digest
  if not all((destination/(view+'.jpg')).exists() for view in ('hero','front','rear','left','right')):run('render_preview.py',root/'packages'/(digest+'.wbcar'),destination)
  print('Rendered '+digest[:12],flush=True)
if __name__=='__main__':main()
