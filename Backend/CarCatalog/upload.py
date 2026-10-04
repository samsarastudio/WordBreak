"""Optional command-line alternative to the browser upload form."""
import argparse, json, time, urllib.request
from pathlib import Path
from urllib.parse import urlencode

def main():
 p=argparse.ArgumentParser();p.add_argument('zip');p.add_argument('--id',required=True);p.add_argument('--name',required=True)
 p.add_argument('--url',default='http://127.0.0.1:8787');p.add_argument('--token-file',default=str(Path(__file__).parent/'data/admin-token.txt'))
 p.add_argument('--yaw',type=int,default=0);p.add_argument('--publish',action='store_true');p.add_argument('--default',action='store_true');a=p.parse_args()
 token=Path(a.token_file).read_text().strip()
 def api(path,data=None):
  request=urllib.request.Request(a.url+path,data=data,headers={'Authorization':'Bearer '+token,'Content-Type':'application/octet-stream'})
  with urllib.request.urlopen(request,timeout=120) as response:return json.load(response)
 query=urlencode(dict(id=a.id,name=a.name,yaw=a.yaw))
 job=api('/admin/upload?'+query,Path(a.zip).read_bytes());deadline=time.monotonic()+480
 while job['state'] in ('queued','converting'):
  if time.monotonic()>deadline:raise RuntimeError('Conversion timed out')
  time.sleep(1);job=api('/admin/jobs/'+job['id'])
 if job['state']!='ready':raise RuntimeError(job['message'])
 if a.publish or a.default:
  catalog=api('/v1/catalog');patch=dict(revision=catalog['revision'],cars=[dict(id=a.id,enabled=True)])
  if a.default:patch['defaultCarId']=a.id
  api('/admin/catalog',json.dumps(patch).encode())
 print(json.dumps(job,indent=2))
if __name__=='__main__':main()
