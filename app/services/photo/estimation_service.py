"""Estimation Service - Business logic for ML estimation results.

This service handles all estimation operations including:
- Bulk creating estimations from ML results
- Band-based estimation (size bands: pequeño, mediano, grande)
- Density-based estimation (avg plants per m²)
- Grid analysis estimation
- Linking estimations to sessions

Architecture:
    Layer: Service Layer (Business Logic)
    Dependencies: EstimationRepository (own repo)
    Pattern: Clean Architecture - Service→Service communication

Critical Rules:
    - Service→Service pattern enforced
    - Calculation method validation (band/density/grid)
    - Bulk insert for performance
    - All database operations are async
"""

from app.core.exceptions import (
    ValidationException,
)
from app.core.logging import get_logger
from app.models.estimation import CalculationMethodEnum
from app.repositories.estimation_repository import EstimationRepository
from app.schemas.estimation_schema import (
    EstimationBulkCreateRequest,
    EstimationCreate,
    EstimationResponse,
    EstimationStatistics,
)

logger = get_logger(__name__)


class EstimationService:
    """Service for managing ML estimation results.

    This service provides business logic for estimation operations including
    bulk creation from ML results, validation, and statistics.

    Key Features:
        - Bulk insert estimations (performance optimized)
        - Band-based estimation support
        - Density-based estimation support
        - Grid analysis estimation support
        - Estimation statistics

    Attributes:
        repo: EstimationRepository for database operations
    """

    def __init__(self, repo: EstimationRepository) -> None:
        """Initialize EstimationService with repository.

        Args:
            repo: EstimationRepository for database operations
        """
        self.repo = repo

    async def create_estimation(self, request: EstimationCreate) -> EstimationResponse:
        """Create single estimation.

        Args:
            request: Estimation creation data

        Returns:
            EstimationResponse with created estimation

        Raises:
            ValidationException: If estimation data is invalid

        Business Rules:
            - vegetation_polygon must be a dict
            - detected_area_cm2 must be ≥0
            - estimated_count must be ≥0
            - estimation_confidence must be 0.0-1.0
        """
        # Validate polygon
        if not isinstance(request.vegetation_polygon, dict):
            raise ValidationException(
                field="vegetation_polygon",
                message="vegetation_polygon must be a dict",
            )

        # Validate area
        if request.detected_area_cm2 < 0.0:
            raise ValidationException(
                field="detected_area_cm2",
                message=f"detected_area_cm2 must be ≥0, got {request.detected_area_cm2}",
            )

        # Validate count
        if request.estimated_count < 0:
            raise ValidationException(
                field="estimated_count",
                message=f"estimated_count must be ≥0, got {request.estimated_count}",
            )

        # Validate confidence
        if not (0.0 <= request.estimation_confidence <= 1.0):
            raise ValidationException(
                field="estimation_confidence",
                message=f"estimation_confidence must be 0.0-1.0, got {request.estimation_confidence}",
            )

        # Create estimation
        estimation_data = request.model_dump()
        estimation = await self.repo.create(estimation_data)

        logger.info(
            "Estimation created",
            extra={
                "estimation_id": estimation.id,
                "session_id": estimation.session_id,
                "estimated_count": estimation.estimated_count,
                "method": estimation.calculation_method.value
                if estimation.calculation_method
                else "None",
            },
        )

        return EstimationResponse.model_validate(estimation)

    async def bulk_create_estimations(
        self, request: EstimationBulkCreateRequest
    ) -> list[EstimationResponse]:
        """Bulk create estimations from ML results (optimized for performance).

        Args:
            request: Bulk creation request with list of estimations

        Returns:
            List of EstimationResponse with created estimations

        Raises:
            ValidationException: If any estimation data is invalid

        Business Rules:
            - All estimations validated before insert
            - Uses bulk_insert for performance
            - All estimations for same session_id
        """
        logger.info(
            "Bulk creating estimations",
            extra={
                "session_id": request.session_id,
                "count": len(request.estimations),
            },
        )

        # Validate all estimations first
        for idx, estimation in enumerate(request.estimations):
            try:
                if not isinstance(estimation.vegetation_polygon, dict):
                    raise ValidationException(
                        field=f"estimations[{idx}].vegetation_polygon",
                        message="vegetation_polygon must be a dict",
                    )

                if estimation.detected_area_cm2 < 0.0:
                    raise ValidationException(
                        field=f"estimations[{idx}].detected_area_cm2",
                        message=f"detected_area_cm2 must be ≥0, got {estimation.detected_area_cm2}",
                    )

                if estimation.estimated_count < 0:
                    raise ValidationException(
                        field=f"estimations[{idx}].estimated_count",
                        message=f"estimated_count must be ≥0, got {estimation.estimated_count}",
                    )

                if not (0.0 <= estimation.estimation_confidence <= 1.0):
                    raise ValidationException(
                        field=f"estimations[{idx}].estimation_confidence",
                        message=f"estimation_confidence must be 0.0-1.0, got {estimation.estimation_confidence}",
                    )
            except ValidationException as e:
                logger.error(
                    f"Validation failed for estimation {idx}",
                    extra={"error": str(e)},
                )
                raise

        # Prepare bulk data
        estimation_dicts = [
            {
                "session_id": request.session_id,
                **estimation.model_dump(),
            }
            for estimation in request.estimations
        ]

        # Bulk insert
        created = await self.repo.bulk_create(estimation_dicts)

        logger.info(
            "Bulk estimations created successfully",
            extra={
                "session_id": request.session_id,
                "count": len(created),
            },
        )

        return [EstimationResponse.model_validate(e) for e in created]

    async def get_estimation_by_id(self, estimation_id: int) -> EstimationResponse | None:
        """Get estimation by ID.

        Args:
            estimation_id: Estimation database ID

        Returns:
            EstimationResponse if found, None otherwise
        """
        estimation = await self.repo.get(estimation_id)
        if not estimation:
            return None

        return EstimationResponse.model_validate(estimation)

    async def get_estimations_by_session(
        self, session_id: int, limit: int = 1000
    ) -> list[EstimationResponse]:
        """Get all estimations for a session.

        Args:
            session_id: Photo processing session ID
            limit: Max results (default 1000)

        Returns:
            List of EstimationResponse
        """
        estimations = await self.repo.get_by_session(session_id, limit=limit)
        return [EstimationResponse.model_validate(e) for e in estimations]

    async def get_estimations_by_method(
        self, calculation_method: CalculationMethodEnum, limit: int = 100
    ) -> list[EstimationResponse]:
        """Get estimations by calculation method.

        Args:
            calculation_method: Calculation method (band/density/grid)
            limit: Max results (default 100)

        Returns:
            List of EstimationResponse
        """
        estimations = await self.repo.get_by_calculation_method(calculation_method, limit=limit)
        return [EstimationResponse.model_validate(e) for e in estimations]

    async def get_estimation_statistics(self, session_id: int) -> EstimationStatistics:
        """Calculate estimation statistics for a session.

        Args:
            session_id: Photo processing session ID

        Returns:
            EstimationStatistics with total count, avg confidence, etc.

        Business Rules:
            - total_estimated_plants = sum of all estimated_count
            - avg_confidence is mean of all confidences
            - Grouped by calculation method
        """
        # Get all estimations for session
        estimations = await self.repo.get_by_session(session_id, limit=10000)

        if not estimations:
            from decimal import Decimal

            return EstimationStatistics(
                total_count=0,
                total_estimated_plants=0,
                avg_confidence=Decimal("0.0"),
                min_confidence=Decimal("0.0"),
                max_confidence=Decimal("0.0"),
                band_estimation_count=0,
                density_estimation_count=0,
                grid_analysis_count=0,
            )

        # Calculate statistics
        from decimal import Decimal

        total_count = len(estimations)
        total_estimated_plants = sum(
            e.estimated_count if e.estimated_count else 0 for e in estimations
        )

        confidences = [
            float(e.estimation_confidence) if e.estimation_confidence is not None else 0.0
            for e in estimations
        ]
        avg_confidence = Decimal(str(sum(confidences) / len(confidences)))
        min_confidence = Decimal(str(min(confidences)))
        max_confidence = Decimal(str(max(confidences)))

        # Count by method
        band_estimation_count = sum(
            1 for e in estimations if e.calculation_method == CalculationMethodEnum.BAND_ESTIMATION
        )
        density_estimation_count = sum(
            1
            for e in estimations
            if e.calculation_method == CalculationMethodEnum.DENSITY_ESTIMATION
        )
        grid_analysis_count = sum(
            1 for e in estimations if e.calculation_method == CalculationMethodEnum.GRID_ANALYSIS
        )

        logger.info(
            "Estimation statistics calculated",
            extra={
                "session_id": session_id,
                "total_count": total_count,
                "total_estimated_plants": total_estimated_plants,
                "avg_confidence": avg_confidence,
            },
        )

        return EstimationStatistics(
            total_count=total_count,
            total_estimated_plants=total_estimated_plants,
            avg_confidence=avg_confidence,
            min_confidence=min_confidence,
            max_confidence=max_confidence,
            band_estimation_count=band_estimation_count,
            density_estimation_count=density_estimation_count,
            grid_analysis_count=grid_analysis_count,
        )
