import fs from 'node:fs/promises';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {FileBlob,PresentationFile} from '@oai/artifact-tool';
import {finalizePresentation} from '/home/future-lab/.codex/plugins/cache/openai-primary-runtime/presentations/26.905.11957/skills/presentations/container_tools/artifact_tool_utils.mjs';
const workspaceDir='/home/future-lab/B002_Future_Lab_Bots/poster_work';
const build=path.join(workspaceDir,'build');
const skill='/home/future-lab/.codex/plugins/cache/openai-primary-runtime/presentations/26.905.11957/skills/presentations';
const source=path.join(build,'Postervorlage_2026_iisys (1).pptx');
const fontPolicy={basis:'reference',families:['Sora','Sora SemiBold','Source Sans Pro'],referencePath:source,referenceSha256:createHash('sha256').update(await fs.readFile(source)).digest('hex')};
const p=await PresentationFile.importPptx(await FileBlob.load(source));
const slide=p.resolve('sl/y90nupkv');
const master=p.masters.items[0];
function style(shape,text,x,y,w,h,size=43,bold=false,family='Source Sans Pro'){
  shape.text=text;
  shape.position={left:x,top:y,width:w,height:h};
  shape.text.style={typeface:family,fontSize:size,bold,color:'#111111',autoFit:'none',wrap:'square',alignment:'left',verticalAlignment:'top',insets:{top:0,right:0,bottom:0,left:0}};
  return shape;
}
function edit(id,...args){return style(p.resolve(id),...args);}
function text(name,...args){return style(slide.shapes.add({name,geometry:'textbox',fill:'none',line:{fill:'none',width:0}}),...args);}
function blank(id){p.resolve(id).delete();}
edit('sh/0bmd476t','Cooperative Robots\nfor Smart Factories',104,130,1310,235,85,true,'Sora SemiBold');
edit('sh/zadcv2p8','An open-source logistics integration blueprint',104,377,1300,65,43,false,'Sora');
edit('sh/e94v2hon','Abstract',104,553,1250,72,53,true,'Sora');
edit('sh/90ve1w7q','A TurtleBot 4 and a MyCobot 280 share logistics tasks\nin a didactic Siemens smart factory. The system links\nrobot navigation, vision and manipulation through\nopen-source software, using only onboard sensors.',104,634,1340,210,43);
edit('sh/vyp0je1s','The integration challenge',104,915,970,75,51,true,'Sora');
edit('sh/wzy1szid','Robot platforms and factory PLCs use different\nsoftware stacks. Reliable operation requires explicit\ncoordination across ROS 2 Jazzy, ROS 2 Galactic\nand the Siemens industrial network.',104,1000,990,240,42);
text('Modular approach heading','A modular solution',1160,915,985,75,51,true,'Sora');
text('Modular approach body','Separate interfaces connect the mobile base,\nmanipulator and OPC UA factory gateway.\nThe dashboard supervises shared missions,\nwhile each robot can also run independently.',1160,1000,985,240,42);
edit('sh/ozmd8r65','Cooperative delivery pipeline',104,1285,1600,75,53,true,'Sora');
blank('sh/nydczmpk');
blank('sh/uxgjq907');
blank('sh/p4bu5s76');
blank('sh/1cvuxc7e');
const photo=p.resolve('im/jih0bmhk');
photo.replace({blob:await fs.readFile('/home/future-lab/Downloads/image.png'),contentType:'image/png',fit:'contain',alt:'Project team with the TurtleBot 4, MyCobot 280 and didactic Siemens factory in the B002 laboratory.'});
photo.frame={left:104,top:2535,width:420,height:315};
photo.crop={left:0,top:0,right:0,bottom:0};
edit('sh/j2pkne14','B002 laboratory and project team.',104,2863,1020,43,29);
slide.images.add({blob:await fs.readFile('/home/future-lab/Downloads/Mídia.jpeg'),contentType:'image/jpeg',fit:'contain',alt:'Hof University and USP project collaboration, including a participant joining remotely.',position:{left:558,top:2535,width:560,height:315}});
edit('sh/mx4v6hoz','Three logistics missions',104,2110,1650,75,53,true,'Sora');
blank('sh/h072l4jy');
text('Delivery mission title','Product delivery',104,2220,640,65,45,true);
text('Delivery mission body','Collect the identified product,\ndeliver it to the destination for\nits colour and return to dock.',104,2295,640,180,41);
text('Retrieval mission title','Defective-part retrieval',800,2220,660,65,45,true);
text('Retrieval mission body','Collect rejected components\nfrom the factory and transport\nthem to the inspection area.',800,2295,660,180,41);
text('Restock mission title','Material restocking',1500,2220,645,65,45,true);
text('Restock mission body','Collect supplies and bring them\nto the factory inventory station\nbefore returning to dock.',1500,2295,645,180,41);
text('Evaluation title','Evaluation & outlook',1200,2530,950,70,49,true,'Sora');
text('Evaluation body','The next benchmark covers clear paths,\nstatic obstacles and moving obstacles.\nROS bag recordings capture robot motion\nand mission events for cycle-time and\ncompletion-rate analysis.',1200,2618,945,245,40);

// Editable pipeline: each block is a real stage in the cooperative delivery.
function stage(name,title,stack,body,x,fill,border){
  const box=slide.shapes.add({name,geometry:'roundRect',borderRadius:15,position:{left:x,top:1510,width:336,height:365},fill,line:{fill:border,width:2.2}});
  text(`${name} title`,title,x+20,1538,296,63,43,true);
  const sub=text(`${name} stack`,stack,x+20,1610,296,60,34,true);
  sub.text.color=border;
  text(`${name} body`,body,x+20,1690,296,155,36);
  return box;
}
const vision=stage('Perception','Perception','Arm camera + YOLO','Detect product\nValidate class\nSend class',104,'#E0F4EE','#2C8070');
const manager=stage('Coordination','Coordination','Mission manager','Select mission\nCheck readiness\nSet destination',530,'#FFF3CA','#9E791B');
const pickup=stage('Pickup','Pickup','TurtleBot 4','Undock\nNavigate to pickup\nConfirm arrival',956,'#E8F1FC','#3C6EA5');
const transfer=stage('Transfer','Transfer','MyCobot 280','Wait for arrival\nPlace product\nConfirm release',1382,'#FCECE5','#AF6447');
const delivery=stage('Delivery','Delivery','TurtleBot 4','Wait for release\nDeliver by colour\nReturn to dock',1808,'#EEE9FA','#75619D');
const nodes=[vision,manager,pickup,transfer,delivery];
for(let i=0;i<4;i++){
  slide.shapes.connect(nodes[i],nodes[i+1],{kind:'straight',fromSide:'right',toSide:'left',line:{fill:'#657078',width:2.5},tail:{type:'triangle',width:'med',length:'med'}});
  const label=text(`Signal ${i}`,['class','task','arrival','release'][i],436+i*426,1626,93,50,23);
  label.text.alignment='center';
}
text('Navigation stack','SLAM mapping · AMCL localisation · Nav2 navigation',104,1395,1180,60,36);
text('Arm stack','MoveIt 2 motion planning + suction gripper',1290,1395,855,60,36);
text('Coordination explanation','The arm waits for the mobile base to reach pickup. The base waits for product release before delivery.',104,1920,2040,110,40);
edit('sh/432dwn6l','Matheus Hipólito Carvalho\nEESC–USP / Hof University of Applied Sciences\nmatheus.carvalho@hof-university.de',1215,3010,950,133,30);
text('Supervision','Supervision: Prof. Dr.-Ing. Christoph Koch\nFuture Lab: Shantall Marucia Cisneros Saldana',1215,2924,950,76,29);
const m=(id)=>master.shapes.items.find(s=>s.id===id);
style(m('10'),'7th Scientific\nInstitute Colloquium',1550,535,650,190,53,true,'Sora');
style(m('15'),'Institute for Information Systems\nHof University of Applied Sciences\nAlfons-Goppel-Platz 1 · 95028 Hof\nwww.hof-university.de',466,2975,510,160,27);
m('12').position={left:1185,top:2910,width:1060,height:268.5};
m('13').position={left:1992,top:2850,width:253,height:60};
m('14').fill='none';m('14').line={fill:'none',width:0};
slide.speakerNotes.textFrame.setText('Sources: user-supplied HOF_USP_Bots_Paper.pdf (architecture, mission definitions, author and affiliations); user-supplied implementation context and turtlebot4_jazzy/scripts/delivery_routine.py (fresh product class, pickup arrival and item-release gates); image.png and Mídia.jpeg (team photographs); Postervorlage_2026_iisys (1).ppt (template and logos). The user-supplied image(2).png informs the pipeline layout only, not its technical content. Performance benchmarking remains future work.');
await fs.writeFile(path.join(build,'poster-v2-preview.png'),new Uint8Array(await (await slide.export({format:'png',scale:.6})).arrayBuffer()));
await fs.writeFile(path.join(build,'poster-v2.layout.json'),await (await slide.export({format:'layout'})).text());
const candidatePath=path.join(build,'candidate-v2.pptx');
await (await PresentationFile.exportPptx(p)).save(candidatePath);
const result=await finalizePresentation({workspaceDir,candidatePath,finalPath:path.join(workspaceDir,'output','B002_Future_Lab_Poster_Revised_EN.pptx'),pythonExecutable:'/home/future-lab/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3',integrityValidatorPath:path.join(skill,'container_tools/inspect_presentation_package_integrity.py'),layoutValidatorPath:path.join(skill,'container_tools/inspect_presentation_layout_geometry.py'),layoutArgs:['--expected-slide-size-emu','21383625,30275213','--validate-bullet-geometry','--validate-heading-fit'],explicitTotalSlideCount:1,fontPolicy,verifyArtifactToolImport:true,receiptPath:path.join(build,'validation-revised.json')});
console.log(result);
