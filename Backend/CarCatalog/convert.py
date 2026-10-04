"""Blender worker: FBX/GLB -> bounded, data-only WBCAR001 mesh/texture package."""
import bpy, sys, math, struct, json, io
from pathlib import Path
from mathutils import Vector, Matrix

source,output,report,yaw=sys.argv[sys.argv.index('--')+1:]
source=Path(source);output=Path(output)
bpy.ops.wm.read_factory_settings(use_empty=True)
if source.suffix.lower()=='.fbx':bpy.ops.import_scene.fbx(filepath=str(source),use_anim=False)
elif source.suffix.lower()=='.glb':bpy.ops.import_scene.gltf(filepath=str(source))
else:raise ValueError('Unsupported model format')
bpy.context.view_layer.update()
objects=[o for o in bpy.context.scene.objects if o.type=='MESH']
if not objects:raise ValueError('Model contains no meshes')
rotation=Matrix.Rotation(math.radians(int(yaw)),4,'Z')
vertices=[rotation@o.matrix_world@v.co for o in objects for v in o.data.vertices]
if len(vertices)>300000:raise ValueError('Model exceeds 300,000 source vertices; simplify before uploading')
lo=Vector(tuple(min(v[i] for v in vertices) for i in range(3)));hi=Vector(tuple(max(v[i] for v in vertices) for i in range(3)))
if any(not math.isfinite(v) for v in (*lo,*hi)) or hi.y-lo.y<.001:raise ValueError('Invalid model bounds')
scale=4.2/(hi.y-lo.y);offset=Vector(((hi.x+lo.x)/2,(hi.y+lo.y)/2,lo.z))
width=(hi.x-lo.x)*scale;height=(hi.z-lo.z)*scale
if not .8<=width<=3.5 or not .4<=height<=3.2:raise ValueError('Car proportions look wrong. Adjust forward rotation or export with Z up in Blender.')
def unity(p):return Vector((p.x,p.z,-p.y))
materials=[];material_ids={};parts=[];warnings=[];wheel_found=set()
files={p.name.lower():p for p in source.parent.parent.rglob('*') if p.is_file()}
def material_index(material):
 key=material.name if material else '__default'
 if key in material_ids:return material_ids[key]
 if len(materials)>=32:raise ValueError('Maximum 32 materials; merge material slots before uploading')
 color=list(material.diffuse_color) if material else [.7,.7,.7,1];image=None
 if material and material.use_nodes:
  bsdf=next((n for n in material.node_tree.nodes if n.type=='BSDF_PRINCIPLED'),None)
  if bsdf:
   color=list(bsdf.inputs['Base Color'].default_value)
   # Use the base-color link only: normal/roughness images are not color maps.
   links=list(bsdf.inputs['Base Color'].links)
   if links and links[0].from_node.type=='TEX_IMAGE':image=links[0].from_node.image
 if image:
  if not image.packed_file and not Path(bpy.path.abspath(image.filepath)).exists():
   match=files.get(Path(image.filepath.replace('\\','/')).name.lower())
   if match:image.filepath=str(match);image.reload()
  if image.size[0]==0:raise ValueError('Missing color texture: '+image.name)
  if max(image.size)>2048:
   factor=2048/max(image.size);image.scale(max(1,int(image.size[0]*factor)),max(1,int(image.size[1]*factor)))
  texture_path=output.parent/('texture-'+str(len(materials))+'.png')
  image.filepath_raw=str(texture_path);image.file_format='PNG';image.save()
  texture=texture_path.read_bytes()
  # Generated FBX often sets the diffuse fallback to gray even with a full-color map.
  color=[1,1,1,1]
 else:texture=b''
 if len(texture)>16*1024*1024:raise ValueError('Texture too large')
 material_ids[key]=len(materials);materials.append((color,texture));return len(materials)-1

for obj in objects:
 mesh=obj.data;mesh.calc_loop_triangles()
 matrix=rotation@obj.matrix_world;normal_matrix=matrix.to_3x3().inverted().transposed()
 positions=[(matrix@v.co-offset)*scale for v in mesh.vertices]
 adj=[[] for v in positions]
 for edge in mesh.edges:
  a,b=edge.vertices;adj[a].append(b);adj[b].append(a)
 remaining=set(range(len(positions)));labels={}
 while remaining:
  pending=[remaining.pop()];group=[]
  while pending:
   a=pending.pop();group.append(a)
   for b in adj[a]:
    if b in remaining:remaining.remove(b);pending.append(b)
  low=Vector(tuple(min(positions[v][i] for v in group) for i in range(3)))
  high=Vector(tuple(max(positions[v][i] for v in group) for i in range(3)))
  size=high-low;center=(high+low)/2
  named='wheel' in obj.name.lower() or 'tire' in obj.name.lower() or 'tyre' in obj.name.lower()
  candidate=(abs(center.x)>width*.26 and abs(center.y)>.42 and high.z<height*.57 and size.x<width*.42
    and size.z>.15 and .55<size.y/max(.001,size.z)<1.65)
  label=('Wheel'+('F' if center.y<0 else 'R')+('L' if center.x<0 else 'R')) if (candidate or named) else 'Body'
  if label!='Body':wheel_found.add(label)
  for v in group:labels[v]=label
 batches={}
 uv=mesh.uv_layers.active.data if mesh.uv_layers.active else None
 if uv is None:warnings.append(obj.name+': no UVs; flat material used')
 for triangle in mesh.loop_triangles:
  label=labels[triangle.vertices[0]]
  material=mesh.materials[triangle.material_index] if triangle.material_index<len(mesh.materials) else None
  mat=material_index(material);key=(label,mat)
  batches.setdefault(key,[]).append(triangle)
 for (label,mat),triangles in batches.items():
  # Deduplicate complete vertex attributes, retaining UV seams and split normals.
  packed=[];indices=[];lookup={}
  for triangle in triangles:
   face=[]
   for loop_index in triangle.loops:
    loop=mesh.loops[loop_index];p=unity(positions[loop.vertex_index])
    n=unity(normal_matrix@mesh.vertices[loop.vertex_index].normal).normalized()
    tex=uv[loop_index].uv if uv else (0,0)
    value=tuple(float(x) for x in (*p,*n,*tex))
    if not all(math.isfinite(x) for x in value):raise ValueError('Mesh contains invalid numbers')
    if value not in lookup:lookup[value]=len(packed);packed.append(value)
    face.append(lookup[value])
   # Keep cross-product normals aligned with the triangles after this axis rotation.
   indices.extend(face)
  parts.append(dict(label=label,material=mat,vertices=packed,indices=indices))

if sum(len(p['indices']) for p in parts)>600000 or sum(len(p['vertices']) for p in parts)>300000:
 raise ValueError('Beta limit: 200,000 triangles / 300,000 vertices after UV seams')
if len(parts)>128:raise ValueError('Too many mesh parts; merge objects/materials')
centers={}
for wheel in wheel_found:
 verts=[v for p in parts if p['label']==wheel for v in p['vertices']]
 centers[wheel]=tuple((min(v[i] for v in verts)+max(v[i] for v in verts))/2 for i in range(3))
if len(wheel_found)!=4:warnings.append('Not all four wheels could be separated automatically; remaining wheel geometry stays fixed. Export separate wheel objects for animation.')
with output.open('wb') as f:
 def integer(n):f.write(struct.pack('<i',n))
 def floats(values):f.write(struct.pack('<'+'f'*len(values),*values))
 f.write(b'WBCAR001');floats((width,height,4.2));integer(len(materials));integer(len(parts))
 for color,texture in materials:floats(color);integer(len(texture));f.write(texture)
 for p in parts:
  name=p['label'].encode();integer(len(name));f.write(name);integer(p['material'])
  pivot=centers.get(p['label'],(0,0,0));floats(pivot);integer(len(p['vertices']));integer(len(p['indices']))
  for v in p['vertices']:floats(tuple(v[i]-pivot[i] for i in range(3))+v[3:])
  f.write(struct.pack('<'+'i'*len(p['indices']),*p['indices']))
Path(report).write_text(json.dumps(dict(triangles=sum(len(p['indices'])//3 for p in parts),wheelCount=len(wheel_found),warnings=list(dict.fromkeys(warnings)),width=width,height=height,length=4.2)),encoding='utf-8')
print('WBCAR_CONVERT_PASS',output)
