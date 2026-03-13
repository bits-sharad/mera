"""
Initialize MongoDB indexes for history collection

Run this script to create indexes for optimal query performance:
    python -m src.services.init_history_indexes
"""

import logging
from src.services.history import SessionHistoryService
from src.core.config import settings

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


def main():
    """Initialize history collection indexes"""
    logger.info("Starting history collection index creation...")

    try:
        # Initialize history service
        history_service = SessionHistoryService()

        # Create indexes
        history_service.create_indexes()

        logger.info("✓ History collection indexes created successfully!")

        # Close connection
        history_service.close()

    except Exception as e:
        logger.error(f"✗ Failed to create indexes: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
