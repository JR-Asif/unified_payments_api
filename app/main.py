from fastapi import FastAPI
from app.database import engine, Base
from app.routers import payments
from app.routers import refunds
from app.utils.loggers import logger

app = FastAPI(
    title="Unified Payments Engine API",
    description="An enterprise-grade strategy-pattern payment microservice.",
    version="1.0.0",
)

app.include_router(payments.router)
app.include_router(refunds.router)

logger.info("app.startup_complete service=unified-payments-api version=1.0.0")


# Health check — for load balancers and uptime monitors
@app.get("/")
def health_check():
    """Health check — confirms the service is up."""
    logger.debug("health.check_invoked")
    return {
        "status": "ONLINE",
        "service": "payments-ledger-microservice",
        "database_connectivity": "CONNECTED",
    }
