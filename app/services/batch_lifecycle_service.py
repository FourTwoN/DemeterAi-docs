"""Batch lifecycle business logic service."""

from datetime import date, timedelta


class BatchLifecycleService:
    """Service for managing stock batch lifecycle events."""

    def __init__(self) -> None:
        pass

    async def calculate_batch_age_days(self, planting_date: date) -> int:
        """Calculate batch age in days from planting date."""
        if not planting_date:
            return 0
        today = date.today()
        return (today - planting_date).days

    async def estimate_ready_date(self, planting_date: date, growth_days: int) -> date:
        """Estimate when batch will be ready for sale."""
        if not planting_date:
            return date.today()
        return planting_date + timedelta(days=growth_days)

    async def check_batch_status(self, batch_data: dict) -> dict:
        """Check batch lifecycle status.

        Returns status indicators:
        - stage: seedling, growing, mature, ready
        - health: good, warning, critical
        - days_to_ready: int
        """
        age_days = await self.calculate_batch_age_days(batch_data.get("planting_date"))

        # Simple heuristic
        if age_days < 30:
            stage = "seedling"
        elif age_days < 90:
            stage = "growing"
        elif age_days < 180:
            stage = "mature"
        else:
            stage = "ready"

        quality_score = batch_data.get("quality_score", 3.0)
        if quality_score >= 4.0:
            health = "good"
        elif quality_score >= 2.5:
            health = "warning"
        else:
            health = "critical"

        return {
            "stage": stage,
            "health": health,
            "age_days": age_days,
            "quality_score": quality_score,
        }
