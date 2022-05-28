#!/usr/bin/env python3

import argparse
from collections import defaultdict, deque
from enum import Enum
import time
import socket
import json

team_name = "TABLETURNERS"

# global variables
# positions = defaultdict(int)
# for key in ['BOND', 'VALBZ', 'VALE', 'GS', 'MS', 'WFC', 'XLF']: positions[key] = 0
positions = {s : 0 for s in ['BOND', 'VALBZ', 'VALE', 'GS', 'MS', 'WFC', 'XLF']}


def main():
    # Setup
    args = parse_arguments()
    exchange = ExchangeConnection(args=args)

    # Say hello to the exchange
    hello_message = exchange.read_message()
    print("First message from exchange:", hello_message)

    order_id = 0
    timer_bond = Delaytimer(0.01)

    while True:
        message = exchange.read_message()
        positions_update(positions, message)

        if timer_bond.update():
            # Penny Pinching
            order_id += 1
            exchange.send_add_message(order_id=order_id, symbol="BOND", dir=Dir.BUY, price=999, size=1)
            order_id += 1
            exchange.send_add_message(order_id=order_id, symbol="BOND", dir=Dir.SELL, price=1001, size=1)

            # Modeling ADR with share
            valbz_bid_price = None
            valbz_ask_price = None
            vale_bid_price = None
            vale_ask_price = None
            if message["type"] == "book" and message["symbol"] == "VALBZ":

                def best_price(side):
                    if message[side]:
                        return message[side][0][0]


                valbz_bid_price = best_price("buy")
                valbz_ask_price = best_price("sell")

                # now = time.time()

                # if now > vale_last_print_time + 1:
                #     vale_last_print_time = now
                #     if see_bestprice:
                #         print(
                #             {
                #                 "vale_bid_price": vale_bid_price,
                #                 "vale_ask_price": vale_ask_price,
                #             }
                #         )


            if (valbz_bid_price!=None and
            message["type"] == "book" and message["symbol"] == "VALE"):

                def best_price(side):
                    if message[side]:
                        return message[side][0][0]

                vale_bid_price = best_price("buy")
                vale_ask_price = best_price("sell")


                # now = time.time()
                valbz_fairvalue = (valbz_bid_price + valbz_ask_price) // 2

                # sell at high bid price
                if vale_bid_price > valbz_fairvalue:
                    order_id += 1
                    exchange.send_add_message(order_id=order_id, symbol="VALE",
                     dir=Dir.SELL, price=vale_bid_price, size=1)
                # buy at low bid price
                if vale_ask_price < valbz_fairvalue:
                    order_id += 1
                    exchange.send_add_message(order_id=order_id, symbol="VALE",
                     dir=Dir.BUY, price=vale_ask_price, size=1)
                # if now > vale_last_print_time + 1:
                #     vale_last_print_time = now
                #     if see_bestprice:
                #         print(
                #             {
                #                 "vale_bid_price": vale_bid_price,
                #                 "vale_ask_price": vale_ask_price,
                #             }
                #         )




            # main_debug_print(message, see_bestprice = False)
            if message["type"] == "close":
                print("The round has ended")
                break

def positions_update(positions: dict, message: dict):
    print(message["type"])
    if message["type"] == "fill":
        if message["dir"] == "BUY":
            positions[message["symbol"]] += message["size"]
        elif message["dir"] == "SELL":
            positions[message["symbol"]] -= message["size"]
        print("positions: ", positions)

class Delaytimer:
    def __init__(self, delay):
        self.delay = delay
        self.wait_until = time.time() + self.delay

    def update(self):
        if self.wait_until < time.time():
            self.wait_until = time.time() + self.delay
            return True
        return False

def main_debug_print(message, see_bestprice):
    vale_bid_price, vale_ask_price = None, None
    vale_last_print_time = time.time()
    # Some of the message types below happen infrequently and contain
    # important information to help you understand what your bot is doing,
    # so they are printed in full. We recommend not always printing every
    # message because it can be a lot of information to read. Instead, let
    # your code handle the messages and just print the information
    # important for you!
    if message["type"] == "close":
        print("The round has ended")
    elif message["type"] == "error":
        print(message)
    elif message["type"] == "reject":
        print(message)
    elif message["type"] == "fill":
        print(message)
    elif message["type"] == "book":
        if message["symbol"] == "VALE":

            def best_price(side):
                if message[side]:
                    return message[side][0][0]

            vale_bid_price = best_price("buy")
            vale_ask_price = best_price("sell")

            now = time.time()

            if now > vale_last_print_time + 1:
                vale_last_print_time = now
                if see_bestprice:
                    print(
                        {
                            "vale_bid_price": vale_bid_price,
                            "vale_ask_price": vale_ask_price,
                        }
                    )


# ~~~~~============== PROVIDED CODE ==============~~~~~

# You probably don't need to edit anything below this line, but feel free to
# ask if you have any questions about what it is doing or how it works. If you
# do need to change anything below this line, please feel free to


class Dir(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class ExchangeConnection:
    def __init__(self, args):
        self.message_timestamps = deque(maxlen=500)
        self.exchange_hostname = args.exchange_hostname
        self.port = args.port
        self.exchange_socket = self._connect(add_socket_timeout=args.add_socket_timeout)

        self._write_message({"type": "hello", "team": team_name.upper()})

    def read_message(self):
        """Read a single message from the exchange"""
        message = json.loads(self.exchange_socket.readline())
        if "dir" in message:
            message["dir"] = Dir(message["dir"])
        return message

    def send_add_message(
        self, order_id: int, symbol: str, dir: Dir, price: int, size: int
    ):
        """Add a new order"""
        self._write_message(
            {
                "type": "add",
                "order_id": order_id,
                "symbol": symbol,
                "dir": dir,
                "price": price,
                "size": size,
            }
        )

    def send_convert_message(self, order_id: int, symbol: str, dir: Dir, size: int):
        """Convert between related symbols"""
        self._write_message(
            {
                "type": "convert",
                "order_id": order_id,
                "symbol": symbol,
                "dir": dir,
                "size": size,
            }
        )

    def send_cancel_message(self, order_id: int):
        """Cancel an existing order"""
        self._write_message({"type": "cancel", "order_id": order_id})

    def _connect(self, add_socket_timeout):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        if add_socket_timeout:
            # Automatically raise an exception if no data has been recieved for
            # multiple seconds. This should not be enabled on an "empty" test
            # exchange.
            s.settimeout(5)
        s.connect((self.exchange_hostname, self.port))
        return s.makefile("rw", 1)

    def _write_message(self, message):
        json.dump(message, self.exchange_socket)
        self.exchange_socket.write("\n")

        now = time.time()
        self.message_timestamps.append(now)
        if len(
            self.message_timestamps
        ) == self.message_timestamps.maxlen and self.message_timestamps[0] > (now - 1):
            print(
                "WARNING: You are sending messages too frequently. The exchange will start ignoring your messages. Make sure you are not sending a message in response to every exchange message."
            )


def parse_arguments():
    test_exchange_port_offsets = {"prod-like": 0, "slower": 1, "empty": 2}

    parser = argparse.ArgumentParser(description="Trade on an ETC exchange!")
    exchange_address_group = parser.add_mutually_exclusive_group(required=True)
    exchange_address_group.add_argument(
        "--production", action="store_true", help="Connect to the production exchange."
    )
    exchange_address_group.add_argument(
        "--test",
        type=str,
        choices=test_exchange_port_offsets.keys(),
        help="Connect to a test exchange.",
    )

    # Connect to a specific host. This is only intended to be used for debugging.
    exchange_address_group.add_argument(
        "--specific-address", type=str, metavar="HOST:PORT", help=argparse.SUPPRESS
    )

    args = parser.parse_args()
    args.add_socket_timeout = True

    if args.production:
        args.exchange_hostname = "production"
        args.port = 25000
    elif args.test:
        args.exchange_hostname = "test-exch-" + team_name
        args.port = 25000 + test_exchange_port_offsets[args.test]
        if args.test == "empty":
            args.add_socket_timeout = False
    elif args.specific_address:
        args.exchange_hostname, port = args.specific_address.split(":")
        args.port = int(port)

    return args


if __name__ == "__main__":
    # Check that [team_name] has been updated.
    assert (
        team_name != "REPLACEME"
    ), "Please put your team name in the variable [team_name]."

    main()
