use std::process::Command;

#[test]
fn markdown_hygiene() {
    let output = Command::new("python3")
        .arg("scripts/doc_lint.py")
        .output()
        .expect("failed to run doc_lint script");
    if !output.status.success() {
        let text = String::from_utf8_lossy(&output.stdout);
        if text.contains("markdownlint not found") {
            eprintln!("markdownlint missing; skipping doc lint test");
            return;
        }
        panic!("doc lint failed: {}", text);
    }
}
