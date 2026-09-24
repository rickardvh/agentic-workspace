//! Explicit repository authoring, outside the lazy operating read path.
use crate::{CoreError, decision_source};
use cap_std::{ambient_authority, fs::Dir};
use serde::Deserialize;
use serde_json::{Value, json};
use std::io::Write;

fn read(root: &Dir, path: &str) -> Result<Vec<u8>, CoreError> {
    crate::native_planning::read(root, path)?
        .ok_or_else(|| err(format!("activation source unavailable: {path}")))
}

fn err(message: impl ToString) -> CoreError {
    CoreError::new(message.to_string())
}

pub(crate) fn run(input: Value) -> Result<Value, CoreError> {
    #[derive(Deserialize)]
    #[serde(deny_unknown_fields)]
    struct Request {
        registry: String,
        mode: String,
    }
    let request: Request = serde_json::from_value(input["request"].clone()).map_err(err)?;
    if !["check", "write", "render"].contains(&request.mode.as_str()) {
        return Err(err("activation-index mode must be check, write or render"));
    }
    decision_source::relative(&request.registry)?;
    if !request.registry.ends_with("/REGISTRY.json") && request.registry != "REGISTRY.json" {
        return Err(err("activation-index requires a REGISTRY.json source"));
    }
    let root = Dir::open_ambient_dir(input["target"].as_str().unwrap_or("."), ambient_authority())
        .map_err(err)?;
    let original = read(&root, &request.registry)?;
    let mut body: Value = serde_json::from_slice(&original).map_err(err)?;
    let skills = body["skills"]
        .as_array()
        .ok_or_else(|| err("registry skills must be an array"))?;
    if skills.len() > 4096 {
        return Err(err("authoring registry exceeds 4096 skills"));
    }
    let base = request
        .registry
        .rsplit_once('/')
        .map_or("", |(base, _)| base);
    let mut rows = Vec::new();
    for skill in skills {
        let Some(resource) = skill["procedure_resource"].as_str() else {
            continue;
        };
        let path = skill["path"]
            .as_str()
            .ok_or_else(|| err("skill path missing"))?;
        decision_source::relative(path)?;
        decision_source::relative(resource)?;
        let parent = path.rsplit_once('/').map_or("", |(parent, _)| parent);
        let reference = [base, parent, resource]
            .into_iter()
            .filter(|part| !part.is_empty())
            .collect::<Vec<_>>()
            .join("/");
        let bytes = read(&root, &reference)?;
        if bytes.len() > 65536 {
            return Err(err("activation procedure exceeds bound"));
        }
        let text = std::str::from_utf8(&bytes)
            .map_err(err)?
            .replace("\r\n", "\n");
        let marker = "```agentic-procedure\n";
        if !text.contains(marker) {
            continue;
        }
        if text.matches(marker).count() != 1 {
            return Err(err("ambiguous procedure declaration"));
        }
        let declaration: Value = serde_json::from_str(
            text.split_once(marker)
                .unwrap()
                .1
                .split_once("\n```")
                .ok_or_else(|| err("unterminated procedure declaration"))?
                .0,
        )
        .map_err(err)?;
        let Some(activation) = declaration.get("activation") else {
            continue;
        };
        crate::native_activation::validate(activation)?;
        let route = &skill["semantic_routes"][0];
        rows.push(
            json!({"id":skill["id"],"path":path,"procedure_resource":resource,
            "semantic_routes":[route.get("id").unwrap_or(route)],"activation":activation}),
        );
    }
    if rows.len() > 128 {
        return Err(err("activation index exceeds 128 entries"));
    }
    if rows.is_empty() {
        body.as_object_mut().unwrap().remove("activation_index");
    } else {
        body["activation_index"] = json!(rows);
    }
    let drift = serde_json::from_slice::<Value>(&original).map_err(err)? != body;
    if drift && request.mode == "check" {
        return Err(err(
            "activation index stale; run activation-index with mode write after editing procedure sources",
        ));
    }
    if drift && request.mode == "write" {
        // Confined reads reject linked parents/files. Replace atomically within
        // the same directory; never follow an existing temporary file.
        let temporary = format!("{}.activation-{}", request.registry, std::process::id());
        let mut options = cap_std::fs::OpenOptions::new();
        options.write(true).create_new(true);
        let mut file = root.open_with(&temporary, &options).map_err(err)?;
        let write = (|| {
            file.write_all(serde_json::to_string_pretty(&body).map_err(err)?.as_bytes())
                .map_err(err)?;
            file.write_all(b"\n").map_err(err)?;
            file.sync_all().map_err(err)?;
            if read(&root, &request.registry)? != original {
                return Err(err("registry changed during derivation"));
            }
            root.rename(&temporary, &root, &request.registry)
                .map_err(err)
        })();
        drop(file);
        if write.is_err() {
            let _ = root.remove_file(&temporary);
        }
        write?;
    }
    let mut result = json!({"kind":"agentic-workspace/activation-index/v1","registry":request.registry,"status":if drift && request.mode == "render" { "stale" } else { "current" },"updated":drift && request.mode == "write","drift":drift,"entries":rows.len()});
    if request.mode == "render" {
        result["projection"] = body;
    }
    Ok(result)
}
