#!/usr/bin/env python3
"""
test_cache_performance.py - Test availability service with Redis caching
Keep it simple for direct before/after comparison
"""

from locust import HttpUser, task, between, events
import random
import time
from datetime import datetime

# Spaces from baseline population
EXISTING_SPACES = [
    "Library-101", "Library-102", "Library-103",
    "Engineering-101", "Engineering-102", "Engineering-103",
    "Science-101", "Science-102", "Science-103",
    "Business-101", "Business-102", "Business-103",
    "Arts-101", "Arts-102", "Arts-103"
]

# Track cache behavior
cache_hits = {"first_access": [], "repeat_access": []}

class SpaceReadUser(HttpUser):
    """Simple user that reads space data"""
    
    wait_time = between(1, 2)
    
    def on_start(self):
        """Track spaces this user has already viewed (simulates cache hits)"""
        self.viewed_spaces = set()
    
    @task(80)
    def get_space_by_id(self):
        """Main task - get space details"""
        space_id = random.choice(EXISTING_SPACES)
        
        # Track if this should be a cache hit
        is_repeat = space_id in self.viewed_spaces
        start_time = time.time()
        
        response = self.client.get(
            f"/space/{space_id}", 
            name="/space/:id"
        )
        
        response_time = (time.time() - start_time) * 1000  # Convert to ms
        
        # Track response times for cache analysis
        if response.status_code == 200:
            if is_repeat:
                cache_hits["repeat_access"].append(response_time)
            else:
                cache_hits["first_access"].append(response_time)
                self.viewed_spaces.add(space_id)
    
    @task(20)
    def get_popular_spaces(self):
        """Simulate cache-friendly pattern - some spaces are accessed more"""
        # Popular spaces (should have high cache hit rate)
        popular = ["Library-101", "Engineering-101", "Science-101"]
        space_id = random.choice(popular)
        
        self.client.get(f"/space/{space_id}", name="/space/:id (popular)")

class BurstUser(HttpUser):
    """Simulates burst traffic to test cache under load"""
    
    wait_time = between(0.1, 0.5)  # Faster requests
    weight = 1  # Less common than regular users
    
    @task
    def rapid_lookups(self):
        """Quick succession of lookups (tests cache performance)"""
        # Same space multiple times (should be cached after first)
        space_id = random.choice(EXISTING_SPACES[:5])  # Focus on fewer spaces
        
        for _ in range(3):
            self.client.get(f"/space/{space_id}", name="/space/:id (burst)")

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    print("\n" + "="*60)
    print("CACHE PERFORMANCE TEST")
    print("="*60)
    print("Testing with Redis caching enabled")
    print(f"Target spaces: {len(EXISTING_SPACES)} spaces")
    print("Compare these results with non-cache baseline")
    print("="*60 + "\n")

@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    print("\n" + "="*60)
    print("CACHE PERFORMANCE SUMMARY")
    print("="*60)
    
    if cache_hits["first_access"] and cache_hits["repeat_access"]:
        avg_first = sum(cache_hits["first_access"]) / len(cache_hits["first_access"])
        avg_repeat = sum(cache_hits["repeat_access"]) / len(cache_hits["repeat_access"])
        
        print(f"First access (cache miss) avg: {avg_first:.2f}ms")
        print(f"Repeat access (cache hit) avg: {avg_repeat:.2f}ms")
        print(f"Cache speedup: {avg_first/avg_repeat:.1f}x faster")
    
    print("\nCompare with baseline results to measure improvement")
    print("="*60)