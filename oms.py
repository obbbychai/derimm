from dataclasses import dataclass
from typing import Dict, List
import heapq

@dataclass
class Order:
    id: str
    price: float
    quantity: int
    side: str  # 'buy' or 'sell'
    timestamp: float
    instrument_name: str
    status: str = 'pending'
    
    def __lt__(self, other):
        # For priority queue ordering
        return self.timestamp < other.timestamp

class PendingOrderTracker:
    def __init__(self):
        self.orders: Dict[str, Order] = {}  # Fast lookup by order ID
        self.buy_orders: List[Order] = []   # Priority queue for buy orders
        self.sell_orders: List[Order] = []  # Priority queue for sell orders

    def add_order(self, order: Order):
        self.orders[order.id] = order
        if order.side == 'buy':
            heapq.heappush(self.buy_orders, (-order.price, order))
            print(f"buy {order}")
        else:
            heapq.heappush(self.sell_orders, (order.price, order))
            print(f"sell {order}")

    def remove_order(self, order_id: str) -> Order:
        order = self.orders.pop(order_id, None)
        if order:
            if order.side == 'buy':
                self.buy_orders = [o for o in self.buy_orders if o[1].id != order_id]
                heapq.heapify(self.buy_orders)
            else:
                self.sell_orders = [o for o in self.sell_orders if o[1].id != order_id]
                heapq.heapify(self.sell_orders)
        return order

    def get_order(self, order_id: str) -> Order:
        return self.orders.get(order_id)

    def update_order(self, order_id: str, **kwargs):
        if order_id in self.orders:
            for key, value in kwargs.items():
                setattr(self.orders[order_id], key, value)
                print("orderid", order_id)

    def get_best_buy_order(self) -> Order:
        while self.buy_orders:
            _, order = self.buy_orders[0]
            if order.id in self.orders:
                return order
            heapq.heappop(self.buy_orders)  # Remove stale entry
        return None

    def get_best_sell_order(self) -> Order:
        while self.sell_orders:
            _, order = self.sell_orders[0]
            if order.id in self.orders:
                return order
            heapq.heappop(self.sell_orders)  # Remove stale entry
        return None

    def get_all_pending_orders(self) -> List[Order]:
        return list(self.orders.values())

    def get_pending_buy_orders(self) -> List[Order]:
        return [order for _, order in self.buy_orders if order.id in self.orders]

    def get_pending_sell_orders(self) -> List[Order]:
        return [order for _, order in self.sell_orders if order.id in self.orders]
    
    def print_buy_orders(self):
        print("Current Buy Orders:")
        for order in self.get_pending_buy_orders():
            print(f"Order ID: {order.id}, Price: {order.price}, Quantity: {order.quantity}, Status: {order.status}")

    def print_sell_orders(self):
        print("Current Sell Orders:")
        for order in self.get_pending_sell_orders():
            print(f"Order ID: {order.id}, Price: {order.price}, Quantity: {order.quantity}, Status: {order.status}")