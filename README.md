Implementing a blockchain in python by following article found here

https://hackernoon.com/learn-blockchains-by-building-one-117428612f46

## Things left to consider
- [ ] currently, pow will keep alternating between values of 100 and 9576. Block chain should take into account transcations when creating proof of work so that transactions cannot be edited
- [ ] need to validate user to ensure that user creating transaction is indeed user who owns that currency
  - private / public key pair so user can sign transaction and can be verified
- [ ] how to ensure user was in possession of currency when transaction was created
   - wallets?
   - double spending problem
   
