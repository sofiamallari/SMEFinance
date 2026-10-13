const {chromium}=require('C:/Users/User/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const {spawn}=require('child_process');
const path=require('path');
(async()=>{const proc=spawn('C:/Users/User/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe',['-m','copilot.server','--port','8123'],{cwd:process.cwd(),env:{...process.env,COPILOT_AUTH_MODE:"demo",COPILOT_TRANSACTION_FILE:path.resolve('evidence/ui-ledger-'+Date.now()+'.jsonl')},windowsHide:true});let browser;
try{browser=await chromium.launch({headless:true,channel:"msedge"});const page=await browser.newPage({viewport:{width:1440,height:1000}});let errors=[];page.on('pageerror',e=>errors.push(e.message));
await page.goto('http://127.0.0.1:8123');await page.waitForSelector('#merchant option',{state:'attached'});await page.click('[data-tab="transactions"]');await page.fill('#tamount','456.78');await page.fill('#tref','UI-SALE-001');await page.click('#singleform button');await page.waitForSelector('#tledger [data-edit]');
await page.setInputFiles('#tfile',{name:'test.csv',mimeType:'text/csv',buffer:Buffer.from('date,type,amount,channel,reference\n2026-09-29,expense,12.34,cash,UI-EXP-001\n')});await page.waitForFunction(()=>!document.querySelector('#timport').disabled);page.once('dialog',d=>d.accept());await page.click('#timport');await page.waitForFunction(()=>document.querySelector('#tpreview').textContent.includes('Saved 1'));
await page.click('[data-tab="dashboard"]');await page.waitForFunction(()=>document.querySelector('#dkpis').textContent.includes('Expenses'));await page.screenshot({path:'evidence/dashboard.png',fullPage:true});
await page.selectOption('#role','staff');await page.click('[data-tab="transactions"]');await page.waitForFunction(()=>!document.querySelector('#tledger [data-edit]'));await page.screenshot({path:'evidence/transactions.png',fullPage:true});await page.selectOption('#role','lender_analyst');await page.waitForFunction(()=>document.querySelector('#tfile').disabled);
if(errors.length)throw Error(errors.join('\n'));console.log('PASS: single save, CSV preview/confirmation, dashboard render, staff and financing-agent UI permissions');
}finally{if(browser)await browser.close();proc.kill()}})().catch(e=>{console.error(e);process.exitCode=1});


