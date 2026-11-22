/// Returns the n-th Fibonacci number (fib(0) = 0, fib(1) = 1).
/// Arithmetic is done over felt252, so results wrap modulo the Cairo prime
/// for large n. That is fine here: the goal is a computation whose number
/// of execution steps grows linearly with n.
pub fn fib(n: u32) -> felt252 {
    let mut a: felt252 = 0;
    let mut b: felt252 = 1;
    let mut i: u32 = 0;
    while i != n {
        let next = a + b;
        a = b;
        b = next;
        i += 1;
    }
    a
}

#[cfg(test)]
mod tests {
    use super::fib;

    #[test]
    fn known_values() {
        assert_eq!(fib(0), 0);
        assert_eq!(fib(1), 1);
        assert_eq!(fib(2), 1);
        assert_eq!(fib(10), 55);
        assert_eq!(fib(20), 6765);
    }
}
