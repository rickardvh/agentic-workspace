//! The proof owner's single serialized index publication boundary.
//! Receipt-carried planned custody proves an exact attempt relationship, not proof sufficiency.
use crate::{CoreError, attempt_store};
use cap_std::{
    ambient_authority,
    fs::{Dir, OpenOptions},
};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::{io::Write, path::Path};
const STORE: &str = ".agentic-workspace/proof/receipts";
const INDEX: &str = ".agentic-workspace/proof/receipts/index.json";
const CUSTODY: &str = "publication_custody";
fn err(e: impl std::fmt::Display) -> CoreError {
    CoreError::new(e.to_string())
}
fn hash(bytes: &[u8]) -> String {
    format!("{:x}", Sha256::digest(bytes))
}
#[cfg(test)]
thread_local! { static SOURCE_READS: std::cell::Cell<usize> = const { std::cell::Cell::new(0) }; }
fn read(root: &Dir, path: &str) -> Result<Option<Vec<u8>>, CoreError> {
    #[cfg(test)]
    SOURCE_READS.with(|count| count.set(count.get() + 1));
    crate::native_verification::read(root, path).map_err(err)
}
fn parse(bytes: &[u8]) -> Result<Value, CoreError> {
    serde_json::from_slice(bytes).map_err(err)
}
fn receipt_path(id: &str) -> Result<String, CoreError> {
    if id.len() != 16 || !id.bytes().all(|b| b.is_ascii_hexdigit()) {
        return Err(err("proof publication receipt identity invalid"));
    }
    Ok(format!("{STORE}/{id}.json"))
}
fn retained(target: &Path, receipt: &Value) -> Result<Value, CoreError> {
    let held = &receipt[CUSTODY];
    if held["kind"] != "agentic-workspace/proof-publication-custody/v1"
        || held["outcome"]["value"]["publication"]["reference"]
            != format!(
                "proof://receipts/{}",
                receipt["receipt_id"].as_str().unwrap_or("")
            )
        || crate::native_verification::publication_identity(receipt)?
            != receipt["receipt_id"].as_str().unwrap_or("")
    {
        return Err(err(
            "proof publication carrier does not name an admitted producer result; preserved",
        ));
    }
    let prepared = attempt_store::prepare_commit(
        &target.to_string_lossy(),
        held["custody"].clone(),
        held["outcome"].clone(),
    )?;
    let invocation = &prepared["record"]["invocation"];
    if prepared["custody"] != held["custody"]
        || invocation["source_owner"] != "verification"
        || invocation["operation_id"] != "proof.report"
        || receipt["source_ref"] != crate::native_proof::run_path(invocation)?
        || receipt["command"] != invocation["arguments"]["selection"]["choice"]["command"]
        || receipt["proof_subject"] != invocation["arguments"]["selection"]["proof_subject"]
        || receipt["changed_paths"] != invocation["arguments"]["changed"]
    {
        return Err(err(
            "proof publication differs from retained exact producer attempt; preserved",
        ));
    }
    Ok(prepared)
}
fn owned_index(target: &Path, root: &Dir, bytes: Option<&[u8]>) -> Result<Value, CoreError> {
    let Some(bytes) = bytes else {
        return Ok(
            json!({"kind":"agentic-workspace/trusted-producer-receipt-index/v1","receipts":{}}),
        );
    };
    let index = parse(bytes)?;
    let entries = index["receipts"]
        .as_object()
        .ok_or_else(|| err("proof-publication-index-custody-required; existing index preserved"))?;
    if index["kind"] != "agentic-workspace/trusted-producer-receipt-index/v1"
        || entries.len() > 2048
    {
        return Err(err(
            "proof-publication-index-custody-required; existing index preserved",
        ));
    }
    // A locator bounds IO; only the exact committed index hash grants custody.
    // The predecessor native format had one receipt. Multiple unlocated entries
    // require transfer rather than a historical receipt/attempt scan.
    let candidate = match index.get("current_publication") {
        Some(Value::String(id)) => entries.get_key_value(id),
        None if entries.len() == 1 => entries.iter().next(),
        _ => None,
    };
    if let Some((id, entry)) = candidate
        && let Ok(path) = receipt_path(id)
        && entry["path"] == format!("{id}.json")
        && let Some(receipt) = read(root, &path)?.and_then(|b| parse(&b).ok())
    {
        if receipt.get(CUSTODY).is_none()
            && crate::native_verification::publication_identity(&receipt)? == *id
            && let Ok(Some(committed)) =
                crate::native_proof::committed_publication(target, &receipt)
            && committed["outcome"]["value"]["publication"]["index_sha256"] == hash(bytes)
        {
            return Ok(index);
        }
        if retained(target, &receipt).is_ok()
            && let Ok(committed) = attempt_store::inspect_committed(
                &target.to_string_lossy(),
                receipt[CUSTODY]["custody"].clone(),
            )
            && committed["outcome"]["value"]["publication"]["index_sha256"] == hash(bytes)
        {
            return Ok(index);
        }
    }
    Err(err(
        "proof-publication-index-custody-required; existing index preserved; explicit owner transfer is required",
    ))
}
/// No write and no schema-based acquisition; used before launching a new process.
pub(crate) fn check(target: &Path) -> Result<(), CoreError> {
    let root = Dir::open_ambient_dir(target, ambient_authority()).map_err(err)?;
    owned_index(target, &root, read(&root, INDEX)?.as_deref()).map(|_| ())
}
fn lock(root: &Dir) -> Result<std::fs::File, CoreError> {
    // Confined reader rejects directory links/reparse points before creation.
    read(root, INDEX)?;
    root.create_dir_all(STORE).map_err(err)?;
    let path = format!("{STORE}/publication.lock");
    if let Ok(metadata) = root.symlink_metadata(&path) {
        #[cfg(windows)]
        let linked = {
            use cap_std::fs::MetadataExt;
            metadata.file_attributes() & 0x400 != 0
        };
        #[cfg(not(windows))]
        let linked = metadata.is_symlink();
        if linked || !metadata.is_file() {
            return Err(err("linked or non-file proof publication lock preserved"));
        }
    }
    let file = root
        .open_with(
            &path,
            OpenOptions::new().read(true).write(true).create(true),
        )
        .map_err(err)?
        .into_std();
    if file.metadata().map_err(err)?.len() != 0 {
        return Err(err("unrecognized proof publication lock preserved"));
    }
    let until = std::time::Instant::now() + std::time::Duration::from_secs(2);
    loop {
        match file.try_lock() {
            Ok(()) => break,
            Err(std::fs::TryLockError::WouldBlock) if std::time::Instant::now() < until => {
                std::thread::sleep(std::time::Duration::from_millis(10))
            }
            Err(error) => return Err(err(format!("proof publication owner busy: {error}"))),
        }
    }
    Ok(file)
}
fn create(root: &Dir, path: &str, bytes: &[u8]) -> Result<(), CoreError> {
    read(root, path)?;
    let mut file = root
        .open_with(path, OpenOptions::new().write(true).create_new(true))
        .map_err(err)?;
    file.write_all(bytes).map_err(err)?;
    file.sync_all().map_err(err)
}
fn install(root: &Dir, expected: Option<&[u8]>, next: &[u8], nonce: &str) -> Result<(), CoreError> {
    let temporary = format!("{STORE}/publication-{nonce}.tmp");
    create(root, &temporary, next)?;
    if read(root, INDEX)?.as_deref() != expected {
        return Err(err(
            "proof publication changed before replacement; temporary preserved",
        ));
    }
    if expected.is_none() {
        // A hard link is an absent-only atomic installation of already durable bytes.
        // No truncate/create interval can expose a partial index.
        root.hard_link(&temporary, root, INDEX).map_err(err)?;
    } else {
        root.rename(&temporary, root, INDEX).map_err(err)?;
    }
    Ok(())
}
/// Called only with the current globally admitted producer invocation/custody.
/// The callback revalidates live authority under the short publication lock.
pub(crate) fn publish(
    target: &Path,
    receipt: &Value,
    invocation: &Value,
    custody: &Value,
    outcome: Value,
    revalidate: impl FnMut() -> Result<(), CoreError>,
) -> Result<Value, CoreError> {
    publish_checked(
        target,
        receipt,
        invocation,
        custody,
        outcome,
        revalidate,
        |_| Ok(()),
    )
}
#[allow(clippy::too_many_arguments)]
fn publish_checked(
    target: &Path,
    receipt: &Value,
    invocation: &Value,
    custody: &Value,
    mut outcome: Value,
    mut revalidate: impl FnMut() -> Result<(), CoreError>,
    mut after: impl FnMut(&str) -> Result<(), CoreError>,
) -> Result<Value, CoreError> {
    let root = Dir::open_ambient_dir(target, ambient_authority()).map_err(err)?;
    let _lock = lock(&root)?;
    revalidate()?;
    let before = read(&root, INDEX)?;
    let mut next = owned_index(target, &root, before.as_deref())?;
    if next["receipts"].as_object().unwrap().len() >= 2048 {
        return Err(err(
            "proof-publication-index-capacity-reached; owner compaction required; receipt and index preserved",
        ));
    }
    let id = receipt["receipt_id"]
        .as_str()
        .ok_or_else(|| err("receipt identity missing"))?;
    let path = receipt_path(id)?;
    if crate::native_verification::publication_identity(receipt)? != id {
        return Err(err("receipt publication identity mismatch"));
    }
    if read(&root, &path)?.is_some() {
        return Err(err(
            "existing receipt requires exact publication recovery; preserved",
        ));
    }
    next["receipts"][id] = json!({"path":format!("{id}.json"),"producer_class":"aw-proof","revision":receipt["revision"],"source_ref":receipt["source_ref"],"status":"current"});
    next["current_publication"] = json!(id);
    let next_bytes = serde_json::to_vec_pretty(&next).map_err(err)?;
    outcome["value"]["publication"] = json!({"status":"published","reference":format!("proof://receipts/{id}"),"index_sha256":hash(&next_bytes)});
    let prepared =
        attempt_store::prepare_commit(&target.to_string_lossy(), custody.clone(), outcome.clone())?;
    if prepared["record"]["invocation"] != *invocation {
        return Err(err("publication invocation differs from retained producer"));
    }
    let mut receipt = receipt.clone();
    receipt[CUSTODY] = json!({"kind":"agentic-workspace/proof-publication-custody/v1","custody":prepared["custody"],"outcome":outcome,"before_sha256":before.as_ref().map(|b|hash(b))});
    create(
        &root,
        &path,
        &serde_json::to_vec_pretty(&receipt).map_err(err)?,
    )?;
    after("receipt-retained")?;
    revalidate()?;
    let nonce = format!(
        "{}-{}",
        std::process::id(),
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map_err(err)?
            .as_nanos()
    );
    install(&root, before.as_deref(), &next_bytes, &nonce)?;
    after("index-replaced")?;
    let committed =
        attempt_store::commit(json!({"target":target,"custody":custody,"outcome":outcome}))?;
    after("commit-written")?;
    Ok(committed)
}

/// Recover only a retained exact local publication, never an external command.
pub(crate) fn recover(
    target: &Path,
    invocation: &Value,
    mut revalidate: impl FnMut() -> Result<(), CoreError>,
) -> Result<Option<Value>, CoreError> {
    let root = Dir::open_ambient_dir(target, ambient_authority()).map_err(err)?;
    if root.symlink_metadata(STORE).is_err() {
        return Ok(None);
    }
    let _lock = lock(&root)?;
    let mut candidate = None;
    let mut count = 0;
    let mut inventory = 0;
    for entry in root.read_dir(STORE).map_err(err)? {
        let entry = entry.map_err(err)?;
        inventory += 1;
        if inventory > 8192 {
            return Err(err(
                "proof publication recovery total inventory exceeds bound; state preserved",
            ));
        }
        let name = entry.file_name().to_string_lossy().into_owned();
        let Some(id) = name.strip_suffix(".json") else {
            continue;
        };
        let Ok(path) = receipt_path(id) else { continue };
        count += 1;
        if count > 4096 {
            return Err(err(
                "proof publication recovery receipt inventory exceeds bound",
            ));
        }
        let Some(bytes) = read(&root, &path)? else {
            continue;
        };
        let Ok(receipt) = parse(&bytes) else { continue };
        if receipt[CUSTODY]["custody"]["attempt"]["path"]
            != attempt_store::write_paths(invocation)?[0]
        {
            continue;
        }
        if retained(target, &receipt)?["record"]["invocation"] != *invocation {
            return Err(err("publication recovery invocation differs"));
        }
        if candidate.replace(receipt).is_some() {
            return Err(err(
                "multiple publication carriers name this attempt; preserved",
            ));
        }
    }
    let Some(receipt) = candidate else {
        return Ok(None);
    };
    let held = &receipt[CUSTODY];
    let current = read(&root, INDEX)?;
    revalidate()?;
    let post_hash = &held["outcome"]["value"]["publication"]["index_sha256"];
    if current.as_ref().map(|bytes| json!(hash(bytes))).as_ref() != Some(post_hash) {
        if current
            .as_ref()
            .map(|b| json!(hash(b)))
            .unwrap_or(Value::Null)
            != held["before_sha256"]
        {
            return Err(err(
                "proof publication recovery requires exact preimage or postimage; preserved",
            ));
        }
        let mut next = owned_index(target, &root, current.as_deref())?;
        let id = receipt["receipt_id"].as_str().unwrap();
        next["receipts"][id] = json!({"path":format!("{id}.json"),"producer_class":"aw-proof","revision":receipt["revision"],"source_ref":receipt["source_ref"],"status":"current"});
        next["current_publication"] = json!(id);
        let next_bytes = serde_json::to_vec_pretty(&next).map_err(err)?;
        if *post_hash != hash(&next_bytes) {
            return Err(err(
                "publication would alter unrelated index entries; preserved",
            ));
        }
        let nonce = format!(
            "recovery-{}-{}",
            std::process::id(),
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .map_err(err)?
                .as_nanos()
        );
        install(&root, current.as_deref(), &next_bytes, &nonce)?;
    }
    let mut custody = held["custody"].clone();
    // The predeclared reference is authority only when its exact bytes exist.
    if let Ok(record) = attempt_store::inspect_committed(&target.to_string_lossy(), custody.clone())
    {
        return Ok(Some(json!({"record":record,"custody":custody})));
    }
    custody["committed"] = Value::Null;
    Ok(Some(attempt_store::commit(
        json!({"target":target,"custody":custody,"outcome":held["outcome"]}),
    )?))
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;
    use std::sync::atomic::{AtomicU64, Ordering};
    static NEXT_REPO: AtomicU64 = AtomicU64::new(0);
    struct Repo(std::path::PathBuf);
    impl Repo {
        fn new() -> Self {
            let path = std::env::temp_dir().join(format!(
                "aw-publication-{}-{}-{}",
                std::process::id(),
                std::time::SystemTime::now()
                    .duration_since(std::time::UNIX_EPOCH)
                    .unwrap()
                    .as_nanos(),
                NEXT_REPO.fetch_add(1, Ordering::Relaxed)
            ));
            fs::create_dir_all(path.join(".agentic-workspace/verification")).unwrap();
            fs::write(path.join("a.txt"), "current").unwrap();
            fs::write(path.join(".agentic-workspace/verification/manifest.toml"),"schema_version='agentic-workspace/verification-manifest/v1'\n[protocols.check]\napplies_to_paths=['a.txt']\n[proof_routes.check]\nprotocol_refs=['check']\ncommands=['echo checked']\n").unwrap();
            Self(path)
        }
        fn prepared(&self) -> (Value, Value, Value, Value) {
            let mut input = json!({"target":self.0,"task":"Check source","changed":["a.txt"]});
            let initial = crate::native_public::start(input.clone()).unwrap();
            let mut request = initial["verification"]["record_requests"][0].clone();
            request["arguments"]["result"] = json!("passed");
            input["request"] = request;
            let current = crate::native_public::start(input).unwrap();
            let invocation = current["decision_packet"]["primary_action"].clone();
            let admission=attempt_store::admit(json!({"target":self.0,"decision":current["decision_packet"],"invocation":invocation})).unwrap();
            let mut receipt = json!({"kind":"agentic-workspace/proof-receipt/v1","command":"echo checked","result":"passed","changed_paths":["a.txt"],"proof_subject":invocation["arguments"]["selection"]["proof_subject"],"producer_class":"aw-proof","authority":"aw-proof","revision":"2026-09-08T00:00:00Z","recorded_at":"2026-09-08T00:00:00Z","source_ref":crate::native_proof::run_path(&invocation).unwrap()});
            let id = crate::native_verification::publication_identity(&receipt).unwrap();
            receipt["receipt_id"] = json!(id);
            receipt["publication_id"] = json!(id);
            let outcome = json!({"status":"applied","effects":["proof-execution"],"value":{"kind":"agentic-workspace/proof-execution-result/v1","producer_admission":"unproven-interoperability-observation"}});
            (invocation, admission["custody"].clone(), receipt, outcome)
        }
    }
    impl Drop for Repo {
        fn drop(&mut self) {
            let _ = fs::remove_dir_all(&self.0);
        }
    }
    #[test]
    fn retained_pre_and_post_image_recover_without_execution() {
        for stage in ["receipt-retained", "index-replaced", "commit-written"] {
            let repo = Repo::new();
            let (invocation, custody, receipt, outcome) = repo.prepared();
            let result = publish_checked(
                &repo.0,
                &receipt,
                &invocation,
                &custody,
                outcome,
                || Ok(()),
                |at| {
                    if at == stage {
                        Err(err("injected process interruption"))
                    } else {
                        Ok(())
                    }
                },
            );
            assert!(result.is_err());
            let recovered = recover(&repo.0, &invocation, || Ok(())).unwrap().unwrap();
            assert_eq!(
                recovered["record"]["outcome"]["value"]["publication"]["status"],
                "published"
            );
            assert_eq!(
                attempt_store::inspect_committed(
                    &repo.0.to_string_lossy(),
                    recovered["custody"].clone()
                )
                .unwrap(),
                recovered["record"]
            );
            assert_eq!(
                recover(&repo.0, &invocation, || Ok(())).unwrap().unwrap(),
                recovered
            );
            check(&repo.0).unwrap();
        }
    }
    #[test]
    fn current_locator_bounds_reads_and_cannot_grant_custody() {
        let repo = Repo::new();
        let (invocation, custody, receipt, outcome) = repo.prepared();
        publish(&repo.0, &receipt, &invocation, &custody, outcome, || Ok(())).unwrap();
        let root = Dir::open_ambient_dir(&repo.0, ambient_authority()).unwrap();
        let bytes = fs::read(repo.0.join(INDEX)).unwrap();
        SOURCE_READS.with(|count| count.set(0));
        owned_index(&repo.0, &root, Some(&bytes)).unwrap();
        assert_eq!(SOURCE_READS.with(|count| count.get()), 1);
        let mut index = parse(&bytes).unwrap();
        for n in 0..2047 {
            let id = format!("{n:016x}");
            index["receipts"][&id] = json!({"path": format!("{id}.json")});
        }
        // Valid receipt/attempt, wrong index: the hint cannot grant adoption.
        SOURCE_READS.with(|count| count.set(0));
        assert!(owned_index(&repo.0, &root, Some(&serde_json::to_vec(&index).unwrap())).is_err());
        assert_eq!(SOURCE_READS.with(|count| count.get()), 1);
        index["current_publication"] = json!("0000000000000000");
        SOURCE_READS.with(|count| count.set(0));
        assert!(owned_index(&repo.0, &root, Some(&serde_json::to_vec(&index).unwrap())).is_err());
        assert_eq!(SOURCE_READS.with(|count| count.get()), 1);
        index.as_object_mut().unwrap().remove("current_publication");
        SOURCE_READS.with(|count| count.set(0));
        assert!(owned_index(&repo.0, &root, Some(&serde_json::to_vec(&index).unwrap())).is_err());
        assert_eq!(SOURCE_READS.with(|count| count.get()), 0);
        assert_eq!(fs::read(repo.0.join(INDEX)).unwrap(), bytes);
    }
    #[test]
    fn full_owned_index_refuses_publication_before_mutation() {
        let repo = Repo::new();
        let (invocation, custody, mut receipt, mut outcome) = repo.prepared();
        let id = receipt["receipt_id"].as_str().unwrap().to_owned();
        let mut index = json!({"kind":"agentic-workspace/trusted-producer-receipt-index/v1","receipts":{},"current_publication":id});
        for n in 0..2047 {
            let historical = format!("{n:016x}");
            index["receipts"][&historical] = json!({"path":format!("{historical}.json")});
        }
        index["receipts"][&id] = json!({"path":format!("{id}.json")});
        let bytes = serde_json::to_vec_pretty(&index).unwrap();
        outcome["value"]["publication"] = json!({"status":"published","reference":format!("proof://receipts/{id}"),"index_sha256":hash(&bytes)});
        let prepared = attempt_store::prepare_commit(
            &repo.0.to_string_lossy(),
            custody.clone(),
            outcome.clone(),
        )
        .unwrap();
        receipt[CUSTODY] = json!({"kind":"agentic-workspace/proof-publication-custody/v1","custody":prepared["custody"],"outcome":outcome,"before_sha256":null});
        fs::create_dir_all(repo.0.join(STORE)).unwrap();
        let receipt_bytes = serde_json::to_vec_pretty(&receipt).unwrap();
        fs::write(repo.0.join(receipt_path(&id).unwrap()), &receipt_bytes).unwrap();
        fs::write(repo.0.join(INDEX), &bytes).unwrap();
        attempt_store::commit(json!({"target":repo.0,"custody":custody,"outcome":outcome}))
            .unwrap();
        check(&repo.0).unwrap();
        let error =
            publish(&repo.0, &receipt, &invocation, &custody, outcome, || Ok(())).unwrap_err();
        assert!(error.to_string().contains("index-capacity-reached"));
        assert_eq!(fs::read(repo.0.join(INDEX)).unwrap(), bytes);
        assert_eq!(
            fs::read(repo.0.join(receipt_path(&id).unwrap())).unwrap(),
            receipt_bytes
        );
    }
    #[test]
    fn recovery_ignores_unrelated_temporary_inventory() {
        let repo = Repo::new();
        let (invocation, custody, receipt, outcome) = repo.prepared();
        assert!(
            publish_checked(
                &repo.0,
                &receipt,
                &invocation,
                &custody,
                outcome,
                || Ok(()),
                |at| if at == "receipt-retained" {
                    Err(err("interrupt"))
                } else {
                    Ok(())
                }
            )
            .is_err()
        );
        for n in 0..4097 {
            fs::write(
                repo.0.join(format!("{STORE}/unrelated-{n}.tmp")),
                b"preserve",
            )
            .unwrap();
        }
        assert!(recover(&repo.0, &invocation, || Ok(())).unwrap().is_some());
        assert_eq!(
            fs::read(repo.0.join(format!("{STORE}/unrelated-4096.tmp"))).unwrap(),
            b"preserve"
        );
        let index = fs::read(repo.0.join(INDEX)).unwrap();
        for n in 4097..8193 {
            fs::write(
                repo.0.join(format!("{STORE}/unrelated-{n}.tmp")),
                b"preserve",
            )
            .unwrap();
        }
        assert!(
            recover(&repo.0, &invocation, || Ok(()))
                .unwrap_err()
                .to_string()
                .contains("total inventory exceeds bound")
        );
        assert_eq!(fs::read(repo.0.join(INDEX)).unwrap(), index);
        assert_eq!(
            fs::read(repo.0.join(format!("{STORE}/unrelated-8192.tmp"))).unwrap(),
            b"preserve"
        );
    }
    #[test]
    fn changed_index_cannot_be_acquired() {
        let repo = Repo::new();
        let (invocation, custody, receipt, outcome) = repo.prepared();
        assert!(
            publish_checked(
                &repo.0,
                &receipt,
                &invocation,
                &custody,
                outcome,
                || Ok(()),
                |at| if at == "index-replaced" {
                    Err(err("interrupt"))
                } else {
                    Ok(())
                }
            )
            .is_err()
        );
        let original = fs::read(repo.0.join(INDEX)).unwrap();
        let mut changed: Value = serde_json::from_slice(&original).unwrap();
        changed["unowned"] = json!(true);
        let changed_bytes = serde_json::to_vec(&changed).unwrap();
        fs::write(repo.0.join(INDEX), &changed_bytes).unwrap();
        assert!(recover(&repo.0, &invocation, || Ok(())).is_err());
        assert_eq!(fs::read(repo.0.join(INDEX)).unwrap(), changed_bytes);
        assert!(check(&repo.0).is_err());
    }
    #[test]
    fn lock_serializes_publishers_and_preserves_unknown_index() {
        let repo = Repo::new();
        let (invocation, custody, receipt, outcome) = repo.prepared();
        let root = Dir::open_ambient_dir(&repo.0, ambient_authority()).unwrap();
        let held = lock(&root).unwrap();
        assert!(
            publish(
                &repo.0,
                &receipt,
                &invocation,
                &custody,
                outcome.clone(),
                || Ok(())
            )
            .is_err()
        );
        drop(held);
        fs::write(
            repo.0.join(INDEX),
            b"{\"kind\":\"agentic-workspace/trusted-producer-receipt-index/v1\",\"receipts\":{}}",
        )
        .unwrap();
        let original = fs::read(repo.0.join(INDEX)).unwrap();
        assert!(publish(&repo.0, &receipt, &invocation, &custody, outcome, || Ok(())).is_err());
        assert_eq!(fs::read(repo.0.join(INDEX)).unwrap(), original);
    }
    #[test]
    fn publication_crash_child() {
        let Ok(target) = std::env::var("AW_PUBLICATION_TEST_TARGET") else {
            return;
        };
        let stage = std::env::var("AW_PUBLICATION_TEST_STAGE").unwrap();
        let repo = Repo(target.into());
        let (invocation, custody, receipt, outcome) = repo.prepared();
        let run = crate::native_proof::run_path(&invocation).unwrap();
        fs::create_dir_all(repo.0.join(&run).parent().unwrap()).unwrap();
        fs::write(repo.0.join(&run),serde_json::to_vec(&json!({"kind":"agentic-workspace/proof-execution-run/v1","invocation":invocation,"custody":custody})).unwrap()).unwrap();
        fs::write(
            repo.0.join("test-invocation.json"),
            serde_json::to_vec(&invocation).unwrap(),
        )
        .unwrap();
        let _ = publish_checked(
            &repo.0,
            &receipt,
            &invocation,
            &custody,
            outcome,
            || Ok(()),
            |at| {
                if at == stage {
                    std::process::exit(91)
                };
                Ok(())
            },
        );
        panic!("crash point was not reached");
    }
    #[test]
    fn publication_recovery_child() {
        let Ok(target) = std::env::var("AW_PUBLICATION_RECOVERY_TARGET") else {
            return;
        };
        let path = std::path::PathBuf::from(&target);
        let invocation: Value =
            serde_json::from_slice(&fs::read(path.join("test-invocation.json")).unwrap()).unwrap();
        let result=crate::native_public::invoke(json!({"target":target,"task":"Check source","changed":["a.txt"],"invocation":invocation})).unwrap();
        assert_eq!(result["value"]["publication"]["status"], "published");
        assert_eq!(
            result["value"]["producer_admission"],
            "unproven-interoperability-observation"
        );
    }
    #[test]
    fn process_exit_at_each_publication_boundary_recovers_in_fresh_process() {
        for stage in ["receipt-retained", "index-replaced", "commit-written"] {
            let repo = Repo::new();
            let status = std::process::Command::new(std::env::current_exe().unwrap())
                .args([
                    "--exact",
                    "proof_publication::tests::publication_crash_child",
                ])
                .env("AW_PUBLICATION_TEST_TARGET", &repo.0)
                .env("AW_PUBLICATION_TEST_STAGE", stage)
                .output()
                .unwrap();
            assert_eq!(
                status.status.code(),
                Some(91),
                "{}",
                String::from_utf8_lossy(&status.stdout)
            );
            let recovered = std::process::Command::new(std::env::current_exe().unwrap())
                .args([
                    "--exact",
                    "proof_publication::tests::publication_recovery_child",
                ])
                .env("AW_PUBLICATION_RECOVERY_TARGET", &repo.0)
                .output()
                .unwrap();
            assert!(
                recovered.status.success(),
                "{} {}",
                String::from_utf8_lossy(&recovered.stdout),
                String::from_utf8_lossy(&recovered.stderr)
            );
        }
    }
}
