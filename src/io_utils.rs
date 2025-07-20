//! See [Kolyma Spec](../kolyma.pdf) - 2025-07-20 - commit c48b123cf3a8761a15713b9bf18697061ab23976
use std::fmt;
use std::io;
use std::path::Path;

#[derive(Debug)]
pub struct CliError(pub String);

impl fmt::Display for CliError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        self.0.fmt(f)
    }
}

impl std::error::Error for CliError {}

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
    CliError(format_io_error(operation, path, &err))
}

/// Convert an I/O error into a std::io::Error with context.
pub fn io_error(operation: &str, path: &Path, err: io::Error) -> io::Error {
    io::Error::new(err.kind(), format_io_error(operation, path, &err))
}

/// Simple CLI error from string.
pub fn simple_cli_error(msg: &str) -> CliError {
    CliError(msg.to_string())
}

/// Invalid file extension error.
pub fn extension_error(path: &Path) -> CliError {
    CliError(format!(
        "Invalid file extension for '{}'. Expected .tlmr. Check the input file.",
        path.display()
    ))
}
