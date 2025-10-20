"""Movement validation business logic service."""


class MovementValidationService:
    """Service for validating stock movements before creation."""

    def __init__(self) -> None:
        pass

    async def validate_movement_request(self, movement_data: dict) -> dict:
        """Validate movement data before creation.

        Rules:
        - Quantity must be non-zero
        - Inbound movements have positive quantities
        - Outbound movements have negative quantities
        - Required fields present
        """
        errors = []

        quantity = movement_data.get("quantity", 0)
        is_inbound = movement_data.get("is_inbound", False)

        if quantity == 0:
            errors.append("Quantity cannot be zero")

        if is_inbound and quantity < 0:
            errors.append("Inbound movements must have positive quantity")

        if not is_inbound and quantity > 0:
            errors.append("Outbound movements must have negative quantity")

        if not movement_data.get("movement_type"):
            errors.append("Movement type is required")

        if errors:
            return {"valid": False, "errors": errors}

        return {"valid": True, "errors": []}
