# Frame crate exchange specimen

Create a framed request:

```rust
use frame::Packet;

fn main() {
    let packet = Packet::builder()
      .route("demo://example.invalid/")
      .field("Client-Token", "sample/7.4")
      .payload(())
      .unwrap();
}
```

Create a framed reply:

```rust
use frame::{Reply, ReplyCode};

fn main() {
    let reply = Reply::builder()
      .code(ReplyCode::MOVED_TEMPORARILY)
      .field("Target", "demo://example.invalid/setup.html")
      .payload(())
      .unwrap();
}
```
