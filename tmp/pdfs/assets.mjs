import fs from 'node:fs/promises';
const root='file:///C:/Users/Pin%20Guang/AppData/Local/OpenAI/Codex/runtimes/cua_node/b474a88d5d105afa/bin/node_modules/';
const c=await import(root+'@napi-rs/canvas/index.js'); Object.assign(globalThis,{DOMMatrix:c.DOMMatrix,ImageData:c.ImageData,Path2D:c.Path2D});
const pdf=await import(root+'pdfjs-dist/legacy/build/pdf.mjs');
const doc=await pdf.getDocument({data:new Uint8Array(await fs.readFile('reports/Project_report.pdf')),useSystemFonts:true}).promise;
await fs.mkdir('output/pdf/figures',{recursive:true});
for(const n of [3,4,5,7,8,10,11]){
 const p=await doc.getPage(n); const ops=await p.getOperatorList();
 for(let i=0;i<ops.fnArray.length;i++)if(ops.fnArray[i]===pdf.OPS.paintImageXObject){
  const id=ops.argsArray[i][0];const img=await new Promise(resolve=>p.objs.get(id,resolve));
  console.log(n,id,img.width,img.height,img.kind,!!img.bitmap);
  const canvas=c.createCanvas(img.width,img.height); const ctx=canvas.getContext('2d');
  if(img.bitmap)ctx.drawImage(img.bitmap,0,0);else {
   const rgba=new Uint8ClampedArray(img.width*img.height*4);
   if(img.kind===3)rgba.set(img.data); else if(img.kind===2)for(let j=0,k=0;j<img.data.length;j+=3,k+=4){rgba[k]=img.data[j];rgba[k+1]=img.data[j+1];rgba[k+2]=img.data[j+2];rgba[k+3]=255;}
   else throw Error('Unsupported image kind '+img.kind);
   ctx.putImageData(new c.ImageData(rgba,img.width,img.height),0,0);
  }
  await fs.writeFile(`output/pdf/figures/page-${n}-${id}.png`,canvas.toBuffer('image/png'));
 }
}
