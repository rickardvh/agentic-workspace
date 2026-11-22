//! Checkout-local records of reported external review. No review authority is admitted.
use crate::{CoreError, current_projection, digest, native_planning, native_verification};
use cap_std::{
    ambient_authority,
    fs::{Dir, OpenOptions},
};
use serde_json::{Value, json};
use std::{path::Path, process::Command, time::Duration};

pub(crate) const REQUEST: &str = "verification/manual-pr-review/v1";
pub(crate) const OP: &str = "verification.record-manual-pr-review";
pub(crate) const EFFECT: &str = "manual-review-record";
const STORE: &str = ".agentic-workspace/local/manual-pr-reviews";
const RESULT: &str = "agentic-workspace/manual-pr-review/v1";
const MAX_REPORTS: usize = 32;

fn err(e: impl ToString) -> CoreError {
    CoreError::new(e.to_string())
}

pub(crate) fn extend_contract(owner: &mut Value) {
    let reference =
        json!({"type":"string","maxLength":1024,"pattern":"^[A-Za-z][A-Za-z0-9+.-]*:\\S+$"});
    owner["requests"].as_array_mut().unwrap().push(json!({
    "kind":REQUEST,"result_kind":RESULT,
    "input_schema":{"$schema":"https://json-schema.org/draft/2020-12/schema",
        "type":"object","additionalProperties":false,"required":["pull_request"],
        "properties":{"pull_request":reference,"report":{
            "type":"object","additionalProperties":false,
            "required":["reference","reviewed_revision","disposition"],
            "properties":{"reference":reference,"supersedes":reference,
                "reviewed_revision":{"type":"string","pattern":"^([a-f0-9]{40}|[a-f0-9]{64})$"},
                "disposition":{"enum":["approved","changes-requested","rejected"]}}
        }}
    }}));
    owner["effects"]
        .as_array_mut()
        .unwrap()
        .push(json!({"id":EFFECT,"domain":"verification"}));
    owner["operations"].as_array_mut().unwrap().push(json!({
        "id":OP,"semantic_revision":"manual-pr-review/v1","effects":[EFFECT],"reads":["verification"],
        "result_kind":RESULT,"input_schema":{"$schema":"https://json-schema.org/draft/2020-12/schema",
            "type":"object","additionalProperties":false,"required":["target","pull_request","record"],
            "properties":{"target":{"type":"string"},"pull_request":reference,"record":{"type":"object"}}
        }}));
}

fn git(target: &Path) -> Command {
    let mut command = Command::new("git");
    command
        .arg("-C")
        .arg(target)
        .args(["-c", "core.fsmonitor=false"])
        .env("GIT_OPTIONAL_LOCKS", "0")
        .env_remove("GIT_DIR")
        .env_remove("GIT_COMMON_DIR")
        .env_remove("GIT_WORK_TREE")
        .env_remove("GIT_INDEX_FILE");
    command
}

fn has_uncommitted_inputs(
    root: &Dir,
    target: &Path,
    changed: &[String],
) -> Result<bool, CoreError> {
    let mut specs = Vec::new();
    for path in crate::native_source_reconciliation::scope_files(root, changed)? {
        match root.symlink_metadata(&path) {
            Ok(metadata) if metadata.is_dir() => {
                return Err(err(
                    "Select concrete changed files or a bounded file pattern to compare with the reviewed commit",
                ));
            }
            Ok(_) => specs.push(path),
            Err(error) if error.kind() == std::io::ErrorKind::NotFound => {}
            Err(error) => return Err(err(error)),
        }
    }
    if specs.is_empty() {
        return Ok(false);
    }
    let magic = if cfg!(windows) {
        ":(literal,icase)"
    } else {
        ":(literal)"
    };
    let specs: Vec<_> = specs.iter().map(|path| format!("{magic}{path}")).collect();
    if specs
        .iter()
        .map(|spec| spec.encode_utf16().count() + 3)
        .sum::<usize>()
        > 12_000
    {
        return Err(err(
            "Narrow changed paths to compare them with the reviewed commit within the Git query bound",
        ));
    }
    let mut command = git(target);
    command
        .args(["ls-files", "--cached", "--error-unmatch", "-z", "--"])
        .args(specs)
        .env("GIT_LITERAL_PATHSPECS", "0")
        .env("GIT_GLOB_PATHSPECS", "0")
        .env("GIT_NOGLOB_PATHSPECS", "0")
        .env("GIT_ICASE_PATHSPECS", "0");
    let (status, _) = native_verification::bounded_git_output_with_limit(
        &mut command,
        Duration::from_secs(3),
        64 * 1024,
    )
    .map_err(err)?;
    match status.code() {
        Some(0) => Ok(false),
        Some(1) => Ok(true),
        _ => Err(err(
            "Git could not compare the selected source paths with the index",
        )),
    }
}

fn checkout(root: &Dir, target: &Path, changed: &[String]) -> Result<Value, CoreError> {
    let mut command = git(target);
    command.args([
        "status",
        "--porcelain=v2",
        "--branch",
        "-z",
        "--untracked-files=no",
        "--no-renames",
        "--ignore-submodules=none",
    ]);
    let (status, output) = native_verification::bounded_git_output_with_limit(
        &mut command,
        Duration::from_secs(3),
        64 * 1024,
    )
    .map_err(err)?;
    if !status.success() {
        return Err(err("Git could not observe the current checkout revision"));
    }
    let mut rows = output
        .split(|byte| *byte == 0)
        .filter(|row| !row.is_empty());
    let revision = rows
        .next()
        .and_then(|row| row.strip_prefix(b"# branch.oid "))
        .and_then(|value| std::str::from_utf8(value).ok())
        .filter(|value| {
            matches!(value.len(), 40 | 64) && value.bytes().all(|byte| byte.is_ascii_hexdigit())
        })
        .ok_or_else(|| err("The checkout has no observable commit"))?;
    let tracked_changes = rows.any(|row| !row.starts_with(b"# "));
    let uncommitted_inputs = !tracked_changes && has_uncommitted_inputs(root, target, changed)?;
    Ok(
        json!({"revision":revision,"tracked_changes":tracked_changes,
        "uncommitted_inputs":uncommitted_inputs,"basis":"local-git-checkout"}),
    )
}

fn dirty(checkout: &Value) -> bool {
    checkout["tracked_changes"] == true || checkout["uncommitted_inputs"] == true
}

fn path(pull_request: &str) -> Result<String, CoreError> {
    let identity = digest(&json!(pull_request))?;
    Ok(format!("{STORE}/{}.json", &identity[7..]))
}

fn record_shape(record: &Value) -> bool {
    let strings = |field: &str| {
        record[field]
            .as_array()
            .is_some_and(|values| values.iter().all(Value::is_string))
    };
    record.as_object().is_some_and(|fields| fields.len() == 7)
        && record["reference"].is_string()
        && record["reviewed_revision"].is_string()
        && (record.get("supersedes") == Some(&Value::Null) || record["supersedes"].is_string())
        && matches!(
            record["disposition"].as_str(),
            Some("approved" | "changes-requested" | "rejected")
        )
        && strings("required_reviewer_roles")
        && strings("handoff_evidence_refs")
        && record["provenance"] == "externally-reported"
}

fn state(root: &Dir, pull_request: &str) -> Result<Value, CoreError> {
    let Some(value) = current_projection::read(root, &path(pull_request)?)? else {
        return Ok(json!({"kind":RESULT,"pull_request":pull_request,"records":[]}));
    };
    if value.as_object().is_none_or(|fields| fields.len() != 3)
        || value["kind"] != RESULT
        || value["pull_request"] != pull_request
        || value["records"].as_array().is_none_or(|records| {
            records.len() > MAX_REPORTS || records.iter().any(|record| !record_shape(record))
        })
    {
        return Err(err(
            "Unrecognised manual review record; preserve it and inspect the local record",
        ));
    }
    Ok(value)
}

fn latest(state: &Value) -> Option<&Value> {
    state["records"]
        .as_array()
        .and_then(|records| records.last())
}

fn submission(state: &Value, report: &Value) -> Result<bool, &'static str> {
    let records = state["records"].as_array().unwrap();
    if let Some(prior) = records
        .iter()
        .find(|prior| prior["reference"] == report["reference"])
    {
        return if ["reviewed_revision", "disposition", "supersedes"]
            .iter()
            .all(|key| prior[*key] == report[*key])
        {
            Ok(false)
        } else {
            Err(
                "This external review reference already has a different record. Preserve it and use a distinct external reference for a new result.",
            )
        };
    }
    if let Some(prior) = records.last() {
        if (prior["reviewed_revision"] == report["reviewed_revision"]
            || !report["supersedes"].is_null())
            && prior["reference"] != report["supersedes"]
        {
            return Err(
                "To replace the reported result for this revision, supply the current external review reference in supersedes.",
            );
        }
    } else if !report["supersedes"].is_null() {
        return Err("There is no existing report to supersede.");
    }
    if records.len() == MAX_REPORTS {
        return Err("The checkout-local review record has reached its history limit.");
    }
    Ok(true)
}

pub(crate) fn view(
    target: &Path,
    (work, changed): (&Value, &[String]),
    configuration: &Value,
    verification: &Value,
    contract: &Value,
    request: Option<&Value>,
    executing: bool,
) -> Result<Option<Value>, CoreError> {
    let local = configuration["safety"]["requires_human_verification_on_pr"] == true;
    let protocols = verification["strategy"]["protocols"]
        .as_object()
        .into_iter()
        .flatten();
    let manual_protocols: Vec<_> = protocols
        .filter(|(_, row)| row["manual_required"] == true)
        .collect();
    if !local && manual_protocols.is_empty() {
        return if request.is_none() {
            Ok(None)
        } else {
            Err(err("Current policy does not select manual PR review"))
        };
    }
    let mut reviewers = std::collections::BTreeSet::new();
    for row in verification["assurance_applicability"]["requirements"]
        .as_array()
        .into_iter()
        .flatten()
    {
        if row["status"] == "applicable"
            && matches!(
                row["force"].as_str(),
                Some("required-before-closeout" | "blocking")
            )
        {
            if let Some(role) = row["source_requirement"]["review_owner"].as_str() {
                reviewers.insert(role);
            }
        }
    }
    for (_, row) in &manual_protocols {
        if let Some(role) = row["review_owner"].as_str() {
            reviewers.insert(role);
        }
    }
    if reviewers.is_empty() {
        reviewers.insert("maintainer");
    }
    let evidence: Vec<_> = verification["evidence"]
        .as_array()
        .into_iter()
        .flatten()
        .filter(|row| {
            row["runtime_admission"]["status"] == "reusable"
                && row["evidence_freshness"] == "reusable"
        })
        .filter_map(|row| row["reference"].as_str())
        .take(64)
        .collect();
    let owner = contract["owners"]
        .as_array()
        .unwrap()
        .iter()
        .find(|row| row["owner"] == "verification")
        .unwrap();
    let mut template = json!({"kind":"agentic-workspace/public-request/v1","id":REQUEST,"owner":"verification",
        "request_kind":REQUEST,"owner_revision":owner["revision"],"capability_revision":contract["revision"],
        "source_revision":digest(&json!([REQUEST,configuration["revision"],verification["source"]["revision"]]))?,
        "task_identity":work,"arguments":{"pull_request":"<repository-qualified PR reference>"}});
    let mut view = json!({"kind":RESULT,"reviewers":reviewers,"evidence_refs":evidence,
        "manual_protocols":manual_protocols.iter().map(|(id,_)| id.as_str()).collect::<Vec<_>>(),
        "review_status":"pending","recording_status":"subject-required","reviewer_provenance":"unverified",
        "approval_authority":"repository","completion_authority":false,"request":template});
    let Some(request) = request else {
        return Ok(Some(view));
    };
    crate::prepare_request_value(
        json!({"request":request,"current_work":work,"capability_contract":contract}),
    )?;
    let arguments = &request["arguments"];
    let pull_request = arguments["pull_request"].as_str().unwrap();
    if pull_request.len() > 1024 {
        return Err(err("Pull request reference exceeds its byte limit"));
    }
    template["arguments"] = arguments.clone();
    if template != *request {
        return Err(err(
            "Manual review request is no longer current; select the pull request again",
        ));
    }
    template["arguments"] = json!({"pull_request":pull_request});
    view["request"] = template;
    view["pull_request"] = json!(pull_request);
    let root = Dir::open_ambient_dir(target, ambient_authority()).map_err(err)?;
    let state = match state(&root, pull_request) {
        Ok(value) => value,
        Err(error) => {
            view["recording_status"] = json!("unavailable");
            view["detail"] = json!(error.to_string());
            return Ok(Some(view));
        }
    };
    let prior = latest(&state);
    if let Some(record) = prior {
        view["recorded_report"] = record.clone();
    }
    let observed = match checkout(&root, target, changed) {
        Ok(value) => value,
        Err(error) => {
            view["recording_status"] = json!("unavailable");
            view["detail"] = json!(error.to_string());
            if prior.is_some() {
                view["review_status"] = json!("currentness-unverified");
            }
            return Ok(Some(view));
        }
    };
    view["checkout"] = observed.clone();
    view["recording_status"] = json!("available");
    if let Some(record) = prior {
        view["review_status"] = json!(if record["reviewed_revision"] != observed["revision"]
            || dirty(&observed)
        {
            "stale"
        } else {
            "recorded-externally"
        });
    }
    if let Some(report) = arguments.get("report") {
        let submitted = submission(&state, report);
        if submitted == Ok(false) && !executing {
            view["recording_status"] = json!("already-recorded");
            return Ok(Some(view));
        }
        if report["reviewed_revision"] != observed["revision"] || dirty(&observed) {
            view["recording_status"] = json!("subject-differs");
            view["detail"] = json!(
                "The report must name the observed commit with its selected inputs committed. Preserve the old review and reselect the current revision."
            );
            return Ok(Some(view));
        }
        if let Err(reason) = submitted {
            view["recording_status"] = json!("conflict");
            view["detail"] = json!(reason);
            return Ok(Some(view));
        }
        let record = json!({"reference":report["reference"],"reviewed_revision":report["reviewed_revision"],
            "disposition":report["disposition"],"supersedes":report["supersedes"],
            "required_reviewer_roles":reviewers,"handoff_evidence_refs":evidence,"provenance":"externally-reported"});
        view["recording_status"] = json!("ready-to-record");
        view["action"] = json!({"operation_id":OP,"dependency_revision":digest(&json!([request,observed,record]))?,
            "arguments":{"target":target,"pull_request":pull_request,"record":record},
            "effects":[EFFECT],"source_requests":[request]});
    }
    Ok(Some(view))
}

pub(crate) fn finalize(verification: &mut Value, decision: &Value) {
    let Some(view) = verification.get("manual_review") else {
        return;
    };
    let reviewer_only: Vec<_> = verification["assurance_owner_gaps"]
        .as_array()
        .into_iter()
        .flatten()
        .filter(|gap| gap["missing_admissions"] == json!(["required-reviewer-result-not-admitted"]))
        .filter_map(|gap| gap["requirement_id"].as_str())
        .map(|id| format!("assurance:{id}:applicable"))
        .collect();
    let mut gaps = Vec::new();
    for blocker in decision["blockers"].as_array().into_iter().flatten() {
        let code = blocker["code"].as_str().unwrap_or_default();
        let selected_protocol = code
            .strip_prefix("protocol-review-required:")
            .is_some_and(|id| {
                view["manual_protocols"]
                    .as_array()
                    .unwrap()
                    .iter()
                    .any(|entry| entry == id)
            });
        let relevant = blocker["affects"]
            .as_array()
            .into_iter()
            .flatten()
            .filter_map(Value::as_str)
            .any(|scope| {
                scope == "task" || scope.starts_with("claim:") || scope == "effect:proof-execution"
            });
        if relevant
            && code != "local-human-review-required"
            && !reviewer_only.iter().any(|entry| entry == code)
            && !selected_protocol
        {
            gaps.push(json!({"code":code,"message":blocker["message"]}));
        }
    }
    let claim = &verification["claim_review"];
    if claim["status"] != "current" || claim["claim"]["judgment"] != "satisfied" {
        gaps.push(json!({"code":"work-readiness-unconfirmed","message":"Establish that the current implementation and evidence satisfy the requested result."}));
    }
    let clean = view["checkout"].is_object() && !dirty(&view["checkout"]);
    if dirty(&view["checkout"]) {
        gaps.push(json!({"code":"checkout-has-uncommitted-inputs","message":"Review a committed revision. The checkout has pending tracked changes or selected inputs outside the commit."}));
    }
    let view = &mut verification["manual_review"];
    view["implementation_gaps"] = json!(gaps);
    let (status, next) = match view["review_status"].as_str() {
        Some("recorded-externally") => match view["recorded_report"]["disposition"].as_str() {
            Some("changes-requested") => (
                "external-changes-requested",
                "Address the requested changes through the repository's review process.",
            ),
            Some("rejected") => (
                "external-rejection-reported",
                "Use the external rejection to resolve the repository's next step.",
            ),
            _ => (
                "external-approval-reported",
                "Approval reported externally. Reviewer provenance unverified by AW. Use the repository's approval process for closeout.",
            ),
        },
        Some("stale") => (
            "stale-review",
            "The recorded review covers an earlier subject. Ask for review of the current revision when the work is ready.",
        ),
        Some("currentness-unverified") => (
            "review-currentness-unverified",
            "The external result is recorded. Restore checkout observation to compare its revision.",
        ),
        _ if view["recording_status"] == "unavailable" => (
            "recording-unavailable",
            "Follow the repository's review process. Inspect the local recording limitation before trying to retain the outcome.",
        ),
        _ if gaps.is_empty() && clean => (
            "ready-for-maintainer-review",
            "Ready for maintainer review. Review the identified PR revision and evidence through the repository's usual process.",
        ),
        _ if view["recording_status"] == "subject-required" => (
            "pull-request-required",
            "Identify the pull request to prepare the maintainer handoff.",
        ),
        _ => (
            "work-not-ready",
            "Resolve the listed implementation or evidence gaps before requesting review.",
        ),
    };
    view["handoff_status"] = json!(status);
    view["next_step"] = json!(next);
}

pub(crate) fn write_scope(action: &Value) -> Result<Vec<String>, CoreError> {
    let path = path(
        action["arguments"]["pull_request"]
            .as_str()
            .ok_or_else(|| err("Manual review action is missing its PR reference"))?,
    )?;
    Ok(vec![format!("{path}.lock"), format!("{path}.tmp"), path])
}

pub(crate) fn execute(
    target: &Path,
    invocation: &Value,
    revalidate: impl FnOnce() -> Result<(), CoreError>,
) -> Result<Value, CoreError> {
    let args = &invocation["arguments"];
    let pull_request = args["pull_request"].as_str().unwrap();
    let path = path(pull_request)?;
    let lock_path = format!("{path}.lock");
    let root = Dir::open_ambient_dir(target, ambient_authority()).map_err(err)?;
    native_planning::read(&root, &lock_path)?;
    root.create_dir_all(STORE).map_err(err)?;
    let lock = root
        .open_with(
            &lock_path,
            OpenOptions::new().read(true).write(true).create(true),
        )
        .map_err(err)?
        .into_std();
    if lock.metadata().map_err(err)?.len() != 0 {
        return Err(err(
            "Unrecognised manual review publication lock; preserve it",
        ));
    }
    lock.try_lock().map_err(err)?;
    revalidate()?;
    let mut state = state(&root, pull_request)?;
    let record = &args["record"];
    let inserted = submission(&state, record).map_err(err)?;
    if inserted {
        state["records"]
            .as_array_mut()
            .unwrap()
            .push(record.clone());
        current_projection::write(&root, &path, &state)?;
    }
    Ok(
        json!({"outcome":{"status":if inserted {"applied"} else {"unchanged"},
        "effects":if inserted {json!([EFFECT])} else {json!([])},
        "value":{"pull_request":pull_request,"recorded_report":record,"reviewer_provenance":"unverified","completion_authority":false}},
        "post_effect_changed_paths":[]}),
    )
}
