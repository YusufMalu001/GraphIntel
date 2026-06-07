import os
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()
uri = os.getenv('NEO4J_URI')
user = os.getenv('NEO4J_USER')
pw = os.getenv('NEO4J_PASSWORD')
driver = GraphDatabase.driver(uri, auth=(user, pw))

with driver.session() as session:
    res = session.run('MATCH (n) WHERE toString(id(n)) IN ["1239", "1759", "1977", "1137", "1431", "1455", "391", "1987", "1767", "1012", "1074", "1200", "393", "550", "1136", "397", "1415", "971", "1171", "1980"] RETURN n.name')
    print([r['n.name'] for r in res])
