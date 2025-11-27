"""Tests for monitoring endpoints.

Tests health checks and metrics endpoints.
"""
import time
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, func

from main import app
from src.models.game import GameRoom
from src.models.user import Player


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestHealthCheck:
    """Test health check endpoint."""
    
    def test_health_check_success(self, client):
        """Test health check returns healthy status."""
        response = client.get("/monitoring/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] in ["healthy", "degraded"]
        assert "timestamp" in data
        assert "version" in data
        assert "uptime_seconds" in data
        assert "database" in data
    
    def test_health_check_includes_uptime(self, client):
        """Test health check includes uptime."""
        response = client.get("/monitoring/health")
        data = response.json()
        
        assert isinstance(data["uptime_seconds"], int)
        assert data["uptime_seconds"] >= 0
    
    def test_health_check_timestamp_format(self, client):
        """Test timestamp is in ISO format."""
        response = client.get("/monitoring/health")
        data = response.json()
        
        # Should be parseable as ISO datetime
        timestamp = datetime.fromisoformat(data["timestamp"].replace('Z', '+00:00'))
        assert isinstance(timestamp, datetime)


class TestMetrics:
    """Test metrics endpoint."""
    
    def test_metrics_prometheus_format(self, client):
        """Test metrics returns Prometheus format."""
        response = client.get("/monitoring/metrics")
        assert response.status_code == 200
        
        data = response.json()
        assert "metrics" in data
        assert "timestamp" in data
        
        metrics_text = data["metrics"]
        assert "# HELP" in metrics_text
        assert "# TYPE" in metrics_text
    
    def test_metrics_includes_active_games(self, client):
        """Test metrics includes active games count."""
        response = client.get("/monitoring/metrics")
        data = response.json()
        
        assert "active_games" in data["metrics"]
    
    def test_metrics_includes_waiting_rooms(self, client):
        """Test metrics includes waiting rooms count."""
        response = client.get("/monitoring/metrics")
        data = response.json()
        
        assert "waiting_rooms" in data["metrics"]
    
    def test_metrics_includes_total_players(self, client):
        """Test metrics includes total players count."""
        response = client.get("/monitoring/metrics")
        data = response.json()
        
        assert "total_players" in data["metrics"]
    
    def test_metrics_includes_guest_players(self, client):
        """Test metrics includes guest players count."""
        response = client.get("/monitoring/metrics")
        data = response.json()
        
        assert "guest_players" in data["metrics"]
    
    def test_metrics_includes_completed_games(self, client):
        """Test metrics includes completed games count."""
        response = client.get("/monitoring/metrics")
        data = response.json()
        
        assert "completed_games_total" in data["metrics"]
    
    def test_metrics_includes_uptime(self, client):
        """Test metrics includes uptime."""
        response = client.get("/monitoring/metrics")
        data = response.json()
        
        assert "uptime_seconds" in data["metrics"]


class TestMetricsJson:
    """Test JSON metrics endpoint."""
    
    def test_metrics_json_format(self, client):
        """Test metrics JSON returns proper structure."""
        response = client.get("/monitoring/metrics/json")
        assert response.status_code == 200
        
        data = response.json()
        assert "timestamp" in data
        assert "uptime_seconds" in data
        assert "games" in data
        assert "players" in data
    
    def test_metrics_json_games_structure(self, client):
        """Test games section structure."""
        response = client.get("/monitoring/metrics/json")
        data = response.json()
        
        games = data["games"]
        assert "active" in games
        assert "waiting" in games
        assert "completed_total" in games
        
        assert isinstance(games["active"], int)
        assert isinstance(games["waiting"], int)
        assert isinstance(games["completed_total"], int)
    
    def test_metrics_json_players_structure(self, client):
        """Test players section structure."""
        response = client.get("/monitoring/metrics/json")
        data = response.json()
        
        players = data["players"]
        assert "total" in players
        assert "registered" in players
        assert "guests" in players
        
        assert isinstance(players["total"], int)
        assert isinstance(players["registered"], int)
        assert isinstance(players["guests"], int)
    
    def test_metrics_json_uptime(self, client):
        """Test uptime is included."""
        response = client.get("/monitoring/metrics/json")
        data = response.json()
        
        assert isinstance(data["uptime_seconds"], int)
        assert data["uptime_seconds"] >= 0
    
    def test_metrics_json_player_totals(self, client):
        """Test player totals are consistent."""
        response = client.get("/monitoring/metrics/json")
        data = response.json()
        
        players = data["players"]
        # Total should equal registered + guests
        assert players["total"] == players["registered"] + players["guests"]


class TestReadinessCheck:
    """Test readiness probe endpoint."""
    
    def test_readiness_check_success(self, client):
        """Test readiness check when ready."""
        response = client.get("/monitoring/readiness")
        assert response.status_code == 200
        
        data = response.json()
        assert "ready" in data
        assert "timestamp" in data
        assert isinstance(data["ready"], bool)
    
    def test_readiness_check_timestamp(self, client):
        """Test readiness check includes timestamp."""
        response = client.get("/monitoring/readiness")
        data = response.json()
        
        timestamp = datetime.fromisoformat(data["timestamp"].replace('Z', '+00:00'))
        assert isinstance(timestamp, datetime)


class TestLivenessCheck:
    """Test liveness probe endpoint."""
    
    def test_liveness_check_success(self, client):
        """Test liveness check returns alive."""
        response = client.get("/monitoring/liveness")
        assert response.status_code == 200
        
        data = response.json()
        assert data["alive"] is True
        assert "timestamp" in data
        assert "uptime_seconds" in data
    
    def test_liveness_check_uptime(self, client):
        """Test liveness check includes uptime."""
        response = client.get("/monitoring/liveness")
        data = response.json()
        
        assert isinstance(data["uptime_seconds"], int)
        assert data["uptime_seconds"] >= 0
    
    def test_liveness_check_timestamp(self, client):
        """Test liveness check includes timestamp."""
        response = client.get("/monitoring/liveness")
        data = response.json()
        
        timestamp = datetime.fromisoformat(data["timestamp"].replace('Z', '+00:00'))
        assert isinstance(timestamp, datetime)


class TestMonitoringIntegration:
    """Integration tests for monitoring endpoints."""
    
    def test_all_endpoints_accessible(self, client):
        """Test all monitoring endpoints are accessible."""
        endpoints = [
            "/monitoring/health",
            "/monitoring/metrics",
            "/monitoring/metrics/json",
            "/monitoring/readiness",
            "/monitoring/liveness"
        ]
        
        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code == 200, f"Failed to access {endpoint}"
    
    def test_metrics_consistency(self, client):
        """Test metrics are consistent between formats."""
        prometheus_response = client.get("/monitoring/metrics")
        json_response = client.get("/monitoring/metrics/json")
        
        assert prometheus_response.status_code == 200
        assert json_response.status_code == 200
        
        # Both should succeed
        assert "metrics" in prometheus_response.json()
        assert "games" in json_response.json()
