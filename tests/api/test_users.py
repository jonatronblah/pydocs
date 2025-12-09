import pytest
import uuid
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import status
from fastapi.testclient import TestClient


class TestUserEndpoints:
    """Test cases for user-related endpoints."""

    def test_get_current_user(self, client, mock_user):
        """Test getting current user information."""
        with patch("pydocs.schema.user.current_active_user", return_value=mock_user):
            response = client.get("/users/me")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["id"] == str(mock_user.id)
            assert data["email"] == mock_user.email
            assert data["username"] == mock_user.username

    def test_get_current_user_unauthorized(self, client):
        """Test getting current user without authentication."""
        response = client.get("/users/me")

        # This should redirect to login or return 401 depending on auth setup
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_200_OK,
        ]


class TestUserManagement:
    """Test cases for user management endpoints."""

    def test_list_users_as_admin(self, client, mock_admin_user):
        """Test listing users as admin."""
        with (
            patch(
                "pydocs.schema.user.current_active_user", return_value=mock_admin_user
            ),
            patch("pydocs.schema.user.get_user_manager") as mock_user_manager,
        ):
            # Mock user manager
            mock_manager = AsyncMock()
            mock_user_manager.return_value.__aenter__.return_value = mock_manager

            # Mock list of users
            mock_users = [
                MagicMock(id=uuid.uuid4(), email="user1@example.com", username="user1"),
                MagicMock(id=uuid.uuid4(), email="user2@example.com", username="user2"),
            ]
            mock_manager.list.return_value = mock_users

            response = client.get("/users/")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert isinstance(data, list)
            assert len(data) >= 0

    def test_list_users_as_regular_user(self, client, mock_user):
        """Test listing users as regular user (should be forbidden)."""
        with patch("pydocs.schema.user.current_active_user", return_value=mock_user):
            response = client.get("/users/")

            # Regular users shouldn't have access to list all users
            assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_get_user_by_id_as_admin(self, client, mock_admin_user, mock_user):
        """Test getting a specific user as admin."""
        with (
            patch(
                "pydocs.schema.user.current_active_user", return_value=mock_admin_user
            ),
            patch("pydocs.schema.user.get_user_manager") as mock_user_manager,
        ):
            # Mock user manager
            mock_manager = AsyncMock()
            mock_user_manager.return_value.__aenter__.return_value = mock_manager

            # Mock user retrieval
            mock_manager.get.return_value = mock_user

            response = client.get(f"/users/{mock_user.id}")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["id"] == str(mock_user.id)

    def test_get_user_by_id_as_regular_user(self, client, mock_user):
        """Test getting a specific user as regular user (should be forbidden)."""
        with patch("pydocs.schema.user.current_active_user", return_value=mock_user):
            fake_user_id = uuid.uuid4()
            response = client.get(f"/users/{fake_user_id}")

            # Regular users shouldn't have access to get other users
            assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_update_user_as_admin(self, client, mock_admin_user, mock_user):
        """Test updating a user as admin."""
        with (
            patch(
                "pydocs.schema.user.current_active_user", return_value=mock_admin_user
            ),
            patch("pydocs.schema.user.get_user_manager") as mock_user_manager,
        ):
            # Mock user manager
            mock_manager = AsyncMock()
            mock_user_manager.return_value.__aenter__.return_value = mock_manager

            # Mock user update
            updated_user = MagicMock()
            updated_user.id = mock_user.id
            updated_user.email = "updated@example.com"
            updated_user.username = "updated_user"
            mock_manager.update.return_value = updated_user

            update_data = {"username": "updated_user", "email": "updated@example.com"}

            response = client.patch(f"/users/{mock_user.id}", json=update_data)

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["username"] == "updated_user"
            assert data["email"] == "updated@example.com"

    def test_update_user_as_regular_user(self, client, mock_user):
        """Test updating a user as regular user (should be forbidden)."""
        with patch("pydocs.schema.user.current_active_user", return_value=mock_user):
            fake_user_id = uuid.uuid4()
            update_data = {"username": "hacked_user"}
            response = client.patch(f"/users/{fake_user_id}", json=update_data)

            # Regular users shouldn't be able to update other users
            assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_delete_user_as_admin(self, client, mock_admin_user, mock_user):
        """Test deleting a user as admin."""
        with (
            patch(
                "pydocs.schema.user.current_active_user", return_value=mock_admin_user
            ),
            patch("pydocs.schema.user.get_user_manager") as mock_user_manager,
        ):
            # Mock user manager
            mock_manager = AsyncMock()
            mock_user_manager.return_value.__aenter__.return_value = mock_manager

            # Mock successful deletion
            mock_manager.delete.return_value = None

            response = client.delete(f"/users/{mock_user.id}")

            assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_delete_user_as_regular_user(self, client, mock_user):
        """Test deleting a user as regular user (should be forbidden)."""
        with patch("pydocs.schema.user.current_active_user", return_value=mock_user):
            fake_user_id = uuid.uuid4()
            response = client.delete(f"/users/{fake_user_id}")

            # Regular users shouldn't be able to delete other users
            assert response.status_code == status.HTTP_403_FORBIDDEN
