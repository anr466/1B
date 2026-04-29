"""
ML Module - Public API for machine learning components
Exports get_ml_classifier and get_hybrid_system
"""

import logging

logger = logging.getLogger(__name__)


def get_ml_classifier():
    """Get the ML signal classifier instance (lazy singleton)"""
    try:
        from backend.ml.signal_classifier import SignalClassifier
        return SignalClassifier()
    except ImportError as e:
        logger.warning(f"SignalClassifier not available: {e}")
        return None
    except Exception as e:
        logger.error(f"Error initializing classifier: {e}")
        return None


def get_hybrid_system():
    """Get the hybrid ML system instance (lazy singleton)"""
    try:
        from backend.ml.hybrid_learning_system import HybridMLSystem
        return HybridMLSystem()
    except ImportError as e:
        logger.warning(f"HybridMLSystem not available: {e}")
        return None
    except Exception as e:
        logger.error(f"Error initializing hybrid system: {e}")
        return None
