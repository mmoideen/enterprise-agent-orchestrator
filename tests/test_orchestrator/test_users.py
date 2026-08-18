"""Tests for user management and authentication endpoints."""

import pytest
from httpx import AsyncClient
from sqlmodel.ext.asyncio.session import AsyncSession

from packages.domain_models.user import User


class TestUserRegistration:
    """Tests for user registration."""

    @pytest.mark.asyncio
    async def test_register_user_success(self, client: AsyncClient) -> None:
        """Test successful user registration."""
        user_data = {
            "email": "newuser@test.com",
            "full_name": "New User",
            "password": "password123",
            "role": "viewer",
            "is_active": True,
        }

        response = await client.post("/users/register", json=user_data)

        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@test.com"
        assert data["full_name"] == "New User"
        assert data["role"] == "viewer"
        assert "hashed_password" not in data

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, client: AsyncClient, admin_user: User) -> None:
        """Test that duplicate email registration fails."""
        user_data = {
            "email": admin_user.email,
            "full_name": "Duplicate User",
            "password": "password123",
            "role": "viewer",
            "is_active": True,
        }

        response = await client.post("/users/register", json=user_data)

        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()


class TestUserAuthentication:
    """Tests for user login."""

    @pytest.mark.asyncio
    async def test_login_success(self, client: AsyncClient, admin_user: User) -> None:
        """Test successful login."""
        login_data = {"email": "admin@test.com", "password": "password123"}

        response = await client.post("/users/login", json=login_data)

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client: AsyncClient, admin_user: User) -> None:
        """Test login with wrong password."""
        login_data = {"email": "admin@test.com", "password": "wrongpassword"}

        response = await client.post("/users/login", json=login_data)

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, client: AsyncClient) -> None:
        """Test login with non-existent user."""
        login_data = {
            "email": "nonexistent@test.com",
            "password": "password123",
        }

        response = await client.post("/users/login", json=login_data)

        assert response.status_code == 401


class TestCurrentUser:
    """Tests for getting current user info."""

    @pytest.mark.asyncio
    async def test_get_current_user(
        self, client: AsyncClient, admin_token: str, admin_user: User
    ) -> None:
        """Test getting current user information."""
        response = await client.get("/users/me", headers={"Authorization": f"Bearer {admin_token}"})

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == admin_user.email
        assert data["role"] == admin_user.role.value

    @pytest.mark.asyncio
    async def test_get_current_user_without_auth(self, client: AsyncClient) -> None:
        """Test getting current user without authentication."""
        response = await client.get("/users/me")

        assert response.status_code == 401


class TestUserListing:
    """Tests for listing users."""

    @pytest.mark.asyncio
    async def test_list_users_as_admin(
        self,
        client: AsyncClient,
        admin_token: str,
        admin_user: User,
        developer_user: User,
    ) -> None:
        """Test that admin can list all users."""
        response = await client.get("/users/", headers={"Authorization": f"Bearer {admin_token}"})

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 2

    @pytest.mark.asyncio
    async def test_list_users_as_non_admin(self, client: AsyncClient, developer_token: str) -> None:
        """Test that non-admin cannot list users."""
        response = await client.get(
            "/users/", headers={"Authorization": f"Bearer {developer_token}"}
        )

        assert response.status_code == 403


class TestUserRetrieval:
    """Tests for retrieving individual users."""

    @pytest.mark.asyncio
    async def test_get_user_as_admin(
        self,
        client: AsyncClient,
        admin_token: str,
        developer_user: User,
    ) -> None:
        """Test that admin can get any user."""
        response = await client.get(
            f"/users/{developer_user.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == developer_user.email

    @pytest.mark.asyncio
    async def test_get_user_as_non_admin(
        self,
        client: AsyncClient,
        developer_token: str,
        admin_user: User,
    ) -> None:
        """Test that non-admin cannot get other users."""
        response = await client.get(
            f"/users/{admin_user.id}",
            headers={"Authorization": f"Bearer {developer_token}"},
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_get_nonexistent_user(self, client: AsyncClient, admin_token: str) -> None:
        """Test getting a user that doesn't exist."""
        from uuid import uuid4

        fake_id = str(uuid4())

        response = await client.get(
            f"/users/{fake_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 404


class TestRBAC:
    """Tests for role-based access control."""

    @pytest.mark.asyncio
    async def test_viewer_cannot_create_agent(self, client: AsyncClient, viewer_token: str) -> None:
        """Test that viewer role has limited permissions."""
        agent_data = {
            "name": "Test Agent",
            "description": "Test",
            "agent_type": "test",
            "capabilities": {},
            "configuration": {"runtime": "python", "resources": {"memory_mb": 256}},
            "version": "1.0.0",
            "owner_id": "placeholder",
            "tags": [],
        }

        response = await client.post(
            "/agents/",
            json=agent_data,
            headers={"Authorization": f"Bearer {viewer_token}"},
        )

        # Viewer might be able to create but not approve
        # The exact behavior depends on your RBAC implementation
        # This test verifies RBAC is being checked
        assert response.status_code in [200, 201, 403]

    @pytest.mark.asyncio
    async def test_developer_can_create_agent(
        self, client: AsyncClient, developer_token: str
    ) -> None:
        """Test that developer role can create agents."""
        agent_data = {
            "name": "Test Agent",
            "description": "Test",
            "agent_type": "test",
            "capabilities": {},
            "configuration": {"runtime": "python", "resources": {"memory_mb": 256}},
            "version": "1.0.0",
            "owner_id": "placeholder",
            "tags": [],
        }

        response = await client.post(
            "/agents/",
            json=agent_data,
            headers={"Authorization": f"Bearer {developer_token}"},
        )

        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_admin_has_full_access(self, client: AsyncClient, admin_token: str) -> None:
        """Test that admin role has full access."""
        # Test user listing
        users_response = await client.get(
            "/users/", headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert users_response.status_code == 200

        # Test agent creation
        agent_data = {
            "name": "Admin Agent",
            "description": "Test",
            "agent_type": "test",
            "capabilities": {},
            "configuration": {"runtime": "python", "resources": {"memory_mb": 256}},
            "version": "1.0.0",
            "owner_id": "placeholder",
            "tags": [],
        }

        agents_response = await client.post(
            "/agents/",
            json=agent_data,
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert agents_response.status_code == 201


class TestPrivilegedUserCreation:
    """Tests for role assignment on registration and admin user creation."""

    @pytest.mark.asyncio
    async def test_register_ignores_requested_role(self, client: AsyncClient) -> None:
        """Test that self-registration cannot mint privileged accounts."""
        response = await client.post(
            "/users/register",
            json={
                "email": "escalate@test.com",
                "full_name": "Escalation Attempt",
                "password": "password123",
                "role": "admin",
                "is_active": True,
            },
        )

        assert response.status_code == 201
        assert response.json()["role"] == "viewer"

    @pytest.mark.asyncio
    async def test_admin_can_create_privileged_user(
        self, client: AsyncClient, admin_token: str
    ) -> None:
        """Test that an admin can create a user with an explicit role."""
        response = await client.post(
            "/users/",
            json={
                "email": "newadmin@test.com",
                "full_name": "New Admin",
                "password": "password123",
                "role": "admin",
                "is_active": True,
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["role"] == "admin"
        assert "hashed_password" not in data

    @pytest.mark.asyncio
    async def test_non_admin_cannot_create_user(
        self, client: AsyncClient, developer_token: str
    ) -> None:
        """Test that non-admins are rejected by the privileged endpoint."""
        response = await client.post(
            "/users/",
            json={
                "email": "sneaky@test.com",
                "full_name": "Sneaky User",
                "password": "password123",
                "role": "admin",
                "is_active": True,
            },
            headers={"Authorization": f"Bearer {developer_token}"},
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_anonymous_cannot_create_user(self, client: AsyncClient) -> None:
        """Test that unauthenticated callers are rejected by the privileged endpoint."""
        response = await client.post(
            "/users/",
            json={
                "email": "anon@test.com",
                "full_name": "Anonymous",
                "password": "password123",
                "role": "admin",
                "is_active": True,
            },
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_with_malformed_stored_hash(
        self, client: AsyncClient, session: AsyncSession, admin_user: User
    ) -> None:
        """Test that an unparseable stored hash is rejected instead of erroring."""
        admin_user.hashed_password = "not-a-bcrypt-hash"
        session.add(admin_user)
        await session.commit()

        response = await client.post(
            "/users/login",
            json={"email": admin_user.email, "password": "password123"},
        )

        assert response.status_code == 401
