"""
Main application entry point
Initializes all components and starts the monitoring system
"""
import asyncio
import signal
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from monitoring_system.config import settings
from monitoring_system.config.logging import configure_logging, get_logger
from monitoring_system.core.database import init_database, close_database
from monitoring_system.telegram.bot import create_bot, start_bot, stop_bot
from monitoring_system.monitoring.health_checker import HealthChecker
from monitoring_system.monitoring.credit_monitor import CreditMonitor

# Configure logging first
configure_logging(settings.environment, settings.log_level)
log = get_logger(__name__)


class Application:
    """Main application class"""

    def __init__(self):
        self.scheduler = None
        self.bot_application = None
        self.health_checker = HealthChecker()
        self.credit_monitor = CreditMonitor()
        self.shutdown_event = asyncio.Event()

    async def startup(self):
        """Initialize all components"""
        log.info(
            "application_startup",
            environment=settings.environment,
            debug=settings.debug,
            bot=settings.active_bot_username,
        )

        # Initialize database
        await init_database()
        log.info("database_initialized")

        # Start scheduler
        self.scheduler = AsyncIOScheduler(
            timezone=settings.scheduler_timezone,
            job_defaults=settings.scheduler_job_defaults,
        )

        # Add health check job
        self.scheduler.add_job(
            self.health_checker.check_all_services,
            trigger=IntervalTrigger(seconds=settings.default_health_check_interval),
            id="health_checks",
            name="Health Checks",
            replace_existing=True,
        )

        # Add credit monitoring job
        self.scheduler.add_job(
            self.credit_monitor.check_all_services,
            trigger=IntervalTrigger(hours=settings.default_credit_check_interval),
            id="credit_checks",
            name="Credit Checks",
            replace_existing=True,
        )

        self.scheduler.start()
        log.info("scheduler_started", jobs=len(self.scheduler.get_jobs()))

        # Initialize and start Telegram bot
        self.bot_application = create_bot(settings.environment)
        await start_bot(self.bot_application)
        log.info("telegram_bot_started", bot=settings.active_bot_username)

        log.info("application_startup_complete")

    async def shutdown(self):
        """Gracefully shutdown all components"""
        log.info("application_shutdown_initiated")

        # Stop Telegram bot
        if self.bot_application:
            await stop_bot(self.bot_application)
            log.info("telegram_bot_stopped")

        # Stop scheduler
        if self.scheduler:
            self.scheduler.shutdown(wait=True)
            log.info("scheduler_stopped")

        # Close database connections
        await close_database()
        log.info("database_closed")

        log.info("application_shutdown_complete")

    async def run(self):
        """Run the application"""
        try:
            await self.startup()

            # Wait for shutdown signal
            await self.shutdown_event.wait()

        except KeyboardInterrupt:
            log.info("received_keyboard_interrupt")
        except Exception as e:
            log.error("application_error", error=str(e), exc_info=True)
            raise
        finally:
            await self.shutdown()


# Global app instance
app = None


def handle_shutdown_signal(signum, frame):
    """Handle shutdown signals"""
    log.info("shutdown_signal_received", signal=signum)
    if app:
        asyncio.create_task(app.shutdown_event.set())


async def main():
    """Main entry point"""
    global app

    log.info(
        "starting_monitoring_system",
        version="1.0.0",
        environment=settings.environment,
        debug=settings.debug,
    )

    # Create application
    app = Application()

    # Register signal handlers
    signal.signal(signal.SIGTERM, handle_shutdown_signal)
    signal.signal(signal.SIGINT, handle_shutdown_signal)

    # Run application
    await app.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("received_keyboard_interrupt")
    except Exception as e:
        log.error("fatal_error", error=str(e), exc_info=True)
        raise
