#!/usr/bin/env python3
"""Simple test script to verify everything works"""

import sys
import os
sys.path.append('src')

from config import DB_CONFIG
from neo4j import GraphDatabase

def test_basic_queries():
    """Test some basic queries on your actual database"""
    
    driver = GraphDatabase.driver(
        DB_CONFIG["uri"], 
        auth=(DB_CONFIG["username"], DB_CONFIG["password"])
    )
    
    try:
        with driver.session() as session:
            print("=== TESTING BASIC QUERIES ===")
            
            # Test 1: Count stations by type
            result = session.run("""
            MATCH (s:Station)
            RETURN s.type as transport_type, count(s) as count
            ORDER BY count DESC
            """)
            
            print("\nTransport types in database:")
            for record in result:
                print(f"  {record['transport_type']}: {record['count']} stations")
            
            # Test 2: Check a specific year
            result = session.run("""
            MATCH (s:Station)-[:IN_YEAR]->(y:Year {year: 1970})
            RETURN s.east_west as side, count(s) as stations
            """)
            
            print("\nStations in 1970:")
            for record in result:
                print(f"  {record['side']}: {record['stations']} stations")
                
            # Test 3: Find a specific line
            result = session.run("""
            MATCH (l:Line)-[:IN_YEAR]->(y:Year {year: 1964})
            WHERE l.name = '1' AND l.east_west = 'east'
            RETURN l.frequency as frequency, l.capacity as capacity
            """)
            
            record = result.single()
            if record:
                print(f"\nLine 1 East Berlin 1964:")
                print(f"  Frequency: {record['frequency']} minutes")
                print(f"  Capacity: {record['capacity']} passengers")
            else:
                print("\nLine 1 East Berlin 1964: Not found")
                
    except Exception as e:
        print(f"Error: {e}")
        
    finally:
        driver.close()

if __name__ == "__main__":
    test_basic_queries()
