'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
function fixture(){
  const elements=new Map(), timers=new Map();let timerId=0;
  function element(id){
    if(!elements.has(id))elements.set(id,{value:'',classList:{toggle(){}},addEventListener(){},
      removeAttribute(key){delete this[key];},replaceChildren(){},append(){}});
    return elements.get(id);
  }
  const c=vm.createContext({document:{getElementById:element},window:{addEventListener(){}},
    setInterval(){},setTimeout:(f,ms)=>{timers.set(++timerId,{f,ms});return timerId;},
    clearTimeout:id=>timers.delete(id),performance,AbortController,FormData,
    URL:{createObjectURL:()=> 'blob:test',revokeObjectURL(){}},
    fetch:async()=>({ok:true,json:async()=>({})})});
  vm.runInContext(fs.readFileSync('ui/app.js','utf8'),c);
  const run=source=>vm.runInContext(source,c);
  run("render=()=>{};current={id:'A',status:'analyzing',images:[]};page='round'");
  return {c,run,timers,element};
}
(async()=>{
  {
    const {run}=fixture();
    run('api=()=>new Promise(r=>globalThis.reply=r)');
    const pending=run('pollSession()');
    run("show('history');current={id:'B',status:'draft',images:[]};reply({id:'A',status:'review'})");
    await pending;assert.equal(run('current.id'),'B');
  }
  {
    const {run}=fixture();
    run('api=()=>new Promise(r=>globalThis.reply=r)');
    const pending=run('pollSession()');
    run("navigationVersion++;current={id:'A',status:'final',images:[]};reply({id:'A',status:'review'})");
    await pending;assert.equal(run('current.status'),'final');
  }
  {
    const {run,element}=fixture();
    run("current.status='review';$('notes').value='old';api=()=>new Promise(r=>globalThis.reply=r)");
    const saving=run('saveReview()');
    run("$('notes').value='new';reply({id:'A',status:'review',review:{notes:'old'}})");
    await assert.rejects(saving);assert.equal(run('reviewDirty'),true);
    assert.equal(element('notes').value,'new');
    run('working=true;renderButtons()');assert.equal(element('notes').disabled,true);
  }
  {
    const {c,run,timers}=fixture();
    c.fetch=async()=>({ok:true,blob:async()=>({})});
    run("current.status='draft';live=true");
    await run('previewLoop(previewVersion)');
    assert.equal(timers.size,1);
    const old=[...timers.values()][0].f;
    run('stopPreview();live=true');await run('previewLoop(previewVersion)');
    assert.equal(timers.size,1);await old();assert.equal(timers.size,1);
    assert.ok([...timers.values()][0].ms<=100);
  }
  {
    const {c,run,element}=fixture();let reply;
    c.fetch=()=>new Promise(r=>reply=r);
    run("current.status='draft';live=true");
    const pending=run('previewLoop(previewVersion)');
    run('stopPreview()');reply({ok:true,blob:async()=>({})});await pending;
    assert.equal(element('preview').hidden,true);assert.equal(element('preview').src,undefined);
  }
  console.log('PASS: 5 UI regression cases (stale polls, review edits, preview lifecycle)');
})().catch(e=>{console.error(e);process.exitCode=1;});
