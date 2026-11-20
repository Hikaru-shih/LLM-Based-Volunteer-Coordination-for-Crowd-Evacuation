import path from 'node:path';
import fs from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {pathToFileURL} from 'node:url';
const root='D:/LLM-Based-Volunteer-Coordination-for-Crowd-Evacuation';
const skill='C:/Users/Pin Guang/.codex/plugins/cache/openai-primary-runtime/presentations/26.1118.11504/skills/presentations';
const runtime='C:/Program Files/WindowsApps/OpenAI.CodexPrimaryRuntime.v26-1118-904-0_26.1118.904.0_x64__3k8sg7r9htsxt/dependencies';
process.env.RUNTIME_NODE_MODULES=runtime+'/node/node_modules';
const {finalizePresentation}=await import(pathToFileURL(skill+'/container_tools/artifact_tool_utils.mjs').href);
const referenceSha256=createHash('sha256').update(await fs.readFile(root+'/local_archive/20261119_final_delivery/Presentation.en.pptx')).digest('hex');
const result=await finalizePresentation({materializeLiteralChartWorkbooks:true,workspaceDir:root,candidatePath:root+'/report/.build/delivery_20261119/candidate.pptx',finalPath:root+'/report/.build/delivery_20261119/output/Presentation.en.pptx',pythonExecutable:runtime+'/python/python.exe',integrityValidatorPath:skill+'/container_tools/inspect_presentation_package_integrity.py',layoutValidatorPath:skill+'/container_tools/inspect_presentation_layout_geometry.py',layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-bullet-geometry','--validate-heading-fit'],explicitTotalSlideCount:13,requiredNativeChartOwnerSlides:[7,8],requiredNativeTableOwnerSlides:[],fontPolicy:{basis:'reference',families:['Arial'],referencePath:root+'/local_archive/20261119_final_delivery/Presentation.en.pptx',referenceSha256},verifyArtifactToolImport:true,receiptPath:root+'/report/.build/delivery_20261119/PRESENTATION_VALIDATION.json'});
console.log(JSON.stringify(result));

