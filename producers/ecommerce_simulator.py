
import json
import random
import time
from datetime import datetime, timedelta
from faker import Faker
from kafka import KafkaProducer
import uuid
import threading
from dataclasses import dataclass, asdict
from typing import Dict, List
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

fake = Faker()

@dataclass
class Product:
    product_id: str
    name: str
    category: str
    price: float
    brand: str
    
@dataclass 
class User:
    user_id: str
    email: str
    age: int
    gender: str
    location: str
    signup_date: str

class ECommerceDataGenerator:
    def __init__(self):
        # Sample products database
        self.products = [
            Product("P001", "iPhone 15 Pro", "Electronics", 999.99, "Apple"),
            Product("P002", "Nike Air Max", "Shoes", 129.99, "Nike"),
            Product("P003", "Sony WH-1000XM4", "Electronics", 349.99, "Sony"),
            Product("P004", "Levi's 501 Jeans", "Clothing", 89.99, "Levi's"),
            Product("P005", "MacBook Pro M3", "Electronics", 1999.99, "Apple"),
            Product("P006", "Adidas Ultraboost", "Shoes", 179.99, "Adidas"),
            Product("P007", "Samsung Galaxy S24", "Electronics", 799.99, "Samsung"),
            Product("P008", "The North Face Jacket", "Clothing", 299.99, "The North Face"),
            Product("P009", "Kindle Paperwhite", "Electronics", 139.99, "Amazon"),
            Product("P010", "Instant Pot", "Home & Kitchen", 79.99, "Instant Pot")
        ]
        
        # Sample users database  
        self.users = []
        for i in range(1000):  # Generate 1000 users
            self.users.append(User(
                user_id=f"U{i:04d}",
                email=fake.email(),
                age=random.randint(18, 65),
                gender=random.choice(["M", "F", "Other"]),
                location=fake.city(),
                signup_date=fake.date_between(start_date="-2y", end_date="today").isoformat()
            ))
    
    def generate_user_event(self) -> Dict:
        """Generate user behavior events"""
        user = random.choice(self.users)
        product = random.choice(self.products)
        
        event_types = ["page_view", "product_view", "add_to_cart", "remove_from_cart", "search"]
        event_type = random.choice(event_types)
        
        base_event = {
            "event_id": str(uuid.uuid4()),
            "user_id": user.user_id,
            "event_type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "session_id": f"session_{random.randint(1000, 9999)}",
            "ip_address": fake.ipv4(),
            "user_agent": fake.user_agent()
        }
        
        if event_type in ["product_view", "add_to_cart", "remove_from_cart"]:
            base_event.update({
                "product_id": product.product_id,
                "product_name": product.name,
                "category": product.category,
                "price": product.price,
                "brand": product.brand
            })
        
        if event_type == "search":
            search_terms = ["laptop", "shoes", "headphones", "jeans", "jacket", "phone"]
            base_event["search_query"] = random.choice(search_terms)
            base_event["results_count"] = random.randint(0, 100)
        
        return base_event
    
    def generate_transaction_event(self) -> Dict:
        """Generate purchase transaction events"""
        user = random.choice(self.users)
        
        # Random number of items in transaction (1-5)
        num_items = random.randint(1, 5)
        items = random.sample(self.products, num_items)
        
        transaction = {
            "transaction_id": str(uuid.uuid4()),
            "user_id": user.user_id,
            "event_type": "purchase",
            "timestamp": datetime.utcnow().isoformat(),
            "payment_method": random.choice(["credit_card", "debit_card", "paypal", "apple_pay"]),
            "shipping_address": {
                "street": fake.street_address(),
                "city": fake.city(),
                "state": fake.state(),
                "zip_code": fake.zipcode(),
                "country": "USA"
            },
            "items": [],
            "total_amount": 0,
            "discount_amount": 0,
            "tax_amount": 0,
            "shipping_cost": random.choice([0, 9.99, 19.99])
        }
        
        total = 0
        for item in items:
            quantity = random.randint(1, 3)
            item_total = item.price * quantity
            total += item_total
            
            transaction["items"].append({
                "product_id": item.product_id,
                "product_name": item.name,
                "category": item.category,
                "price": item.price,
                "quantity": quantity,
                "item_total": item_total,
                "brand": item.brand
            })
        
        # Add discount (20% chance)
        if random.random() < 0.2:
            transaction["discount_amount"] = round(total * 0.1, 2)  # 10% discount
        
        transaction["tax_amount"] = round(total * 0.08, 2)  # 8% tax
        transaction["total_amount"] = round(
            total - transaction["discount_amount"] + 
            transaction["tax_amount"] + transaction["shipping_cost"], 2
        )
        
        return transaction
    
    def generate_inventory_event(self) -> Dict:
        """Generate inventory update events"""
        product = random.choice(self.products)
        
        return {
            "event_id": str(uuid.uuid4()),
            "event_type": "inventory_update",
            "product_id": product.product_id,
            "product_name": product.name,
            "category": product.category,
            "stock_change": random.randint(-50, 100),  # Can be negative (sold) or positive (restocked)
            "current_stock": random.randint(0, 1000),
            "warehouse_location": random.choice(["NYC", "LA", "CHI", "MIA", "SEA"]),
            "timestamp": datetime.utcnow().isoformat(),
            "updated_by": f"system_user_{random.randint(1, 10)}"
        }

class KafkaEventProducer:
    def __init__(self, bootstrap_servers: str = "localhost:9092"):
        self.bootstrap_servers = bootstrap_servers
        self.producer = None
        self.data_generator = ECommerceDataGenerator()
        self.running = False
        
    def connect(self):
        """Initialize Kafka producer"""
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8'),
                key_serializer=lambda k: str(k).encode('utf-8') if k else None,
                acks='all',  # Wait for all replicas to acknowledge
                retries=3,
                batch_size=16384,
                linger_ms=10,  # Wait up to 10ms to batch messages
                buffer_memory=33554432,
                max_request_size=1048576
            )
            logger.info("Connected to Kafka successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Kafka: {e}")
            return False
    
    def send_event(self, topic: str, event: Dict, key: str = None):
        """Send single event to Kafka topic"""
        try:
            future = self.producer.send(topic, value=event, key=key)
            # Don't wait for each message in high-throughput scenarios
            return True
        except Exception as e:
            logger.error(f"Failed to send event to {topic}: {e}")
            return False
    
    def produce_user_events(self, events_per_second: int = 10):
        """Producer thread for user behavior events"""
        logger.info(f"Starting user events producer: {events_per_second} events/sec")
        
        while self.running:
            try:
                event = self.data_generator.generate_user_event()
                self.send_event("user-events", event, event["user_id"])
                
                # Control rate
                time.sleep(1.0 / events_per_second)
                
            except Exception as e:
                logger.error(f"Error in user events producer: {e}")
                time.sleep(1)
    
    def produce_transactions(self, transactions_per_minute: int = 30):
        """Producer thread for transaction events"""
        logger.info(f"Starting transaction producer: {transactions_per_minute} transactions/min")
        
        while self.running:
            try:
                transaction = self.data_generator.generate_transaction_event()
                self.send_event("transactions", transaction, transaction["user_id"])
                
                # Control rate (convert per minute to seconds)
                time.sleep(60.0 / transactions_per_minute)
                
            except Exception as e:
                logger.error(f"Error in transaction producer: {e}")
                time.sleep(1)
    
    def produce_inventory_updates(self, updates_per_minute: int = 20):
        """Producer thread for inventory events"""
        logger.info(f"Starting inventory producer: {updates_per_minute} updates/min")
        
        while self.running:
            try:
                inventory_event = self.data_generator.generate_inventory_event()
                self.send_event("inventory-updates", inventory_event, inventory_event["product_id"])
                
                # Control rate
                time.sleep(60.0 / updates_per_minute)
                
            except Exception as e:
                logger.error(f"Error in inventory producer: {e}")
                time.sleep(1)
    
    def start_production(self, user_events_per_sec=10, transactions_per_min=30, inventory_per_min=20):
        """Start all producer threads"""
        if not self.connect():
            logger.error("Failed to connect to Kafka. Exiting.")
            return
        
        self.running = True
        
        # Start producer threads
        threads = [
            threading.Thread(target=self.produce_user_events, args=(user_events_per_sec,)),
            threading.Thread(target=self.produce_transactions, args=(transactions_per_min,)),
            threading.Thread(target=self.produce_inventory_updates, args=(inventory_per_min,))
        ]
        
        for thread in threads:
            thread.daemon = True
            thread.start()
        
        logger.info("🚀 All producers started! Generating events...")
        logger.info(f"📊 Rates: {user_events_per_sec} user events/sec, {transactions_per_min} transactions/min, {inventory_per_min} inventory updates/min")
        
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutting down producers...")
            self.running = False
            if self.producer:
                self.producer.close()

if __name__ == "__main__":
    # Create producer instance
    producer = KafkaEventProducer()
    
    # Start generating events
    # Adjust rates as needed: (user_events_per_sec, transactions_per_min, inventory_per_min)
    producer.start_production(user_events_per_sec=20, transactions_per_min=60, inventory_per_min=40)
