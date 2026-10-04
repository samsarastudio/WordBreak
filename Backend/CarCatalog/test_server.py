import io, json, tempfile, unittest, zipfile
from unittest.mock import patch
from pathlib import Path
from server import Catalog, extract_model

class CatalogTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.catalog=Catalog(self.root/'data','missing-blender')
 def tearDown(self):self.catalog.pool.shutdown();self.temp.cleanup()
 def test_preview_cache_skips_blender(self):
  digest='a'*64;folder=self.catalog.root/'previews'/digest;folder.mkdir(parents=True)
  for view in ('hero','front','rear','left','right'):(folder/(view+'.jpg')).write_bytes(b'image')
  with patch('server.subprocess.run') as run:
   self.assertTrue(self.catalog.render_previews(Path('unused'),digest));run.assert_not_called()
 def test_preview_failure_keeps_import_available(self):
  with patch('server.subprocess.run',side_effect=OSError('renderer unavailable')):
   self.assertFalse(self.catalog.render_previews(Path('unused'),'b'*64))
  self.assertIn('renderer unavailable',(self.catalog.root/'last-preview.log').read_text())
 def test_partial_preview_set_is_not_success(self):
  with patch('server.subprocess.run') as run:
   run.return_value.returncode=0;run.return_value.stdout='';run.return_value.stderr=''
   self.assertFalse(self.catalog.render_previews(Path('unused'),'c'*64))
 def test_delete_removes_only_unshared_assets(self):
  digest='d'*64;shared='e'*64
  self.catalog.data['cars'].extend([dict(id='delete-me',sha256=digest,wheelRepairOriginal={'sha256':shared}),dict(id='keep',sha256=shared)])
  for sha in (digest,shared):
   (self.catalog.root/'packages'/(sha+'.wbcar')).write_bytes(b'package')
   folder=self.catalog.root/'previews'/sha;folder.mkdir(parents=True);(folder/'hero.jpg').write_bytes(b'image')
  self.catalog.delete_car(dict(id='delete-me',revision=1))
  self.assertFalse((self.catalog.root/'packages'/(digest+'.wbcar')).exists())
  self.assertFalse((self.catalog.root/'previews'/digest).exists())
  self.assertTrue((self.catalog.root/'packages'/(shared+'.wbcar')).exists())
  self.assertEqual(json.loads(self.catalog.path.read_text())['revision'],2)
 def test_delete_guards(self):
  with self.assertRaises(ValueError):self.catalog.delete_car(dict(id='cinder',revision=1))
  self.catalog.data['cars'].append(dict(id='uploaded'))
  with self.assertRaises(ValueError):self.catalog.delete_car(dict(id='uploaded',revision=0))
  self.catalog.data['defaultCarId']='uploaded'
  with self.assertRaises(ValueError):self.catalog.delete_car(dict(id='uploaded',revision=1))
  self.catalog.data['defaultCarId']='cinder';self.catalog.jobs['busy']={'state':'converting'}
  with self.assertRaises(ValueError):self.catalog.delete_car(dict(id='uploaded',revision=1))
 def test_defaults_and_persistence(self):
  c=self.catalog.snapshot();self.assertEqual(len(c['cars']),6)
  c=self.catalog.edit(dict(revision=c['revision'],defaultCarId='kenney-sedan'))
  self.assertEqual(c['defaultRevision'],2)
  reopened=Catalog(self.root/'data','missing');self.assertEqual(reopened.snapshot()['defaultCarId'],'kenney-sedan');reopened.pool.shutdown()
 def test_cannot_disable_default(self):
  with self.assertRaises(ValueError):self.catalog.edit(dict(revision=1,cars=[dict(id='cinder',enabled=False)]))
  self.assertTrue(self.catalog.snapshot()['cars'][0]['enabled'])
 def test_stale_write_rejected(self):
  self.catalog.edit(dict(revision=1))
  with self.assertRaises(ValueError):self.catalog.edit(dict(revision=1))
 def test_force_default_epoch(self):
  c=self.catalog.edit(dict(revision=1,forceDefault=True));self.assertEqual(c['defaultRevision'],2)
  c=self.catalog.edit(dict(revision=2,applyDefaultNow=True));self.assertEqual(c['defaultRevision'],3)
 def archive(self,entries):
  path=self.root/'upload.zip'
  with zipfile.ZipFile(path,'w') as z:
   for name,body in entries:z.writestr(name,body)
  return path
 def test_zip_traversal_rejected(self):
  for path in ('../escape.fbx','C:/escape.fbx','/absolute.fbx','a/../../escape.fbx'):
   with self.assertRaises(ValueError):extract_model(self.archive([(path,b'bad')]),self.root/'source')
 def test_exactly_one_model_and_ignore_scripts(self):
  archive=self.archive([('car.fbx',b'fbx'),('run.py',b'raise Exception()'),('car.fbm/color.png',b'png')])
  model=extract_model(archive,self.root/'source');self.assertEqual(model.name,'car.fbx');self.assertFalse((self.root/'source/run.py').exists())
 def test_ambiguous_models_rejected(self):
  with self.assertRaises(ValueError):extract_model(self.archive([('one.fbx',b''),('two.glb',b'')]),self.root/'source')
 def test_builtin_cannot_be_overwritten(self):
  with self.assertRaises(ValueError):self.catalog.upload(self.root/'unused.zip','Bad','cinder',0)
if __name__=='__main__':unittest.main()
