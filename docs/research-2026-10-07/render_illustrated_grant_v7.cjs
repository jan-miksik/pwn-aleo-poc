// Render the original HTML design and extract only its illustration components.
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const { pathToFileURL } = require('url');

(async () => {
  const docs = path.resolve(__dirname, '..');
  const assetDir = path.join(docs, 'grant-assets-v6');
  fs.mkdirSync(assetDir, {recursive:true});
  const browser = await chromium.launch({
    executablePath:'/Users/janm/Library/Caches/ms-playwright/chromium-1223/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing',
    headless:true,
  });
  const page = await browser.newPage({viewport:{width:1100,height:900},deviceScaleFactor:3});
  await page.route('https://**/*', route => route.abort());
  await page.goto(pathToFileURL(path.join(docs,'private-lending-aleo-grant-overview-v7.html')).href);
  await page.evaluate(()=>document.fonts.ready);
  await page.pdf({path:path.join(docs,'private-lending-aleo-grant-draft-v7.pdf'),format:'A4',printBackground:true,preferCSSPageSize:true});
  await page.emulateMedia({media:'screen'});
  await page.addStyleTag({content:'body {max-width:487pt !important; margin:0 auto !important; padding:0 !important;}'});
  const figures=[
    ['lifecycle','section:has(> h2:text-is("Protocol model")) svg'],
    ['elastic-draws','.draws'],
    ['discovery','section:has(> h2:text-is("Discovery and indexing")) .flow'],
    ['architecture','section:has(> h2:text-is("Architecture")) svg'],
    ['privacy-boundary','section:has(> h2:text-is("Privacy model, measured on testnet")) .fig .flow'],
    ['timeline','.timeline'],
  ];
  const manifest=[];
  for(const [id, selector] of figures) {
    const target=page.locator(selector);
    await target.screenshot({path:path.join(assetDir,id+'.png')});
    const markup=await target.evaluate(el=>el.outerHTML);
    fs.writeFileSync(path.join(assetDir,id+'.'+(id==='lifecycle'||id==='architecture'?'svg':'html')),markup);
    manifest.push({id,selector,image:'grant-assets-v6/'+id+'.png'});
  }
  fs.writeFileSync(path.join(assetDir,'figures.json'),JSON.stringify(manifest,null,2));
  console.log(JSON.stringify({pdf:path.join(docs,'private-lending-aleo-grant-draft-v7.pdf'),figures:manifest.length}));
  await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
