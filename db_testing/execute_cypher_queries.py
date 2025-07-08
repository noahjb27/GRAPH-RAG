import os
import re
import json
from dotenv import load_dotenv
from neo4j import GraphDatabase
import argparse
import logging

# --- Configuration ---
# Set up basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables from a .env file
load_dotenv()

# --- Database Connection ---
def get_driver():
    """
    Creates and returns a Neo4j driver instance.
    Credentials are fetched from environment variables.
    """
    uri = os.getenv("NEO4J_AURA_URI")
    user = os.getenv("NEO4J_AURA_USERNAME")
    password = os.getenv("NEO4J_AURA_PASSWORD")

    if not all([uri, user, password]):
        logging.error("Missing database credentials. Ensure NEO4J_URI, NEO4J_USERNAME, and NEO4J_PASSWORD are set in your .env file.")
        return None
        
    try:
        driver = GraphDatabase.driver(uri, auth=(user, password))
        driver.verify_connectivity()
        logging.info("Successfully connected to Neo4j database.")
        return driver
    except Exception as e:
        logging.error(f"Failed to connect to Neo4j: {e}")
        return None

# --- Query File Processing ---
def parse_cypher_file(file_path):
    """
    Parses a file containing multiple Cypher queries.
    Queries are expected to be separated by a comment line starting with '--'.
    Each comment is treated as the title for the subsequent query.
    """
    if not os.path.exists(file_path):
        logging.error(f"Query file not found at: {file_path}")
        return []
        
    with open(file_path, 'r') as f:
        content = f.read()

    # Split queries by the comment lines that act as titles
    # A query block starts with '--' and ends before the next '--'
    query_blocks = re.split(r'(^--.*$)', content, flags=re.MULTILINE)[1:]
    
    queries = []
    for i in range(0, len(query_blocks), 2):
        # The title is the captured comment line
        title = query_blocks[i].strip("-- ").strip()
        # The query is the code block that follows
        query_text = query_blocks[i+1].strip()
        
        if query_text:
            queries.append({"title": title, "query": query_text})
            
    logging.info(f"Parsed {len(queries)} queries from {file_path}.")
    return queries

def sanitize_filename(name):
    """Sanitizes a string to be used as a valid filename."""
    name = name.lower()
    name = re.sub(r'[^a-z0-9\s-]', '', name)
    name = re.sub(r'[\s-]+', '_', name)
    return name

# --- Main Execution Logic ---
def execute_and_save_queries(driver, queries, output_dir):
    """
    Executes a list of queries and saves their results to JSON files.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        logging.info(f"Created output directory: {output_dir}")

    with driver.session() as session:
        for i, item in enumerate(queries):
            title = item['title']
            query = item['query']
            filename = f"{i+1:02d}_{sanitize_filename(title)}.json"
            output_path = os.path.join(output_dir, filename)
            
            logging.info(f"Executing query: '{title}'...")
            
            try:
                result = session.run(query)
                # Convert results to a list of dictionaries for JSON serialization
                data = [record.data() for record in result]
                
                with open(output_path, 'w') as f:
                    json.dump(data, f, indent=4, default=str) # Use default=str for complex types
                    
                logging.info(f"Successfully saved results to {output_path}")
                
            except Exception as e:
                logging.error(f"Failed to execute query '{title}': {e}")
                # Create an error file
                error_info = {"error": str(e), "query": query}
                with open(output_path.replace('.json', '_error.json'), 'w') as f:
                    json.dump(error_info, f, indent=4)


def main():
    """
    Main function to orchestrate the script's operations.
    """
    parser = argparse.ArgumentParser(description="Execute Cypher queries from a file and save results to JSON.")
    parser.add_argument("query_file", help="Path to the .cypher file containing the queries.")
    parser.add_argument("output_dir", help="Directory to save the JSON result files.")
    
    args = parser.parse_args()

    driver = get_driver()
    if driver:
        queries = parse_cypher_file(args.query_file)
        if queries:
            execute_and_save_queries(driver, queries, args.output_dir)
        driver.close()
        logging.info("Script finished.")

if __name__ == "__main__":
    main()
