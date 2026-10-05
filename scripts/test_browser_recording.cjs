const { chromium } = require(process.env.MAI_PLAYWRIGHT || '../.runtime/browser/node_modules/playwright');
(async()=>{
 const browser=await chromium.launch({headless:true,channel:'chromium',args:['--no-sandbox','--use-fake-device-for-media-stream','--use-fake-ui-for-media-stream']});
 const context=await browser.newContext({permissions:['microphone'],viewport:{width:390,height:844}});
 const page=await context.newPage(); const errors=[]; page.on('pageerror',e=>errors.push(e.message));
 await page.goto('http://127.0.0.1:8000');
 await page.getByRole('button',{name:'Register',exact:true}).click();
 await page.locator('input[type=email]').fill(`recording-${Date.now()}@example.invalid`);
 await page.locator('input[type=password]').fill('Laptop-validation-2026');
 await page.getByRole('button',{name:'Create Account',exact:true}).click();
 await page.getByRole('button',{name:'Start Recording',exact:true}).click();
 await page.getByRole('button',{name:'Stop & Save',exact:true}).waitFor();
 await page.waitForTimeout(6000);
 await page.getByRole('button',{name:'Stop & Save',exact:true}).click();
 await page.getByText('Recording saved on this device.',{exact:true}).waitFor();
 await page.reload();
 await page.getByRole('button',{name:'Recover recording',exact:true}).click();
 await page.getByText('1 file(s) ready',{exact:true}).waitFor();
 const exists=await page.evaluate(()=>new Promise((resolve,reject)=>{
  const r=indexedDB.open('meet-iq-recording',1);r.onsuccess=()=>{const t=r.result.transaction('chunks','readonly');const count=t.objectStore('chunks').count(); count.onsuccess=()=>resolve(count.result);};r.onerror=reject;
 }));
 console.log(JSON.stringify({savedChunks:exists,recoveredAfterReload:true,errors}));
 if(errors.length||!exists)throw new Error('Recording recovery failed');
 await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
