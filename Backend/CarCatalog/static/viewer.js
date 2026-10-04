import * as THREE from './vendor/three.module.min.js';

export class CarViewer {
 constructor(container){
  this.container=container;this.renderer=new THREE.WebGLRenderer({antialias:true,alpha:true});this.renderer.setPixelRatio(Math.min(devicePixelRatio,2));this.renderer.outputColorSpace=THREE.SRGBColorSpace;this.renderer.toneMapping=THREE.ACESFilmicToneMapping;this.renderer.toneMappingExposure=1.3;container.append(this.renderer.domElement);
  this.scene=new THREE.Scene();this.camera=new THREE.PerspectiveCamera(35,1,.1,100);this.scene.add(new THREE.HemisphereLight(0xe3efff,0x5b6674,2.4));
  for(const [position,color,power] of [[[4,7,6],0xffe1c2,3],[[-5,3,0],0xb9d9ff,2],[[2,5,-6],0xffffff,2.5]]){const light=new THREE.DirectionalLight(color,power);light.position.set(...position);this.scene.add(light)}
  const floor=new THREE.Mesh(new THREE.CircleGeometry(3.6,80),new THREE.MeshBasicMaterial({color:0x18212c,transparent:true,opacity:.5}));floor.rotation.x=-Math.PI/2;floor.position.y=-.045;this.scene.add(floor);
  const ring=new THREE.Mesh(new THREE.RingGeometry(3.2,3.21,90),new THREE.MeshBasicMaterial({color:0x7b8a9c,transparent:true,opacity:.25,side:THREE.DoubleSide}));ring.rotation.x=-Math.PI/2;ring.position.y=-.04;this.scene.add(ring);
  this.target=new THREE.Vector3(0,.7,0);this.reset();this.serial=0;this.auto=false;this.enabled=true;
  this.observer=new ResizeObserver(()=>this.resize());this.observer.observe(container);this.resize();
  let last=null;const canvas=this.renderer.domElement;
  canvas.addEventListener('pointerdown',e=>{last=[e.clientX,e.clientY];canvas.setPointerCapture(e.pointerId);this.auto=false;container.dispatchEvent(new Event('orbitstart'))});
  canvas.addEventListener('pointermove',e=>{if(!last)return;this.theta-=(e.clientX-last[0])*.009;this.phi=Math.max(.22,Math.min(1.65,this.phi+(e.clientY-last[1])*.008));last=[e.clientX,e.clientY]});
  canvas.addEventListener('pointerup',()=>last=null);canvas.addEventListener('pointercancel',()=>last=null);
  canvas.addEventListener('wheel',e=>{e.preventDefault();this.radius=Math.max(4,Math.min(16,this.radius*Math.exp(e.deltaY*.001)))},{passive:false});
  container.parentElement.addEventListener('keydown',e=>{const keys=['ArrowLeft','ArrowRight','ArrowUp','ArrowDown','+','=','-'];if(!keys.includes(e.key))return;e.preventDefault();if(e.key==='ArrowLeft')this.theta-=.15;if(e.key==='ArrowRight')this.theta+=.15;if(e.key==='ArrowUp')this.phi=Math.max(.22,this.phi-.1);if(e.key==='ArrowDown')this.phi=Math.min(1.65,this.phi+.1);if(e.key==='+'||e.key==='=')this.radius=Math.max(4,this.radius-.5);if(e.key==='-')this.radius=Math.min(16,this.radius+.5)});
  this.wheelAngle=0;this.spinWheels=false;this.steerWheels=0;
  let previous=performance.now();this.renderer.setAnimationLoop(now=>{const dt=Math.min(.1,(now-previous)/1000);previous=now;if(!this.enabled||document.hidden)return;if(this.auto)this.theta+=dt*.22;if(this.spinWheels)this.wheelAngle+=dt*2;for(const mesh of this.model?.children||[]){if(!mesh.name.startsWith('Wheel'))continue;mesh.rotation.set(0,0,0);mesh.rotateY(mesh.name.startsWith('WheelF')?this.steerWheels:0);mesh.rotateX(this.wheelAngle)}this.camera.position.set(this.radius*Math.sin(this.phi)*Math.sin(this.theta),this.target.y+this.radius*Math.cos(this.phi),this.radius*Math.sin(this.phi)*Math.cos(this.theta));this.camera.lookAt(this.target);this.renderer.render(this.scene,this.camera)});
 }
 resize(){const {width,height}=this.container.getBoundingClientRect();if(!width||!height)return;this.renderer.setSize(width,height,false);this.camera.aspect=width/height;this.camera.updateProjectionMatrix()}
 reset(){this.theta=.7;this.phi=1.16;this.radius=8.8}
 angle(view){this.auto=false;const angles={hero:[.7,1.16],front:[0,Math.PI/2-.04],rear:[Math.PI,Math.PI/2-.04],left:[-Math.PI/2,Math.PI/2-.04],right:[Math.PI/2,Math.PI/2-.04]};[this.theta,this.phi]=angles[view];this.radius=8.8}
 clear(){this.setWheelRegions([]);this.spinWheels=false;this.steerWheels=0;this.wheelAngle=0;if(!this.model)return;this.scene.remove(this.model);const mats=new Set();this.model.traverse(o=>{o.geometry?.dispose();if(o.material)mats.add(o.material)});for(const m of mats){m.map?.dispose();m.dispose()}this.model=null}
 setWheelRegions(regions,selected=0){
  if(this.guides){this.scene.remove(this.guides);this.guides.traverse(o=>{o.geometry?.dispose();o.material?.dispose()})}
  this.guides=new THREE.Group();this.scene.add(this.guides);
  regions.forEach((r,i)=>{const geometry=new THREE.CylinderGeometry(r.radius,r.radius,r.width,24,1,true);geometry.rotateZ(Math.PI/2);const edges=new THREE.EdgesGeometry(geometry);geometry.dispose();const line=new THREE.LineSegments(edges,new THREE.LineBasicMaterial({color:i===selected?0xff854f:0x56d5d1,depthTest:false,transparent:true,opacity:i===selected?1:.4}));line.position.set(r.x,r.y,r.z);line.renderOrder=10;this.guides.add(line)});
 }
 suggestedWheelRegions(){
  const [width,height,length]=this.bounds;const clamp=(v,a,b)=>Math.min(b,Math.max(a,v));
  return ['WheelFL','WheelFR','WheelRL','WheelRR'].map(name=>{
   const box=new THREE.Box3();for(const mesh of this.model.children.filter(o=>o.name===name)){mesh.geometry.computeBoundingBox();box.union(mesh.geometry.boundingBox.clone().translate(mesh.position))}
   const center=new THREE.Vector3(),size=new THREE.Vector3();if(!box.isEmpty()){box.getCenter(center);box.getSize(size)}else{center.set((name.endsWith('L')?-1:1)*width*.4,height*.25,(name.startsWith('WheelF')?1:-1)*length*.32);size.set(width*.17,height*.5,height*.5)}
   return {name,x:clamp(center.x,-1.8,1.8),y:clamp(center.y,.05,1.6),z:clamp(center.z,-2.2,2.2),radius:clamp(Math.max(size.y,size.z)*.515,.12,.85),width:clamp(size.x+.025,.05,.8)};
  });
 }
 async load(url){
  const serial=++this.serial;this.clear();const response=await fetch(url);if(!response.ok)throw Error('Model preview unavailable');const buffer=await response.arrayBuffer();if(serial!==this.serial)return;
  if(buffer.byteLength>64*1024*1024)throw Error('Preview exceeds size limit');const data=new DataView(buffer);let offset=0;
  const take=n=>{if(n<0||offset+n>data.byteLength)throw Error('Incomplete car package');let b=new Uint8Array(buffer,offset,n);offset+=n;return b};
  const int=()=>{const b=take(4);return new DataView(b.buffer,b.byteOffset,4).getInt32(0,true)};
  const float=()=>{const b=take(4);const v=new DataView(b.buffer,b.byteOffset,4).getFloat32(0,true);if(!Number.isFinite(v))throw Error('Invalid mesh');return v};
  const count=(max,min=0)=>{let n=int();if(n<min||n>max)throw Error('Invalid package size');return n};
  if(new TextDecoder().decode(take(8))!=='WBCAR001')throw Error('Unknown preview format');this.bounds=[float(),float(),float()];const nm=count(32,1),np=count(128,1);const materials=[];const textures=[];const group=new THREE.Group();
  try{
   for(let i=0;i<nm;i++){
    const color=new THREE.Color().setRGB(float(),float(),float());float();const n=count(16*1024*1024);let map=null;
    if(n){const bytes=take(n);const url=URL.createObjectURL(new Blob([bytes],{type:'image/png'}));try{map=await new THREE.TextureLoader().loadAsync(url);map.colorSpace=THREE.SRGBColorSpace;map.anisotropy=4;textures.push(map)}finally{URL.revokeObjectURL(url)}}
    materials.push(new THREE.MeshStandardMaterial({color,map,roughness:.65,metalness:.08,side:THREE.DoubleSide}));
   }
   let total=0;
   for(let part=0;part<np;part++){
    const name=new TextDecoder().decode(take(count(32,1)));const material=count(nm-1);const pivot=[float(),float(),float()];const nv=count(300000,3),ni=count(600000,3);total+=nv;if(total>300000||ni%3)throw Error('Invalid mesh limits');
    const positions=new Float32Array(nv*3),normals=new Float32Array(nv*3),uv=new Float32Array(nv*2);
    for(let i=0;i<nv;i++){for(let j=0;j<3;j++)positions[i*3+j]=float();for(let j=0;j<3;j++)normals[i*3+j]=float();uv[i*2]=float();uv[i*2+1]=float()}
    const indices=new Uint32Array(ni);for(let i=0;i<ni;i++)indices[i]=count(nv-1);
    const geometry=new THREE.BufferGeometry();geometry.setAttribute('position',new THREE.BufferAttribute(positions,3));geometry.setAttribute('normal',new THREE.BufferAttribute(normals,3));geometry.setAttribute('uv',new THREE.BufferAttribute(uv,2));geometry.setIndex(new THREE.BufferAttribute(indices,1));
    const mesh=new THREE.Mesh(geometry,materials[material]);mesh.position.set(...pivot);mesh.name=name;group.add(mesh);
   }
   if(serial!==this.serial){group.traverse(o=>o.geometry?.dispose());for(const m of materials)m.dispose();for(const t of textures)t.dispose();return}
   this.model=group;this.scene.add(group);this.reset();
  }catch(e){group.traverse(o=>o.geometry?.dispose());for(const m of materials)m.dispose();for(const t of textures)t.dispose();throw e}
 }
}
