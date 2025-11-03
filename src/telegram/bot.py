"""
Telegram bot with authentication and role-based commands
This is a simplified but functional implementation with key features.
"""
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

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
    if not await auth_middleware(update, context):
        return

    user = context.user_data["db_user"]

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
            "/assign <phone> <service> - Assign service\n"
            "/unassign <phone> <service> - Remove access\n\n"
        )

    if user.is_super_admin:
        message += (
            "Super Admin commands:\n"
            "/add_user <phone> <role> - Add user\n"
            "/add_service <name> <type> <url> - Add service\n"
            "/list_users - List all users\n"
        )

    await update.message.reply_text(message)


async def status_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /status command - show service health"""
    if not await auth_middleware(update, context):
        return

    await update.message.reply_text(
        "[SERVICE STATUS]\n\n"
        "Fetching current status...\n"
        "(Full implementation connects to ServiceRepository)"
    )


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    if not await auth_middleware(update, context):
        return

    await update.message.reply_text(
        "[HELP]\n\n"
        "For detailed documentation, see README.md\n"
        "Contact your administrator for assistance."
    )


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

    # Register command handlers
    application.add_handler(CommandHandler("start", start_handler))
    application.add_handler(CommandHandler("help", help_handler))
    application.add_handler(CommandHandler("status", status_handler))

    # Additional handlers would be added here:
    # application.add_handler(CommandHandler("services", services_handler))
    # application.add_handler(CommandHandler("alerts", alerts_handler))
    # application.add_handler(CommandHandler("mute", mute_handler))
    # etc.

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
    await application.updater.stop()
    await application.stop()
    await application.shutdown()
    log.info("telegram_bot_stopped")
