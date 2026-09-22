"""Check source or installed façades against the native public envelope contract."""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def expected_envelope(template, material):
    if isinstance(template, str) and template.startswith("$"):
        return material[template[1:]]
    if isinstance(template, dict):
        result = dict(material[template["$spread"]]) if "$spread" in template else {}
        result.update({key: expected_envelope(value, material) for key, value in template.items() if key != "$spread"})
        return result
    return template


def cases(contract):
    # Unknown nested owner data must survive transport, including null and Unicode.
    material = {"context": {"target": "雪", "request": {"unknown_owner": [None, False, 7]}},
                "carriage": {"opaque": ["å", None]}, "reference": "exact-ref", "answer": {"choice": None}}
    result = []
    for operation in contract["operations"]:
        envelope = expected_envelope(operation["envelope"], material)
        result.append({**operation, "values": [material[name] for name in operation["arguments"]], "expected": envelope})
        if operation.get("optional"):
            omitted = json.loads(json.dumps(envelope))
            del omitted["start"]["answer"]
            result.append({**operation, "values": [material[name] for name in operation["arguments"][:-1]], "expected": omitted})
    return result


def check_python(contract, package=None):
    import agentic_workspace
    from agentic_workspace import _binding as binding
    names = agentic_workspace.__all__
    expected = {op["python"] for op in contract["operations"]} | set(contract["adapter_exports"]["python"])
    assert set(names) == expected, (names, expected)
    original = binding._request
    try:
        binding._request = lambda payload: payload
        for case in cases(contract):
            function = getattr(agentic_workspace, case["python"])
            values = case["values"]
            actual = function(*values[:2], answer=values[2]) if case.get("optional") and len(values) == 3 else function(*values)
            assert actual == case["expected"], (case["python"], actual, case["expected"])
    finally:
        binding._request = original


def check_node(contract, facade, core):
    declarations = facade.with_name("operating.d.mts").read_text()
    assert declarations == contract["typescript_declarations"], "TypeScript declaration drift"
    names = set(re.findall(r"export function (\w+)\(", declarations))
    assert names == {op["typescript"] for op in contract["operations"]}
    # Intercept only the subprocess boundary, so the runtime façade still builds
    # and serializes every real request. No Rust semantic suite is duplicated.
    program = r'''
import cp from 'node:child_process';
import {syncBuiltinESMExports} from 'node:module';
import {pathToFileURL} from 'node:url';
import fs from 'node:fs';
const input=JSON.parse(fs.readFileSync(0,'utf8'));
cp.spawnSync=(_binary,_args,options)=>({status:0,stdout:options.input,stderr:''});
syncBuiltinESMExports();
process.env.AGENTIC_WORKSPACE_CORE_BINARY=input.core;
const api=await import(pathToFileURL(input.facade));
const names=Object.keys(api).sort();
if(JSON.stringify(names)!==JSON.stringify(input.names.sort())) throw Error('facade export drift: '+names);
for(const row of input.cases) {
  const actual=api[row.typescript](...row.values);
  if(JSON.stringify(actual)!==JSON.stringify(row.expected)) throw Error('envelope drift: '+row.typescript);
}
'''
    result = subprocess.run([shutil.which("node"), "--input-type=module", "-e", program],
                            input=json.dumps({"core": str(core), "facade": str(facade), "cases": cases(contract),
                                              "names": [op["typescript"] for op in contract["operations"]]}),
                            text=True, capture_output=True)
    assert result.returncode == 0, result.stderr


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--installed-python", action="store_true")
    parser.add_argument("--node-facade", type=Path)
    parser.add_argument("--core", type=Path)
    args = parser.parse_args()
    contract = json.loads((ROOT / "src/core/contracts/source_decision_contract.json").read_text())["language_facade"]
    check_python(contract, True if args.installed_python else None)
    if args.node_facade:
        check_node(contract, args.node_facade.resolve(), args.core.resolve())
    print("Language facade exports and envelopes match the native contract")


if __name__ == "__main__":
    main()
