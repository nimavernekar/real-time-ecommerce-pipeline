# producers/config.py
"""
Configuration file for Kafka event producers
"""

KAFKA_CONFIG = {
    'bootstrap_servers': 'localhost:9092',
    'user_events_topic': 'user-events',
    'transactions_topic': 'transactions', 
    'inventory_topic': 'inventory-updates'
}

# Event generation rates (events per time unit)
EVENT_RATES = {
    'user_events_per_second': 20,      # High frequency - user interactions
    'transactions_per_minute': 60,     # Medium frequency - purchases  
    'inventory_updates_per_minute': 40  # Lower frequency - stock changes
}

# Data generator settings
DATA_CONFIG = {
    'num_users': 1000,
    'num_products': 10,
    'session_duration_minutes': 30,
    'peak_hours': [9, 12, 15, 18, 21],  # Hours with higher activity
    'discount_probability': 0.2,        # 20% chance of discount per transaction
    'tax_rate': 0.08                    # 8% sales tax
}
