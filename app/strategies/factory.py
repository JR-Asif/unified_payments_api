from fastapi import HTTPException, status
from app.strategies.base import PaymentStrategy
from app.strategies.provider_a import ProviderAStrategy
from app.strategies.provider_b import ProviderBStrategy
from app.utils.loggers import logger


class PaymentProcessorFactory:
    """Returns the right provider strategy for a given provider name (provider_a / provider_b)."""

    _strategies = {
        "provider_a": ProviderAStrategy(),
        "provider_b": ProviderBStrategy(),
    }

    @classmethod
    def get_strategy(cls, provider_name: str) -> PaymentStrategy:
        strategy = cls._strategies.get(provider_name.lower())

        if not strategy:
            logger.warning(f"strategy.unknown_provider provider={provider_name}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Payment provider '{provider_name}' is not integrated into this service.",
            )
        return strategy
