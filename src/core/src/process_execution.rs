//! Bounded native process transport. Domain owners retain admission and outcomes.
use crate::CoreError;
use serde_json::{Value, json};
use std::{
    io::{Read, Write},
    process::{Command, Stdio},
    time::{Duration, Instant},
};
fn err(e: impl std::fmt::Display) -> CoreError {
    CoreError::new(e.to_string())
}

struct ProcessGuard(Box<dyn process_wrap::std::ChildWrapper>);
impl Drop for ProcessGuard {
    fn drop(&mut self) {
        let _ = self.0.start_kill();
        let until = Instant::now() + Duration::from_millis(250);
        while Instant::now() < until {
            if !matches!(self.0.try_wait(), Ok(None)) {
                break;
            }
            std::thread::sleep(Duration::from_millis(10));
        }
    }
}
pub(crate) fn run(
    mut command: Command,
    input: Option<Vec<u8>>,
    budget: Duration,
) -> Result<Value, CoreError> {
    use process_wrap::std::*;
    if input.as_ref().is_some_and(|bytes| bytes.len() > 1_048_576) {
        return Err(err("process input exceeds bounded handoff limit"));
    }
    command
        .stdin(if input.is_some() {
            Stdio::piped()
        } else {
            Stdio::null()
        })
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());
    let mut cmd = CommandWrap::from(command);
    #[cfg(windows)]
    {
        cmd.wrap(CreationFlags(
            windows::Win32::System::Threading::CREATE_NO_WINDOW,
        ))
        .wrap(JobObject);
    }
    #[cfg(unix)]
    {
        cmd.wrap(ProcessGroup::leader());
    }
    let started = Instant::now();
    let mut guard = ProcessGuard(cmd.spawn().map_err(err)?);
    let child = &mut guard.0;
    let input_done = input.map(|bytes| {
        let (sender, receiver) = std::sync::mpsc::channel();
        let mut stream = child.stdin().take();
        std::thread::spawn(move || {
            let result = stream
                .as_mut()
                .ok_or_else(|| "process stdin unavailable".to_owned())
                .and_then(|stream| stream.write_all(&bytes).map_err(|e| e.to_string()));
            drop(stream);
            let _ = sender.send(result);
        });
        receiver
    });
    let (sender, receiver) = std::sync::mpsc::channel();
    for (name, stream) in [
        (
            "stdout",
            child
                .stdout()
                .take()
                .map(|v| Box::new(v) as Box<dyn Read + Send>),
        ),
        (
            "stderr",
            child
                .stderr()
                .take()
                .map(|v| Box::new(v) as Box<dyn Read + Send>),
        ),
    ] {
        let sender = sender.clone();
        std::thread::spawn(move || {
            let mut tail = Vec::new();
            let mut total = 0usize;
            let mut chunk = [0; 4096];
            if let Some(mut stream) = stream {
                while let Ok(n) = stream.read(&mut chunk) {
                    if n == 0 {
                        break;
                    }
                    total = total.saturating_add(n);
                    tail.extend_from_slice(&chunk[..n]);
                    if tail.len() > 65536 {
                        tail.drain(..tail.len() - 65536);
                    }
                }
            }
            let _ = sender.send((name, total, tail));
        });
    }
    let mut timed_out = false;
    let status = 'execution: loop {
        if started.elapsed() >= budget {
            timed_out = true;
            child.start_kill().map_err(err)?;
            let until = Instant::now() + Duration::from_millis(250);
            loop {
                if let Some(status) = child.try_wait().map_err(err)? {
                    break 'execution status;
                }
                if Instant::now() >= until {
                    return Err(err(
                        "process termination remains uncertain; owner recovery required",
                    ));
                }
                std::thread::sleep(Duration::from_millis(10));
            }
        }
        if let Some(status) = child.try_wait().map_err(err)? {
            break status;
        }
        std::thread::sleep(Duration::from_millis(10));
    };
    // A command leaving descendants behind cannot extend the evidence lifetime.
    // ChildWrapper::kill also waits for the whole Windows job. A prior
    // try_wait may already have consumed its completion notification, so that
    // second wait is unbounded even after a successful short command.
    let _ = child.start_kill();
    let mut output = serde_json::Map::new();
    for _ in 0..2 {
        match receiver.recv_timeout(Duration::from_secs(2)) {
            Ok((name, count, bytes)) => {
                output.insert(name.into(),json!({"bytes":count,"tail":String::from_utf8_lossy(&bytes),"truncated":count>bytes.len()}));
            }
            Err(_) => {
                return Err(err(
                    "process output drain incomplete; execution outcome requires owner recovery",
                ));
            }
        }
    }
    if let Some(receiver) = input_done {
        receiver
            .recv_timeout(Duration::from_secs(2))
            .map_err(|_| err("process input drain incomplete; owner recovery required"))?
            .map_err(err)?;
    }
    Ok(
        json!({"status":if timed_out {"timeout"}else if status.success(){"passed"}else{"failed"},"exit_code":status.code(),
        "duration_ms":started.elapsed().as_millis(),"output":output,"execution_kind":"trusted-process"}),
    )
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn short_commands_finish_without_a_second_job_wait() {
        for _ in 0..32 {
            #[cfg(windows)]
            let mut command = Command::new("cmd.exe");
            #[cfg(windows)]
            command.args(["/d", "/c", "echo bounded"]);
            #[cfg(unix)]
            let mut command = Command::new("sh");
            #[cfg(unix)]
            command.args(["-c", "echo bounded"]);
            let result = run(command, None, Duration::from_secs(2)).unwrap();
            assert_eq!(result["status"], "passed");
            assert!(
                result["output"]["stdout"]["tail"]
                    .as_str()
                    .unwrap()
                    .contains("bounded")
            );
        }
    }
    #[test]
    fn timeout_terminates_without_an_unbounded_job_wait() {
        #[cfg(windows)]
        let mut command = Command::new("cmd.exe");
        #[cfg(windows)]
        command.args(["/d", "/c", "ping -n 30 127.0.0.1 > nul"]);
        #[cfg(unix)]
        let mut command = Command::new("sh");
        #[cfg(unix)]
        command.args(["-c", "sleep 30"]);
        let began = Instant::now();
        let result = run(command, None, Duration::from_millis(100)).unwrap();
        assert_eq!(result["status"], "timeout");
        assert!(began.elapsed() < Duration::from_secs(5));
    }
}
