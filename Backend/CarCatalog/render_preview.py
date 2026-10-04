"""Render the exact runtime package into a consistent studio thumbnail/gallery."""
import bpy, struct, sys, math
from pathlib import Path
from mathutils import Vector
package,destination=sys.argv[sys.argv.index('--')+1:];destination=Path(destination);destination.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
with open(package,'rb') as f:
 def integer():return struct.unpack('<i',f.read(4))[0]
 def floats(n):return struct.unpack('<'+'f'*n,f.read(n*4))
 def position(v):return (v[0],-v[2],v[1])
 assert f.read(8)==b'WBCAR001';size=floats(3);nm=integer();np=integer();materials=[]
 for i in range(nm):
  color=floats(4);length=integer();mat=bpy.data.materials.new('Surface');mat.diffuse_color=color;mat.use_nodes=True
  bsdf=mat.node_tree.nodes.get('Principled BSDF');bsdf.inputs['Base Color'].default_value=color;bsdf.inputs['Roughness'].default_value=.62
  if length:
   path=destination/('texture-'+str(i)+'.png');path.write_bytes(f.read(length));image=bpy.data.images.load(str(path));node=mat.node_tree.nodes.new('ShaderNodeTexImage');node.image=image;mat.node_tree.links.new(node.outputs['Color'],bsdf.inputs['Base Color'])
  materials.append(mat)
 for part in range(np):
  name=f.read(integer()).decode();material=integer();pivot=floats(3);nv=integer();ni=integer();values=[floats(8) for _ in range(nv)];indices=[integer() for _ in range(ni)]
  mesh=bpy.data.meshes.new(name);mesh.from_pydata([position(tuple(v[i]+pivot[i] for i in range(3))) for v in values],[],[indices[i:i+3] for i in range(0,ni,3)]);mesh.update()
  uv=mesh.uv_layers.new(name='UVMap')
  for loop in mesh.loops:uv.data[loop.index].uv=values[loop.vertex_index][6:8]
  for p in mesh.polygons:p.use_smooth=True
  obj=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(obj);mesh.materials.append(materials[material])
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=12;scene.cycles.use_denoising=True
scene.world=bpy.data.worlds.new('Studio');scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.22,.26,.32,1);scene.world.node_tree.nodes['Background'].inputs[1].default_value=.65
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.035));ground=bpy.context.object
mat=bpy.data.materials.new('Floor');mat.diffuse_color=(.105,.13,.17,1);ground.data.materials.append(mat)
for location,energy,area in [((3,-4,6),950,5),((-4,-1,3),750,4),((1,4,5),1100,3)]:
 data=bpy.data.lights.new('Softbox','AREA');data.energy=energy;data.shape='DISK';data.size=area;light=bpy.data.objects.new('Softbox',data);scene.collection.objects.link(light);light.location=location;light.rotation_euler=(Vector((0,0,.7))-light.location).to_track_quat('-Z','Y').to_euler()
cam=bpy.data.objects.new('Camera',bpy.data.cameras.new('Camera'));scene.collection.objects.link(cam);scene.camera=cam;cam.data.type='ORTHO';cam.data.ortho_scale=6.1
scene.render.resolution_x=720;scene.render.resolution_y=450;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='JPEG';scene.render.image_settings.quality=88
scene.view_settings.view_transform='AgX'
for name,location in [('hero',(5,-7,3.5)),('front',(0,-8,1.1)),('rear',(0,8,1.1)),('left',(-8,0,1.1)),('right',(8,0,1.1))]:
 cam.location=location;cam.rotation_euler=(Vector((0,0,.7))-cam.location).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(destination/(name+'.jpg'));bpy.ops.render.render(write_still=True)
for file in destination.glob('texture-*.png'):file.unlink()
print('CAR_PREVIEW_PASS')
