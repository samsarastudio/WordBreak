import {CarViewer} from './viewer.js';

const $=id=>document.getElementById(id);
const dimensions=[['x','Across car (X)',-1.8,1.8],['y','Hub height (Y)',.05,1.6],['z','Along car (Z)',-2.2,2.2],['radius','Tire radius',.12,.85],['width','Tire width',.05,.8]];

export function createWheelEditor({api,onApplied}){
 let viewer,car,revision,regions,job,busy=false,testing=false;
 const dialog=$('wheelDialog');
 for(const [key,label,min,max] of dimensions){
  const row=document.createElement('div');row.className='wheel-dimension';
  row.innerHTML=`<label for="wheel-${key}">${label}</label><div><input id="wheel-${key}" type="number" min="${min}" max="${max}" step="0.01"><input id="wheel-range-${key}" type="range" min="${min}" max="${max}" step="0.01" aria-label="${label} slider"></div>`;
  $('wheelDimensions').append(row);
  for(const prefix of ['wheel-','wheel-range-'])$(prefix+key).oninput=e=>{
   const value=e.target.valueAsNumber;if(!Number.isFinite(value)||value<min||value>max)return;
   regions[Number($('wheelSelect').value)][key]=value;
   $(prefix==='wheel-'?'wheel-range-'+key:'wheel-'+key).value=value;
   viewer.setWheelRegions(regions,Number($('wheelSelect').value));
  };
 }
 function fields(){const index=Number($('wheelSelect').value),region=regions[index];for(const [key] of dimensions){$('wheel-'+key).value=region[key].toFixed(3);$('wheel-range-'+key).value=region[key]}viewer.setWheelRegions(regions,index)}
 function lock(value){busy=value;$('wheelFields').disabled=value||testing;$('wheelBuild').disabled=value;$('wheelClose').disabled=value;$('wheelAdjust').disabled=value;$('wheelRestore').disabled=value;$('wheelApply').disabled=value||!$('wheelReviewed').checked}
 function testMode(value){testing=value;$('wheelTest').hidden=!value;$('wheelReviewLabel').hidden=!value;$('wheelApply').hidden=!value;$('wheelBuild').hidden=value;$('wheelReviewed').checked=false;$('wheelSpin').checked=false;$('wheelSteer').value=0;viewer.spinWheels=false;viewer.steerWheels=0;viewer.wheelAngle=0;lock(false)}
 async function loadOriginal(){lock(true);try{await viewer.load(car.wheelRepairOriginal?.package||car.package);testMode(false);fields();$('wheelStatus').textContent='Position the cylinders, then build a preview. Your saved car is unchanged.'}finally{lock(false)}}
 $('wheelSelect').onchange=fields;
 $('wheelMirror').onclick=()=>{const index=Number($('wheelSelect').value),other=index^1;regions[other]={...regions[index],name:regions[other].name,x:-regions[index].x};fields()};
 document.querySelectorAll('[data-wheel-view]').forEach(b=>b.onclick=()=>viewer.angle(b.dataset.wheelView));
 $('wheelSpin').onchange=()=>viewer.spinWheels=$('wheelSpin').checked;
 $('wheelSteer').oninput=()=>viewer.steerWheels=Number($('wheelSteer').value)*Math.PI/180;
 $('wheelReviewed').onchange=()=>lock(busy);
 $('wheelAdjust').onclick=()=>{job=null;$('wheelError').textContent='';loadOriginal().catch(e=>$('wheelError').textContent=e.message)};
 $('wheelBuild').onclick=async()=>{
  lock(true);job=null;$('wheelError').textContent='';$('wheelStatus').textContent='Cutting wheel regions and rendering a test preview…';
  try{
   let task=await api('/admin/wheels/preview',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:car.id,sha256:car.sha256,regions,neutralInner:$('wheelNeutral').checked,cleanFragments:$('wheelClean').checked,centerPivots:$('wheelCenter').checked})});
   const deadline=Date.now()+480000;
   while(['queued','converting'].includes(task.state)){
    if(Date.now()>deadline)throw Error('Preview timed out. Close this window and try again after the current job finishes.');
    await new Promise(resolve=>setTimeout(resolve,1200));task=await api('/admin/jobs/'+task.id);
   }
   if(task.state!=='ready')throw Error(task.message||'Preview failed');
   await viewer.load(task.asset.package);job=task;testMode(true);
   $('wheelStatus').textContent='Test preview only — not applied. '+'Removed '+(task.asset.removedTriangles||0)+' fragment triangles. '+Object.entries(task.asset.wheelTriangleCounts).filter(([name])=>name!=='Body').map(([name,n])=>name.replace('Wheel','')+': '+n.toLocaleString()+' triangles').join(' · ');
  }catch(e){$('wheelError').textContent=e.message;$('wheelStatus').textContent='Your saved model has not changed.'}finally{lock(false)}
 };
 $('wheelApply').onclick=async()=>{
  if(!job||!$('wheelReviewed').checked)return;
  lock(true);$('wheelError').textContent='';
  try{await api('/admin/wheels/apply',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({job:job.id,revision})});lock(false);dialog.close();await onApplied(car.id,'Wheel repair applied. The original wheel setup is saved for restore.')}
  catch(e){$('wheelError').textContent=e.message}finally{lock(false)}
 };
 $('wheelRestore').onclick=async()=>{
  if(!confirm('Restore the original wheel setup? Available cars update on the next sync.'))return;
  lock(true);$('wheelError').textContent='';
  try{await api('/admin/wheels/restore',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:car.id,revision})});lock(false);dialog.close();await onApplied(car.id,'Original wheel setup restored.')}
  catch(e){$('wheelError').textContent=e.message}finally{lock(false)}
 };
 $('wheelClose').onclick=()=>{if(!busy)dialog.close()};dialog.addEventListener('cancel',e=>{if(busy)e.preventDefault()});dialog.addEventListener('close',()=>{viewer.enabled=false;viewer.clear()});
 window.addEventListener('beforeunload',e=>{if(busy){e.preventDefault();e.returnValue=''}});
 return {async open(selected,catalogRevision){
  car=structuredClone(selected);$('wheelClean').checked=!!car.wheelCleanFragments;$('wheelCenter').checked=!!car.wheelCenterPivots;$('wheelNeutral').checked=!!car.wheelNeutralInner;revision=catalogRevision;job=null;testing=false;$('wheelError').textContent='';$('wheelStatus').textContent='Loading wheel setup…';$('wheelSelect').value='0';
  $('wheelApplyNote').textContent=car.enabled?'Applying replaces this available car for players on their next sync. The original model is kept for restore.':'Applying saves the repaired model. This car stays in review until you enable and publish it.';
  $('wheelRestore').hidden=!car.wheelRepairOriginal;dialog.showModal();viewer??=new CarViewer($('wheelViewer'));viewer.enabled=true;testMode(false);lock(true);
  try{await viewer.load(car.wheelRepairOriginal?.package||car.package);regions=structuredClone(car.wheelRegions||viewer.suggestedWheelRegions());fields();$('wheelStatus').textContent='Adjust each cylinder to enclose only its tire and rim. Your saved model is unchanged.'}
  catch(e){$('wheelError').textContent=e.message;lock(false);$('wheelBuild').disabled=true;$('wheelFields').disabled=true;return}
  lock(false);
 }};
}
