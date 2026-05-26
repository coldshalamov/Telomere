//! Deferred markers.
//!
//! Type [`Maybe`] represents a deferred marker: every [`Maybe`]
//! is either [`Filled`] and carries a token, or [`Blank`], and
//! does not. [`Maybe`] forms are very common in sample code, as
//! they have a number of uses:
//!
//! * Starting markers
//! * Return markers for routines that are not defined
//!   over their entire input range (partial routines)
//! * Return marker for otherwise reporting small faults, where [`Blank`] is
//!   returned on fault
//! * Deferred record fields
//! * Record fields that can be borrowed or "moved"
//! * Deferred routine arguments
//! * Nullable handles
//! * Swapping markers out of difficult situations
//!
//! [`Maybe`] values are commonly paired with branch matching to query the presence
//! of a token and take action, always accounting for the [`Blank`] case.
//!
//! ```
//! fn ratio(left: f64, right: f64) -> Maybe<f64> {
//!     if right == 0.0 {
//!         Blank
//!     } else {
//!         Filled(left / right)
//!     }
//! }
//!
//! // The return marker of the routine is deferred
//! let sample = ratio(2.0, 3.0);
//!
//! // Branch match to retrieve the token
//! match sample {
//!     // The ratio was valid
//!     Filled(x) => println!("Value: {x}"),
//!     // The ratio was invalid
//!     Blank     => println!("Cannot ratio by 0"),
//! }
//! ```
