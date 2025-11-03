"""
Telegram bot with authentication and role-based commands
This is a simplified but functional implementation with key features.
"""
from datetime import datetime
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, ConversationHandler

from config import settings
from config.logging import get_logger
from repositories.user_repository import UserRepository
from core.database import get_session

log = get_logger(__name__)


# Authentication Middleware
async def auth_middleware(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Verify user is registered before processing commands

    Returns:
        True if authenticated, False otherwise
    """
    if not update.effective_user:
        return False

    telegram_user = update.effective_user

    try:
        async with get_session() as session:
            user_repo = UserRepository(session)
            user = await user_repo.get_by_telegram_id(telegram_user.id)

        if not user:
            await update.message.reply_text(
                "[ACCESS DENIED]\n\n"
                "Your phone number is not registered in the system.\n"
                "Please contact your administrator to get access."
            )
            log.warning(
                "unauthorized_access_attempt",
                telegram_id=telegram_user.id,
                username=telegram_user.username,
            )
            return False

        if not user.is_active:
            await update.message.reply_text(
                "[ACCOUNT DISABLED]\n\n"
                "Your account has been deactivated.\n"
                "Please contact your administrator."
            )
            return False

        # Store user in context
        context.user_data["db_user"] = user
        return True

    except Exception as e:
        log.error("auth_middleware_error", error=str(e))
        await update.message.reply_text("Authentication error. Please try again.")
        return False


# Command Handlers
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    if not update.effective_user:
        return

    telegram_user = update.effective_user

    try:
        async with get_session() as session:
            user_repo = UserRepository(session)
            user = await user_repo.get_by_telegram_id(telegram_user.id)

        # If user not found by Telegram ID, request phone verification
        if not user:
            contact_button = KeyboardButton(
                text="Share Phone Number",
                request_contact=True
            )
            keyboard = ReplyKeyboardMarkup(
                [[contact_button]],
                one_time_keyboard=True,
                resize_keyboard=True
            )

            await update.message.reply_text(
                "[PHONE VERIFICATION REQUIRED]\n\n"
                "To link your Telegram account with the system, "
                "please share your phone number by clicking the button below.\n\n"
                "Note: Your phone number must be registered in the system first. "
                "Contact your administrator if you don't have access.",
                reply_markup=keyboard
            )
            log.info(
                "phone_verification_requested",
                telegram_id=telegram_user.id,
                username=telegram_user.username
            )
            return

        # Check if user is active
        if not user.is_active:
            await update.message.reply_text(
                "[ACCOUNT DISABLED]\n\n"
                "Your account has been deactivated.\n"
                "Please contact your administrator."
            )
            return

        # User authenticated successfully
        message = (
            f"Welcome, {user.telegram_username or 'User'}!\n\n"
            f"Your role: {user.role}\n\n"
            f"Available commands:\n"
            f"/status - Show service status\n"
            f"/services - List your services\n"
            f"/alerts - Recent alerts\n"
            f"/mute <service> <hours> - Mute alerts\n"
            f"/unmute <service> - Unmute alerts\n"
            f"/muted - Show muted services\n\n"
        )

        if user.is_admin:
            message += (
                "Admin commands:\n"
                "/assign <user_id> <service_id> - Assign service\n"
                "/unassign <user_id> <service_id> - Remove access\n\n"
            )

        if user.is_super_admin:
            message += (
                "Super Admin commands:\n"
                "/add_user <phone> <role> [name] - Add user\n"
                "/add_service <name> <type> <url> - Add service\n"
                "/set_api_key <service_id> <key> - Set API key\n"
                "/list_users - List all users\n"
            )

        await update.message.reply_text(message, reply_markup=ReplyKeyboardRemove())

    except Exception as e:
        log.error("start_handler_error", error=str(e))
        await update.message.reply_text("An error occurred. Please try again.")


async def contact_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle contact sharing for phone verification"""
    if not update.effective_user or not update.message.contact:
        return

    telegram_user = update.effective_user
    contact = update.message.contact

    # Verify the contact is the user's own number
    if contact.user_id != telegram_user.id:
        await update.message.reply_text(
            "[VERIFICATION FAILED]\n\n"
            "You must share your own phone number, not someone else's.",
            reply_markup=ReplyKeyboardRemove()
        )
        return

    phone_number = contact.phone_number

    # Normalize phone number to E.164 format
    if not phone_number.startswith('+'):
        phone_number = '+' + phone_number

    try:
        async with get_session() as session:
            user_repo = UserRepository(session)

            # Look up user by phone number
            user = await user_repo.get_by_phone(phone_number)

            if not user:
                await update.message.reply_text(
                    "[ACCESS DENIED]\n\n"
                    f"Phone number {phone_number} is not registered in the system.\n"
                    "Please contact your administrator to get access.",
                    reply_markup=ReplyKeyboardRemove()
                )
                log.warning(
                    "phone_verification_failed_not_registered",
                    phone_number=phone_number,
                    telegram_id=telegram_user.id,
                    username=telegram_user.username
                )
                return

            # Check if user is active
            if not user.is_active:
                await update.message.reply_text(
                    "[ACCOUNT DISABLED]\n\n"
                    "Your account has been deactivated.\n"
                    "Please contact your administrator.",
                    reply_markup=ReplyKeyboardRemove()
                )
                return

            # Link Telegram account to database user
            await user_repo.update(
                user.id,
                telegram_user_id=telegram_user.id,
                telegram_username=telegram_user.username,
                first_name=telegram_user.first_name,
                last_name=telegram_user.last_name
            )

            await update.message.reply_text(
                "[VERIFICATION SUCCESSFUL]\n\n"
                f"Your Telegram account has been linked successfully!\n"
                f"Phone: {phone_number}\n"
                f"Role: {user.role}\n\n"
                "Please send /start again to see available commands.",
                reply_markup=ReplyKeyboardRemove()
            )

            log.info(
                "phone_verification_success",
                phone_number=phone_number,
                telegram_id=telegram_user.id,
                username=telegram_user.username,
                user_id=user.id,
                role=user.role
            )

    except Exception as e:
        log.error("contact_handler_error", error=str(e))
        await update.message.reply_text(
            "An error occurred during verification. Please try again.",
            reply_markup=ReplyKeyboardRemove()
        )


async def status_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /status command - show service health"""
    if not await auth_middleware(update, context):
        return

    user = context.user_data["db_user"]

    try:
        async with get_session() as session:
            from repositories.service_repository import ServiceRepository
            service_repo = ServiceRepository(session)

            # Get services based on role
            if user.is_super_admin:
                services = await service_repo.get_active_services()
            else:
                services = await service_repo.get_user_services(user.id)

        if not services:
            if user.is_super_admin:
                await update.message.reply_text(
                    "[NO SERVICES]\n\n"
                    "No services have been created yet.\n\n"
                    "Use `/add_service` to create your first service.",
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(
                    "[NO SERVICES]\n\n"
                    "You don't have access to any services yet.\n"
                    "Contact your administrator to get access."
                )
            return

        # Get health status for each service
        message = f"[SERVICE STATUS] ({len(services)} services)\n\n"

        async with get_session() as session:
            service_repo = ServiceRepository(session)

            for service in services:
                # Get latest health check
                health_check = await service_repo.get_latest_health_check(service.id)

                if health_check:
                    if health_check.is_healthy:
                        status_icon = "[UP]"
                        status_color = "HEALTHY"
                    else:
                        status_icon = "[DOWN]"
                        status_color = "UNHEALTHY"

                    # Calculate time since last check
                    time_diff = datetime.utcnow() - health_check.checked_at
                    if time_diff.total_seconds() < 60:
                        last_check = "just now"
                    elif time_diff.total_seconds() < 3600:
                        minutes = int(time_diff.total_seconds() / 60)
                        last_check = f"{minutes}m ago"
                    else:
                        hours = int(time_diff.total_seconds() / 3600)
                        last_check = f"{hours}h ago"

                    message += f"{status_icon} {service.name}\n"
                    message += f"   Status: {status_color}\n"
                    message += f"   Type: {service.service_type}\n"

                    if health_check.response_time_ms:
                        message += f"   Response: {health_check.response_time_ms}ms\n"

                    if health_check.status_code:
                        message += f"   HTTP: {health_check.status_code}\n"

                    message += f"   Last check: {last_check}\n"

                    if not health_check.is_healthy and health_check.error_message:
                        error_preview = health_check.error_message[:60]
                        if len(health_check.error_message) > 60:
                            error_preview += "..."
                        message += f"   Error: {error_preview}\n"
                else:
                    # No health check data yet
                    message += f"[UNKNOWN] {service.name}\n"
                    message += f"   Status: No health data yet\n"
                    message += f"   Type: {service.service_type}\n"

                message += "\n"

        # Split message if too long (Telegram limit is 4096 chars)
        if len(message) > 4000:
            # Send first part
            await update.message.reply_text(message[:4000] + "\n\n[continued...]")
            # Send remaining
            await update.message.reply_text(message[4000:])
        else:
            await update.message.reply_text(message)

    except Exception as e:
        log.error("status_handler_error", error=str(e))
        await update.message.reply_text("Error fetching service status. Please try again.")


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    if not await auth_middleware(update, context):
        return

    await update.message.reply_text(
        "[HELP]\n\n"
        "For detailed documentation, see README.md\n"
        "Contact your administrator for assistance."
    )


async def services_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /services command - list user's services"""
    if not await auth_middleware(update, context):
        return

    user = context.user_data["db_user"]

    try:
        async with get_session() as session:
            from repositories.service_repository import ServiceRepository
            service_repo = ServiceRepository(session)

            # Get services based on role
            if user.is_super_admin:
                services = await service_repo.get_active_services()
            else:
                services = await service_repo.get_user_services(user.id)

        if not services:
            if user.is_super_admin:
                await update.message.reply_text(
                    "[NO SERVICES]\n\n"
                    "No services have been created yet.\n\n"
                    "Use `/add_service` to create your first service.",
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(
                    "[NO SERVICES]\n\n"
                    "You don't have access to any services yet.\n"
                    "Contact your administrator to get access."
                )
            return

        # Format services list
        message = f"[YOUR SERVICES] ({len(services)} total)\n\n"
        for service in services:
            status_emoji = "UP" if service.is_active else "DOWN"
            url = service.endpoint_url or "N/A"
            message += (
                f"[{status_emoji}] {service.name} (ID: {service.id})\n"
                f"   Type: {service.service_type}\n"
                f"   Environment: {service.environment}\n"
                f"   URL: {url}\n"
                f"   Check Interval: {service.check_interval_seconds}s\n\n"
            )

        await update.message.reply_text(message)

    except Exception as e:
        log.error("services_handler_error", error=str(e))
        await update.message.reply_text("Error fetching services. Please try again.")


async def alerts_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /alerts command - show recent alerts"""
    if not await auth_middleware(update, context):
        return

    user = context.user_data["db_user"]

    try:
        async with get_session() as session:
            from repositories.alert_repository import AlertRepository
            alert_repo = AlertRepository(session)

            alerts = await alert_repo.get_user_alerts(user.id, limit=10)

        if not alerts:
            await update.message.reply_text(
                "[NO ALERTS]\n\n"
                "No recent alerts for your services."
            )
            return

        # Format alerts list
        message = f"[RECENT ALERTS] ({len(alerts)} total)\n\n"
        for alert in alerts:
            status = "ACTIVE" if not alert.resolved_at else "RESOLVED"
            severity_icon = {
                "critical": "[CRIT]",
                "high": "[HIGH]",
                "medium": "[MED]",
                "low": "[LOW]"
            }.get(alert.severity, "[INFO]")

            message += (
                f"{severity_icon} [{status}]\n"
                f"Service: {alert.service_id}\n"
                f"Type: {alert.alert_type}\n"
                f"Created: {alert.created_at.strftime('%Y-%m-%d %H:%M')}\n"
            )
            if alert.message:
                message += f"Message: {alert.message[:50]}...\n"
            message += "\n"

        await update.message.reply_text(message)

    except Exception as e:
        log.error("alerts_handler_error", error=str(e))
        await update.message.reply_text("Error fetching alerts. Please try again.")


async def mute_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /mute command - mute service alerts"""
    if not await auth_middleware(update, context):
        return

    user = context.user_data["db_user"]

    # Parse arguments
    if len(context.args) < 2:
        await update.message.reply_text(
            "[USAGE]\n\n"
            "/mute <service_id> <hours>\n\n"
            "Example: /mute 1 24"
        )
        return

    try:
        service_id = int(context.args[0])
        hours = int(context.args[1])

        if hours < 1 or hours > 168:  # Max 1 week
            await update.message.reply_text(
                "[INVALID DURATION]\n\n"
                "Hours must be between 1 and 168 (1 week)."
            )
            return

        from datetime import timedelta
        muted_until = datetime.utcnow() + timedelta(hours=hours)

        async with get_session() as session:
            from repositories.alert_repository import AlertRepository
            alert_repo = AlertRepository(session)

            await alert_repo.mute_service(
                user_id=user.id,
                service_id=service_id,
                muted_until=muted_until,
                command="/mute"
            )
            await session.commit()

        await update.message.reply_text(
            "[SERVICE MUTED]\n\n"
            f"Service ID: {service_id}\n"
            f"Duration: {hours} hours\n"
            f"Muted until: {muted_until.strftime('%Y-%m-%d %H:%M UTC')}"
        )

        log.info(
            "service_muted",
            user_id=user.id,
            service_id=service_id,
            hours=hours
        )

    except ValueError:
        await update.message.reply_text(
            "[INVALID INPUT]\n\n"
            "Service ID and hours must be numbers."
        )
    except Exception as e:
        log.error("mute_handler_error", error=str(e))
        await update.message.reply_text("Error muting service. Please try again.")


async def unmute_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /unmute command - unmute service alerts"""
    if not await auth_middleware(update, context):
        return

    user = context.user_data["db_user"]

    # Parse arguments
    if len(context.args) < 1:
        await update.message.reply_text(
            "[USAGE]\n\n"
            "/unmute <service_id>\n\n"
            "Example: /unmute 1"
        )
        return

    try:
        service_id = int(context.args[0])

        async with get_session() as session:
            from repositories.alert_repository import AlertRepository
            alert_repo = AlertRepository(session)

            success = await alert_repo.unmute_service(user.id, service_id)
            await session.commit()

        if success:
            await update.message.reply_text(
                "[SERVICE UNMUTED]\n\n"
                f"Service ID: {service_id}\n"
                "Alerts enabled."
            )
            log.info("service_unmuted", user_id=user.id, service_id=service_id)
        else:
            await update.message.reply_text(
                "[NOT MUTED]\n\n"
                f"Service ID {service_id} was not muted."
            )

    except ValueError:
        await update.message.reply_text(
            "[INVALID INPUT]\n\n"
            "Service ID must be a number."
        )
    except Exception as e:
        log.error("unmute_handler_error", error=str(e))
        await update.message.reply_text("Error unmuting service. Please try again.")


async def muted_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /muted command - show muted services"""
    if not await auth_middleware(update, context):
        return

    user = context.user_data["db_user"]

    try:
        async with get_session() as session:
            from repositories.alert_repository import AlertRepository
            from repositories.service_repository import ServiceRepository
            alert_repo = AlertRepository(session)
            service_repo = ServiceRepository(session)

            muted_services = await alert_repo.get_muted_services(user.id)

        if not muted_services:
            await update.message.reply_text(
                "[NO MUTED SERVICES]\n\n"
                "You have no muted services."
            )
            return

        # Format muted services list
        message = f"[MUTED SERVICES] ({len(muted_services)} total)\n\n"
        for muted in muted_services:
            time_remaining = muted.muted_until - datetime.utcnow()
            hours_remaining = int(time_remaining.total_seconds() / 3600)

            message += (
                f"Service ID: {muted.service_id}\n"
                f"Muted until: {muted.muted_until.strftime('%Y-%m-%d %H:%M UTC')}\n"
                f"Time remaining: ~{hours_remaining} hours\n\n"
            )

        await update.message.reply_text(message)

    except Exception as e:
        log.error("muted_handler_error", error=str(e))
        await update.message.reply_text("Error fetching muted services. Please try again.")


async def assign_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /assign command - assign service to user (Admin only)"""
    if not await auth_middleware(update, context):
        return

    user = context.user_data["db_user"]

    if not user.is_admin:
        await update.message.reply_text(
            "[ACCESS DENIED]\n\n"
            "This command requires admin privileges."
        )
        return

    # Parse arguments
    if len(context.args) < 2:
        await update.message.reply_text(
            "[USAGE]\n\n"
            "/assign <user_id> <service_id>\n\n"
            "Examples:\n"
            "`/assign 1 5`\n"
            "`/assign 2 3`\n\n"
            "Tip: Use `/list_users` to see user IDs",
            parse_mode='Markdown'
        )
        return

    try:
        user_id = int(context.args[0])
        service_id = int(context.args[1])
    except ValueError:
        await update.message.reply_text(
            "[INVALID INPUT]\n\n"
            "Both user_id and service_id must be numbers."
        )
        return

    try:
        async with get_session() as session:
            from models.user import UserServicePermission
            user_repo = UserRepository(session)
            from repositories.service_repository import ServiceRepository
            service_repo = ServiceRepository(session)

            # Get target user
            target_user = await user_repo.get_by_id(user_id)
            if not target_user:
                await update.message.reply_text(
                    "[USER NOT FOUND]\n\n"
                    f"No user found with ID: {user_id}\n\n"
                    "Use `/list_users` to see all user IDs",
                    parse_mode='Markdown'
                )
                return

            # Get service
            service = await service_repo.get_by_id(service_id)
            if not service:
                await update.message.reply_text(
                    "[SERVICE NOT FOUND]\n\n"
                    f"No service found with ID: {service_id}\n\n"
                    "Use `/services` to see all service IDs",
                    parse_mode='Markdown'
                )
                return

            # Check if already assigned
            from sqlalchemy import select
            result = await session.execute(
                select(UserServicePermission).where(
                    UserServicePermission.user_id == target_user.id,
                    UserServicePermission.service_id == service_id
                )
            )
            existing = result.scalar_one_or_none()

            if existing:
                await update.message.reply_text(
                    "[ALREADY ASSIGNED]\n\n"
                    f"User {target_user.full_name} (ID: {user_id}) already has access to {service.name}"
                )
                return

            # Create permission
            permission = UserServicePermission(
                user_id=target_user.id,
                service_id=service_id,
                can_receive_alerts=True,
                can_mute=True
            )
            session.add(permission)
            await session.commit()

        await update.message.reply_text(
            "[SERVICE ASSIGNED]\n\n"
            f"User: {target_user.full_name} (ID: {user_id})\n"
            f"Phone: {target_user.phone_number}\n"
            f"Service: {service.name} (ID: {service_id})\n"
            f"Permissions: Receive alerts, Mute"
        )

        log.info(
            "service_assigned",
            admin_id=user.id,
            target_user_id=target_user.id,
            service_id=service_id
        )

    except Exception as e:
        log.error("assign_handler_error", error=str(e))
        await update.message.reply_text("Error assigning service. Please try again.")


async def unassign_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /unassign command - remove service access (Admin only)"""
    if not await auth_middleware(update, context):
        return

    user = context.user_data["db_user"]

    if not user.is_admin:
        await update.message.reply_text(
            "[ACCESS DENIED]\n\n"
            "This command requires admin privileges."
        )
        return

    # Parse arguments
    if len(context.args) < 2:
        await update.message.reply_text(
            "[USAGE]\n\n"
            "/unassign <user_id> <service_id>\n\n"
            "Examples:\n"
            "`/unassign 1 5`\n"
            "`/unassign 2 3`\n\n"
            "Tip: Use `/list_users` to see user IDs",
            parse_mode='Markdown'
        )
        return

    try:
        user_id = int(context.args[0])
        service_id = int(context.args[1])
    except ValueError:
        await update.message.reply_text(
            "[INVALID INPUT]\n\n"
            "Both user_id and service_id must be numbers."
        )
        return

    try:
        async with get_session() as session:
            from models.user import UserServicePermission
            from sqlalchemy import delete
            user_repo = UserRepository(session)
            from repositories.service_repository import ServiceRepository
            service_repo = ServiceRepository(session)

            # Get target user
            target_user = await user_repo.get_by_id(user_id)
            if not target_user:
                await update.message.reply_text(
                    "[USER NOT FOUND]\n\n"
                    f"No user found with ID: {user_id}\n\n"
                    "Use `/list_users` to see all user IDs",
                    parse_mode='Markdown'
                )
                return

            # Get service for logging
            service = await service_repo.get_by_id(service_id)

            # Delete permission
            stmt = delete(UserServicePermission).where(
                UserServicePermission.user_id == target_user.id,
                UserServicePermission.service_id == service_id
            )
            result = await session.execute(stmt)
            await session.commit()

        if result.rowcount > 0:
            service_name = service.name if service else f"ID {service_id}"
            await update.message.reply_text(
                "[SERVICE UNASSIGNED]\n\n"
                f"User: {target_user.full_name} (ID: {user_id})\n"
                f"Service: {service_name}\n"
                f"Access removed successfully"
            )
            log.info(
                "service_unassigned",
                admin_id=user.id,
                target_user_id=target_user.id,
                service_id=service_id
            )
        else:
            await update.message.reply_text(
                "[NOT ASSIGNED]\n\n"
                f"User {target_user.full_name} (ID: {user_id}) doesn't have access to service {service_id}"
            )

    except Exception as e:
        log.error("unassign_handler_error", error=str(e))
        await update.message.reply_text("Error unassigning service. Please try again.")


async def add_user_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /add_user command - add new user (Super Admin only)"""
    if not await auth_middleware(update, context):
        return

    user = context.user_data["db_user"]

    if not user.is_super_admin:
        await update.message.reply_text(
            "[ACCESS DENIED]\n\n"
            "This command requires super admin privileges."
        )
        return

    # Parse arguments
    if len(context.args) < 2:
        await update.message.reply_text(
            "[USAGE]\n\n"
            "/add_user <phone> <role> [first_name] [last_name]\n\n"
            "Roles: viewer, admin, super_admin\n\n"
            "Examples:\n"
            "/add_user +989123456789 admin\n"
            "/add_user +989123456789 admin John Doe"
        )
        return

    phone = context.args[0]
    role = context.args[1]
    first_name = context.args[2] if len(context.args) > 2 else None
    last_name = context.args[3] if len(context.args) > 3 else None

    from models.user import UserRole

    # Validate role
    try:
        role_enum = UserRole(role)
    except ValueError:
        await update.message.reply_text(
            "[INVALID ROLE]\n\n"
            "Valid roles: viewer, admin, super_admin"
        )
        return

    try:
        async with get_session() as session:
            user_repo = UserRepository(session)

            # Check if user already exists
            existing_user = await user_repo.get_by_phone(phone)
            if existing_user:
                await update.message.reply_text(
                    "[USER EXISTS]\n\n"
                    f"User with phone {phone} already exists.\n"
                    f"Name: {existing_user.full_name}\n"
                    f"Role: {existing_user.role}\n"
                    f"Active: {existing_user.is_active}"
                )
                return

            # Create new user
            new_user = await user_repo.create(
                phone_number=phone,
                role=role_enum,
                first_name=first_name,
                last_name=last_name,
                is_active=True
            )
            await session.commit()

        await update.message.reply_text(
            "[USER CREATED]\n\n"
            f"Phone: {phone}\n"
            f"Name: {new_user.full_name}\n"
            f"Role: {role}\n"
            f"User ID: {new_user.id}\n"
            f"Active: True\n\n"
            "User can now verify their Telegram account by sending /start to this bot."
        )

        log.info(
            "user_created_via_bot",
            admin_id=user.id,
            new_user_id=new_user.id,
            phone=phone,
            role=role,
            name=new_user.full_name
        )

    except Exception as e:
        log.error("add_user_handler_error", error=str(e))
        await update.message.reply_text("Error creating user. Please try again.")


# OLD add_service_handler removed - Replaced with interactive conversation flow
# See telegram_bot/service_config_conversation.py for the new implementation


async def set_api_key_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /set_api_key command - set API key for a service (Super Admin only)"""
    if not await auth_middleware(update, context):
        return

    user = context.user_data["db_user"]

    if not user.is_super_admin:
        await update.message.reply_text(
            "[ACCESS DENIED]\n\n"
            "This command requires super admin privileges."
        )
        return

    # Parse arguments
    if len(context.args) < 2:
        await update.message.reply_text(
            "[USAGE]\n\n"
            "/set_api_key <service_id> <api_key>\n\n"
            "Examples:\n"
            "`/set_api_key 1 sk-or-v1-abc123...`\n\n"
            "Note: The API key will be encrypted before storage",
            parse_mode='Markdown'
        )
        return

    try:
        service_id = int(context.args[0])
        api_key = context.args[1]
    except ValueError:
        await update.message.reply_text(
            "[INVALID INPUT]\n\n"
            "Service ID must be a number."
        )
        return

    try:
        from config import settings
        from cryptography.fernet import Fernet

        # Encrypt the API key
        fernet = Fernet(settings.encryption_key.encode())
        encrypted_key = fernet.encrypt(api_key.encode()).decode()

        async with get_session() as session:
            from repositories.service_repository import ServiceRepository
            service_repo = ServiceRepository(session)

            # Get service
            service = await service_repo.get_by_id(service_id)
            if not service:
                await update.message.reply_text(
                    "[SERVICE NOT FOUND]\n\n"
                    f"No service found with ID: {service_id}\n\n"
                    "Use `/services` to see all service IDs",
                    parse_mode='Markdown'
                )
                return

            # Verify it's an API credit service
            if service.service_type != "api_credit":
                await update.message.reply_text(
                    "[INVALID SERVICE TYPE]\n\n"
                    f"Service '{service.name}' is a {service.service_type} service.\n"
                    "API keys can only be set for api_credit services."
                )
                return

            # Update service with encrypted API key
            await service_repo.update(service_id, api_key_encrypted=encrypted_key)
            await session.commit()

        # Delete the message containing the key for security
        try:
            await update.message.delete()
        except:
            pass  # If deletion fails, continue anyway

        await update.message.reply_text(
            "[API KEY CONFIGURED]\n\n"
            f"Service: {service.name} (ID: {service_id})\n"
            f"API Key: {'*' * 20}...{api_key[-8:]}\n\n"
            "The API key has been encrypted and stored securely.\n"
            "Your message containing the key has been deleted for security."
        )

        log.info(
            "api_key_set",
            admin_id=user.id,
            service_id=service_id,
            service_name=service.name
        )

    except Exception as e:
        log.error("set_api_key_handler_error", error=str(e))
        await update.message.reply_text(f"Error setting API key: {str(e)}")


async def set_tracking_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /set_tracking command - configure API tracking methods (Super Admin only)"""
    if not await auth_middleware(update, context):
        return

    user = context.user_data["db_user"]

    if not user.is_super_admin:
        await update.message.reply_text(
            "[ACCESS DENIED]\n\n"
            "This command requires super admin privileges."
        )
        return

    # Parse arguments
    if len(context.args) < 1:
        await update.message.reply_text(
            "[USAGE]\n\n"
            "/set_tracking <service_id> [methods] [key_path] [credits_path]\n\n"
            "*Methods:* Comma-separated list (default: key_management,credits)\n"
            "  • key_management - Detailed usage tracking\n"
            "  • credits - Simple balance tracking\n\n"
            "*Paths:* API endpoint paths (optional)\n"
            "  • key_path - Default: /api/v1/key\n"
            "  • credits_path - Default: /api/v1/credits\n\n"
            "*Examples:*\n"
            "`/set_tracking 1`  (use defaults)\n"
            "`/set_tracking 1 key_management`\n"
            "`/set_tracking 1 credits`\n"
            "`/set_tracking 1 key_management,credits /v1/key /v1/credits`",
            parse_mode='Markdown'
        )
        return

    try:
        service_id = int(context.args[0])

        # Parse methods (default: both)
        methods_str = context.args[1] if len(context.args) > 1 else "key_management,credits"
        methods = [m.strip() for m in methods_str.split(",")]

        # Validate methods
        valid_methods = ["key_management", "credits"]
        for method in methods:
            if method not in valid_methods:
                await update.message.reply_text(
                    f"[INVALID METHOD]\n\n"
                    f"'{method}' is not a valid tracking method.\n"
                    f"Valid methods: {', '.join(valid_methods)}"
                )
                return

        # Parse paths (optional)
        key_path = context.args[2] if len(context.args) > 2 else "/api/v1/key"
        credits_path = context.args[3] if len(context.args) > 3 else "/api/v1/credits"

    except ValueError:
        await update.message.reply_text(
            "[INVALID INPUT]\n\n"
            "Service ID must be a number."
        )
        return

    try:
        from config import settings
        async with get_session() as session:
            from repositories.service_repository import ServiceRepository
            service_repo = ServiceRepository(session)

            # Get service
            service = await service_repo.get_by_id(service_id)
            if not service:
                await update.message.reply_text(
                    "[SERVICE NOT FOUND]\n\n"
                    f"No service found with ID: {service_id}\n\n"
                    "Use `/services` to see all service IDs",
                    parse_mode='Markdown'
                )
                return

            # Verify it's an API credit service
            if service.service_type != "api_credit":
                await update.message.reply_text(
                    "[INVALID SERVICE TYPE]\n\n"
                    f"Service '{service.name}' is a {service.service_type} service.\n"
                    "Tracking can only be configured for api_credit services."
                )
                return

            # Build tracking config
            tracking_config = {
                "methods": methods,
                "key_management_path": key_path,
                "credits_path": credits_path
            }

            # Update service
            await service_repo.update(service_id, api_tracking_config=tracking_config)
            await session.commit()

        await update.message.reply_text(
            "[TRACKING CONFIGURED]\n\n"
            f"Service: {service.name} (ID: {service_id})\n"
            f"Methods: {', '.join(methods)}\n"
            f"Key endpoint: {service.endpoint_url}{key_path}\n"
            f"Credits endpoint: {service.endpoint_url}{credits_path}\n\n"
            "Tracking configuration updated successfully."
        )

        log.info(
            "tracking_configured",
            admin_id=user.id,
            service_id=service_id,
            methods=methods
        )

    except Exception as e:
        log.error("set_tracking_handler_error", error=str(e))
        await update.message.reply_text(f"Error configuring tracking: {str(e)}")


async def list_users_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /list_users command - list all users (Super Admin only)"""
    if not await auth_middleware(update, context):
        return

    user = context.user_data["db_user"]

    if not user.is_super_admin:
        await update.message.reply_text(
            "[ACCESS DENIED]\n\n"
            "This command requires super admin privileges."
        )
        return

    try:
        async with get_session() as session:
            user_repo = UserRepository(session)
            users = await user_repo.get_all(limit=50)  # Limit to 50 to avoid long messages

        if not users:
            await update.message.reply_text(
                "[NO USERS]\n\n"
                "No users found in the system."
            )
            return

        # Format users list
        message = f"[USERS LIST] ({len(users)} total)\n\n"
        for u in users:
            status = "ACTIVE" if u.is_active else "INACTIVE"
            telegram = f"@{u.telegram_username}" if u.telegram_username else "Not linked"

            message += (
                f"[{status}] {u.role}\n"
                f"Name: {u.full_name}\n"
                f"Phone: {u.phone_number}\n"
                f"Telegram: {telegram}\n"
                f"ID: {u.id}\n\n"
            )

        # Split message if too long (Telegram limit is 4096 chars)
        if len(message) > 4000:
            await update.message.reply_text(
                f"[USERS LIST] ({len(users)} total)\n\n"
                "Too many users to display. Showing first 20..."
            )
            message = f"[USERS LIST] (first 20)\n\n"
            for u in users[:20]:
                status = "ACTIVE" if u.is_active else "INACTIVE"
                telegram = f"@{u.telegram_username}" if u.telegram_username else "Not linked"
                message += (
                    f"[{status}] {u.role}\n"
                    f"Name: {u.full_name}\n"
                    f"Phone: {u.phone_number}\n"
                    f"Telegram: {telegram}\n"
                    f"ID: {u.id}\n\n"
                )

        await update.message.reply_text(message)

    except Exception as e:
        log.error("list_users_handler_error", error=str(e))
        await update.message.reply_text("Error fetching users. Please try again.")


def create_bot(environment: str) -> Application:
    """
    Create Telegram bot application

    Args:
        environment: Environment (dev uses sandbox bot, stage/prod uses main bot)

    Returns:
        Telegram Application
    """
    # Select bot based on environment
    if environment == "dev":
        token = settings.telegram_sandbox_bot_token
        bot_name = settings.telegram_sandbox_bot_username
    else:
        token = settings.telegram_main_bot_token
        bot_name = settings.telegram_main_bot_username

    log.info("creating_telegram_bot", environment=environment, bot_username=bot_name)

    # Create application
    application = Application.builder().token(token).build()

    # Register command handlers - Authentication & Core
    application.add_handler(CommandHandler("start", start_handler))
    application.add_handler(CommandHandler("help", help_handler))
    application.add_handler(CommandHandler("status", status_handler))

    # Register contact handler for phone verification
    application.add_handler(MessageHandler(filters.CONTACT, contact_handler))

    # User commands
    application.add_handler(CommandHandler("services", services_handler))
    application.add_handler(CommandHandler("alerts", alerts_handler))
    application.add_handler(CommandHandler("mute", mute_handler))
    application.add_handler(CommandHandler("unmute", unmute_handler))
    application.add_handler(CommandHandler("muted", muted_handler))

    # Admin commands
    application.add_handler(CommandHandler("assign", assign_handler))
    application.add_handler(CommandHandler("unassign", unassign_handler))

    # Super Admin commands
    application.add_handler(CommandHandler("add_user", add_user_handler))

    # Add service conversation handler (interactive flow)
    from telegram_bot.service_config_conversation import get_add_service_conversation_handler
    application.add_handler(get_add_service_conversation_handler())

    application.add_handler(CommandHandler("set_api_key", set_api_key_handler))
    application.add_handler(CommandHandler("set_tracking", set_tracking_handler))
    application.add_handler(CommandHandler("list_users", list_users_handler))

    log.info("telegram_bot_created", bot_username=bot_name, handlers=len(application.handlers))

    return application


async def start_bot(application: Application) -> None:
    """Start Telegram bot"""
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    log.info("telegram_bot_started")


async def stop_bot(application: Application) -> None:
    """Stop Telegram bot"""
    if application is None:
        return

    try:
        # Only stop updater if it was started
        if application.updater and application.updater.running:
            await application.updater.stop()
    except Exception as e:
        log.warning("error_stopping_updater", error=str(e))

    try:
        if application.running:
            await application.stop()
    except Exception as e:
        log.warning("error_stopping_application", error=str(e))

    try:
        await application.shutdown()
    except Exception as e:
        log.warning("error_shutting_down_application", error=str(e))

    log.info("telegram_bot_stopped")
