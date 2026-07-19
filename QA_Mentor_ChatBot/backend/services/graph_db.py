from neo4j import GraphDatabase
from core.config import settings

_driver = None

def get_neo4j_driver():
    global _driver
    if _driver is None:
        try:
            _driver = GraphDatabase.driver(
                settings.neo4j_uri,
                auth=(settings.neo4j_user, settings.neo4j_password)
            )
            _driver.verify_connectivity()
        except Exception as e:
            _driver = None
    return _driver

def close_neo4j_driver():
    global _driver
    if _driver is not None:
        _driver.close()
        _driver = None
