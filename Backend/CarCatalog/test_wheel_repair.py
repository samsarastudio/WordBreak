import hashlib, json, math, struct, tempfile, unittest
from pathlib import Path
from server import Catalog, atomic_json
from wheel_repair import LABELS, read_package, repair, validate_regions, remove_small_islands

def regions():
    return [dict(name=name,x=-.9 if name.endswith('L') else .9,y=.4,
                 z=1.3 if name.startswith('WheelF') else -1.3,radius=.4,width=.4) for name in LABELS]

def connected_fixture(path):
    # A single welded sheet spans both axles and the body. Adjacent triangles
    # share vertices; successful extraction cannot depend on loose parts.
    vertices=[(x/10,.4,z/10,0,1,0,(x+11)/22,(z+20)/40) for x in range(-11,12) for z in range(-20,21)]
    indices=[]
    for x in range(22):
        for z in range(40):
            a=x*41+z;b=a+41;indices.extend((a,b,a+1,a+1,b,b+1))
    with path.open('wb') as f:
        def i(v): f.write(struct.pack('<i',v))
        def fs(v): f.write(struct.pack('<'+'f'*len(v),*v))
        f.write(b'WBCAR001');fs((2.2,1.2,4.2));i(1);i(1)
        fs((.8,.4,.1,1));i(0);i(4);f.write(b'Body');i(0);fs((0,0,0));i(len(vertices));i(len(indices))
        for v in vertices:fs(v)
        for index in indices:i(index)

def area(parts):
    result=0
    for part in parts:
        for t in range(0,len(part['indices']),3):
            a,b,c=[part['vertices'][j] for j in part['indices'][t:t+3]]
            result+=abs((b[0]-a[0])*(c[2]-a[2])-(b[2]-a[2])*(c[0]-a[0]))/2
    return result

class WheelRepairTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.source=self.root/'source.wbcar';connected_fixture(self.source)
    def tearDown(self):self.temp.cleanup()
    def test_connected_surface_split_preserves_area_uv_and_material(self):
        before=self.source.read_bytes();output=self.root/'cut.wbcar'
        report=repair(self.source,output,regions());bounds,materials,parts=read_package(output)
        self.assertEqual(report['wheelCount'],4)
        self.assertEqual({p['name'] for p in parts},{'Body',*LABELS})
        self.assertAlmostEqual(area(parts),area(read_package(self.source)[2]),places=4)
        self.assertEqual(materials,read_package(self.source)[1]);self.assertEqual(self.source.read_bytes(),before)
        for part in parts:
            for v in part['vertices']:
                self.assertAlmostEqual(v[6],(v[0]+1.1)/2.2,places=5)
                self.assertAlmostEqual(v[7],(v[2]+2)/4,places=5)
                self.assertAlmostEqual(sum(x*x for x in v[3:6]),1,places=5)
                if part['name']!='Body':
                    region=next(r for r in regions() if r['name']==part['name'])
                    self.assertLessEqual(abs(v[0]-region['x']),region['width']/2+1e-6)
                    self.assertLessEqual(math.hypot(v[1]-region['y'],v[2]-region['z']),region['radius']+1e-6)
    def test_cleanup_removes_tiny_island_not_main_surface(self):
        parts=read_package(self.source)[2]
        tiny=dict(name='Body',material=0,vertices=[(3,0,0,0,1,0,0,0),(3.01,0,0,0,1,0,0,0),(3,0,.01,0,1,0,0,0)],indices=[0,1,2])
        cleaned,count=remove_small_islands(parts+[tiny])
        self.assertEqual(count,1);self.assertEqual(cleaned[0]['indices'],parts[0]['indices']);self.assertEqual(cleaned[-1]['indices'],[])
    def test_centered_pivots_preserve_geometry(self):
        a=self.root/'a.wbcar';b=self.root/'b.wbcar'
        repair(self.source,a,regions());report=repair(self.source,b,regions(),center_pivots=True)
        self.assertTrue(report['wheelCenterPivots'])
        self.assertAlmostEqual(area(read_package(a)[2]),area(read_package(b)[2]),places=4)
    def test_invalid_regions_rejected(self):
        for key,value in [('radius',float('nan')),('width',-1),('x',.9),('y',float('inf'))]:
            values=regions();values[0][key]=value
            with self.assertRaises(ValueError):validate_regions(values)
        values=regions();values[2]['z']=-.2;values[0]['z']=.2
        with self.assertRaisesRegex(ValueError,'overlap'):validate_regions(values)
    def test_neutral_inner_faces_leave_body_and_outer_wheels_unchanged(self):
        raw=bytearray(self.source.read_bytes())
        for i in range(23*41):
            offset=80+i*32;x=struct.unpack_from('<f',raw,offset)[0]
            struct.pack_into('<fff',raw,offset+12,1 if x<0 else -1,0,0)
        self.source.write_bytes(raw)
        output=self.root/'neutral.wbcar';report=repair(self.source,output,regions(),neutral_inner=True)
        _,materials,parts=read_package(output)
        self.assertTrue(report['wheelNeutralInner']);self.assertEqual(len(materials),2)
        neutral=[p for p in parts if p['material']==1]
        self.assertEqual({p['name'] for p in neutral},set(LABELS))
        self.assertTrue(all(p['material']==0 for p in parts if p['name']=='Body'))
        for part in neutral:
            self.assertTrue(all(abs(v[0])<.901 for v in part['vertices']))
    def test_empty_region_rejected(self):
        values=regions();values[0]['y']=1.5
        with self.assertRaisesRegex(ValueError,'Too little geometry'):repair(self.source,self.root/'bad.wbcar',values)
    def setup_catalog(self):
        c=Catalog(self.root/'data','missing-blender');sha=hashlib.sha256(self.source.read_bytes()).hexdigest()
        (c.root/'packages'/(sha+'.wbcar')).write_bytes(self.source.read_bytes())
        entry=dict(id='connected-test',name='Connected test',builtin='',enabled=False,order=6,sha256=sha,package='/packages/'+sha+'.wbcar',bytes=self.source.stat().st_size,triangles=1760,wheelCount=0,width=2.2,height=1.2,length=4.2,warnings=['No wheels'])
        c.data['cars'].append(entry);atomic_json(c.path,c.data)
        return c,entry
    def test_preview_apply_restore_and_persistence(self):
        c,entry=self.setup_catalog();before=c.snapshot()
        job=c.wheel_preview(dict(id=entry['id'],sha256=entry['sha256'],regions=regions()));c.pool.shutdown(wait=True)
        self.assertEqual(c.jobs[job['id']]['state'],'ready',c.jobs[job['id']])
        self.assertEqual(c.snapshot(),before,'Preview must not publish')
        with self.assertRaisesRegex(ValueError,'Catalog changed'):c.wheel_apply(dict(job=job['id'],revision=0))
        applied=c.wheel_apply(dict(job=job['id'],revision=before['revision']));car=applied['cars'][-1]
        self.assertEqual(car['wheelCount'],4);self.assertFalse(car['enabled']);self.assertEqual(car['wheelRepairOriginal']['sha256'],entry['sha256'])
        reopened=Catalog(c.root,'missing-blender')
        try:
            self.assertEqual(reopened.snapshot(),applied)
            restored=reopened.wheel_restore(dict(id=entry['id'],revision=applied['revision']))
            self.assertEqual(restored['cars'][-1],entry)
        finally:reopened.pool.shutdown()
    def test_changed_model_cannot_apply_old_preview(self):
        c,entry=self.setup_catalog()
        job=c.wheel_preview(dict(id=entry['id'],sha256=entry['sha256'],regions=regions()));c.pool.shutdown(wait=True)
        c.data['cars'][-1]['sha256']='a'*64
        with self.assertRaisesRegex(ValueError,'Model changed'):c.wheel_apply(dict(job=job['id'],revision=c.data['revision']))
    def test_builtin_and_stale_source_rejected(self):
        c,entry=self.setup_catalog()
        try:
            with self.assertRaisesRegex(ValueError,'uploaded'):c.wheel_preview(dict(id='cinder',regions=regions()))
            with self.assertRaisesRegex(ValueError,'Model changed'):c.wheel_preview(dict(id=entry['id'],sha256='bad',regions=regions()))
        finally:c.pool.shutdown()

if __name__=='__main__':unittest.main()
