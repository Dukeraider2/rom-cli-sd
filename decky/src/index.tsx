import {useEffect,useRef,useState,ReactNode} from "react";
import {ButtonItem,DropdownItem,Focusable,PanelSection,PanelSectionRow,TextField,staticClasses} from "@decky/ui";
import {callable,definePlugin} from "@decky/api";
import {previous,jobAction} from "./navigation.js";

type Suite="emudeck"|"retrodeck";
type FileHit={id:string;provider:string;item:string;name:string;title:string;systems:string[];size:number|null;checksums:Record<string,string>};
type Results={results:FileHit[];more:boolean;more_files:boolean};
type Platform={platform:Suite;status:string;root:string|null};
type Preview={destination:string;duplicate:string;token:string;file:FileHit;can_install:boolean};
type Job={id:string;name:string;platform:Suite;state:string;bytes:number;total:number|null;error:string|null};
type Game={id:number;game_id:number;display_title:string;system:string;platform:Suite;path:string;recorded_status:string;verified_at:string};
type Report={count:number;findings:{status:string;path?:string;reason?:string}[]};
type Reply={ok:true;data:unknown}|{ok:false;error:{code:string;message:string}};
type Operation="search"|"get_result"|"enqueue"|"list_platforms"|"list_consoles"|"list_jobs"|"list_games"|"cancel"|"retry"|"inspect_game"|"reconcile_preview";
const rpc=callable<[number,Operation,Record<string,unknown>],Reply>("rpc");
async function call<T>(op:Operation,args:Record<string,unknown>):Promise<T>{
  const r=await rpc(1,op,args);
  if(!r.ok) throw new Error(r.error.message);
  return r.data as T;
}
const systems="nes snes gb gbc gba n64 nds psx ps2 psp gc wii dreamcast saturn genesis".split(" ");
const label=(p:string)=>p==="emudeck"?"EmuDeck":"RetroDECK";
const bytes=(n:number|null)=>n===null?"unknown size":(n/1048576).toFixed(2)+" MiB";

const sourcePreference = "rom-cli-sd.search-source";

function Content(){
  const [screen,go]=useState("search"),[query,setQuery]=useState(""),[provider,setProvider]=useState(()=>localStorage.getItem(sourcePreference)==="mirror"?"mirror":"archive");
  const [filter,setFilter]=useState(""),[system,choose]=useState(""),[suite,setSuite]=useState<Suite>("emudeck");
  const [page,setPage]=useState(1),[filePage,setFilePage]=useState(1),[listPage,setListPage]=useState(1);
  const [results,setResults]=useState<Results>(),[hit,select]=useState<FileHit>(),[platforms,setPlatforms]=useState<Platform[]>([]);
  const [preview,setPreview]=useState<Preview>(),[jobs,setJobs]=useState<Job[]>([]),[games,setGames]=useState<Game[]>([]);
  const [details,setDetails]=useState<Game[]>([]),[report,setReport]=useState<Report>(),[error,fail]=useState("");
  const [reportParent,fromReport]=useState("game");
  const [consoles,setConsoles]=useState<{system:string;available:boolean;error?:string}[]>([]);
  const [busy,setBusy]=useState(false),epoch=useRef(0),locked=useRef(false);
  useEffect(()=>()=>{epoch.current++;},[]);
  function back(){
    epoch.current++; locked.current=false; setBusy(false); fail(""); go(screen==="report"?reportParent:previous(screen));
  }
  async function load<T>(task:()=>Promise<T>,apply:(data:T)=>void){
    if(locked.current)return;
    const ticket=++epoch.current;
    locked.current=true;setBusy(true);fail("");
    try{const data=await task(); if(ticket===epoch.current)apply(data);}
    catch(e){if(ticket===epoch.current)fail(String(e instanceof Error?e.message:e));}
    finally{if(ticket===epoch.current){locked.current=false;setBusy(false);}}
  }
  useEffect(()=>{
    if(screen!=="jobs" || !jobs.some(j=>["queued","resolving","downloading","verifying","installing"].includes(j.state)))return;
    let live=true;
    const timer=setTimeout(async()=>{
      try{const data=await call<Job[]>("list_jobs",{page:listPage});if(live)setJobs(data);}
      catch(e){if(live)fail(String(e));}
    },1000);
    return ()=>{live=false;clearTimeout(timer);};
  },[screen,jobs,listPage]);
  const button=(text:string,fn:()=>void,disabled=false,key=text)=><PanelSectionRow key={key}><ButtonItem layout="below" disabled={busy||disabled} onClick={fn}>{text}</ButtonItem></PanelSectionRow>;
  function search(p:number,f:number){
    load(()=>call<Results>("search",{provider,query,system:filter||null,page:p,file_page:f}),r=>{setResults(r);setPage(p);setFilePage(f);go("results");});
  }
  function showJobs(p:number){
    load(()=>call<Job[]>("list_jobs",{page:p}),r=>{setJobs(r);setListPage(p);go("jobs");});
  }
  function library(p:number){
    load(()=>call<Game[]>("list_games",{page:p}),r=>{setGames(r);setListPage(p);go("library");});
  }
  function display(name:string,data:string[],value:string,change:(s:string)=>void){
    return <PanelSectionRow><DropdownItem label={name} selectedOption={value} rgOptions={data.map(s=>({data:s,label:s||"All systems"}))} onChange={o=>change(o.data)}/></PanelSectionRow>;
  }
  let content:ReactNode;
  switch(screen){
    case "search": content=<>
      <PanelSectionRow><TextField label="Game title" description="Use Steam + X to open the keyboard." value={query} onChange={e=>setQuery(e.target.value.slice(0,80))}/></PanelSectionRow>
      {button("Source · "+(provider==="archive"?"Archive":"Mirror"),()=>{
        const next=provider==="archive"?"mirror":"archive";
        localStorage.setItem(sourcePreference,next);
        setProvider(next);
      },false,"search-source")}{display("Console",["",...systems],filter,setFilter)}
      {button("Search",()=>search(1,1),!query.trim())}{button("Downloads",()=>showJobs(1))}{button("Installed library",()=>library(1))}
    </>;break;
    case "results": content=<>
      {!results?.results.length&&<p>No supported files on this page.</p>}
      {results?.results.map(r=>button(r.title+" · "+r.name,()=>{select(r);go("system");},false,r.id))}
      {results?.more_files&&button("More files in this item",()=>search(page,filePage+1))}
      {results?.more&&button("Next source page",()=>search(page+1,1))}
      {(page>1||filePage>1)&&button("Previous page",()=>filePage>1?search(page,filePage-1):search(page-1,1))}
    </>;break;
    case "system": content=hit&&<><p>{hit.title}<br/>{hit.name}<br/>{hit.provider} · {hit.item}</p>
      {hit.systems.map(s=>button(s.toUpperCase(),()=>load(()=>call<Platform[]>("list_platforms",{}),r=>{choose(s);setPlatforms(r);go("destination");})))}</>;break;
    case "destination": content=<>{platforms.map(p=><div key={p.platform}><p>{p.root??p.status}</p>
      {button(label(p.platform)+" · "+p.status,()=>load(()=>call<Preview>("get_result",{result:hit!.id,system,platform:p.platform}),
        r=>{setPreview(r);select(r.file);setSuite(p.platform);go("confirm");}),p.status!=="ready")}</div>)}</>;break;
    case "confirm": content=hit&&preview&&<><p>{hit.name}<br/>{hit.provider} · {hit.item}<br/>{system.toUpperCase()} · {label(suite)}</p>
      <p>{preview.destination}<br/>{preview.duplicate}</p><p>{bytes(hit.size)}<br/>{Object.entries(hit.checksums).map(([k,v])=>k+" "+v).join(" · ")||"No source checksum; local SHA-256 will be recorded."}</p>
      {button("I’m authorized · Download and install",()=>load(async()=>{await call("enqueue",{token:preview.token,confirmed:true});return call<Job[]>("list_jobs",{page:1});},
        r=>{setJobs(r);setListPage(1);go("jobs");}),!preview.can_install)}</>;break;
    case "jobs": content=<>{!jobs.length&&<p>No downloads on this page.</p>}{jobs.map(j=>{
      const action=jobAction(j.state);
      return <div key={j.id}><p>{j.name}<br/>{label(j.platform)} · {j.state.replace("_"," ")}<br/>{bytes(j.bytes)} / {bytes(j.total)}<br/>{j.error}</p>
        {action&&button(action==="retry"?"Confirm retry":"Cancel download",()=>load(async()=>{
          await call(action,{job:j.id,...(action==="retry"?{confirmed:true}:{})});return call<Job[]>("list_jobs",{page:listPage});},setJobs))}
        {j.state==="completed"&&<p>Reopen ES-DE to discover and play. Use its scraper for artwork or parse and save shortcuts in Steam ROM Manager.</p>}</div>;
      })}{button("Refresh downloads",()=>showJobs(listPage))}{jobs.length===20&&button("Next jobs",()=>showJobs(listPage+1))}{listPage>1&&button("Previous jobs",()=>showJobs(listPage-1))}</>;break;
    case "library": content=<>{(["emudeck","retrodeck"] as Suite[]).map(s=>button("Check "+label(s)+" console",()=>load(()=>call<typeof consoles>("list_consoles",{platform:s}),r=>{setSuite(s);setConsoles(r);go("checks");})))}
      {!games.length&&<p>No recorded installations on this page.</p>}{games.map(g=>button(g.display_title+" · "+label(g.platform),()=>load(()=>call<Game[]>("inspect_game",{game:g.game_id}),r=>{setDetails(r);go("game");}),false,String(g.id)))}
      {games.length===20&&button("Next games",()=>library(listPage+1))}{listPage>1&&button("Previous games",()=>library(listPage-1))}</>;break;
    case "game": content=<>{details.map(g=><div key={g.id}><p>{g.display_title}<br/>{g.path}<br/>{g.recorded_status} · Last verified {g.verified_at||"unknown"}</p>
      {button("Check "+label(g.platform)+" "+g.system,()=>load(()=>call<Report>("reconcile_preview",{platform:g.platform,system:g.system}),r=>{setReport(r);fromReport("game");go("report");}))}</div>)}</>;break;
    case "checks": content=consoles.map(c=>button(c.system.toUpperCase()+(c.available?"":" · "+c.error),()=>load(()=>call<Report>("reconcile_preview",{platform:suite,system:c.system}),r=>{setReport(r);fromReport("checks");go("report");}),!c.available));break;
    case "report": content=<><p>{report?.count} findings</p>{report?.findings.map((f,i)=><p key={i}>{f.status} · {f.path||f.reason}</p>)}</>;break;
  }
  return <Focusable flow-children="vertical" onCancel={e=>{if(screen!=="search"){e.stopPropagation();back();}}} style={{overflowWrap:"anywhere"}}>
    <PanelSection title={{search:"Find a game",results:"Search results",system:"Choose console",destination:"Choose destination",confirm:"Confirm download",jobs:"Downloads",library:"Installed library",game:"Installation details",report:"Library check"}[screen]}>
      {screen!=="search"&&<PanelSectionRow><ButtonItem layout="below" onClick={back}>Back</ButtonItem></PanelSectionRow>}
      {content}{busy&&<p role="status">Loading…</p>}{error&&<p role="alert">{error}</p>}
    </PanelSection></Focusable>;
}
export default definePlugin(()=>({name:"ROM Library",titleView:<div className={staticClasses.Title}>ROM Library</div>,content:<Content/>,icon:<span aria-hidden>▤</span>,onDismount(){}}));

