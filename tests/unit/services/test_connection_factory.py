"""
ConnectionFactory单元测试
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from app.services.connection_factory import ConnectionFactory, MySQLConnection, PostgreSQLConnection, SQLServerConnection, OracleConnection
from app.models.instance import Instance
from app.models.credential import Credential


@pytest.mark.unit
def test_connection_factory_create_mysql_connection():
    """Test creating MySQL connection."""
    # 1. Arrange
    instance = Instance(
        name="test-mysql",
        db_type="mysql",
        host="localhost",
        port=3306,
        database_name="testdb"
    )
    
    # 2. Act
    connection = ConnectionFactory.create_connection(instance)
    
    # 3. Assert
    assert isinstance(connection, MySQLConnection)
    assert connection.instance == instance


@pytest.mark.unit
def test_connection_factory_create_postgresql_connection():
    """Test creating PostgreSQL connection."""
    # 1. Arrange
    instance = Instance(
        name="test-postgres",
        db_type="postgresql",
        host="localhost",
        port=5432,
        database_name="testdb"
    )
    
    # 2. Act
    connection = ConnectionFactory.create_connection(instance)
    
    # 3. Assert
    assert isinstance(connection, PostgreSQLConnection)
    assert connection.instance == instance


@pytest.mark.unit
def test_connection_factory_create_sqlserver_connection():
    """Test creating SQL Server connection."""
    # 1. Arrange
    instance = Instance(
        name="test-sqlserver",
        db_type="sqlserver",
        host="localhost",
        port=1433,
        database_name="testdb"
    )
    
    # 2. Act
    connection = ConnectionFactory.create_connection(instance)
    
    # 3. Assert
    assert isinstance(connection, SQLServerConnection)
    assert connection.instance == instance


@pytest.mark.unit
def test_connection_factory_create_oracle_connection():
    """Test creating Oracle connection."""
    # 1. Arrange
    instance = Instance(
        name="test-oracle",
        db_type="oracle",
        host="localhost",
        port=1521,
        database_name="testdb"
    )
    
    # 2. Act
    connection = ConnectionFactory.create_connection(instance)
    
    # 3. Assert
    assert isinstance(connection, OracleConnection)
    assert connection.instance == instance


@pytest.mark.unit
def test_connection_factory_unsupported_database_type():
    """Test creating connection with unsupported database type."""
    # 1. Arrange
    instance = Instance(
        name="test-unsupported",
        db_type="unsupported",
        host="localhost",
        port=3306,
        database_name="testdb"
    )
    
    # 2. Act & Assert
    with pytest.raises(ValueError):
        ConnectionFactory.create_connection(instance)


@pytest.mark.unit
def test_connection_factory_none_instance():
    """Test creating connection with None instance."""
    # 2. Act & Assert
    with pytest.raises(AttributeError):
        ConnectionFactory.create_connection(None)


@pytest.mark.unit
def test_mysql_connection_init():
    """Test MySQLConnection initialization."""
    # 1. Arrange
    instance = Instance(
        name="test-mysql",
        db_type="mysql",
        host="localhost",
        port=3306,
        database_name="testdb"
    )
    
    # 2. Act
    connection = MySQLConnection(instance)
    
    # 3. Assert
    assert connection.instance == instance
    assert connection.connection is None
    assert connection.is_connected is False
    assert connection.db_logger is not None


@pytest.mark.unit
@patch('app.services.connection_factory.pymysql.connect')
def test_mysql_connection_connect_success(mock_connect):
    """Test MySQL connection success."""
    # 1. Arrange
    instance = Instance(
        name="test-mysql",
        db_type="mysql",
        host="localhost",
        port=3306,
        database_name="testdb"
    )
    
    mock_conn = Mock()
    mock_connect.return_value = mock_conn
    connection = MySQLConnection(instance)
    
    # 2. Act
    result = connection.connect()
    
    # 3. Assert
    assert result is True
    assert connection.is_connected is True
    assert connection.connection == mock_conn
    mock_connect.assert_called_once()


@pytest.mark.unit
@patch('app.services.connection_factory.pymysql.connect')
def test_mysql_connection_connect_failure(mock_connect):
    """Test MySQL connection failure."""
    # 1. Arrange
    instance = Instance(
        name="test-mysql",
        db_type="mysql",
        host="localhost",
        port=3306,
        database_name="testdb"
    )
    
    mock_connect.side_effect = Exception("Connection failed")
    connection = MySQLConnection(instance)
    
    # 2. Act
    result = connection.connect()
    
    # 3. Assert
    assert result is False
    assert connection.is_connected is False
    assert connection.connection is None


@pytest.mark.unit
def test_mysql_connection_disconnect():
    """Test MySQL connection disconnect."""
    # 1. Arrange
    instance = Instance(
        name="test-mysql",
        db_type="mysql",
        host="localhost",
        port=3306,
        database_name="testdb"
    )
    
    connection = MySQLConnection(instance)
    mock_conn = Mock()
    connection.connection = mock_conn
    connection.is_connected = True
    
    # 2. Act
    connection.disconnect()
    
    # 3. Assert
    assert connection.is_connected is False
    mock_conn.close.assert_called_once()


@pytest.mark.unit
def test_mysql_connection_disconnect_no_connection():
    """Test MySQL connection disconnect with no connection."""
    # 1. Arrange
    instance = Instance(
        name="test-mysql",
        db_type="mysql",
        host="localhost",
        port=3306,
        database_name="testdb"
    )
    
    connection = MySQLConnection(instance)
    connection.connection = None
    connection.is_connected = False
    
    # 2. Act
    connection.disconnect()
    
    # 3. Assert
    assert connection.is_connected is False


@pytest.mark.unit
@patch('app.services.connection_factory.pymysql.connect')
def test_mysql_connection_test_connection_success(mock_connect):
    """Test MySQL connection test success."""
    # 1. Arrange
    instance = Instance(
        name="test-mysql",
        db_type="mysql",
        host="localhost",
        port=3306,
        database_name="testdb"
    )
    
    mock_conn = Mock()
    mock_connect.return_value = mock_conn
    connection = MySQLConnection(instance)
    
    # 2. Act
    result = connection.test_connection()
    
    # 3. Assert
    assert result["success"] is True
    assert "连接成功" in result["message"]


@pytest.mark.unit
@patch('app.services.connection_factory.pymysql.connect')
def test_mysql_connection_test_connection_failure(mock_connect):
    """Test MySQL connection test failure."""
    # 1. Arrange
    instance = Instance(
        name="test-mysql",
        db_type="mysql",
        host="localhost",
        port=3306,
        database_name="testdb"
    )
    
    mock_connect.side_effect = Exception("Connection failed")
    connection = MySQLConnection(instance)
    
    # 2. Act
    result = connection.test_connection()
    
    # 3. Assert
    assert result["success"] is False
    assert "连接失败" in result["message"]


@pytest.mark.unit
@patch('app.services.connection_factory.pymysql.connect')
def test_mysql_connection_execute_query_success(mock_connect):
    """Test MySQL connection execute query success."""
    # 1. Arrange
    instance = Instance(
        name="test-mysql",
        db_type="mysql",
        host="localhost",
        port=3306,
        database_name="testdb"
    )
    
    mock_conn = Mock()
    mock_cursor = Mock()
    mock_cursor.fetchall.return_value = [("result1",), ("result2",)]
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_connect.return_value = mock_conn
    
    connection = MySQLConnection(instance)
    connection.connect()
    
    # 2. Act
    result = connection.execute_query("SELECT * FROM users")
    
    # 3. Assert
    assert result == [("result1",), ("result2",)]
    mock_cursor.execute.assert_called_once_with("SELECT * FROM users", None)


@pytest.mark.unit
@patch('app.services.connection_factory.pymysql.connect')
def test_mysql_connection_execute_query_with_params(mock_connect):
    """Test MySQL connection execute query with parameters."""
    # 1. Arrange
    instance = Instance(
        name="test-mysql",
        db_type="mysql",
        host="localhost",
        port=3306,
        database_name="testdb"
    )
    
    mock_conn = Mock()
    mock_cursor = Mock()
    mock_cursor.fetchall.return_value = [("result1",)]
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_connect.return_value = mock_conn
    
    connection = MySQLConnection(instance)
    connection.connect()
    
    # 2. Act
    result = connection.execute_query("SELECT * FROM users WHERE id = %s", (1,))
    
    # 3. Assert
    assert result == [("result1",)]
    mock_cursor.execute.assert_called_once_with("SELECT * FROM users WHERE id = %s", (1,))


@pytest.mark.unit
@patch('app.services.connection_factory.pymysql.connect')
def test_mysql_connection_execute_query_failure(mock_connect):
    """Test MySQL connection execute query failure."""
    # 1. Arrange
    instance = Instance(
        name="test-mysql",
        db_type="mysql",
        host="localhost",
        port=3306,
        database_name="testdb"
    )
    
    mock_conn = Mock()
    mock_cursor = Mock()
    mock_cursor.execute.side_effect = Exception("Query failed")
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_connect.return_value = mock_conn
    
    connection = MySQLConnection(instance)
    connection.connect()
    
    # 2. Act
    result = connection.execute_query("SELECT * FROM users")
    
    # 3. Assert
    assert result is None


@pytest.mark.unit
@patch('app.services.connection_factory.pymysql.connect')
def test_mysql_connection_get_version_success(mock_connect):
    """Test MySQL connection get version success."""
    # 1. Arrange
    instance = Instance(
        name="test-mysql",
        db_type="mysql",
        host="localhost",
        port=3306,
        database_name="testdb"
    )
    
    mock_conn = Mock()
    mock_cursor = Mock()
    mock_cursor.fetchone.return_value = ("8.0.32",)
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_connect.return_value = mock_conn
    
    connection = MySQLConnection(instance)
    connection.connect()
    
    # 2. Act
    result = connection.get_version()
    
    # 3. Assert
    assert result == "8.0.32"
    mock_cursor.execute.assert_called_once_with("SELECT VERSION()")


@pytest.mark.unit
@patch('app.services.connection_factory.pymysql.connect')
def test_mysql_connection_get_version_failure(mock_connect):
    """Test MySQL connection get version failure."""
    # 1. Arrange
    instance = Instance(
        name="test-mysql",
        db_type="mysql",
        host="localhost",
        port=3306,
        database_name="testdb"
    )
    
    mock_conn = Mock()
    mock_cursor = Mock()
    mock_cursor.execute.side_effect = Exception("Version query failed")
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_connect.return_value = mock_conn
    
    connection = MySQLConnection(instance)
    connection.connect()
    
    # 2. Act
    result = connection.get_version()
    
    # 3. Assert
    assert result is None


@pytest.mark.unit
def test_mysql_connection_with_credential():
    """Test MySQL connection with credential."""
    # 1. Arrange
    credential = Credential(
        name="test-cred",
        credential_type="database",
        username="testuser",
        password="testpass",
        db_type="mysql"
    )
    
    instance = Instance(
        name="test-mysql",
        db_type="mysql",
        host="localhost",
        port=3306,
        database_name="testdb",
        credential_id=1
    )
    instance.credential = credential
    
    # 2. Act
    connection = MySQLConnection(instance)
    
    # 3. Assert
    assert connection.instance == instance
    assert connection.instance.credential == credential


@pytest.mark.unit
def test_postgresql_connection_init():
    """Test PostgreSQLConnection initialization."""
    # 1. Arrange
    instance = Instance(
        name="test-postgres",
        db_type="postgresql",
        host="localhost",
        port=5432,
        database_name="testdb"
    )
    
    # 2. Act
    connection = PostgreSQLConnection(instance)
    
    # 3. Assert
    assert connection.instance == instance
    assert connection.connection is None
    assert connection.is_connected is False


@pytest.mark.unit
@patch('app.services.connection_factory.psycopg2.connect')
def test_postgresql_connection_connect_success(mock_connect):
    """Test PostgreSQL connection success."""
    # 1. Arrange
    instance = Instance(
        name="test-postgres",
        db_type="postgresql",
        host="localhost",
        port=5432,
        database_name="testdb"
    )
    
    mock_conn = Mock()
    mock_connect.return_value = mock_conn
    connection = PostgreSQLConnection(instance)
    
    # 2. Act
    result = connection.connect()
    
    # 3. Assert
    assert result is True
    assert connection.is_connected is True
    assert connection.connection == mock_conn


@pytest.mark.unit
@patch('app.services.connection_factory.psycopg2.connect')
def test_postgresql_connection_connect_failure(mock_connect):
    """Test PostgreSQL connection failure."""
    # 1. Arrange
    instance = Instance(
        name="test-postgres",
        db_type="postgresql",
        host="localhost",
        port=5432,
        database_name="testdb"
    )
    
    mock_connect.side_effect = Exception("Connection failed")
    connection = PostgreSQLConnection(instance)
    
    # 2. Act
    result = connection.connect()
    
    # 3. Assert
    assert result is False
    assert connection.is_connected is False


@pytest.mark.unit
def test_sqlserver_connection_init():
    """Test SQLServerConnection initialization."""
    # 1. Arrange
    instance = Instance(
        name="test-sqlserver",
        db_type="sqlserver",
        host="localhost",
        port=1433,
        database_name="testdb"
    )
    
    # 2. Act
    connection = SQLServerConnection(instance)
    
    # 3. Assert
    assert connection.instance == instance
    assert connection.connection is None
    assert connection.is_connected is False


@pytest.mark.unit
@patch('app.services.connection_factory.pyodbc.connect')
def test_sqlserver_connection_connect_success(mock_connect):
    """Test SQL Server connection success."""
    # 1. Arrange
    instance = Instance(
        name="test-sqlserver",
        db_type="sqlserver",
        host="localhost",
        port=1433,
        database_name="testdb"
    )
    
    mock_conn = Mock()
    mock_connect.return_value = mock_conn
    connection = SQLServerConnection(instance)
    
    # 2. Act
    result = connection.connect()
    
    # 3. Assert
    assert result is True
    assert connection.is_connected is True
    assert connection.connection == mock_conn


@pytest.mark.unit
@patch('app.services.connection_factory.pyodbc.connect')
def test_sqlserver_connection_connect_failure(mock_connect):
    """Test SQL Server connection failure."""
    # 1. Arrange
    instance = Instance(
        name="test-sqlserver",
        db_type="sqlserver",
        host="localhost",
        port=1433,
        database_name="testdb"
    )
    
    mock_connect.side_effect = Exception("Connection failed")
    connection = SQLServerConnection(instance)
    
    # 2. Act
    result = connection.connect()
    
    # 3. Assert
    assert result is False
    assert connection.is_connected is False


@pytest.mark.unit
def test_oracle_connection_init():
    """Test OracleConnection initialization."""
    # 1. Arrange
    instance = Instance(
        name="test-oracle",
        db_type="oracle",
        host="localhost",
        port=1521,
        database_name="testdb"
    )
    
    # 2. Act
    connection = OracleConnection(instance)
    
    # 3. Assert
    assert connection.instance == instance
    assert connection.connection is None
    assert connection.is_connected is False


@pytest.mark.unit
@patch('app.services.connection_factory.cx_Oracle.connect')
def test_oracle_connection_connect_success(mock_connect):
    """Test Oracle connection success."""
    # 1. Arrange
    instance = Instance(
        name="test-oracle",
        db_type="oracle",
        host="localhost",
        port=1521,
        database_name="testdb"
    )
    
    mock_conn = Mock()
    mock_connect.return_value = mock_conn
    connection = OracleConnection(instance)
    
    # 2. Act
    result = connection.connect()
    
    # 3. Assert
    assert result is True
    assert connection.is_connected is True
    assert connection.connection == mock_conn


@pytest.mark.unit
@patch('app.services.connection_factory.cx_Oracle.connect')
def test_oracle_connection_connect_failure(mock_connect):
    """Test Oracle connection failure."""
    # 1. Arrange
    instance = Instance(
        name="test-oracle",
        db_type="oracle",
        host="localhost",
        port=1521,
        database_name="testdb"
    )
    
    mock_connect.side_effect = Exception("Connection failed")
    connection = OracleConnection(instance)
    
    # 2. Act
    result = connection.connect()
    
    # 3. Assert
    assert result is False
    assert connection.is_connected is False


@pytest.mark.unit
def test_connection_factory_all_database_types():
    """Test ConnectionFactory with all supported database types."""
    # 1. Arrange
    database_types = ["mysql", "postgresql", "sqlserver", "oracle"]
    
    for db_type in database_types:
        instance = Instance(
            name=f"test-{db_type}",
            db_type=db_type,
            host="localhost",
            port=3306,
            database_name="testdb"
        )
        
        # 2. Act
        connection = ConnectionFactory.create_connection(instance)
        
        # 3. Assert
        assert connection is not None
        assert connection.instance == instance


@pytest.mark.unit
def test_connection_factory_case_sensitive():
    """Test ConnectionFactory case sensitivity."""
    # 1. Arrange
    instance = Instance(
        name="test-mysql",
        db_type="MySQL",  # Uppercase
        host="localhost",
        port=3306,
        database_name="testdb"
    )
    
    # 2. Act & Assert
    with pytest.raises(ValueError):
        ConnectionFactory.create_connection(instance)


@pytest.mark.unit
def test_connection_factory_empty_database_type():
    """Test ConnectionFactory with empty database type."""
    # 1. Arrange
    instance = Instance(
        name="test-empty",
        db_type="",
        host="localhost",
        port=3306,
        database_name="testdb"
    )
    
    # 2. Act & Assert
    with pytest.raises(ValueError):
        ConnectionFactory.create_connection(instance)


@pytest.mark.unit
def test_connection_factory_none_database_type():
    """Test ConnectionFactory with None database type."""
    # 1. Arrange
    instance = Instance(
        name="test-none",
        db_type=None,
        host="localhost",
        port=3306,
        database_name="testdb"
    )
    
    # 2. Act & Assert
    with pytest.raises(ValueError):
        ConnectionFactory.create_connection(instance)
