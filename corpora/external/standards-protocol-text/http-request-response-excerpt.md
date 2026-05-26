# HTTP crate request/response excerpt

Create an HTTP request:

```rust
use http::Request;

fn main() {
    let request = Request::builder()
      .uri("https://www.rust-lang.org/")
      .header("User-Agent", "awesome/1.0")
      .body(())
      .unwrap();
}
```

Create an HTTP response:

```rust
use http::{Response, StatusCode};

fn main() {
    let response = Response::builder()
      .status(StatusCode::MOVED_PERMANENTLY)
      .header("Location", "https://www.rust-lang.org/install.html")
      .body(())
      .unwrap();
}
```
