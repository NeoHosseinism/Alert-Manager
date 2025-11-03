"""
Interactive conversation flow for configuring API credit tracking services

Supports both pre-defined providers (OpenRouter, etc.) and custom providers
with guided configuration through multi-step conversation.
"""
import json
from typing import Dict, Any
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters
)

from config import settings
from config.logging import get_logger
from config.providers import get_provider, list_providers, STANDARD_METRICS
from repositories.service_repository import ServiceRepository
from core.database import get_session

log = get_logger(__name__)


# Helper function for MarkdownV2 escaping
def escape_markdown_v2(text: str) -> str:
    """Escape special characters for Telegram MarkdownV2 format"""
    chars_to_escape = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in chars_to_escape:
        text = text.replace(char, f'\\{char}')
    return text


# Conversation states
(
    CHOOSE_SERVICE_TYPE,
    ENTER_BASIC_INFO,
    CHOOSE_PROVIDER_MODE,
    SELECT_PROVIDER,
    CUSTOM_BASE_URL,
    CUSTOM_ENDPOINT_COUNT,
    CUSTOM_ENDPOINT_CONFIG,
    CUSTOM_FIELD_MAPPING,
    CONFIRM_CONFIG,
) = range(9)


async def add_service_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the add service conversation"""
    # Import here to avoid circular imports
    from telegram_bot.bot import auth_middleware

    if not await auth_middleware(update, context):
        return ConversationHandler.END

    user = context.user_data["db_user"]
    if not user.is_super_admin:
        await update.message.reply_text(
            "[ACCESS DENIED]\n\nThis command requires super admin privileges."
        )
        return ConversationHandler.END

    # Initialize conversation data
    context.user_data["service_config"] = {}

    keyboard = [
        [InlineKeyboardButton("Health Check", callback_data="type_health_check")],
        [InlineKeyboardButton("API Credit Tracking", callback_data="type_api_credit")],
        [InlineKeyboardButton("Cancel", callback_data="cancel")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "[SERVICE SETUP - Step 1/5]\n\n"
        "What type of service do you want to add?",
        reply_markup=reply_markup
    )

    return CHOOSE_SERVICE_TYPE


async def choose_service_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle service type selection"""
    query = update.callback_query
    await query.answer()

    if query.data == "cancel":
        await query.edit_message_text("[CANCELLED]\n\nService creation cancelled.")
        return ConversationHandler.END

    service_type = query.data.replace("type_", "")
    context.user_data["service_config"]["service_type"] = service_type

    if service_type == "health_check":
        # Simple flow for health check
        await query.edit_message_text(
            "*SERVICE SETUP \\- Step 2/5*\n\n"
            "Enter service details in this format:\n\n"
            "<name> <url> \\[interval\\_seconds\\]\n\n"
            "Example:\n"
            "`MyAPI https://api\\.example\\.com/health 300`\n\n"
            "Or type /cancel to cancel\\.",
            parse_mode='MarkdownV2'
        )
        return ENTER_BASIC_INFO

    # API Credit flow - ask about provider mode
    keyboard = [
        [InlineKeyboardButton("Pre-defined Provider (OpenRouter, etc.)", callback_data="mode_predefined")],
        [InlineKeyboardButton("Custom Provider (Interactive Setup)", callback_data="mode_custom")],
        [InlineKeyboardButton("Cancel", callback_data="cancel")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        "[SERVICE SETUP - Step 2/5]\n\n"
        "Choose provider configuration mode:",
        reply_markup=reply_markup
    )

    return CHOOSE_PROVIDER_MODE


async def choose_provider_mode(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle provider mode selection"""
    query = update.callback_query
    await query.answer()

    if query.data == "cancel":
        await query.edit_message_text("[CANCELLED]\n\nService creation cancelled.")
        return ConversationHandler.END

    mode = query.data.replace("mode_", "")
    context.user_data["service_config"]["provider_mode"] = mode

    if mode == "predefined":
        # Show list of pre-defined providers
        providers = list_providers()
        keyboard = []

        for provider in providers:
            keyboard.append([
                InlineKeyboardButton(
                    f"{provider.name} - {provider.description}",
                    callback_data=f"provider_{provider.provider_id}"
                )
            ])

        keyboard.append([InlineKeyboardButton("Cancel", callback_data="cancel")])
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            "[SERVICE SETUP - Step 3/5]\n\n"
            "Select a pre-defined provider:",
            reply_markup=reply_markup
        )

        return SELECT_PROVIDER

    # Custom provider flow
    await query.edit_message_text(
        "*SERVICE SETUP \\- Step 3/5*\n\n"
        "Let's configure your custom API provider\\.\n\n"
        "First, enter the service name and base URL:\n\n"
        "<service\\_name> <base\\_url>\n\n"
        "Example:\n"
        "`MyAPI https://api\\.myprovider\\.com`\n\n"
        "Or type /cancel to cancel\\.",
        parse_mode='MarkdownV2'
    )

    return CUSTOM_BASE_URL


async def select_provider(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle pre-defined provider selection"""
    query = update.callback_query
    await query.answer()

    if query.data == "cancel":
        await query.edit_message_text("[CANCELLED]\n\nService creation cancelled.")
        return ConversationHandler.END

    provider_id = query.data.replace("provider_", "")
    provider = get_provider(provider_id)

    if not provider:
        await query.edit_message_text("[ERROR]\n\nProvider not found.")
        return ConversationHandler.END

    context.user_data["service_config"]["provider"] = provider

    # Show provider details and ask for service name and custom base URL (optional)
    endpoints_info = "\n".join([f"  • {ep.name}: {ep.path}" for ep in provider.endpoints])

    await query.edit_message_text(
        f"*SERVICE SETUP \\- Step 4/5*\n\n"
        f"Provider: {escape_markdown_v2(provider.name)}\n"
        f"Default Base URL: {escape_markdown_v2(provider.base_url)}\n"
        f"Endpoints:\n{escape_markdown_v2(endpoints_info)}\n\n"
        f"Enter service name and optional custom base URL:\n\n"
        f"<service\\_name> \\[custom\\_base\\_url\\]\n\n"
        f"Examples:\n"
        f"`MyOpenRouter`  \\(uses default {escape_markdown_v2(provider.base_url)}\\)\n"
        f"`MyCustom https://custom\\.openrouter\\.ai`\n\n"
        f"Or type /cancel to cancel\\.",
        parse_mode='MarkdownV2'
    )

    return ENTER_BASIC_INFO


async def handle_basic_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle basic info input"""
    text = update.message.text.strip()

    if text == "/cancel":
        await update.message.reply_text("[CANCELLED]\n\nService creation cancelled.")
        return ConversationHandler.END

    parts = text.split()
    service_config = context.user_data["service_config"]
    service_type = service_config["service_type"]

    if service_type == "health_check":
        if len(parts) < 2:
            await update.message.reply_text(
                "*INVALID INPUT*\n\n"
                "Please provide at least name and URL\\.\n\n"
                "Format: <name> <url> \\[interval\\_seconds\\]",
                parse_mode='MarkdownV2'
            )
            return ENTER_BASIC_INFO

        service_config["name"] = parts[0]
        service_config["url"] = parts[1]
        service_config["interval"] = int(parts[2]) if len(parts) > 2 else 300

        # Create health check service immediately
        return await create_health_check_service(update, context)

    # API Credit service
    if len(parts) < 1:
        await update.message.reply_text(
            "[INVALID INPUT]\n\n"
            "Please provide at least service name."
        )
        return ENTER_BASIC_INFO

    service_config["name"] = parts[0]

    if "provider" in service_config:
        # Pre-defined provider
        provider = service_config["provider"]
        service_config["base_url"] = parts[1] if len(parts) > 1 else provider.base_url

        # Show configuration and ask for confirmation
        return await show_config_confirmation(update, context)

    # Custom provider - continue with endpoint configuration
    if len(parts) < 2:
        await update.message.reply_text(
            "[INVALID INPUT]\n\n"
            "Please provide both service name and base URL."
        )
        return ENTER_BASIC_INFO

    service_config["base_url"] = parts[1]

    await update.message.reply_text(
        "[SERVICE SETUP - Step 4/5]\n\n"
        "How many API endpoints does your provider have?\n\n"
        "Common scenarios:\n"
        "  • 1 endpoint - Single API for all data\n"
        "  • 2 endpoints - Separate APIs (like OpenRouter's key + credits)\n\n"
        "Enter a number (1-5) or /cancel:",
    )

    return CUSTOM_ENDPOINT_COUNT


async def handle_endpoint_count(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle custom endpoint count"""
    text = update.message.text.strip()

    if text == "/cancel":
        await update.message.reply_text("[CANCELLED]\n\nService creation cancelled.")
        return ConversationHandler.END

    try:
        count = int(text)
        if count < 1 or count > 5:
            raise ValueError()
    except ValueError:
        await update.message.reply_text(
            "[INVALID INPUT]\n\nPlease enter a number between 1 and 5."
        )
        return CUSTOM_ENDPOINT_COUNT

    service_config = context.user_data["service_config"]
    service_config["endpoint_count"] = count
    service_config["current_endpoint"] = 0
    service_config["endpoints"] = []

    # Start configuring first endpoint
    await update.message.reply_text(
        f"*SERVICE SETUP \\- Endpoint 1/{count}*\n\n"
        f"Configure endpoint 1:\n\n"
        f"Enter endpoint details in JSON format:\n\n"
        f"```json\n"
        f"{{\n"
        f'  "name": "key_info",\n'
        f'  "path": "/api/v1/key",\n'
        f'  "method": "GET"\n'
        f"}}\n"
        f"```\n\n"
        f"Or type /cancel to cancel\\.",
        parse_mode='MarkdownV2'
    )

    return CUSTOM_ENDPOINT_CONFIG


async def handle_endpoint_config(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle custom endpoint configuration JSON"""
    text = update.message.text.strip()

    if text == "/cancel":
        await update.message.reply_text("[CANCELLED]\n\nService creation cancelled.")
        return ConversationHandler.END

    try:
        endpoint_data = json.loads(text)
        required_fields = ["name", "path", "method"]

        for field in required_fields:
            if field not in endpoint_data:
                raise ValueError(f"Missing required field: {field}")

        service_config = context.user_data["service_config"]
        service_config["endpoints"].append(endpoint_data)
        service_config["current_endpoint"] += 1

        current = service_config["current_endpoint"]
        total = service_config["endpoint_count"]

        if current < total:
            # Configure next endpoint
            await update.message.reply_text(
                f"*SERVICE SETUP \\- Endpoint {current \\+ 1}/{total}*\n\n"
                f"Configure endpoint {current \\+ 1}:\n\n"
                f"Enter endpoint details in JSON format:\n\n"
                f"```json\n"
                f"{{\n"
                f'  "name": "credits",\n'
                f'  "path": "/api/v1/credits",\n'
                f'  "method": "GET"\n'
                f"}}\n"
                f"```\n\n"
                f"Or type /cancel to cancel\\.",
                parse_mode='MarkdownV2'
            )
            return CUSTOM_ENDPOINT_CONFIG

        # All endpoints configured - now ask for field mappings
        await update.message.reply_text(
            "[SERVICE SETUP - Step 5/5]\n\n"
            "Now let's map the API response fields to standard metrics.\n\n"
            "For each endpoint, I'll show you example response fields.\n"
            "You'll map them to standard metrics for unified reporting.\n\n"
            "Standard metrics:\n" +
            "\n".join([f"  • {key}: {desc}" for key, desc in list(STANDARD_METRICS.items())[:8]]) +
            "\n\nReady? Reply 'yes' to continue or /cancel:",
        )

        service_config["current_mapping_endpoint"] = 0
        return CUSTOM_FIELD_MAPPING

    except json.JSONDecodeError:
        await update.message.reply_text(
            "[INVALID JSON]\n\n"
            "Please enter valid JSON format."
        )
        return CUSTOM_ENDPOINT_CONFIG
    except ValueError as e:
        await update.message.reply_text(
            f"[INVALID CONFIG]\n\n{str(e)}"
        )
        return CUSTOM_ENDPOINT_CONFIG


async def handle_field_mapping(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle field mapping input"""
    text = update.message.text.strip().lower()

    if text == "/cancel":
        await update.message.reply_text("[CANCELLED]\n\nService creation cancelled.")
        return ConversationHandler.END

    service_config = context.user_data["service_config"]

    if text == "yes" and service_config.get("current_mapping_endpoint") == 0:
        # Start mapping first endpoint
        endpoint = service_config["endpoints"][0]
        metrics_list = escape_markdown_v2("\n".join([f"  • {key}" for key in list(STANDARD_METRICS.keys())[:10]]))
        await update.message.reply_text(
            f"*FIELD MAPPING \\- Endpoint: {escape_markdown_v2(endpoint['name'])}*\n\n"
            f"Enter field mappings in JSON format:\n\n"
            f"```json\n"
            f"{{\n"
            f'  "balance": "remaining_credit",\n'
            f'  "limit": "total_credit",\n'
            f'  "used": "total_usage"\n'
            f"}}\n"
            f"```\n\n"
            f"Map your API's field names \\(left\\) to standard metrics \\(right\\)\\.\n\n"
            f"Available standard metrics:\n{metrics_list}"
            f"\n\nOr type /cancel:",
            parse_mode='MarkdownV2'
        )
        return CUSTOM_FIELD_MAPPING

    try:
        mapping = json.loads(text)

        # Validate mappings against standard metrics
        for external_field, internal_metric in mapping.items():
            if internal_metric not in STANDARD_METRICS:
                raise ValueError(f"Unknown metric: {internal_metric}")

        # Store mapping for current endpoint
        endpoint_idx = service_config["current_mapping_endpoint"]
        service_config["endpoints"][endpoint_idx]["field_mappings"] = mapping

        service_config["current_mapping_endpoint"] += 1

        if service_config["current_mapping_endpoint"] < len(service_config["endpoints"]):
            # Map next endpoint
            next_endpoint = service_config["endpoints"][service_config["current_mapping_endpoint"]]
            await update.message.reply_text(
                f"*FIELD MAPPING \\- Endpoint: {escape_markdown_v2(next_endpoint['name'])}*\n\n"
                f"Enter field mappings for the next endpoint in JSON format or type /cancel:",
                parse_mode='MarkdownV2'
            )
            return CUSTOM_FIELD_MAPPING

        # All mappings done - show confirmation
        return await show_config_confirmation(update, context)

    except json.JSONDecodeError:
        await update.message.reply_text(
            "[INVALID JSON]\n\nPlease enter valid JSON format."
        )
        return CUSTOM_FIELD_MAPPING
    except ValueError as e:
        await update.message.reply_text(
            f"[INVALID MAPPING]\n\n{str(e)}\n\n"
            f"Available metrics:\n" +
            "\n".join([f"  • {key}" for key in STANDARD_METRICS.keys()])
        )
        return CUSTOM_FIELD_MAPPING


async def show_config_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show configuration summary and ask for confirmation"""
    service_config = context.user_data["service_config"]

    if "provider" in service_config:
        # Pre-defined provider
        provider = service_config["provider"]
        config_summary = (
            "[CONFIGURATION SUMMARY]\n\n"
            f"Service Name: {service_config['name']}\n"
            f"Type: API Credit Tracking\n"
            f"Provider: {provider.name} (Pre-defined)\n"
            f"Base URL: {service_config['base_url']}\n"
            f"Endpoints: {len(provider.endpoints)}\n"
        )
        for ep in provider.endpoints:
            config_summary += f"  • {ep.name}: {ep.path}\n"
    else:
        # Custom provider
        config_summary = (
            "[CONFIGURATION SUMMARY]\n\n"
            f"Service Name: {service_config['name']}\n"
            f"Type: API Credit Tracking\n"
            f"Provider: Custom\n"
            f"Base URL: {service_config['base_url']}\n"
            f"Endpoints: {len(service_config['endpoints'])}\n"
        )
        for ep in service_config['endpoints']:
            config_summary += f"  • {ep['name']}: {ep['method']} {ep['path']}\n"

    keyboard = [
        [InlineKeyboardButton("✅ Create Service", callback_data="confirm_yes")],
        [InlineKeyboardButton("❌ Cancel", callback_data="confirm_no")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await update.callback_query.message.reply_text(
            config_summary + "\n\nConfirm creation?",
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            config_summary + "\n\nConfirm creation?",
            reply_markup=reply_markup
        )

    return CONFIRM_CONFIG


async def confirm_config(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle configuration confirmation"""
    query = update.callback_query
    await query.answer()

    if query.data == "confirm_no":
        await query.edit_message_text("[CANCELLED]\n\nService creation cancelled.")
        return ConversationHandler.END

    # Create the service
    service_config = context.user_data["service_config"]

    try:
        async with get_session() as session:
            service_repo = ServiceRepository(session)

            # Build service parameters
            service_params = {
                "name": service_config["name"],
                "service_type": "api_credit",
                "environment": settings.environment,
                "is_active": True,
                "check_interval_seconds": 3600,  # Default 1 hour
                "endpoint_url": service_config["base_url"],
            }

            # Build api_tracking_config
            if "provider" in service_config:
                # Pre-defined provider
                provider = service_config["provider"]
                api_config = {
                    "provider_id": provider.provider_id,
                    "provider_name": provider.name,
                    "endpoints": []
                }

                for ep in provider.endpoints:
                    api_config["endpoints"].append({
                        "name": ep.name,
                        "path": ep.path,
                        "method": ep.method,
                        "headers_template": ep.headers_template,
                        "response_data_path": ep.response_data_path,
                        "field_mappings": ep.field_mappings,
                    })
            else:
                # Custom provider
                api_config = {
                    "provider_id": "custom",
                    "provider_name": "Custom",
                    "endpoints": service_config["endpoints"]
                }

            service_params["api_tracking_config"] = api_config
            service_params["api_provider"] = api_config["provider_name"]

            # Create service
            new_service = await service_repo.create(**service_params)
            await session.commit()

        await query.edit_message_text(
            "*SERVICE CREATED*\n\n"
            f"Service: {escape_markdown_v2(new_service.name)}\n"
            f"ID: {new_service.id}\n"
            f"Type: API Credit Tracking\n\n"
            f"Next steps:\n"
            f"1\\. Set API key: `/set_api_key {new_service.id} <key>`\n"
            f"2\\. Assign users: `/assign <user_id> {new_service.id}`\n"
            f"3\\. Edit if needed: `/edit_service {new_service.id}`",
            parse_mode='MarkdownV2'
        )

        log.info(
            "service_created_interactive",
            service_id=new_service.id,
            name=new_service.name,
            provider=api_config["provider_name"]
        )

    except Exception as e:
        log.error("service_creation_error", error=str(e))
        await query.edit_message_text(
            f"[ERROR]\n\nFailed to create service: {str(e)}"
        )

    return ConversationHandler.END


async def create_health_check_service(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Create a health check service"""
    service_config = context.user_data["service_config"]

    try:
        async with get_session() as session:
            service_repo = ServiceRepository(session)

            service_params = {
                "name": service_config["name"],
                "service_type": "health_check",
                "environment": settings.environment,
                "is_active": True,
                "endpoint_url": service_config["url"],
                "expected_status_code": 200,
                "timeout_seconds": 10,
                "check_interval_seconds": service_config["interval"],
            }

            new_service = await service_repo.create(**service_params)
            await session.commit()

        await update.message.reply_text(
            "*SERVICE CREATED*\n\n"
            f"Service: {escape_markdown_v2(new_service.name)}\n"
            f"ID: {new_service.id}\n"
            f"Type: Health Check\n"
            f"URL: {escape_markdown_v2(service_config['url'])}\n"
            f"Interval: {service_config['interval']}s\n\n"
            f"Next step: `/assign <user_id> {new_service.id}`",
            parse_mode='MarkdownV2'
        )

        log.info(
            "health_check_service_created",
            service_id=new_service.id,
            name=new_service.name
        )

    except Exception as e:
        log.error("service_creation_error", error=str(e))
        await update.message.reply_text(
            f"[ERROR]\n\nFailed to create service: {str(e)}"
        )

    return ConversationHandler.END


async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the conversation"""
    await update.message.reply_text("[CANCELLED]\n\nService creation cancelled.")
    return ConversationHandler.END


# Build the conversation handler
def get_add_service_conversation_handler() -> ConversationHandler:
    """Get the conversation handler for adding services"""
    return ConversationHandler(
        entry_points=[CommandHandler("add_service", add_service_start)],
        states={
            CHOOSE_SERVICE_TYPE: [CallbackQueryHandler(choose_service_type)],
            ENTER_BASIC_INFO: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_basic_info)],
            CHOOSE_PROVIDER_MODE: [CallbackQueryHandler(choose_provider_mode)],
            SELECT_PROVIDER: [CallbackQueryHandler(select_provider)],
            CUSTOM_BASE_URL: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_basic_info)],
            CUSTOM_ENDPOINT_COUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_endpoint_count)],
            CUSTOM_ENDPOINT_CONFIG: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_endpoint_config)],
            CUSTOM_FIELD_MAPPING: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_field_mapping)],
            CONFIRM_CONFIG: [CallbackQueryHandler(confirm_config)],
        },
        fallbacks=[CommandHandler("cancel", cancel_conversation)],
        per_message=True,  # Fix PTBUserWarning: properly track CallbackQueryHandler per message
    )
