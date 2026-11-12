//! Double-entry value books.
//!
//! Every post records where value came from (debit) and where it goes
//! (credit), in one indivisible entry: the conservation law is that the
//! balance sum over all accounts is zero, checked at any time.
//!
//! Books are `Clone` (the cartesian side of the Clone boundary: copying a
//! book is copying data, not minting a move — move tokens are NOT Clone).

use std::collections::BTreeMap;

pub type Account = u32;

/// One indivisible double-entry post.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Post {
    pub debit: Account,
    pub credit: Account,
    pub amount: u128,
}

#[derive(Clone, Debug, Default, PartialEq, Eq)]
pub struct Books {
    posts: Vec<Post>,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct MalformedPost;

impl Books {
    pub fn new() -> Self {
        Books { posts: Vec::new() }
    }

    /// Post one double-entry move. A zero amount is malformed (refused).
    pub fn post(&mut self, debit: Account, credit: Account, amount: u128) -> Result<(), MalformedPost> {
        if amount == 0 || debit == credit {
            return Err(MalformedPost);
        }
        self.posts.push(Post { debit, credit, amount });
        Ok(())
    }

    pub fn len(&self) -> usize {
        self.posts.len()
    }

    pub fn is_empty(&self) -> bool {
        self.posts.is_empty()
    }

    pub fn posts(&self) -> &[Post] {
        &self.posts
    }

    /// Per-account balances (credits minus debits).
    pub fn balances(&self) -> BTreeMap<Account, i128> {
        let mut b: BTreeMap<Account, i128> = BTreeMap::new();
        for p in &self.posts {
            *b.entry(p.debit).or_insert(0) -= p.amount as i128;
            *b.entry(p.credit).or_insert(0) += p.amount as i128;
        }
        b
    }

    /// The conservation law: total balance over all accounts is zero.
    pub fn conservation_holds(&self) -> bool {
        self.balances().values().sum::<i128>() == 0
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn conservation_and_refusals() {
        let mut b = Books::new();
        assert!(b.post(0, 1, 100).is_ok());
        assert!(b.post(1, 2, 30).is_ok());
        assert!(b.conservation_holds());
        assert_eq!(b.balances()[&0], -100);
        assert_eq!(b.balances()[&2], 30);
        // malformed: zero amount and self-post refused
        assert_eq!(b.post(1, 2, 0), Err(MalformedPost));
        assert_eq!(b.post(1, 1, 5), Err(MalformedPost));
        assert_eq!(b.len(), 2);
        // books are Clone (the Clone boundary's cartesian side)
        let c = b.clone();
        assert_eq!(b, c);
    }
}
