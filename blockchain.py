import hashlib
import json
from textwrap import dedent
from time import time
from uuid import uuid4
from flask import Flask, jsonify, request
from urllib.parse import urlparse
import requests


class Blockchain(object):
  def __init__(self):
    self.chain = []
    self.current_transactions = []
    self.nodes = set()

    #Create Genesis Block
    self.new_block(previous_hash=1, proof=100)

  def new_block(self, proof, previous_hash=None):
    """
    Create a new Block in the Blockchain
    :param proof: <int> The proof given by the Proof of Work algorithm
    :param previous_hash: (Optional) <str> Hash of previous Block
    :return: <dict> New Block
    """

    block = {
      'index': len(self.chain) + 1,
      'timestamp': time(),
      'transactions': self.current_transactions,
      'proof': proof,
      'previous_hash': previous_hash or self.hash(self.chain[-1])

    }

    #Reset current list of transactions
    self.current_transactions = []

    self.chain.append(block)
    return block

  def new_transaction(self, sender, recipient, amount):
    """
    Creates a new transaction to go into the next mined Block
    :param sender: <str> Address of the Sender
    :param recipient: <str> Address of the Recipient
    :param amount: <int> Amount
    :return: <int> The index of the Block that will hold this transaction
    """

    self.current_transactions.append({
      'sender': sender,
      'recipient': recipient,
      'amount': amount
    })

    return self.last_block['index'] + 1

  def proof_of_work(self, last_proof):
    """
    Simple Proof of Work Algorithm:
     - Find a number p' such that hash(pp') contains leading 4 zeroes, where p is the previous p'
     - p is the previous proof, and p' is the new proof
    :param last_proof: <int>
    :return: <int>
    """

    proof=0
    while self.valid_proof(last_proof, proof) is False:
      proof+=1
    return proof

  @staticmethod
  def valid_proof(last_proof, proof):
    """
    Validates the Proof: Does hash(last_proof, proof) contain 4 leading zeroes?
    :param last_proof: <int> Previous Proof
    :param proof: <int> Current Proof
    :return: <bool> True if correct, False if not.
    """
    guess = "{}".format(last_proof * proof).encode()
    guess_hash = hashlib.sha256(guess).hexdigest()
    return guess_hash[:4] == "0000"

  @staticmethod
  def hash(block):
    """
    Creates a SHA-256 hash of a Block
    :param block: <dict> Block
    :return: <str>
    """

    # Dictionary keys have to be ordered so that every hash gives same output
    block_string = json.dumps(block, sort_keys=True).encode()
    return hashlib.sha256(block_string).hexdigest()

  def register_node(self, address):
    """
    Add a new node to the list of nodes
    :param address: <str> Address of node. Eg. 'http://192.168.0.5:5000'
    :return: None
    """

    parsed_url = urlparse(address)
    self.nodes.add(parsed_url.netloc)

  def valid_chain(self, chain):
    """
    determine if chain is valid
    :param chain: <list> A blockchain
    :return: <bool> True if valid, False if not
    """
    last_block = chain[0]
    current_index = 1
    while current_index < len(chain):
        block = chain[current_index]
        print('{}'.format(last_block))
        print('{}'.format(block))
        print("\n-----------\n")
        # Check that the hash of the block is correct
        if block['previous_hash'] != self.hash(last_block):
            return False

        # Check that the Proof of Work is correct
        if not self.valid_proof(last_block['proof'], block['proof']):
            return False

        last_block = block
        current_index += 1

    return True

  def resolve_conflicts(self):
    """
    Consensus algo to update chain to use longest chain in the network
    :return: <bool> True if our chain was replaced, False if not
    """
    neighbors = self.nodes
    new_chain = None
    #looking for chains longer than us
    max_length = len(self.chain)
    # Grab and verify the chains from all the nodes in our network
    for node in neighbours:
      response = requests.get(f'http://{node}/chain')
      if response.status_code == 200:
        length = response.json()['length']
        chain = response.json()['chain']
        # Check if the length is longer and the chain is valid
        if length > max_length and self.valid_chain(chain):
          max_length = length
          new_chain = chain
    # if there was a chain longer than ours, new chain will be True. update our chain
    if new_chain:
      self.chain = new_chain
      return True
    # otherwise ours is longer, return False
    return False

  @property
  def last_block(self):
    return self.chain[-1]

# instiate node
app = Flask(__name__)

#create uuid for node
node_identifier = str(uuid4()).replace('-', '')

#create Blockchain
blockchain = Blockchain()

@app.route('/mine', methods=['GET'])
def mine():
    """
    three steps
    1) calculate proof of Work
    2) reward miner
    3) create new block and add to chain
    """

    # run proof of work to get proof_of_work
    last_block = blockchain.last_block
    last_proof = last_block['proof']
    proof = blockchain.proof_of_work(last_proof)

    # get reward for calculating
    # sender id of 0 means node was mined
    previous_hash = blockchain.hash(last_block)
    block = blockchain.new_block(proof, previous_hash)
    response = {
        'message': "New Block Forged",
        'index': block['index'],
        'transactions': block['transactions'],
        'proof': block['proof'],
        'previous_hash': block['previous_hash'],
    }
    return jsonify(response), 200

@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    values = request.get_json()

    # define all rquired fields and ensure they are in the request
    required = ['sender', 'recipient', 'amount']
    if not all(k in values for k in required):
      return 'Missing values', 400

    # create new transaction
    index = blockchain.new_transaction(values['sender'], values['recipient'], values['amount'])
    # new transaction returns the block number that the transaction will be added to, ie index
    response = {
      "message": "Transaction will be added to block {}".format(index),
    }
    return jsonify(response), 201

@app.route('/chain', methods=['GET'])
def full_chain():
    response = {
        'chain': blockchain.chain,
        'length': len(blockchain.chain),
    }
    return jsonify(response), 200

@app.route('/nodes/register', methods=['POST'])
def register_nodes():
  values = request.get_json()
  nodes = values.get('nodes')
  if nodes is None:
    return "Error: Please supply a valid list of nodes", 400
  for node in nodes:
    blockchain.register_node(node)
  response = {
    'message': 'New nodes have been added',
    'total_nodes': list(blockchain.nodes),
  }
  return jsonify(response), 201

@app.route('/nodes/resolve', methods=['GET'])
def consensus():
  replaced = blockchain.resolve_conflicts()
  if replaced:
    response = {
        'message': 'Our chain was replaced',
        'new_chain': blockchain.chain
    }
  else:
    response = {
        'message': 'Our chain is authoritative',
        'chain': blockchain.chain
    }
  return jsonify(response), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
