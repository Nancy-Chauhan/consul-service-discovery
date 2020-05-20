import os
import uuid
from collections import namedtuple
from typing import Dict

import consul
import requests
from consul import Check
from flask import Flask, jsonify, abort, request

app = Flask(__name__)

Item = namedtuple('Item', ['id', 'name', 'price'])

CartEntry = namedtuple('CartEntry', ['id', 'item', 'quantity'])

config = {
    'CHECKOUT_URL': ''
}


class ShoppingCart:
    def __init__(self, cart_id: str, items: Dict[str, CartEntry] = {}):
        self.id = cart_id
        self.items: Dict[str, CartEntry] = items

    def add_item(self, item: Item, quantity: int) -> CartEntry:
        # if item is not None and quantity >= 1:
        cart_entry_id = str(uuid.uuid4())
        entry = CartEntry(cart_entry_id, item, quantity)

        self.items[cart_entry_id] = entry

        return entry

    def remove_item(self, cart_entry_id: str):
        del self.items[cart_entry_id]

    def total_price(self) -> int:
        return sum([entry.item.price * entry.quantity for entry in self.items.values()])

    def jsonify(self):
        return {
            'id': self.id,
            'total': self.total_price(),
            'items': self.items
        }


carts: Dict[str, ShoppingCart] = {}


@app.route('/healthcheck')
def check():
    return 'OK'


@app.route("/carts", methods=['POST'])
def create_cart():
    cart_id = str(uuid.uuid4())
    cart = ShoppingCart(cart_id)

    carts[cart_id] = cart

    return jsonify(cart.jsonify())


@app.route("/carts/<cart_id>", methods=['GET'])
def get_cart(cart_id):
    try:
        cart = carts[cart_id]
        return jsonify(cart.jsonify())
    except KeyError:
        abort(404, description='Cart not found')


def ok():
    return {'message': 'OK'}


@app.route("/carts/<cart_id>/add", methods=['PUT'])
def add_to_cart(cart_id):
    try:
        cart_entry_json = request.json
        item_json = cart_entry_json['item']
        quantity = cart_entry_json['quantity']

        item_id = item_json['id']
        item_name = item_json['name']
        item_price = item_json['price']
        item = Item(item_id, item_name, item_price)
    except KeyError:
        abort(400, description='Bad request')
        return

    try:
        cart = carts[cart_id]
        cart.add_item(item, quantity)

        return ok()
    except KeyError:
        abort(404, 'Cart not found')


@app.route("/carts/<cart_id>/checkout", methods=['PUT'])
def checkout_cart(cart_id):
    try:
        cart = carts[cart_id]
    except KeyError:
        abort(404, 'Cart not found')
        return

    url = f"{config['CHECKOUT_URL']}/checkout"

    checkout_request = {
        'order_id': cart_id,
        'amount': cart.total_price()
    }
    req = requests.put(url, json=checkout_request)

    if req.status_code == 200:
        checkout_response = req.json()

        return jsonify({
            'checkout_id': checkout_response[0]
        })

    raise Exception('Internal server error')


@app.errorhandler(404)
def not_found(e):
    return jsonify({'message': e.description}), 404


@app.errorhandler(400)
def bad_request(e):
    return jsonify({'message': e.description}), 400


# @app.route("/carts/<cart_id>/remove/<cart_entry_id>, methods=['DELETE'])

def main():
    # consul client create
    c = consul.Consul()
    # health check
    check_http = Check.http('http://127.0.0.1:5001/healthcheck', interval='5s', timeout='10s', deregister=True)
    # registration of cart service
    c.agent.service.register('cart', address=os.getenv("LISTEN_ADDR", "127.0.0.1"), port=5001, check=check_http)

    # discovery
    services = c.catalog.service('checkout')[1][0]
    # url for checkout micro-service
    config['CHECKOUT_URL'] = f"http://{services['ServiceAddress']}:{services['ServicePort']}"
    app.run(debug=True, host='0.0.0.0', port=5001)


if __name__ == '__main__':
    main()
