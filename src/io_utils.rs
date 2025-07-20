//! See [Kolyma Spec](../kolyma.pdf) - 2025-07-20 - commit c48b123cf3a8761a15713b9bf18697061ab23976
use std::fmt;
use std::io;
use std::path::Path;

#[derive(Debug)]
pub struct CliError {
    pub msg: String,
    pub source: Option<Box<dyn std::error::Error + Send + Sync>>,
}

impl fmt::Display for CliError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        self.msg.fmt(f)
    }
}

impl std::error::Error for CliError {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        self.source
            .as_deref()
            .map(|e| e as &(dyn std::error::Error + 'static))
    }
}

/// Format a user friendly I/O error message with suggestions.
pub fn format_io_error(operation: &str, path: &Path, err: &io::Error) -> String {
    use io::ErrorKind::*;
    let suggestion = match err.kind() {
        NotFound => "Check that the file exists and the path is correct.",
        PermissionDenied => "Check permissions or run as a different user.",
        UnexpectedEof => "File appears truncated or corrupted.",
        WriteZero => "Disk may be full. Free up space and try again.",
        Other if err.raw_os_error() == Some(28) => "Disk may be full. Free up space and try again.",
        _ => "Check permissions or free up disk space.",
    };
    format!(
        "Error {} '{}': {}. {}",
        operation,
        path.display(),
        err,
        suggestion
    )
}

/// Convert an I/O error into a CLI error with context.
pub fn io_cli_error(operation: &str, path: &Path, err: io::Error) -> CliError {
    CliError {
        msg: format_io_error(operation, path, &err),
        source: Some(Box::new(err)),
    }
}

/// Convert an I/O error into a std::io::Error with context.
pub fn io_error(operation: &str, path: &Path, err: io::Error) -> io::Error {
    io::Error::new(err.kind(), format_io_error(operation, path, &err))
}

/// Simple CLI error from string.
pub fn simple_cli_error(msg: &str) -> CliError {
    CliError {
        msg: msg.to_string(),
        source: None,
    }
}

/// Invalid file extension error.
pub fn extension_error(path: &Path) -> CliError {
    CliError {
        msg: format!(
            "Invalid file extension for '{}'. Expected .tlmr. Check the input file.",
            path.display()
        ),
        source: None,
    }
}

/// Convert a Telomere library error into a CLI error with a hint.
pub fn telomere_cli_error(context: &str, err: crate::TelomereError) -> CliError {
    CliError {
        msg: format!("{}: {}", context, cli_hint(&err)),
        source: Some(Box::new(err)),
    }
}

/// Return an actionable hint for a Telomere error variant.
pub fn cli_hint(err: &crate::TelomereError) -> String {
    use crate::TelomereError::*;
    match err {
        Header(msg) => format!("{msg}. Verify the file is intact."),
        SeedSearch(msg) => format!("{msg}. Check the seed table."),
        Bundling(msg) => format!("{msg}. Bundle selection failed."),
        Superposition(msg) => format!("{msg}. Candidate pruning issue."),
        SuperpositionLimitExceeded(i) => format!("Too many candidates at block {i}."),
        HeaderCodec(e) => format!("{e}. Likely stream malformed, try recompressing."),
        Hash(msg) => format!("{msg}. Hash mismatch."),
        Config(msg) => format!("{msg}. Invalid configuration."),
        Io(io) => format!("{io}"),
        Internal(msg) => format!("{msg}. This is a bug."),
        Decode(msg) | Other(msg) => msg.clone(),
    }
}
