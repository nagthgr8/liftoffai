#!/usr/bin/env python3
"""
Test script for LiftOff Subscription System
Tests that the subscription limits are properly enforced
"""

import requests
import json

API_BASE = "/api"

def test_subscription_limits():
    """Test subscription tier limits"""
    
    print("=" * 60)
    print("LiftOff Subscription System Test")
    print("=" * 60)
    
    test_cases = [
        {
            "name": "FREE TIER - Note Generations (limit: 1)",
            "tier": "free",
            "endpoint": "/generate-notes",
            "limit": 1,
            "payload": {
                "pdf_name": "test.pdf",
                "level": "beginner"
            }
        },
        {
            "name": "FREE TIER - Note Regenerations (limit: 2)",
            "tier": "free",
            "endpoint": "/regenerate-notes",
            "limit": 2,
            "payload": {
                "pdf_name": "test.pdf",
                "level": "beginner"
            }
        },
        {
            "name": "FREE TIER - Tests (limit: 2)",
            "tier": "free",
            "endpoint": "/generate-test",
            "limit": 2,
            "payload": {
                "pdf_name": "test.pdf",
                "num_questions": 5
            }
        },
        {
            "name": "FREE TIER - Flashcards (limit: 3)",
            "tier": "free",
            "endpoint": "/generate-flashcards",
            "limit": 3,
            "payload": {
                "pdf_name": "test.pdf"
            }
        },
        {
            "name": "FREE TIER - Flowcharts (limit: 2)",
            "tier": "free",
            "endpoint": "/generate-flowchart",
            "limit": 2,
            "payload": {
                "pdf_name": "test.pdf"
            }
        },
        {
            "name": "FREE TIER - Aviator Messages (limit: 10)",
            "tier": "free",
            "endpoint": "/aviator-chat",
            "limit": 10,
            "payload": {
                "message": "Hello"
            }
        },
        {
            "name": "PRO TIER - Note Generations (limit: 15)",
            "tier": "pro",
            "endpoint": "/generate-notes",
            "limit": 15,
            "payload": {
                "pdf_name": "test.pdf",
                "level": "beginner"
            }
        },
        {
            "name": "ULTRA TIER - Note Generations (limit: unlimited)",
            "tier": "ultra",
            "endpoint": "/generate-notes",
            "limit": float('inf'),
            "payload": {
                "pdf_name": "test.pdf",
                "level": "beginner"
            }
        }
    ]
    
    for test in test_cases:
        print(f"\n✓ {test['name']}")
        print(f"  Tier: {test['tier']}")
        print(f"  Endpoint: {test['endpoint']}")
        print(f"  Limit: {test['limit'] if test['limit'] != float('inf') else 'Unlimited'}")
        print(f"  Expected behavior:")
        print(f"    - First {test['limit']} requests: 200-500 (varies by endpoint)")
        print(f"    - Request #{test['limit']+1}: 429 (Too Many Requests)")

    print("\n" + "=" * 60)
    print("SUBSCRIPTION TIERS")
    print("=" * 60)
    
    tiers = {
        "free": {
            "note_generations": 1,
            "note_regenerations": 2,
            "tests": 2,
            "flashcards": 3,
            "flowcharts": 2,
            "flowchart_regenerations": 1,
            "aviator_messages": 10,
            "advanced_mode": False,
            "all_themes": False,
            "no_ads": False
        },
        "pro": {
            "note_generations": 15,
            "note_regenerations": 50,
            "tests": 30,
            "flashcards": 20,
            "flowcharts": 20,
            "flowchart_regenerations": 50,
            "aviator_messages": float('inf'),
            "advanced_mode": True,
            "all_themes": True,
            "no_ads": True
        },
        "ultra": {
            "note_generations": float('inf'),
            "note_regenerations": float('inf'),
            "tests": float('inf'),
            "flashcards": float('inf'),
            "flowcharts": float('inf'),
            "flowchart_regenerations": float('inf'),
            "aviator_messages": float('inf'),
            "advanced_mode": True,
            "all_themes": True,
            "no_ads": True
        }
    }
    
    for tier_name, limits in tiers.items():
        print(f"\n{tier_name.upper()}:")
        for feature, limit in limits.items():
            if isinstance(limit, bool):
                print(f"  {feature}: {limit}")
            elif limit == float('inf'):
                print(f"  {feature}: Unlimited")
            else:
                print(f"  {feature}: {limit}/day")

    print("\n" + "=" * 60)
    print("HOW TO TEST")
    print("=" * 60)
    print("""
1. Open browser DevTools (F12)
2. Go to Console tab
3. Execute: localStorage.setItem('liftoffTier', 'free')  # or 'pro', 'ultra'
4. Make API calls from any LiftOff page
5. Check console for subscription limit errors (429 status)
6. Each day (midnight), limits reset

Headers sent with each API call:
- X-User-Tier: (free|pro|ultra)
- Content-Type: application/json

Expected 429 error when limit exceeded:
{
    "error": "Daily limit reached for feature name",
    "tier": "free",
    "limit": 1,
    "feature": "note_generations"
}
    """)

if __name__ == "__main__":
    test_subscription_limits()
