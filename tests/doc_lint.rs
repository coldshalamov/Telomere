use std::process::Command;

#[test]
fn markdown_hygiene() {
    let out = Command::new("python3")
        .arg("scripts/doc_lint.py")
        .output()
        .expect("failed to run doc_lint script");
    if !out.status.success() {
        let text = String::from_utf8_lossy(&out.stdout);
        if text.contains("markdownlint not found") {
            eprintln!("markdownlint missing, skipping doc lint");
            return;
        }
    }
    assert!(out.status.success());
}
