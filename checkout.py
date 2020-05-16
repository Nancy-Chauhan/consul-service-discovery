import uuid
from collections import namedtuple
from typing import Dict

from flask import Flask, request, abort, jsonify

app = Flask(__name__)

Checkout = namedtuple('Checkout', ['id', 'order_id', 'amount'])

checkouts: Dict[str, Checkout] = {}


@app.route('/checkout', methods=["PUT"])
def checkout_order():
    checkout_request = request.json

    try:
        order_id = checkout_request['order_id']
        amount = checkout_request['amount']
    except KeyError:
        abort(400, description='Bad request')
        return

    if order_id in checkouts:
        existing_checkout = checkouts[order_id]

        if amount != existing_checkout.amount:
            abort(400, description='Conflict')

        return jsonify(existing_checkout)

    checkout_id = str(uuid.uuid4())
    checkout = Checkout(checkout_id, order_id, amount)

    checkouts[order_id] = checkout

    return jsonify(checkout)


@app.errorhandler(400)
def bad_request(e):
    return jsonify({'message': e.description}), 400


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
