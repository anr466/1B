from fastapi import APIRouter, Header
from pydantic import BaseModel

portfolio_router = APIRouter()


class PortfolioResponse(BaseModel):
    user_id: int
    balance: float
    available_balance: float
    total_profit_loss: float
    is_demo: bool


@portfolio_router.get("/portfolio", response_model=PortfolioResponse)
async def get_portfolio(user_id: int = Header(None, alias="X-User-Id")):
    # In production, fetch from PortfolioRepository using authenticated user id (from header)
    if user_id is None:
        # No user context; return neutral portfolio
        return PortfolioResponse(
            user_id=0,
            balance=0.0,
            available_balance=0.0,
            total_profit_loss=0.0,
            is_demo=False,
        )
    # Placeholder for actual DB fetch; for now, return a basic portfolio for the user
    return PortfolioResponse(
        user_id=user_id,
        balance=1000.0,
        available_balance=1000.0,
        total_profit_loss=0.0,
        is_demo=False,
    )
