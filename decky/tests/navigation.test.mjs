import assert from "node:assert/strict";
import test from "node:test";
import {previous,jobAction} from "../src/navigation.js";
test("Back traverses selection without confirming",()=>{
  assert.deepEqual(["confirm","destination","system","results"].map(previous),["destination","system","results","search"]);
});
test("publication and completed jobs have no destructive action",()=>{
  assert.equal(jobAction("installing"),null);
  assert.equal(jobAction("completed"),null);
  assert.equal(jobAction("downloading"),"cancel");
  assert.equal(jobAction("failed"),"retry");
});

