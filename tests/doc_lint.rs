use std::process::Command;

#[test]
fn markdown_hygiene() {
    let status = Command::new("python3")
        .arg("scripts/doc_lint.py")
        .status()
        .expect("failed to run doc_lint script");
    assert!(status.success());
}
