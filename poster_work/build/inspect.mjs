import fs from 'node:fs/promises';
import {FileBlob, PresentationFile} from '@oai/artifact-tool';
const dir='/home/future-lab/B002_Future_Lab_Bots/poster_work/build';
const p=await PresentationFile.importPptx(await FileBlob.load(`${dir}/Postervorlage_2026_iisys (1).pptx`));
console.log((await p.inspect({kind:'slide,textbox,shape,image,layout',maxChars:30000})).ndjson);
console.log('MASTERS',p.masters.items.map(x=>({id:x.id,summary:x.placeholders.summary()})));
console.log('LAYOUTS',p.layouts.items.map(x=>({id:x.id,summary:x.placeholders.summary()})));
await fs.writeFile(`${dir}/import.layout.json`,await (await p.slides.getItem(0).export({format:'layout'})).text());
await fs.writeFile(`${dir}/import.png`,new Uint8Array(await (await p.slides.getItem(0).export({format:'png',scale:.45})).arrayBuffer()));
