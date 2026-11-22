/// Entry point proven by Stwo. Input `n` and the returned value are public:
/// the proof attests that fib_core::fib(n) evaluated to this output.
#[executable]
fn main(n: u32) -> felt252 {
    fib_core::fib(n)
}
