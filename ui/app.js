'use strict';
const $ = id => document.getElementById(id);
let current = null, page = 'setup', working = false, live = false, previewURL = '', reviewDirty = false;
let navigationVersion = 0, pollPending = false;
let previewVersion = 0, previewTimer = null, previewRequest = null;
const states = {draft:'ร่าง · ภาพเก็บแล้ว',analyzing:'กำลังวิเคราะห์',review:'รอตรวจทาน',final:'ยืนยันบันทึกแล้ว',error:'วิเคราะห์ไม่สำเร็จ'};
function notice(text='') { $('notice').textContent=text; $('notice').hidden=!text; }
async function api(path, method='GET', body) {
  const options={method,headers:{'X-Tire-Client':'field-ui'}};
  if(body instanceof FormData) options.body=body;
  else if(body!==undefined){options.body=JSON.stringify(body);options.headers['Content-Type']='application/json';}
  const response=await fetch('/api'+path,options);
  if(!response.ok){let data;try{data=await response.json();}catch{data={detail:response.statusText};}throw new Error(typeof data.detail==='string'?data.detail:JSON.stringify(data.detail));}
  return response.json();
}
async function run(action){if(working)return;working=true;navigationVersion++;notice();renderButtons();try{await action();}catch(error){notice(error.message);}finally{working=false;renderButtons();}}
function show(name){navigationVersion++;page=name;for(const id of ['setup','round','history'])$(id).hidden=id!==name;if(name!=='round')stopPreview();}
function renderButtons(){
  const final=current?.status==='final', analyzing=current?.status==='analyzing';
  for(const id of ['create','loadModel','historyButton','startCamera','capture','analyze','saveReview','finalize','back'])$(id).disabled=working;
  if(!current)return;
  $('capture').disabled=working||final||analyzing||!live;
  $('analyze').disabled=working||final||analyzing||!current.images.length;
  $('saveReview').disabled=working||final||analyzing;
  $('finalize').disabled=working||current.status!=='review';
  $('startCamera').disabled=working||final||analyzing;
  $('files').disabled=working||final||analyzing;
  for(const id of ['human','inspector','notes'])$(id).disabled=working||final||analyzing;
}
function setStep(index){for(let n=0;n<4;n++)$('step'+n).classList.toggle('active',index===n);}
function render(fillReview=false){
  if(!current)return;
  if(current.status==='final'&&live)stopPreview();
  $('roundTitle').textContent='ยาง '+current.tire_id;
  $('roundInfo').textContent='ผู้บันทึก '+current.operator+' · รอบ '+current.id.slice(0,8)+' · '+(current.source==='camera'?'กล้อง Pi':'นำเข้าทดสอบ');
  $('state').textContent=states[current.status]||current.status;
  $('cameraArea').hidden=current.source!=='camera';$('uploadArea').hidden=current.source!=='upload';
  $('acquisition').hidden=current.status==='final';$('imageCount').textContent=current.images.length;
  $('progress').textContent=current.status==='analyzing'?'วิเคราะห์แล้ว '+current.completed+' / '+current.images.length+' ภาพ':current.error||'';
  $('gallery').replaceChildren();
  const results=new Map((current.report?.views||[]).map(v=>[v.view_id,v]));
  current.images.forEach((view,index)=>{
    const button=document.createElement('button');button.className='photo-card';
    const img=document.createElement('img');img.src='/api/sessions/'+current.id+'/images/'+view.id;img.alt='ภาพที่ '+(index+1);img.loading='lazy';
    const label=document.createElement('span');const result=results.get(view.id);label.textContent='ภาพที่ '+(index+1)+(result?' · '+result.safety_prediction:'');if(result)label.className=result.safety_prediction;
    button.append(img,label);button.onclick=()=>{$('fullPhoto').src=img.src;$('downloadPhoto').href=img.src;$('photo').showModal();};$('gallery').append(button);
  });
  $('report').hidden=!current.report;
  if(current.report){const r=current.report;$('overall').className='result '+r.overall_condition;$('overall').textContent=r.overall_condition+' · Normal '+r.normal_views_count+' / Warning '+r.warning_views_count+' / Abnormal '+r.abnormal_views_count;$('scores').replaceChildren();r.views.forEach((v,i)=>{const tr=document.createElement('tr');[i+1,v.safety_prediction,...['Normal','Warning','Abnormal'].map(k=>(v.scores[k]*100).toFixed(2)+'%')].forEach(value=>{const td=document.createElement('td');td.textContent=value;tr.append(td);});$('scores').append(tr);});}
  if(fillReview){$('human').value=current.review.inspector_label;$('inspector').value=current.review.inspector;$('notes').value=current.review.notes;reviewDirty=false;$('reviewState').textContent='';}
  $('export').href='/api/sessions/'+current.id+'/export';
  setStep(current.status==='final'?3:current.report?2:1);renderButtons();
}
async function health(){const h=await api('/health');$('health').textContent=(h.model_loaded?'โมเดลพร้อม':'ยังไม่โหลดโมเดล')+' · '+(h.camera_open?'กล้องเปิดแล้ว':'กล้องยังไม่เปิด')+' · พื้นที่ '+h.free_mb+' MB';$('modelVersion').textContent=h.model_version;if(h.model_error)notice(h.model_error);}
function stopPreview(){
  live=false;previewVersion++;clearTimeout(previewTimer);previewTimer=null;
  if(previewRequest)previewRequest.abort();previewRequest=null;
  $('preview').removeAttribute('src');
  if(previewURL)URL.revokeObjectURL(previewURL);previewURL='';
  $('preview').hidden=true;$('previewNote').hidden=false;$('previewNote').textContent='ภาพสดหยุดอยู่';renderButtons();
}
function startPreview(){
  stopPreview();live=true;previewLoop(previewVersion);renderButtons();
}
async function previewLoop(version){
  if(version!==previewVersion||!live||page!=='round'||current?.status==='analyzing')return;
  const started=performance.now(), controller=new AbortController();previewRequest=controller;
  const timeout=setTimeout(()=>controller.abort(),5000);
  try{
    const r=await fetch('/api/camera/preview',{signal:controller.signal,cache:'no-store'});
    if(!r.ok){const e=await r.json();throw new Error(e.detail);}
    const blob=await r.blob();if(version!==previewVersion||!live)return;
    const previous=previewURL;previewURL=URL.createObjectURL(blob);$('preview').src=previewURL;
    if(previous)URL.revokeObjectURL(previous);
    $('preview').hidden=false;$('previewNote').hidden=true;
  }catch(e){
    if(version!==previewVersion)return;
    stopPreview();notice(e.name==='AbortError'?'กล้องไม่ตอบสนอง กรุณากดเชื่อมกล้องใหม่':e.message);return;
  }finally{clearTimeout(timeout);if(previewRequest===controller)previewRequest=null;}
  if(version===previewVersion&&live)previewTimer=setTimeout(()=>previewLoop(version),Math.max(0,100-(performance.now()-started)));
}
function reviewValues(){return {inspector_label:$('human').value,inspector:$('inspector').value,notes:$('notes').value};}
async function saveReview(){
  const sid=current.id, submitted=reviewValues();
  const saved=await api('/sessions/'+sid+'/review','PUT',submitted);
  if(current?.id!==sid)return;
  current=saved;reviewDirty=JSON.stringify(reviewValues())!==JSON.stringify(submitted);
  $('reviewState').textContent=reviewDirty?'มีหมายเหตุที่ยังไม่บันทึก':'บันทึกหมายเหตุแล้ว';
  if(reviewDirty)throw new Error('ข้อความเปลี่ยนระหว่างบันทึก กรุณาบันทึกอีกครั้ง');
}
for(const id of ['human','inspector','notes'])$(id).addEventListener('input',()=>{reviewDirty=true;$('reviewState').textContent='มีหมายเหตุที่ยังไม่บันทึก';});
$('loadModel').onclick=()=>run(async()=>{await api('/model/load','POST');await health();});
$('create').onclick=()=>run(async()=>{current=await api('/sessions','POST',{tire_id:$('tire').value,operator:$('operator').value,source:$('source').value});show('round');render(true);});
$('startCamera').onclick=()=>run(async()=>{stopPreview();await api('/camera/reconnect','POST');startPreview();await health();});
$('capture').onclick=()=>run(async()=>{current=await api('/sessions/'+current.id+'/capture','POST');render();});
$('files').onchange=()=>run(async()=>{const files=[...$('files').files];for(const file of files){const form=new FormData();form.append('file',file);current=await api('/sessions/'+current.id+'/images','POST',form);render();}$('files').value='';});
$('analyze').onclick=()=>run(async()=>{if(reviewDirty)await saveReview();stopPreview();current=await api('/sessions/'+current.id+'/analyze','POST');render();});
$('saveReview').onclick=()=>run(async()=>{await saveReview();render();});
$('finalize').onclick=()=>run(async()=>{await saveReview();current=await api('/sessions/'+current.id+'/finalize','POST');render(true);notice('ยืนยันบันทึกแล้ว สามารถส่งออกและเริ่มยางเส้นถัดไปได้');});
$('back').onclick=()=>run(async()=>{if(reviewDirty)await saveReview();show('setup');setStep(0);current=null;});
$('historyButton').onclick=()=>run(async()=>{if(reviewDirty&&current)await saveReview();const items=await api('/sessions');$('historyList').replaceChildren();for(const item of items){const row=document.createElement('div');row.className='history-row';const text=document.createElement('span');text.textContent=item.tire_id+' · '+states[item.status]+' · '+new Date(item.created_at).toLocaleString('th-TH');const button=document.createElement('button');button.textContent='เปิดรอบตรวจ';button.onclick=()=>run(async()=>{current=await api('/sessions/'+item.id);show('round');render(true);});row.append(text,button);$('historyList').append(row);}if(!items.length)$('historyList').textContent='ยังไม่มีประวัติ';show('history');});
$('closeHistory').onclick=()=>{if(!working)show(current?'round':'setup');};$('closePhoto').onclick=()=>$('photo').close();
window.addEventListener('beforeunload',event=>{if(reviewDirty){event.preventDefault();event.returnValue='';}});
async function pollSession(){
  if(pollPending||working||page!=='round'||current?.status!=='analyzing')return;
  const sid=current.id, version=navigationVersion;pollPending=true;
  try{
    const item=await api('/sessions/'+sid);
    if(working||version!==navigationVersion||current?.id!==sid||current.status!=='analyzing')return;
    current=item;render();
  }catch(e){if(version===navigationVersion&&current?.id===sid)notice(e.message);}
  finally{pollPending=false;}
}
setInterval(pollSession,1000);
health().catch(e=>notice(e.message));
