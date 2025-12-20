import pytest
from unittest.mock import patch, MagicMock
import sys
import os

# Add src to path to import the tool
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src/tool_services/prometheus_tool")))

from tool import PrometheusQueryTool

def test_query_range_success(mock_prometheus_response):
    """Test successful Prometheus range query."""
    tool = PrometheusQueryTool("http://mock-prometheus:9090")
    
    mock_data = mock_prometheus_response(values=[["1600000000", "0.5"], ["1600000030", "0.6"]])
    
    with patch("requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_data
        mock_get.return_value = mock_response
        
        result = tool.query_range("up", 5, 30)
        
        assert "Prometheus query results" in result
        assert "0.50" in result
        assert "0.60" in result
        mock_get.assert_called_once()

def test_query_range_no_data(mock_prometheus_response):
    """Test Prometheus query with no results."""
    tool = PrometheusQueryTool("http://mock-prometheus:9090")
    
    mock_data = {"status": "success", "data": {"resultType": "matrix", "result": []}}
    
    with patch("requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_data
        mock_get.return_value = mock_response
        
        result = tool.query_range("non_existent_metric", 5, 30)
        
        assert "No data found" in result

def test_query_range_invalid_params():
    """Test Prometheus tool with invalid parameters."""
    tool = PrometheusQueryTool("http://mock-prometheus:9090")
    
    # Test non-positive time_range
    result = tool.query_range("up", 0, 30)
    assert "Error: time_range_minutes must be positive" in result
    
    # Test non-positive step
    result = tool.query_range("up", 5, -1)
    assert "Error: step_seconds must be positive" in result

def test_query_range_timeout():
    """Test Prometheus tool handling timeout."""
    tool = PrometheusQueryTool("http://mock-prometheus:9090")
    
    with patch("requests.get", side_effect=Exception("Connection timeout")):
        result = tool.query_range("up", 5, 30)
        assert "Error: Connection timeout" in result
