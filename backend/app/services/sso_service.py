"""
SSO & Enterprise Security Service
Implements Single Sign-On with various identity providers
Competitor: Toast SSO, Oracle MICROS Enterprise Auth
"""

import secrets
import hashlib
import base64
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID, uuid4
from urllib.parse import urlencode
from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.ext.asyncio import Session

from app.models.gap_features_models import (
    SSOConfiguration, SSOSession, SSOProviderType
)


class SSOService:
    """
    Service for Single Sign-On authentication.
    Supports SAML 2.0, OAuth 2.0/OIDC, and enterprise identity providers.
    """

    def __init__(self, db: Session):
        self.db = db

    # ==================== SSO CONFIGURATION ====================

    async def create_sso_config(
        self,
        tenant_id: UUID,
        provider_type: str,  # 'saml', 'oidc', 'google', 'microsoft', 'okta', 'onelogin'
        display_name: str,
        config: Dict[str, Any],
        domain_whitelist: Optional[List[str]] = None,
        auto_provision_users: bool = True,
        default_role: str = "staff"
    ) -> SSOConfiguration:
        """Create an SSO configuration for a tenant."""
        # Validate config based on provider type
        self._validate_config(provider_type, config)

        sso_config = SSOConfiguration(
            id=uuid4(),
            tenant_id=tenant_id,
            provider_type=SSOProviderType(provider_type),
            display_name=display_name,
            config=config,
            domain_whitelist=domain_whitelist or [],
            auto_provision_users=auto_provision_users,
            default_role=default_role,
            is_active=True,
            created_at=datetime.now(timezone.utc)
        )
        self.db.add(sso_config)
        await self.db.commit()
        await self.db.refresh(sso_config)
        return sso_config

    def _validate_config(self, provider_type: str, config: Dict[str, Any]) -> None:
        """Validate SSO configuration for a provider type."""
        required_fields = {
            "saml": ["entity_id", "sso_url", "certificate"],
            "oidc": ["client_id", "client_secret", "issuer_url"],
            "google": ["client_id", "client_secret"],
            "microsoft": ["client_id", "client_secret", "tenant_id"],
            "okta": ["client_id", "client_secret", "domain"],
            "onelogin": ["client_id", "client_secret", "subdomain"]
        }

        required = required_fields.get(provider_type, [])
        missing = [f for f in required if f not in config]

        if missing:
            raise ValueError(f"Missing required config fields: {', '.join(missing)}")

    async def get_sso_config(
        self,
        tenant_id: UUID,
        config_id: Optional[UUID] = None
    ) -> Optional[SSOConfiguration]:
        """Get SSO configuration."""
        query = select(SSOConfiguration).where(
            and_(
                SSOConfiguration.tenant_id == tenant_id,
                SSOConfiguration.is_active == True
            )
        )

        if config_id:
            query = query.where(SSOConfiguration.id == config_id)

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_sso_config_by_domain(
        self,
        email_domain: str
    ) -> Optional[SSOConfiguration]:
        """Get SSO configuration by email domain."""
        result = await self.db.execute(
            select(SSOConfiguration).where(
                and_(
                    SSOConfiguration.is_active == True,
                    SSOConfiguration.domain_whitelist.contains([email_domain])
                )
            )
        )
        return result.scalar_one_or_none()

    async def update_sso_config(
        self,
        config_id: UUID,
        updates: Dict[str, Any]
    ) -> SSOConfiguration:
        """Update SSO configuration."""
        result = await self.db.execute(
            select(SSOConfiguration).where(SSOConfiguration.id == config_id)
        )
        sso_config = result.scalar_one_or_none()

        if not sso_config:
            raise ValueError("SSO configuration not found")

        for key, value in updates.items():
            if hasattr(sso_config, key):
                setattr(sso_config, key, value)

        sso_config.updated_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(sso_config)
        return sso_config

    async def delete_sso_config(self, config_id: UUID) -> bool:
        """Delete (deactivate) SSO configuration."""
        result = await self.db.execute(
            select(SSOConfiguration).where(SSOConfiguration.id == config_id)
        )
        sso_config = result.scalar_one_or_none()

        if sso_config:
            sso_config.is_active = False
            await self.db.commit()
            return True
        return False

    # ==================== OAUTH/OIDC FLOW ====================

    async def initiate_oauth_login(
        self,
        sso_config: SSOConfiguration,
        redirect_uri: str,
        state: Optional[str] = None
    ) -> Dict[str, Any]:
        """Initiate OAuth/OIDC login flow."""
        if state is None:
            state = secrets.token_urlsafe(32)

        provider_type = sso_config.provider_type.value
        config = sso_config.config

        # Build authorization URL based on provider
        if provider_type == "google":
            auth_url = self._build_google_auth_url(config, redirect_uri, state)
        elif provider_type == "microsoft":
            auth_url = self._build_microsoft_auth_url(config, redirect_uri, state)
        elif provider_type == "okta":
            auth_url = self._build_okta_auth_url(config, redirect_uri, state)
        elif provider_type == "onelogin":
            auth_url = self._build_onelogin_auth_url(config, redirect_uri, state)
        elif provider_type == "oidc":
            auth_url = self._build_oidc_auth_url(config, redirect_uri, state)
        else:
            raise ValueError(f"Unsupported provider type: {provider_type}")

        return {
            "auth_url": auth_url,
            "state": state,
            "provider": provider_type
        }

    def _build_google_auth_url(
        self,
        config: Dict[str, Any],
        redirect_uri: str,
        state: str
    ) -> str:
        """Build Google OAuth authorization URL."""
        params = {
            "client_id": config["client_id"],
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "access_type": "offline",
            "prompt": "select_account"
        }
        return f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"

    def _build_microsoft_auth_url(
        self,
        config: Dict[str, Any],
        redirect_uri: str,
        state: str
    ) -> str:
        """Build Microsoft OAuth authorization URL."""
        tenant = config.get("tenant_id", "common")
        params = {
            "client_id": config["client_id"],
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid email profile User.Read",
            "state": state,
            "response_mode": "query"
        }
        return f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize?{urlencode(params)}"

    def _build_okta_auth_url(
        self,
        config: Dict[str, Any],
        redirect_uri: str,
        state: str
    ) -> str:
        """Build Okta OAuth authorization URL."""
        domain = config["domain"]
        params = {
            "client_id": config["client_id"],
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state
        }
        return f"https://{domain}/oauth2/default/v1/authorize?{urlencode(params)}"

    def _build_onelogin_auth_url(
        self,
        config: Dict[str, Any],
        redirect_uri: str,
        state: str
    ) -> str:
        """Build OneLogin OAuth authorization URL."""
        subdomain = config["subdomain"]
        params = {
            "client_id": config["client_id"],
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state
        }
        return f"https://{subdomain}.onelogin.com/oidc/2/auth?{urlencode(params)}"

    def _build_oidc_auth_url(
        self,
        config: Dict[str, Any],
        redirect_uri: str,
        state: str
    ) -> str:
        """Build generic OIDC authorization URL."""
        issuer_url = config["issuer_url"].rstrip("/")
        params = {
            "client_id": config["client_id"],
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": config.get("scope", "openid email profile"),
            "state": state
        }
        return f"{issuer_url}/authorize?{urlencode(params)}"

    async def handle_oauth_callback(
        self,
        sso_config: SSOConfiguration,
        code: str,
        redirect_uri: str
    ) -> Dict[str, Any]:
        """Handle OAuth callback and exchange code for tokens."""
        import httpx

        provider_type = sso_config.provider_type.value
        config = sso_config.config

        # Get token endpoint and user info based on provider
        if provider_type == "google":
            token_url = "https://oauth2.googleapis.com/token"
            userinfo_url = "https://www.googleapis.com/oauth2/v3/userinfo"
        elif provider_type == "microsoft":
            tenant = config.get("tenant_id", "common")
            token_url = f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
            userinfo_url = "https://graph.microsoft.com/v1.0/me"
        elif provider_type == "okta":
            domain = config["domain"]
            token_url = f"https://{domain}/oauth2/default/v1/token"
            userinfo_url = f"https://{domain}/oauth2/default/v1/userinfo"
        elif provider_type == "onelogin":
            subdomain = config["subdomain"]
            token_url = f"https://{subdomain}.onelogin.com/oidc/2/token"
            userinfo_url = f"https://{subdomain}.onelogin.com/oidc/2/me"
        elif provider_type == "oidc":
            issuer_url = config["issuer_url"].rstrip("/")
            token_url = f"{issuer_url}/token"
            userinfo_url = f"{issuer_url}/userinfo"
        else:
            raise ValueError(f"Unsupported provider type: {provider_type}")

        # Exchange code for tokens
        async with httpx.AsyncClient(timeout=30) as client:
            token_response = await client.post(
                token_url,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": redirect_uri,
                    "client_id": config["client_id"],
                    "client_secret": config["client_secret"]
                }
            )
            token_response.raise_for_status()
            tokens = token_response.json()

            # Get user info
            access_token = tokens["access_token"]
            userinfo_response = await client.get(
                userinfo_url,
                headers={"Authorization": f"Bearer {access_token}"}
            )
            userinfo_response.raise_for_status()
            user_info = userinfo_response.json()

        # Normalize user info
        normalized = self._normalize_user_info(provider_type, user_info)

        return {
            "tokens": tokens,
            "user_info": normalized,
            "raw_user_info": user_info
        }

    def _normalize_user_info(
        self,
        provider_type: str,
        user_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Normalize user info from different providers."""
        if provider_type == "google":
            return {
                "sub": user_info.get("sub"),
                "email": user_info.get("email"),
                "email_verified": user_info.get("email_verified", False),
                "name": user_info.get("name"),
                "given_name": user_info.get("given_name"),
                "family_name": user_info.get("family_name"),
                "picture": user_info.get("picture")
            }
        elif provider_type == "microsoft":
            return {
                "sub": user_info.get("id"),
                "email": user_info.get("mail") or user_info.get("userPrincipalName"),
                "email_verified": True,
                "name": user_info.get("displayName"),
                "given_name": user_info.get("givenName"),
                "family_name": user_info.get("surname"),
                "picture": None
            }
        else:
            # Generic OIDC/Okta/OneLogin
            return {
                "sub": user_info.get("sub"),
                "email": user_info.get("email"),
                "email_verified": user_info.get("email_verified", False),
                "name": user_info.get("name"),
                "given_name": user_info.get("given_name"),
                "family_name": user_info.get("family_name"),
                "picture": user_info.get("picture")
            }

    # ==================== SAML FLOW ====================

    async def initiate_saml_login(
        self,
        sso_config: SSOConfiguration,
        relay_state: Optional[str] = None
    ) -> Dict[str, Any]:
        """Initiate SAML login flow."""
        import base64
        import zlib

        config = sso_config.config

        # Generate SAML AuthnRequest
        request_id = f"_{secrets.token_hex(16)}"
        issue_instant = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        authn_request = f"""<?xml version="1.0" encoding="UTF-8"?>
<samlp:AuthnRequest
    xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"
    xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion"
    ID="{request_id}"
    Version="2.0"
    IssueInstant="{issue_instant}"
    Destination="{config['sso_url']}"
    AssertionConsumerServiceURL="{config.get('acs_url', '')}"
    ProtocolBinding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST">
    <saml:Issuer>{config['entity_id']}</saml:Issuer>
    <samlp:NameIDPolicy
        Format="urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress"
        AllowCreate="true"/>
</samlp:AuthnRequest>"""

        # Deflate and base64 encode
        deflated = zlib.compress(authn_request.encode())[2:-4]
        encoded = base64.b64encode(deflated).decode()

        params = {"SAMLRequest": encoded}
        if relay_state:
            params["RelayState"] = relay_state

        auth_url = f"{config['sso_url']}?{urlencode(params)}"

        return {
            "auth_url": auth_url,
            "request_id": request_id,
            "provider": "saml"
        }

    async def handle_saml_callback(
        self,
        sso_config: SSOConfiguration,
        saml_response: str
    ) -> Dict[str, Any]:
        """Handle SAML callback and parse response."""
        import base64
        import xml.etree.ElementTree as ET

        config = sso_config.config

        # Decode SAML response
        decoded = base64.b64decode(saml_response)
        root = ET.fromstring(decoded)

        # SAML namespaces
        ns = {
            "samlp": "urn:oasis:names:tc:SAML:2.0:protocol",
            "saml": "urn:oasis:names:tc:SAML:2.0:assertion"
        }

        # Check status
        status_code = root.find(".//samlp:StatusCode", ns)
        if status_code is not None:
            status = status_code.get("Value", "")
            if "Success" not in status:
                raise ValueError(f"SAML authentication failed: {status}")

        # Extract user info from assertion
        name_id = root.find(".//saml:NameID", ns)
        email = name_id.text if name_id is not None else None

        # Extract attributes
        attributes = {}
        for attr in root.findall(".//saml:Attribute", ns):
            attr_name = attr.get("Name", "")
            values = [v.text for v in attr.findall("saml:AttributeValue", ns)]
            attributes[attr_name] = values[0] if len(values) == 1 else values

        return {
            "user_info": {
                "sub": email,
                "email": email,
                "email_verified": True,
                "name": attributes.get("displayName", attributes.get("name")),
                "given_name": attributes.get("firstName", attributes.get("givenName")),
                "family_name": attributes.get("lastName", attributes.get("sn"))
            },
            "attributes": attributes
        }

    # ==================== SESSION MANAGEMENT ====================

    async def create_sso_session(
        self,
        sso_config_id: UUID,
        user_id: UUID,
        provider_user_id: str,
        tokens: Dict[str, Any],
        user_info: Dict[str, Any]
    ) -> SSOSession:
        """Create an SSO session."""
        # Calculate token expiry
        expires_in = tokens.get("expires_in", 3600)
        token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

        session = SSOSession(
            id=uuid4(),
            sso_config_id=sso_config_id,
            user_id=user_id,
            provider_user_id=provider_user_id,
            access_token=tokens.get("access_token"),
            refresh_token=tokens.get("refresh_token"),
            id_token=tokens.get("id_token"),
            token_expires_at=token_expires_at,
            user_info=user_info,
            is_active=True,
            created_at=datetime.now(timezone.utc),
            last_activity_at=datetime.now(timezone.utc)
        )
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        return session

    async def get_sso_session(
        self,
        session_id: UUID
    ) -> Optional[SSOSession]:
        """Get SSO session by ID."""
        result = await self.db.execute(
            select(SSOSession).where(
                and_(
                    SSOSession.id == session_id,
                    SSOSession.is_active == True
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_user_sso_session(
        self,
        user_id: UUID
    ) -> Optional[SSOSession]:
        """Get active SSO session for a user."""
        result = await self.db.execute(
            select(SSOSession).where(
                and_(
                    SSOSession.user_id == user_id,
                    SSOSession.is_active == True
                )
            ).order_by(desc(SSOSession.last_activity_at))
        )
        return result.scalar_one_or_none()

    async def refresh_sso_session(
        self,
        session: SSOSession,
        sso_config: SSOConfiguration
    ) -> SSOSession:
        """Refresh SSO session tokens."""
        import httpx

        if not session.refresh_token:
            raise ValueError("No refresh token available")

        provider_type = sso_config.provider_type.value
        config = sso_config.config

        # Get token endpoint
        if provider_type == "google":
            token_url = "https://oauth2.googleapis.com/token"
        elif provider_type == "microsoft":
            tenant = config.get("tenant_id", "common")
            token_url = f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
        elif provider_type == "okta":
            domain = config["domain"]
            token_url = f"https://{domain}/oauth2/default/v1/token"
        elif provider_type == "oidc":
            issuer_url = config["issuer_url"].rstrip("/")
            token_url = f"{issuer_url}/token"
        else:
            raise ValueError(f"Token refresh not supported for {provider_type}")

        # Refresh tokens
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                token_url,
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": session.refresh_token,
                    "client_id": config["client_id"],
                    "client_secret": config["client_secret"]
                }
            )
            response.raise_for_status()
            tokens = response.json()

        # Update session
        session.access_token = tokens.get("access_token")
        if tokens.get("refresh_token"):
            session.refresh_token = tokens["refresh_token"]
        if tokens.get("id_token"):
            session.id_token = tokens["id_token"]

        expires_in = tokens.get("expires_in", 3600)
        session.token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
        session.last_activity_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(session)
        return session

    async def end_sso_session(
        self,
        session_id: UUID
    ) -> bool:
        """End an SSO session."""
        result = await self.db.execute(
            select(SSOSession).where(SSOSession.id == session_id)
        )
        session = result.scalar_one_or_none()

        if session:
            session.is_active = False
            session.ended_at = datetime.now(timezone.utc)
            await self.db.commit()
            return True
        return False

    async def cleanup_expired_sessions(self) -> int:
        """Clean up expired SSO sessions."""
        now = datetime.now(timezone.utc)

        result = await self.db.execute(
            select(SSOSession).where(
                and_(
                    SSOSession.is_active == True,
                    SSOSession.token_expires_at < now
                )
            )
        )
        expired_sessions = result.scalars().all()

        count = 0
        for session in expired_sessions:
            session.is_active = False
            session.ended_at = now
            count += 1

        await self.db.commit()
        return count

    # ==================== USER PROVISIONING ====================

    async def provision_sso_user(
        self,
        sso_config: SSOConfiguration,
        user_info: Dict[str, Any],
        venue_id: Optional[UUID] = None
    ) -> Tuple[UUID, bool]:
        """
        Provision or find user from SSO login.
        Returns (user_id, is_new_user).
        """
        from app.models import StaffUser as Staff

        email = user_info.get("email")
        if not email:
            raise ValueError("Email is required for SSO user provisioning")

        # Check domain whitelist
        domain = email.split("@")[-1]
        if sso_config.domain_whitelist and domain not in sso_config.domain_whitelist:
            raise ValueError(f"Email domain {domain} not allowed for this SSO configuration")

        # Check if user exists
        result = await self.db.execute(
            select(Staff).where(Staff.email == email)
        )
        existing_user = result.scalar_one_or_none()

        if existing_user:
            return existing_user.id, False

        # Auto-provision if enabled
        if not sso_config.auto_provision_users:
            raise ValueError("User not found and auto-provisioning is disabled")

        # Create new user
        new_user = Staff(
            id=uuid4(),
            venue_id=venue_id,
            email=email,
            name=user_info.get("name", email.split("@")[0]),
            role=sso_config.default_role,
            is_active=True,
            sso_provider_id=str(sso_config.id),
            sso_user_id=user_info.get("sub"),
            created_at=datetime.now(timezone.utc)
        )
        self.db.add(new_user)
        await self.db.commit()

        return new_user.id, True
