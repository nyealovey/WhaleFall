"""
APIResponse工具类单元测试
"""
import pytest
from flask import Flask
from app.utils.api_response import APIResponse


@pytest.mark.unit
def test_api_response_init():
    """Test APIResponse initialization."""
    # APIResponse is a static class, so we just test that it can be imported
    assert APIResponse is not None


@pytest.mark.unit
def test_success_response():
    """Test success response creation."""
    # Test with data
    response = APIResponse.success(data={"id": 1, "name": "test"})
    assert response.status_code == 200
    
    # Test with custom message
    response = APIResponse.success(message="创建成功", data={"id": 2})
    assert response.status_code == 200


@pytest.mark.unit
def test_success_response_no_data():
    """Test success response without data."""
    response = APIResponse.success()
    assert response.status_code == 200


@pytest.mark.unit
def test_error_response():
    """Test error response creation."""
    # Test with default message
    response = APIResponse.error()
    assert response.status_code == 500
    
    # Test with custom message
    response = APIResponse.error(message="参数错误", code=400)
    assert response.status_code == 400


@pytest.mark.unit
def test_error_response_with_code():
    """Test error response with custom code."""
    response = APIResponse.error(message="未找到", code=404)
    assert response.status_code == 404


@pytest.mark.unit
def test_error_response_with_data():
    """Test error response with data."""
    response = APIResponse.error(message="验证失败", data={"errors": ["字段1不能为空"]})
    assert response.status_code == 500


@pytest.mark.unit
def test_response_json_format():
    """Test response JSON format."""
    # Test success response format
    response = APIResponse.success(data={"id": 1})
    json_data = response.get_json()
    assert json_data["success"] is True
    assert json_data["message"] == "操作成功"
    assert json_data["data"]["id"] == 1
    
    # Test error response format
    response = APIResponse.error(message="测试错误")
    json_data = response.get_json()
    assert json_data["success"] is False
    assert json_data["message"] == "测试错误"


@pytest.mark.unit
def test_response_with_none_data():
    """Test response with None data."""
    response = APIResponse.success(data=None)
    json_data = response.get_json()
    assert json_data["success"] is True
    assert "data" not in json_data


@pytest.mark.unit
def test_response_with_empty_data():
    """Test response with empty data."""
    response = APIResponse.success(data={})
    json_data = response.get_json()
    assert json_data["success"] is True
    assert json_data["data"] == {}


@pytest.mark.unit
def test_response_with_list_data():
    """Test response with list data."""
    data = [{"id": 1, "name": "item1"}, {"id": 2, "name": "item2"}]
    response = APIResponse.success(data=data)
    json_data = response.get_json()
    assert json_data["success"] is True
    assert json_data["data"] == data


@pytest.mark.unit
def test_response_with_string_data():
    """Test response with string data."""
    response = APIResponse.success(data="test string")
    json_data = response.get_json()
    assert json_data["success"] is True
    assert json_data["data"] == "test string"


@pytest.mark.unit
def test_response_with_number_data():
    """Test response with number data."""
    response = APIResponse.success(data=123)
    json_data = response.get_json()
    assert json_data["success"] is True
    assert json_data["data"] == 123


@pytest.mark.unit
def test_response_with_boolean_data():
    """Test response with boolean data."""
    response = APIResponse.success(data=True)
    json_data = response.get_json()
    assert json_data["success"] is True
    assert json_data["data"] is True


@pytest.mark.unit
def test_response_headers():
    """Test response headers."""
    response = APIResponse.success()
    assert response.content_type == "application/json"


@pytest.mark.unit
def test_response_charset():
    """Test response charset."""
    response = APIResponse.success()
    assert "charset" in response.content_type


@pytest.mark.unit
def test_response_consistency():
    """Test response structure consistency."""
    # Test different response types
    success_response = APIResponse.success()
    error_response = APIResponse.error()
    
    success_json = success_response.get_json()
    error_json = error_response.get_json()
    
    # All responses should have these fields
    assert "success" in success_json
    assert "message" in success_json
    assert "success" in error_json
    assert "message" in error_json
    
    # Success should be boolean
    assert isinstance(success_json["success"], bool)
    assert isinstance(error_json["success"], bool)
    
    # Message should be string
    assert isinstance(success_json["message"], str)
    assert isinstance(error_json["message"], str)


@pytest.mark.unit
def test_response_message_types():
    """Test response with different message types."""
    # Test with empty message
    response = APIResponse.success(message="")
    json_data = response.get_json()
    assert json_data["message"] == ""
    
    # Test with unicode message
    response = APIResponse.success(message="测试消息")
    json_data = response.get_json()
    assert json_data["message"] == "测试消息"
    
    # Test with long message
    long_message = "This is a very long message that contains multiple words and should be handled properly by the API response system"
    response = APIResponse.success(message=long_message)
    json_data = response.get_json()
    assert json_data["message"] == long_message


@pytest.mark.unit
def test_response_data_types():
    """Test response with different data types."""
    # Test with dict
    response = APIResponse.success(data={"key": "value"})
    json_data = response.get_json()
    assert json_data["data"]["key"] == "value"
    
    # Test with list
    response = APIResponse.success(data=[1, 2, 3])
    json_data = response.get_json()
    assert json_data["data"] == [1, 2, 3]
    
    # Test with nested structure
    nested_data = {
        "users": [
            {"id": 1, "name": "user1"},
            {"id": 2, "name": "user2"}
        ],
        "total": 2
    }
    response = APIResponse.success(data=nested_data)
    json_data = response.get_json()
    assert json_data["data"]["total"] == 2
    assert len(json_data["data"]["users"]) == 2


@pytest.mark.unit
def test_response_error_codes():
    """Test response with different error codes."""
    error_codes = [400, 401, 403, 404, 422, 500, 502, 503]
    
    for code in error_codes:
        response = APIResponse.error(message=f"Error {code}", code=code)
        assert response.status_code == code


@pytest.mark.unit
def test_response_default_values():
    """Test response default values."""
    # Test success response defaults
    response = APIResponse.success()
    json_data = response.get_json()
    assert json_data["success"] is True
    assert json_data["message"] == "操作成功"
    
    # Test error response defaults
    response = APIResponse.error()
    json_data = response.get_json()
    assert json_data["success"] is False
    assert json_data["message"] == "操作失败"
    assert response.status_code == 500

