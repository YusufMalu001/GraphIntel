import os
import glob
import csv
import json
from collections import defaultdict
from tqdm import tqdm
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()

def batched(iterable, n):
    batch = []
    for item in iterable:
        batch.append(item)
        if len(batch) == n:
            yield batch
            batch = []
    if batch:
        yield batch

def load_graph():
    uri = os.getenv("NEO4J_URI", "neo4j+s://xxxx.databases.neo4j.io")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "password")
    
    driver = GraphDatabase.driver(
        uri, 
        auth=(user, password),
        max_connection_lifetime=3600
    )
    
    total_nodes = 0
    total_rels = 0
    node_types = set()
    
    # Check if Outputs CSVs exist
    node_files = glob.glob("Outputs/Node_*.csv")
    edge_files = glob.glob("Outputs/Edge_*.csv")
    
    if node_files and edge_files:
        print("Found processed CSV files in Outputs/ directory.")
        
        # Process Nodes
        for file in node_files:
            node_type = os.path.basename(file).replace("Node_", "").replace(".csv", "")
            node_types.add(node_type)
            
            with open(file, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                data = list(reader)
                
            if not data: continue
            
            print(f"Loading {node_type} nodes: {len(data)}")
            
            with driver.session() as session:
                for batch in tqdm(batched(data, 500), total=(len(data) + 499) // 500):
                    clean_batch = []
                    for row in batch:
                        name = row.get("name")
                        if not name: continue
                        props = {k: v for k, v in row.items() if v}
                        clean_batch.append({"name": name, "props": props})
                    
                    if not clean_batch: continue
                    
                    query = f"""
                    UNWIND $batch AS item
                    MERGE (n:{node_type} {{name: item.name}})
                    SET n += item.props
                    """
                    session.run(query, batch=clean_batch)
                    total_nodes += len(clean_batch)

        # Process Edges
        for file in edge_files:
            with open(file, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                data = list(reader)
                
            if not data: continue
            
            # Determine relation type from file name if not in data
            # Format: Edge_SourceTargetRelation.csv
            rel_type = "RELATED_TO"
            if "Relation" in data[0] and data[0]["Relation"]:
                rel_type = data[0]["Relation"]
            elif "Label" in data[0] and data[0]["Label"]:
                rel_type = data[0]["Label"]
                
            print(f"Loading edges from {os.path.basename(file)}: {len(data)}")
            
            with driver.session() as session:
                for batch in tqdm(batched(data, 500), total=(len(data) + 499) // 500):
                    clean_batch = []
                    for row in batch:
                        source = row.get("Source")
                        target = row.get("Target")
                        rel = row.get("Relation", row.get("Label", rel_type))
                        
                        if source and target and rel:
                            rel = rel.replace(" ", "_").replace("'", "").upper()
                            clean_batch.append({"source": source, "target": target, "rel": rel})
                            
                    if not clean_batch: continue
                    
                    by_rel = defaultdict(list)
                    for item in clean_batch:
                        by_rel[item["rel"]].append(item)
                        
                    for rel, items in by_rel.items():
                        query = f"""
                        UNWIND $items AS item
                        MATCH (a {{name: item.source}}), (b {{name: item.target}})
                        MERGE (a)-[:{rel}]->(b)
                        """
                        session.run(query, items=items)
                        total_rels += len(items)
                        
    else:
        # Fallback to raw JSON if tabular data is missing
        print("No processed CSVs found. Falling back to Data/ScrapedData.json")
        json_file = "Data/ScrapedData.json"
        if os.path.exists(json_file):
            with open(json_file, 'r', encoding='utf-8') as f:
                raw_data = json.load(f)
            # Inline preprocessing would go here...
            print("Warning: Inline processing of raw Scrapy JSON is a fallback and might not match exact schema.")
        else:
            print("No data files found to load.")
            return

    print(f"Loaded {total_nodes} nodes, {total_rels} relationships across {len(node_types)} node types")
    
    with driver.session() as session:
        node_count = session.run("MATCH (n) RETURN count(n) as count").single()["count"]
        print(f"Verified node count in DB: {node_count}")
        
    driver.close()

if __name__ == "__main__":
    load_graph()
