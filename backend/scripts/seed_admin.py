"""Seed the initial Administrator account for InfraScan Module 1 RBAC."""

import argparse
import asyncio
import logging
import sys
import uuid

from sqlalchemy import select

from backend.app.core.config import settings
from backend.app.core.security import hash_password
from backend.app.db.session import AsyncSessionLocal
from backend.app.models.user import User, UserRole
from backend.app.services.audit_service import record_audit_event

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("seed_admin")


async def seed_admin(
    email: str,
    password: str,
    full_name: str,
    session_factory=None,
) -> None:
    """Create or elevate the initial Admin account in PostgreSQL."""
    maker = session_factory or AsyncSessionLocal
    async with maker() as session:
        # Check if user already exists
        existing_user = await session.scalar(select(User).where(User.email == email.strip().lower()))

        if existing_user:
            logger.info("User with email '%s' already exists (ID: %s).", email, existing_user.id)
            if existing_user.role != UserRole.ADMIN:
                existing_user.role = UserRole.ADMIN
                existing_user.is_active = True
                await session.commit()
                await record_audit_event(
                    session,
                    action="USER_ELEVATED_TO_ADMIN",
                    resource_type="USER",
                    resource_id=existing_user.id,
                    user_id=existing_user.id,
                )
                logger.info("Successfully elevated '%s' to role: ADMIN.", email)
            else:
                logger.info("Account '%s' is already an active Administrator. No changes required.", email)
            return

        # Create new Admin user
        admin_user = User(
            id=uuid.uuid4(),
            full_name=full_name.strip(),
            email=email.strip().lower(),
            password_hash=hash_password(password),
            role=UserRole.ADMIN,
            is_active=True,
        )
        session.add(admin_user)
        await session.commit()
        await session.refresh(admin_user)

        await record_audit_event(
            session,
            action="INITIAL_ADMIN_SEEDED",
            resource_type="USER",
            resource_id=admin_user.id,
            user_id=admin_user.id,
        )

        logger.info("=================================================================")
        logger.info(" Initial Administrator Account Successfully Created")
        logger.info("=================================================================")
        logger.info(" Admin ID:    %s", admin_user.id)
        logger.info(" Full Name:   %s", admin_user.full_name)
        logger.info(" Email:       %s", admin_user.email)
        logger.info(" Role:        %s", admin_user.role.value)
        logger.info(" Is Active:   %s", admin_user.is_active)
        logger.info(" Password:    [PROTECTED via Argon2id]")
        logger.info("=================================================================")


def main():
    parser = argparse.ArgumentParser(description="Seed initial Administrator account for InfraScan.")
    parser.add_argument("--email", default=settings.FIRST_ADMIN_EMAIL, help="Admin email address")
    parser.add_argument("--password", default=settings.FIRST_ADMIN_PASSWORD, help="Admin plain-text password to hash")
    parser.add_argument("--name", default=settings.FIRST_ADMIN_NAME, help="Admin full name")
    args = parser.parse_args()

    asyncio.run(seed_admin(email=args.email, password=args.password, full_name=args.name))


if __name__ == "__main__":
    main()
