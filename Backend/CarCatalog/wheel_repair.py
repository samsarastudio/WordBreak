"""Cut four user-defined wheel cylinders from a WBCAR mesh, preserving UVs.

Works across connected triangles. This is a surface cut, not retopology: it does
not invent a missing wheel or cap an opening where a wheel is welded to the body.
Coordinates match Unity: X right, Y up, Z forward; wheel axle is X.
"""
import argparse, io, json, math, struct
from pathlib import Path

LABELS = ('WheelFL', 'WheelFR', 'WheelRL', 'WheelRR')
SIDES = 24

def validate_regions(regions):
    if not isinstance(regions, list) or len(regions) != 4:
        raise ValueError('Mark exactly four wheel regions')
    result = []
    for label, region in zip(LABELS, regions):
        if not isinstance(region, dict) or region.get('name') != label:
            raise ValueError('Wheel regions must be FL, FR, RL, RR in order')
        values = [region.get(k) for k in ('x', 'y', 'z', 'radius', 'width')]
        if any(type(v) not in (float, int) or not math.isfinite(v) for v in values):
            raise ValueError('Wheel dimensions must be finite numbers')
        x, y, z, radius, width = values
        if not (.1 <= abs(x) <= 1.8 and .05 <= y <= 1.6 and .15 <= abs(z) <= 2.2
                and .12 <= radius <= .85 and .05 <= width <= .8):
            raise ValueError('Wheel region is outside the supported car dimensions')
        if (x < 0) != label.endswith('L') or (z > 0) != (label[5] == 'F'):
            raise ValueError('Wheel region is on the wrong side or axle')
        result.append(dict(name=label, x=x, y=y, z=z, radius=radius, width=width))
    for i, a in enumerate(result):
        for b in result[i+1:]:
            if (abs(a['x']-b['x']) < (a['width']+b['width'])/2 and
                    math.hypot(a['y']-b['y'], a['z']-b['z']) < a['radius']+b['radius']):
                raise ValueError('Wheel regions overlap; reduce their size')
    return result

def read_package(path):
    raw = Path(path).read_bytes()
    if len(raw) > 64*1024*1024:
        raise ValueError('Package exceeds 64 MB')
    f = io.BytesIO(raw)
    def take(n):
        b = f.read(n)
        if len(b) != n: raise ValueError('Incomplete package')
        return b
    def integer(low=0, high=600000):
        n = struct.unpack('<i', take(4))[0]
        if not low <= n <= high: raise ValueError('Invalid package count')
        return n
    def floats(n):
        v = struct.unpack('<'+'f'*n, take(n*4))
        if not all(math.isfinite(x) for x in v): raise ValueError('Invalid geometry')
        return v
    if take(8) != b'WBCAR001': raise ValueError('Unknown car package')
    bounds = floats(3); nm = integer(1,32); np = integer(1,128)
    materials = [(floats(4), take(integer(0,16*1024*1024))) for _ in range(nm)]
    parts = []; total_v = total_i = 0
    for _ in range(np):
        name = take(integer(1,32)).decode(); mat = integer(0,nm-1); pivot = floats(3)
        if name not in ('Body', *LABELS): raise ValueError('Unknown mesh part')
        nv = integer(3,300000); ni = integer(3,600000); total_v += nv; total_i += ni
        if total_v > 300000 or total_i > 600000 or ni % 3: raise ValueError('Mesh limit exceeded')
        vertices = []
        for _ in range(nv):
            v = floats(8)
            vertices.append(tuple(v[i]+pivot[i] for i in range(3))+v[3:])
        indices = [integer(0,nv-1) for _ in range(ni)]
        parts.append(dict(name=name, material=mat, vertices=vertices, indices=indices))
    if f.read(1): raise ValueError('Unexpected package data')
    return bounds, materials, parts

def planes(region):
    x,y,z,r,w = (region[k] for k in ('x','y','z','radius','width'))
    # Inscribed polygon keeps the cut within the displayed cylinder.
    result = [(1,0,0,x+w/2),(-1,0,0,-x+w/2)]
    for i in range(SIDES):
        a = 2*math.pi*(i+.5)/SIDES; c,s = math.cos(a),math.sin(a)
        result.append((0,c,s,c*y+s*z+r*math.cos(math.pi/SIDES)))
    return result

def split_polygon(poly, plane):
    inside = []; outside = []
    def distance(v): return sum(plane[i]*v[i] for i in range(3))-plane[3]
    a = poly[-1]; da = distance(a)
    for b in poly:
        db = distance(b)
        if (da <= 0) != (db <= 0):
            t = da/(da-db); cut = tuple(a[i]+t*(b[i]-a[i]) for i in range(8))
            inside.append(cut); outside.append(cut)
        (inside if db <= 0 else outside).append(b)
        a,da = b,db
    return inside, outside

def remove_small_islands(parts):
    """Drop only tiny disconnected components, joining positions across UV seams."""
    triangles=[]; links={}; parents=[]
    def find(i):
        while parents[i]!=i:
            parents[i]=parents[parents[i]];i=parents[i]
        return i
    for pi,part in enumerate(parts):
        for t in range(0,len(part['indices']),3):
            ids=part['indices'][t:t+3]; index=len(triangles);parents.append(index)
            triangles.append((pi,ids))
            for vi in ids:
                key=tuple(round(v,5) for v in part['vertices'][vi][:3])
                if key in links:parents[find(index)]=find(links[key])
                else:links[key]=index
    groups={}
    for i in range(len(triangles)):groups.setdefault(find(i),[]).append(i)
    removed=set()
    for group in groups.values():
        if len(group)>max(4,len(triangles)*.005):continue
        points=[parts[triangles[i][0]]['vertices'][v] for i in group for v in triangles[i][1]]
        if max(max(v[a] for v in points)-min(v[a] for v in points) for a in range(3))<.18:
            removed.update(group)
    result=[dict(p,indices=[]) for p in parts]
    for i,(pi,ids) in enumerate(triangles):
        if i not in removed:result[pi]['indices'].extend(ids)
    return result,len(removed)

def repair(source, destination, regions, neutral_inner=False, clean_fragments=False, center_pivots=False):
    regions = validate_regions(regions)
    bounds, materials, parts = read_package(source)
    removed=0
    if clean_fragments:parts,removed=remove_small_islands(parts)
    neutral_material=None
    if neutral_inner:
        if len(materials)>=32:raise ValueError('No material slot available for neutral wheel faces')
        neutral_material=len(materials);materials.append(((.055,.06,.065,1),b''))
    region_by_name={r['name']:r for r in regions}
    batches = {}; total_i = total_v = 0
    counts = {label:0 for label in ('Body', *LABELS)}
    cutters = [(r, planes(r)) for r in regions]
    def emit(name, mat, poly):
        nonlocal total_i, total_v
        if len(poly) < 3: return
        for i in range(1,len(poly)-1):
            triangle = (poly[0],poly[i],poly[i+1])
            a,b,c = triangle; u = [b[j]-a[j] for j in range(3)]; v = [c[j]-a[j] for j in range(3)]
            if sum(x*x for x in (u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0])) < 1e-18: continue
            material=mat
            if neutral_material is not None and name in region_by_name:
                region=region_by_name[name];side=-1 if region['x']<0 else 1
                inner=sum(v[0] for v in triangle)/3*side < abs(region['x'])-region['width']*.25
                inward=sum(v[3] for v in triangle)/3*side < -.25
                if inner and inward:material=neutral_material
            batch = batches.setdefault((name,material), dict(vertices=[],indices=[],lookup={}))
            for vertex in triangle:
                normal_len = math.sqrt(sum(x*x for x in vertex[3:6])) or 1
                key = tuple(round(x,7) for x in vertex[:3])+tuple(round(x/normal_len,7) for x in vertex[3:6])+tuple(round(x,7) for x in vertex[6:])
                if key not in batch['lookup']:
                    batch['lookup'][key] = len(batch['vertices']); batch['vertices'].append(key); total_v += 1
                batch['indices'].append(batch['lookup'][key]); total_i += 1
            counts[name] += 1
            if total_i > 600000 or total_v > 300000: raise ValueError('Cut exceeds mesh limits; simplify the model first')
    for part in parts:
        vertices = part['vertices']; indices = part['indices']; mat = part['material']
        for t in range(0,len(indices),3):
            remaining = [[vertices[j] for j in indices[t:t+3]]]
            for region, cuts in cutters:
                rest = []
                for poly in remaining:
                    if any(max(v[axis] for v in poly) < low or min(v[axis] for v in poly) > high
                           for axis,low,high in ((0,region['x']-region['width']/2,region['x']+region['width']/2),
                                                (1,region['y']-region['radius'],region['y']+region['radius']),
                                                (2,region['z']-region['radius'],region['z']+region['radius']))):
                        rest.append(poly); continue
                    inside = poly
                    for plane in cuts:
                        inside,outside = split_polygon(inside,plane)
                        if len(outside) >= 3: rest.append(outside)
                        if len(inside) < 3: break
                    if len(inside) >= 3: emit(region['name'],mat,inside)
                remaining = rest
            for poly in remaining: emit('Body',mat,poly)
    missing = [label for label in LABELS if counts[label] < 4]
    if missing: raise ValueError('Too little geometry in '+', '.join(missing)+'. Adjust the wheel regions.')
    if counts['Body'] < 4: raise ValueError('Wheel regions consume the body; reduce them')
    batches = {k:v for k,v in batches.items() if v['indices']}
    if len(batches) > 128: raise ValueError('Too many mesh parts after cutting')
    pivots = {r['name']:(r['x'],r['y'],r['z']) for r in regions}
    if center_pivots:
        for name in LABELS:
            vertices=[v for (label,_),batch in batches.items() if label==name for v in batch['vertices']]
            pivots[name]=tuple((min(v[a] for v in vertices)+max(v[a] for v in vertices))/2 for a in range(3))
    with Path(destination).open('wb') as f:
        def integer(n): f.write(struct.pack('<i',n))
        def floats(v): f.write(struct.pack('<'+'f'*len(v),*v))
        f.write(b'WBCAR001'); floats(bounds); integer(len(materials)); integer(len(batches))
        for color,texture in materials: floats(color); integer(len(texture)); f.write(texture)
        for (name,mat),batch in batches.items():
            encoded = name.encode(); integer(len(encoded)); f.write(encoded); integer(mat)
            pivot = pivots.get(name,(0,0,0)); floats(pivot)
            integer(len(batch['vertices'])); integer(len(batch['indices']))
            for v in batch['vertices']: floats(tuple(v[i]-pivot[i] for i in range(3))+v[3:])
            f.write(struct.pack('<'+'i'*len(batch['indices']),*batch['indices']))
    if Path(destination).stat().st_size > 64*1024*1024: raise ValueError('Repaired package exceeds 64 MB')
    return dict(triangles=total_i//3,wheelCount=4,width=bounds[0],height=bounds[1],length=bounds[2],
                wheelRegions=regions,wheelNeutralInner=bool(neutral_inner),wheelCleanFragments=bool(clean_fragments),wheelCenterPivots=bool(center_pivots),removedTriangles=removed,wheelTriangleCounts=counts,
                warnings=['Manually cut wheels: inspect spinning and steering for body fragments or open seams. Cut surfaces are not rebuilt.'])

if __name__ == '__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('source'); parser.add_argument('output'); parser.add_argument('regions'); parser.add_argument('report')
    parser.add_argument('--neutral-inner',action='store_true');parser.add_argument('--clean-fragments',action='store_true');parser.add_argument('--center-pivots',action='store_true');args=parser.parse_args()
    try: Path(args.report).write_text(json.dumps(repair(args.source,args.output,json.loads(Path(args.regions).read_text()),args.neutral_inner,args.clean_fragments,args.center_pivots)))
    except ValueError as error: raise SystemExit(str(error))
