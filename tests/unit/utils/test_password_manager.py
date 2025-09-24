"""
PasswordManager工具类单元测试
"""
import pytest
import os
from unittest.mock import patch, Mock
from app.utils.password_manager import PasswordManager


@pytest.mark.unit
def test_password_manager_init():
    """Test PasswordManager initialization."""
    manager = PasswordManager()
    assert manager is not None
    assert manager.key is not None
    assert manager.cipher is not None


@pytest.mark.unit
@patch.dict(os.environ, {'PASSWORD_ENCRYPTION_KEY': 'test-key-123456789012345678901234567890'})
def test_password_manager_with_env_key():
    """Test PasswordManager with environment key."""
    # Convert string to bytes for Fernet
    key = os.environ['PASSWORD_ENCRYPTION_KEY'].encode()
    manager = PasswordManager()
    assert manager.key == key


@pytest.mark.unit
@patch.dict(os.environ, {}, clear=True)
def test_password_manager_without_env_key():
    """Test PasswordManager without environment key."""
    with patch('app.utils.password_manager.Fernet.generate_key') as mock_generate:
        mock_generate.return_value = b'test-generated-key-123456789012345678901234567890'
        manager = PasswordManager()
        assert manager.key == mock_generate.return_value


@pytest.mark.unit
def test_encrypt_password():
    """Test password encryption."""
    manager = PasswordManager()
    password = "test_password_123"
    
    encrypted = manager.encrypt_password(password)
    
    assert encrypted != password
    assert isinstance(encrypted, str)
    assert len(encrypted) > 0


@pytest.mark.unit
def test_decrypt_password():
    """Test password decryption."""
    manager = PasswordManager()
    original_password = "test_password_123"
    
    encrypted = manager.encrypt_password(original_password)
    decrypted = manager.decrypt_password(encrypted)
    
    assert decrypted == original_password


@pytest.mark.unit
def test_encrypt_decrypt_roundtrip():
    """Test encrypt and decrypt roundtrip."""
    manager = PasswordManager()
    test_passwords = [
        "simple",
        "complex_password_123!@#",
        "中文密码",
        "password with spaces",
        "very_long_password_" + "x" * 100,
        "",
        "!@#$%^&*()_+-=[]{}|;':\",./<>?"
    ]
    
    for password in test_passwords:
        encrypted = manager.encrypt_password(password)
        decrypted = manager.decrypt_password(encrypted)
        assert decrypted == password


@pytest.mark.unit
def test_is_encrypted():
    """Test checking if string is encrypted."""
    manager = PasswordManager()
    password = "test_password"
    
    # Test unencrypted string
    assert manager.is_encrypted(password) is False
    
    # Test encrypted string
    encrypted = manager.encrypt_password(password)
    assert manager.is_encrypted(encrypted) is True


@pytest.mark.unit
def test_is_encrypted_invalid_string():
    """Test checking invalid encrypted string."""
    manager = PasswordManager()
    
    # Test invalid base64
    assert manager.is_encrypted("invalid_base64") is False
    
    # Test empty string
    assert manager.is_encrypted("") is False
    
    # Test None
    assert manager.is_encrypted(None) is False


@pytest.mark.unit
def test_encrypt_password_empty():
    """Test encrypting empty password."""
    manager = PasswordManager()
    
    encrypted = manager.encrypt_password("")
    decrypted = manager.decrypt_password(encrypted)
    
    assert decrypted == ""


@pytest.mark.unit
def test_encrypt_password_unicode():
    """Test encrypting unicode password."""
    manager = PasswordManager()
    unicode_password = "测试密码123!@#"
    
    encrypted = manager.encrypt_password(unicode_password)
    decrypted = manager.decrypt_password(encrypted)
    
    assert decrypted == unicode_password


@pytest.mark.unit
def test_encrypt_password_special_chars():
    """Test encrypting password with special characters."""
    manager = PasswordManager()
    special_password = "!@#$%^&*()_+-=[]{}|;':\",./<>?"
    
    encrypted = manager.encrypt_password(special_password)
    decrypted = manager.decrypt_password(encrypted)
    
    assert decrypted == special_password


@pytest.mark.unit
def test_decrypt_invalid_password():
    """Test decrypting invalid password."""
    manager = PasswordManager()
    
    # Test with invalid encrypted string
    with pytest.raises(Exception):  # Should raise an exception
        manager.decrypt_password("invalid_encrypted_string")


@pytest.mark.unit
def test_decrypt_empty_string():
    """Test decrypting empty string."""
    manager = PasswordManager()
    
    with pytest.raises(Exception):  # Should raise an exception
        manager.decrypt_password("")


@pytest.mark.unit
def test_decrypt_none():
    """Test decrypting None."""
    manager = PasswordManager()
    
    with pytest.raises(Exception):  # Should raise an exception
        manager.decrypt_password(None)


@pytest.mark.unit
def test_encrypt_none():
    """Test encrypting None."""
    manager = PasswordManager()
    
    with pytest.raises(Exception):  # Should raise an exception
        manager.encrypt_password(None)


@pytest.mark.unit
def test_password_manager_different_instances():
    """Test that different PasswordManager instances work with same key."""
    # Create two managers with same key
    with patch.dict(os.environ, {'PASSWORD_ENCRYPTION_KEY': 'test-key-123456789012345678901234567890'}):
        manager1 = PasswordManager()
        manager2 = PasswordManager()
        
        password = "test_password"
        
        # Encrypt with one manager
        encrypted = manager1.encrypt_password(password)
        
        # Decrypt with another manager
        decrypted = manager2.decrypt_password(encrypted)
        
        assert decrypted == password


@pytest.mark.unit
def test_password_manager_different_keys():
    """Test that different keys produce different encrypted results."""
    with patch.dict(os.environ, {'PASSWORD_ENCRYPTION_KEY': 'key1-123456789012345678901234567890'}):
        manager1 = PasswordManager()
    
    with patch.dict(os.environ, {'PASSWORD_ENCRYPTION_KEY': 'key2-123456789012345678901234567890'}):
        manager2 = PasswordManager()
    
    password = "test_password"
    
    encrypted1 = manager1.encrypt_password(password)
    encrypted2 = manager2.encrypt_password(password)
    
    # Different keys should produce different encrypted results
    assert encrypted1 != encrypted2


@pytest.mark.unit
def test_encrypt_password_consistency():
    """Test that encrypting the same password multiple times produces different results."""
    manager = PasswordManager()
    password = "test_password"
    
    encrypted1 = manager.encrypt_password(password)
    encrypted2 = manager.encrypt_password(password)
    
    # Same password should produce different encrypted results (due to random IV)
    assert encrypted1 != encrypted2
    
    # But both should decrypt to the same original password
    decrypted1 = manager.decrypt_password(encrypted1)
    decrypted2 = manager.decrypt_password(encrypted2)
    
    assert decrypted1 == password
    assert decrypted2 == password


@pytest.mark.unit
def test_password_manager_key_generation():
    """Test key generation when no environment variable is set."""
    with patch.dict(os.environ, {}, clear=True):
        with patch('app.utils.password_manager.Fernet.generate_key') as mock_generate:
            mock_generate.return_value = b'generated-key-123456789012345678901234567890'
            
            manager = PasswordManager()
            
            assert manager.key == mock_generate.return_value
            mock_generate.assert_called_once()


@pytest.mark.unit
def test_password_manager_logging():
    """Test that PasswordManager logs warnings when no key is set."""
    with patch.dict(os.environ, {}, clear=True):
        with patch('app.utils.password_manager.get_system_logger') as mock_logger:
            mock_logger_instance = Mock()
            mock_logger.return_value = mock_logger_instance
            
            PasswordManager()
            
            # Should log warning about missing key
            mock_logger_instance.warning.assert_called()
            mock_logger_instance.info.assert_called()


@pytest.mark.unit
def test_password_manager_import_error():
    """Test PasswordManager behavior when logger import fails."""
    with patch.dict(os.environ, {}, clear=True):
        with patch('app.utils.password_manager.get_system_logger', side_effect=ImportError):
            with patch('builtins.print') as mock_print:
                PasswordManager()
                
                # Should print warning messages
                mock_print.assert_called()


@pytest.mark.unit
def test_encrypt_password_very_long():
    """Test encrypting very long password."""
    manager = PasswordManager()
    long_password = "x" * 10000  # 10KB password
    
    encrypted = manager.encrypt_password(long_password)
    decrypted = manager.decrypt_password(encrypted)
    
    assert decrypted == long_password


@pytest.mark.unit
def test_encrypt_password_binary_data():
    """Test encrypting password that looks like binary data."""
    manager = PasswordManager()
    binary_like_password = "\x00\x01\x02\x03\x04\x05"
    
    encrypted = manager.encrypt_password(binary_like_password)
    decrypted = manager.decrypt_password(encrypted)
    
    assert decrypted == binary_like_password

