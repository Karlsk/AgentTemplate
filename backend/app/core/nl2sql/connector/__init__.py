"""Auto-register all built-in database connectors."""

from app.core.nl2sql.connector import factory
from app.core.nl2sql.connector.clickhouse import ClickHouseConnector
from app.core.nl2sql.connector.dameng import DamengConnector
from app.core.nl2sql.connector.doris import DorisConnector
from app.core.nl2sql.connector.elasticsearch import ElasticsearchConnector
from app.core.nl2sql.connector.kingbase import KingbaseConnector
from app.core.nl2sql.connector.mysql import MySQLConnector
from app.core.nl2sql.connector.oracle import OracleConnector
from app.core.nl2sql.connector.postgres import PostgreSQLConnector
from app.core.nl2sql.connector.redshift import RedshiftConnector
from app.core.nl2sql.connector.sqlserver import SQLServerConnector
from app.core.nl2sql.connector.starrocks import StarRocksConnector

factory.register(MySQLConnector())
factory.register(PostgreSQLConnector())
factory.register(OracleConnector())
factory.register(SQLServerConnector())
factory.register(ClickHouseConnector())
factory.register(DamengConnector())
factory.register(DorisConnector())
factory.register(StarRocksConnector())
factory.register(KingbaseConnector())
factory.register(RedshiftConnector())
factory.register(ElasticsearchConnector())
