import fs from 'node:fs/promises';
const base='file:///C:/Users/Pin%20Guang/AppData/Local/OpenAI/Codex/runtimes/cua_node/b474a88d5d105afa/bin/node_modules/';
const canvas=await import(base+'@napi-rs/canvas/index.js');
Object.assign(globalThis,{DOMMatrix:canvas.DOMMatrix,ImageData:canvas.ImageData,Path2D:canvas.Path2D});
const pdf=await import(base+'pdfjs-dist/legacy/build/pdf.mjs');
const final=process.argv.includes('--final');
const doc=await pdf.getDocument({data:new Uint8Array(await fs.readFile(final?'output/pdf/Volunteer_Coordination_Paper.pdf':'reports/Project_report.pdf')),useSystemFonts:true}).promise;
let text='';
for(let n=1;n<=doc.numPages;n++){
 const page=await doc.getPage(n); const tc=await page.getTextContent();
 text+=`\n--- PAGE ${n} ---\n`+tc.items.map(x=>x.str+(x.hasEOL?'\n':' ')).join('');
 const viewport=page.getViewport({scale:1.4}); const c=canvas.createCanvas(Math.ceil(viewport.width),Math.ceil(viewport.height));
 await page.render({canvasContext:c.getContext('2d'),viewport}).promise;
 await fs.writeFile(`tmp/pdfs/${final?'final':'original'}-${n}.png`,c.toBuffer('image/png'));
}
await fs.writeFile(`tmp/pdfs/${final?'final':'original'}.txt`,text); console.log(text);
