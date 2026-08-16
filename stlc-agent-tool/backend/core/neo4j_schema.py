import logging
from neo4j import GraphDatabase
from backend.core.config import settings

logger = logging.getLogger(__name__)

# Cypher commands to ensure uniqueness constraints idempotently
CONSTRAINTS = [
    "CREATE CONSTRAINT req_id IF NOT EXISTS FOR (r:Requirement) REQUIRE r.id IS UNIQUE",
    "CREATE CONSTRAINT jira_id IF NOT EXISTS FOR (j:JiraStory) REQUIRE j.jira_id IS UNIQUE",
    "CREATE CONSTRAINT pw_hash IF NOT EXISTS FOR (p:PlaywrightScript) REQUIRE p.hash IS UNIQUE",
    "CREATE CONSTRAINT test_filename IF NOT EXISTS FOR (t:TestResult) REQUIRE t.file_name IS UNIQUE",
    "CREATE CONSTRAINT proj_name IF NOT EXISTS FOR (p:Project) REQUIRE p.name IS UNIQUE",
    "CREATE CONSTRAINT skill_id IF NOT EXISTS FOR (s:Skill) REQUIRE s.id IS UNIQUE",
]

def apply_schema():
    """
    Connects to Neo4j and applies idempotent constraints.
    """
    uri = settings.NEO4J_URI
    user = settings.NEO4J_USER
    password = settings.NEO4J_PASSWORD
    
    logger.info("Applying Neo4j schema constraints...")
    
    try:
        driver = GraphDatabase.driver(uri, auth=(user, password))
        with driver.session() as session:
            for query in CONSTRAINTS:
                session.run(query)
                logger.info(f"Executed: {query}")
        driver.close()
        logger.info("Neo4j schema constraints applied successfully.")
    except Exception as e:
        logger.error(f"Failed to apply Neo4j schema: {e}")
        raise

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    apply_schema()
