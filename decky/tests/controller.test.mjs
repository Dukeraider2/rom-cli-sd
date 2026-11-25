import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {createRequire} from "node:module";
import vm from "node:vm";
import test from "node:test";
import ts from "typescript";
import React from "react";
import renderer,{act} from "react-test-renderer";
import * as navigation from "../src/navigation.js";

globalThis.IS_REACT_ACT_ENVIRONMENT=true;
const require=createRequire(import.meta.url);
const source=readFileSync(new URL("../src/index.tsx",import.meta.url),"utf8");
const {outputText}=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX,target:ts.ScriptTarget.ES2020}});
class MapStorage extends Map {
  getItem(key){return this.get(key) ?? null;}
  setItem(key,value){this.set(key,value);}
}
function mountable(handler,localStorage=new MapStorage()){
  const exports={};
  const ui=Object.fromEntries(["ButtonItem","Focusable","PanelSection","PanelSectionRow","DropdownItem","TextField"].map(k=>[k,k]));
  const imports=name=>{
    if(name==="@decky/ui")return {...ui,staticClasses:{Title:"title"}};
    if(name==="@decky/api")return {callable:()=>handler,definePlugin:fn=>fn()};
    if(name==="./navigation.js")return navigation;
    return require(name);
  };
  vm.runInNewContext(outputText,{exports,require:imports,localStorage,setTimeout,clearTimeout,console});
  return exports.default.content;
}
test("controller workflow previews a destination and requires a separate activation to enqueue",async()=>{
  const calls=[];
  const hit={id:"a".repeat(64),title:"Homebrew",name:"Demo.gba",provider:"mirror",item:"Fixture",systems:["gba"],size:64,checksums:{}};
  async function handler(version,op,args){
    assert.equal(version,1);calls.push([op,args]);
    return {ok:true,data:({search:{results:[hit]},list_platforms:[{platform:"retrodeck",root:"/fixture",status:"ready"}],
      get_result:{destination:"/fixture/gba/Demo.gba",duplicate:"no known match",token:"x",file:hit,can_install:true},enqueue:{id:"job"},list_jobs:[]})[op]};
  }
  let view;
  await act(async()=>{view=renderer.create(mountable(handler));});
  const activate=async label=>{const node=view.root.findAllByType("ButtonItem").find(b=>b.props.children===label);assert.ok(node,label);assert.ok(!node.props.disabled);await act(async()=>node.props.onClick());};
  await act(async()=>view.root.findByType("TextField").props.onChange({target:{value:"Demo"}}));
  await activate("Search");await activate("Homebrew · Demo.gba");await activate("GBA");await activate("RetroDECK · ready");
  assert.equal(calls.filter(c=>c[0]==="enqueue").length,0);
  await act(async()=>view.root.findByType("Focusable").props.onCancel({stopPropagation(){}}));
  await activate("RetroDECK · ready");await activate("I’m authorized · Download and install");
  assert.equal(calls.filter(c=>c[0]==="enqueue").length,1);
  assert.equal(calls.find(c=>c[0]==="enqueue")[1].confirmed,true);
  await act(async()=>view.unmount());
});


test("Mirror remains selected after reopening and is used for the search",async()=>{
  const storage=new MapStorage(),requests=[];
  const handler=async(version,op,args)=>{
    requests.push([op,args.provider]);
    return {ok:true,data:{results:[]}};
  };
  let view;
  const mount=async()=>{await act(async()=>{view=renderer.create(mountable(handler,storage));});};
  const button=label=>view.root.findAllByType("ButtonItem").find(b=>b.props.children===label);
  await mount();
  await act(async()=>button("Source · Archive").props.onClick());
  assert.ok(button("Source · Mirror"));
  await act(async()=>view.unmount());
  await mount();
  assert.ok(button("Source · Mirror"));
  await act(async()=>view.root.findByType("TextField").props.onChange({target:{value:"Cancel Test"}}));
  await act(async()=>button("Search").props.onClick());
  assert.deepEqual(requests,[["search","mirror"]]);
  await act(async()=>view.unmount());
});
