// Capture the real application with isolated, explicitly synthetic data.
const { chromium } = require('../.runtime/browser/node_modules/playwright');
const fs = require('node:fs/promises');
const path = require('node:path');
const assert = require('node:assert/strict');
(async () => {
 const browser = await chromium.launch({headless:true,channel:'chromium',args:['--no-sandbox']});
 try {
  const context = await browser.newContext({viewport:{width:1280,height:850},serviceWorkers:'block'});
  await context.addInitScript(() => {localStorage.setItem('token','presentation-fixture');localStorage.setItem('userEmail','demo@example.invalid');});
  const transcript=[{segment_id:1,start:85,end:93,speaker:'SPEAKER_00',text:'We could use the smaller prototype. Can we check its battery life first?'},{segment_id:2,start:94,end:101,speaker:'SPEAKER_01',text:'I will test the battery and bring the results to our next meeting.'}];
  const data={meeting_overview:{duration_s:300},transcript_segments:transcript,speaker_names:{SPEAKER_00:'Speaker A',SPEAKER_01:'Speaker B'},participants:[],action_items:[],decisions:[],processing:{speaker_separation:true,accuracy_measured:false},discussion_review:{status:'ready',requires_review:true,passages:[{source_segment_id:1,...transcript[0],score:.62}]},event_timeline:[],slides:[],aligned_segments:[]};
  await context.route('**/*',async route=>{
   const u=new URL(route.request().url());assert.equal(u.hostname,'127.0.0.1');const json=body=>route.fulfill({json:body});
   if(u.pathname==='/api/auth/me')return json({user_id:'demo',email:'demo@example.invalid'});
   if(u.pathname==='/api/profile')return json({name:'',role:'',organization:''});
   if(u.pathname==='/api/health')return json({asr_ready:true,asr_model:'small',asr_models:['small','large-v3-turbo'],diarization:{ready:true,message:'Local speaker models are ready.'}});
   if(u.pathname==='/api/meetings')return json({meetings:[{id:'presentation-demo',title:'Prototype planning — illustrative demo',status:'completed',created_at:'2026-10-20T12:00:00'}]});
   if(u.pathname==='/api/meetings/presentation-demo')return json({id:'presentation-demo',title:'Prototype planning — illustrative demo',status:'completed',data,audio_url:null});
   assert(!u.pathname.startsWith('/api/'),u.pathname);
   const file=path.join(__dirname,'../frontend/dist',u.pathname==='/'?'index.html':decodeURIComponent(u.pathname));
   return route.fulfill({body:await fs.readFile(file),contentType:file.endsWith('.js')?'application/javascript':file.endsWith('.css')?'text/css':file.endsWith('.png')?'image/png':'text/html'});
  });
  const page=await context.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto('http://127.0.0.1/');await page.getByRole('button',{name:'History',exact:true}).click();
  await page.getByRole('button',{name:/^Prototype planning/}).click();await page.getByRole('button',{name:'Decisions',exact:true}).click();
  await page.getByRole('heading',{name:'Discussion passages to review',exact:true}).waitFor();
  await fs.mkdir(path.join(__dirname,'assets'),{recursive:true});
  await page.screenshot({path:path.join(__dirname,'assets/review_interface.png'),fullPage:true});
  await page.setViewportSize({width:480,height:950});
  await page.getByRole('heading',{name:'Discussion passages to review',exact:true}).locator('..').screenshot({path:path.join(__dirname,'assets/review_card.png')});
  assert.deepEqual(errors,[]);console.log('Captured real UI using synthetic data; no model inference or user database access.');
 } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
