"""Production data loader - Loads geospatial and catalog data from GeoJSON and CSV files.

This module provides utilities to load production data from:
1. GeoJSON files: GPS coordinates for Warehouse → StorageArea → StorageLocation
2. CSV files: ProductCategories, PriceList, PackagingCatalog data
3. Seed data: StorageBinType catalog entries

The loader is designed to be idempotent - it can be run multiple times without
creating duplicates. Data is loaded in dependency order:
1. Warehouses (from naves.geojson)
2. StorageAreas (from canteros.geojson)
3. StorageLocations (from claros.geojson)
4. ProductCategories (from categories CSV)
5. StorageBinTypes (hardcoded seed data)
6. PriceList (from price_list.csv)

Architecture:
    Layer: Database / Initialization (Infrastructure Layer)
    Dependencies: GeoAlchemy2, SQLAlchemy async, Shapely, pandas
    State: Idempotent - checks for existing data before loading

See:
    - Database ERD: ../../database/database.mmd
    - Production data: ../../production_data/
"""

import json
import re
from pathlib import Path

import pandas as pd
from geoalchemy2.elements import WKTElement
from shapely.geometry import shape
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models import (
    PackagingCatalog,
    PackagingColor,
    PriceList,
    ProductCategory,
    StorageArea,
    StorageBinType,
    StorageLocation,
    Warehouse,
)
from app.models.storage_bin_type import BinCategoryEnum

logger = get_logger(__name__)

# Path to production data directory
PRODUCTION_DATA_DIR = Path(__file__).parent.parent.parent / "production_data"


class ProductionDataLoader:
    """Loader for production data from GeoJSON and CSV files."""

    def __init__(self, session: AsyncSession):
        """Initialize loader with database session.

        Args:
            session: SQLAlchemy AsyncSession
        """
        self.session = session
        self.loaded_count = {
            "warehouses": 0,
            "storage_areas": 0,
            "storage_locations": 0,
            "product_categories": 0,
            "storage_bin_types": 0,
            "price_list": 0,
        }

    # =========================================================================
    # Warehouse Loading (from naves.geojson)
    # =========================================================================

    async def load_warehouses(self) -> int:
        """Load warehouses from Exported GeoJSON file.

        Uses the new consolidated Exported file with proper warehouse definitions.
        Filters for features with "Nave" name that don't have "norte/sur" suffix.

        Returns:
            Number of warehouses loaded/updated
        """
        # Try new file first, fallback to old file
        geojson_file = PRODUCTION_DATA_DIR / "gps_layers" / "Exported 29 fields, 12 lines.geojson"
        if not geojson_file.exists():
            geojson_file = PRODUCTION_DATA_DIR / "gps_layers" / "naves.geojson"

        if not geojson_file.exists():
            logger.warning("Warehouses file not found")
            return 0

        logger.info(f"Loading warehouses from {geojson_file.name}...")

        with open(geojson_file) as f:
            geojson_data = json.load(f)

        count = 0
        for feature in geojson_data.get("features", []):
            try:
                warehouse = self._parse_warehouse_feature(feature)
                if warehouse:
                    try:
                        # Check if already exists
                        stmt = select(Warehouse).where(Warehouse.code == warehouse.code)
                        result = await self.session.execute(stmt)
                        existing = result.scalar_one_or_none()

                        if not existing:
                            self.session.add(warehouse)
                            count += 1
                            logger.info(f"  ✓ Warehouse: {warehouse.name} ({warehouse.code})")
                        else:
                            logger.info(f"  ⊘ Warehouse already exists: {warehouse.code}")
                    except Exception as db_error:
                        # Rollback if database error occurs
                        await self.session.rollback()
                        logger.error(f"  ✗ Database error: {str(db_error)}")

            except Exception as e:
                logger.error(f"  ✗ Error parsing warehouse: {str(e)}", exc_info=True)

        try:
            await self.session.commit()
        except Exception as e:
            logger.error(f"  ✗ Error committing warehouses: {str(e)}")
            await self.session.rollback()

        self.loaded_count["warehouses"] = count
        logger.info(f"✅ Loaded {count} warehouses")
        return count

    def _parse_warehouse_feature(self, feature: dict) -> Warehouse | None:
        """Parse GeoJSON feature into Warehouse model.

        Filters out naves with "norte" or "sur" suffix (those are storage areas, not warehouses).

        Args:
            feature: GeoJSON feature dict

        Returns:
            Warehouse model instance or None if invalid
        """
        try:
            props = feature.get("properties", {})
            geom = feature.get("geometry")

            # Extract name from Name property (format: "Nave 1", "Nave 2", "Nave 5 norte", etc.)
            name = props.get("Name", "Unknown")

            # Only process features with "Nave" in the name (but not "Cantero")
            if "nave" not in name.lower() or "cantero" in name.lower():
                return None

            # Generate code from name: "Nave 1" → "NAVE1", "Nave 5 norte" → "NAVE5NORTE"
            code = re.sub(r"[^A-Za-z0-9]", "", name).upper()[:20]
            if not code:
                code = f"WH{props.get('id', 'X')}"

            # Convert geometry to WKT
            if geom and geom.get("type") == "Polygon":
                shape_geom = shape(geom)
                wkt_geom = WKTElement(shape_geom.wkt, srid=4326)

                warehouse = Warehouse(
                    code=code,
                    name=name,
                    warehouse_type="greenhouse",  # Default type
                    geojson_coordinates=wkt_geom,
                )
                return warehouse
        except Exception as e:
            logger.error(f"Error parsing warehouse feature: {str(e)}")
            return None

    # =========================================================================
    # StorageArea Loading (from canteros.geojson)
    # =========================================================================

    async def load_storage_areas(self) -> int:
        """Load storage areas from Exported GeoJSON file.

        Loads Madres, Tunnels, Sombráculos from consolidated GeoJSON.
        Uses the same consolidated Exported file as warehouses.

        Returns:
            Number of storage areas loaded/updated
        """
        # Try new file first, fallback to old file
        geojson_file = PRODUCTION_DATA_DIR / "gps_layers" / "Exported 29 fields, 12 lines.geojson"
        if not geojson_file.exists():
            geojson_file = PRODUCTION_DATA_DIR / "gps_layers" / "canteros.geojson"

        if not geojson_file.exists():
            logger.warning("Storage areas file not found")
            return 0

        logger.info(f"Loading storage areas from {geojson_file.name}...")

        with open(geojson_file) as f:
            geojson_data = json.load(f)

        # Get first warehouse (default for unmatched storage areas)
        stmt = select(Warehouse).limit(1)
        result = await self.session.execute(stmt)
        default_warehouse = result.scalar_one_or_none()

        if not default_warehouse:
            logger.error("No warehouse found. Load warehouses first.")
            return 0

        # Count and log storage areas to be loaded
        all_names = [
            f.get("properties", {}).get("Name", "?") for f in geojson_data.get("features", [])
        ]
        storage_area_names = [
            n for n in all_names if self._is_storage_area_feature(n) and "cantero" not in n.lower()
        ]
        logger.info(f"  Found {len(storage_area_names)} storage areas to load")
        for name in storage_area_names:
            logger.debug(f"    - {name}")

        # Storage areas can be associated with warehouses by parsing their name
        count = 0
        for feature in geojson_data.get("features", []):
            try:
                name = feature.get("properties", {}).get("Name", "")

                # Skip if not a storage area
                if not self._is_storage_area_feature(name) or "cantero" in name.lower():
                    continue

                warehouse = default_warehouse

                # Try to match warehouse from name if name contains "nave"
                if "nave" in name.lower():
                    nave_match = re.search(r"nave\s*(\d+|\w+)", name, re.IGNORECASE)
                    if nave_match:
                        nave_code = f"NAVE{nave_match.group(1).upper()}"
                        stmt = select(Warehouse).where(Warehouse.code == nave_code)
                        result = await self.session.execute(stmt)
                        matched_warehouse = result.scalar_one_or_none()
                        if matched_warehouse:
                            warehouse = matched_warehouse

                storage_area = self._parse_storage_area_feature(feature, warehouse.warehouse_id)
                if storage_area:
                    stmt = select(StorageArea).where(StorageArea.code == storage_area.code)
                    result = await self.session.execute(stmt)
                    existing = result.scalar_one_or_none()

                    if not existing:
                        self.session.add(storage_area)
                        count += 1
                        logger.info(f"  ✓ StorageArea: {storage_area.name} ({storage_area.code})")
                    else:
                        logger.info(f"  ⊘ StorageArea already exists: {storage_area.code}")

            except Exception as e:
                logger.error(f"  ✗ Error parsing storage area: {str(e)}", exc_info=True)

        await self.session.commit()
        self.loaded_count["storage_areas"] = count
        logger.info(f"✅ Loaded {count} storage areas")
        return count

    def _parse_storage_area_feature(self, feature: dict, warehouse_id: int) -> StorageArea | None:
        """Parse GeoJSON feature into StorageArea model.

        Loads Madres, Tunnels, Sombráculos, and Naves with norte/sur suffix.

        Args:
            feature: GeoJSON feature dict
            warehouse_id: Parent warehouse ID

        Returns:
            StorageArea model instance or None if invalid
        """
        try:
            props = feature.get("properties", {})
            geom = feature.get("geometry")

            # Extract name from Name property
            name = props.get("Name", "Unknown")

            # Only load features that are storage areas (Madres, Tunnels, Sombráculos)
            # NOT "Nave X norte/sur" (those are warehouses), NOT canteros (those are locations)
            if not self._is_storage_area_feature(name) or "cantero" in name.lower():
                return None

            # Generate code from name with WAREHOUSE-AREA format
            # Extract warehouse number/prefix from the full area name
            name_clean = self._clean_name(name)[:35]  # Keep room for area prefix

            # For Madres/Tunnels/Sombraculosand, create code with hyphen
            # Format: WAREHOUSE-AREACODE
            # E.g., "Madres 1 Sur" -> "NA-MADRES1SUR" or "Tunnel 1" -> "NA-TUNNEL1"
            warehouse_prefix = "NA"  # Default warehouse prefix
            code = f"{warehouse_prefix}-{name_clean}".upper()[:50]

            # Map label to position based on directional keywords
            position = "C"  # Default to Center
            name_lower = name.lower()
            if "sur" in name_lower:
                position = "S"
            elif "norte" in name_lower or "north" in name_lower:
                position = "N"
            elif "este" in name_lower or "east" in name_lower:
                position = "E"
            elif "oeste" in name_lower or "west" in name_lower:
                position = "W"

            # Handle both Polygon and LineString geometries
            if geom and geom.get("type") == "Polygon":
                shape_geom = shape(geom)
                wkt_geom = WKTElement(shape_geom.wkt, srid=4326)
            elif geom and geom.get("type") == "LineString":
                # Convert LineString to Polygon by creating a buffer
                shape_geom = shape(geom)
                # Create a small buffer around the line to make it a polygon
                buffered_geom = shape_geom.buffer(0.00005)  # ~5 meters
                wkt_geom = WKTElement(buffered_geom.wkt, srid=4326)
            else:
                logger.warning(
                    f"Unsupported geometry type for storage area '{name}': {geom.get('type') if geom else 'None'}"
                )
                return None

            storage_area = StorageArea(
                warehouse_id=warehouse_id,
                code=code,
                name=name,
                position=position,
                geojson_coordinates=wkt_geom,
            )
            return storage_area
        except Exception as e:
            logger.error(f"Error parsing storage area feature: {str(e)}")
            return None

    def _match_storage_area(self, cantero_name: str, storage_areas: list) -> StorageArea | None:
        """Match a Cantero name to the best storage area.

        Tries to match Cantero names to storage areas:
        - "Canteros nave 5 norte" → Matches "Nave 5 norte" (warehouse match)
        - "Cantero somb 1" → Matches "Sombraculo 1" (storage area match)
        - Otherwise returns first storage area as fallback

        Args:
            cantero_name: Name of the Cantero/StorageLocation
            storage_areas: List of available StorageArea objects

        Returns:
            Best matching StorageArea or None
        """
        name_lower = cantero_name.lower()

        # Try to extract identifying info from cantero name
        if "nave" in name_lower:
            # Extract nave number: "Canteros nave 5 norte" → "5"
            nave_match = re.search(r"nave\s*(\d+)", name_lower)
            if nave_match:
                nave_num = nave_match.group(1)
                # Find storage area with matching nave number
                for area in storage_areas:
                    if f"nave{nave_num}" in area.name.lower():
                        return area

        if "somb" in name_lower:
            # Extract sombraculo number: "Cantero somb 1" → "1"
            somb_match = re.search(r"somb[a-z]*\s*(\d+)?", name_lower)
            if somb_match:
                somb_num = somb_match.group(1) if somb_match.lastindex else None
                if somb_num:
                    for area in storage_areas:
                        if (
                            f"sombraculo {somb_num}" in area.name.lower()
                            or f"somb {somb_num}" in area.name.lower()
                        ):
                            return area

        # Default: return first storage area
        return storage_areas[0] if storage_areas else None

    def _is_storage_area_feature(self, name: str) -> bool:
        """Check if a feature name belongs to a storage area.

        Storage areas include:
        - Madres (various variations)
        - Tunnels
        - Sombráculos (various spellings)

        Args:
            name: Feature name to check

        Returns:
            True if this is a storage area feature
        """
        name_lower = name.lower()
        return any(
            keyword in name_lower for keyword in ["madre", "madres", "tunnel", "sombraculo", "somb"]
        )

    def _clean_name(self, name: str) -> str:
        """Clean name for use in codes.

        Args:
            name: Original name

        Returns:
            Cleaned name (alphanumeric + underscores)
        """
        return re.sub(r"[^A-Za-z0-9_]", "_", name)

    # =========================================================================
    # StorageLocation Loading (from claros.geojson)
    # =========================================================================

    async def load_storage_locations(self) -> int:
        """Load storage locations (Canteros) from Exported GeoJSON file.

        Maps each Cantero to its parent StorageArea based on naming conventions.
        Supports formats like:
        - Canteros nave 5 norte → Nave 5 norte → warehouse+area match
        - Cantero somb 1 → Sombraculo 1 → storage area match

        Returns:
            Number of storage locations loaded/updated
        """
        # Try new file first, fallback to old file
        geojson_file = PRODUCTION_DATA_DIR / "gps_layers" / "Exported 29 fields, 12 lines.geojson"
        if not geojson_file.exists():
            geojson_file = PRODUCTION_DATA_DIR / "gps_layers" / "claros.geojson"

        if not geojson_file.exists():
            logger.warning("Storage locations file not found")
            return 0

        logger.info(f"Loading storage locations from {geojson_file.name}...")

        with open(geojson_file) as f:
            geojson_data = json.load(f)

        # Get available storage areas
        stmt = select(StorageArea).limit(100)
        result = await self.session.execute(stmt)
        storage_areas = result.scalars().all()

        if not storage_areas:
            logger.error("No storage areas found. Load storage areas first.")
            return 0

        logger.info(f"  Found {len(storage_areas)} storage areas to map")

        count = 0
        # Get the highest existing QR code number to avoid duplicates
        stmt = select(StorageLocation).order_by(StorageLocation.qr_code.desc()).limit(1)
        result = await self.session.execute(stmt)
        last_location = result.scalar_one_or_none()

        if last_location and last_location.qr_code:
            try:
                # Extract number from QR code like "LOC000001"
                last_num = int(last_location.qr_code.replace("LOC", ""))
                location_counter = last_num + 1
                logger.info(f"  Resuming from QR code LOC{location_counter:06d}")
            except (ValueError, AttributeError):
                location_counter = 1
                logger.info("  Starting fresh QR code counter")
        else:
            location_counter = 1
            logger.info("  Starting fresh QR code counter")

        for feature in geojson_data.get("features", []):
            try:
                name = feature.get("properties", {}).get("Name", "")

                # Only process Cantero features
                if "cantero" not in name.lower():
                    continue

                # Find the best matching storage area for this cantero
                storage_area = self._match_storage_area(name, storage_areas)
                if not storage_area:
                    logger.warning(f"  ⊘ Could not match storage area for: {name}")
                    # Use first storage area as fallback
                    storage_area = storage_areas[0]

                storage_location = self._parse_storage_location_feature(
                    feature, storage_area.storage_area_id, location_counter
                )
                if storage_location:
                    stmt = select(StorageLocation).where(
                        StorageLocation.code == storage_location.code
                    )
                    result = await self.session.execute(stmt)
                    existing = result.scalar_one_or_none()

                    if not existing:
                        # Double-check QR code uniqueness (idempotency safety)
                        stmt_qr = select(StorageLocation).where(
                            StorageLocation.qr_code == storage_location.qr_code
                        )
                        result_qr = await self.session.execute(stmt_qr)
                        existing_qr = result_qr.scalar_one_or_none()

                        if not existing_qr:
                            self.session.add(storage_location)
                            count += 1
                            logger.info(
                                f"  ✓ StorageLocation: {storage_location.name} ({storage_location.code}) -> {storage_area.name}"
                            )
                        else:
                            logger.info(f"  ⊘ QR code already exists: {storage_location.qr_code}")

                        location_counter += 1
                    else:
                        logger.info(f"  ⊘ StorageLocation already exists: {storage_location.code}")
                        location_counter += 1

            except Exception as e:
                logger.error(f"  ✗ Error parsing storage location: {str(e)}", exc_info=True)
                location_counter += 1
                # Don't stop processing, continue with next location

        try:
            await self.session.commit()
        except Exception as e:
            logger.error(f"  ✗ Error committing storage locations: {str(e)}")
            await self.session.rollback()
        self.loaded_count["storage_locations"] = count
        logger.info(f"✅ Loaded {count} storage locations")
        return count

    def _parse_storage_location_feature(
        self, feature: dict, storage_area_id: int, location_number: int
    ) -> StorageLocation | None:
        """Parse GeoJSON feature into StorageLocation model.

        Loads Cantero LineString features (routes within storage areas).
        Format: WAREHOUSE-AREA-LOC-### (e.g., NA-MADRES1SUR-LOC-001)

        Args:
            feature: GeoJSON feature dict
            storage_area_id: Parent storage area ID
            location_number: Sequential location number

        Returns:
            StorageLocation model instance or None if invalid
        """
        try:
            props = feature.get("properties", {})
            geom = feature.get("geometry")

            # Only load Cantero features
            name = props.get("Name", "Unknown")
            if "cantero" not in name.lower():
                return None

            # Generate code with WAREHOUSE-AREA-LOC-### pattern
            # E.g., "Canteros nave 1" -> "NA-CANTEROSNAVE1-LOC-001"
            name_clean = self._clean_name(name)[:30]  # Keep room for prefix and suffix
            warehouse_prefix = "NA"  # Default warehouse prefix
            code = f"{warehouse_prefix}-{name_clean}-LOC-{location_number:03d}".upper()[:50]
            qr_code = f"LOC{location_number:06d}"

            # Convert geometry to WKT (POLYGON)
            # Model expects POLYGON, so create buffer around LineString or use geometry directly
            if geom and geom.get("type") == "LineString":
                shape_geom = shape(geom)
                # Create small buffer around line (5 meters)
                buffered_geom = shape_geom.buffer(0.00005)
                wkt_geom = WKTElement(buffered_geom.wkt, srid=4326)
            elif geom and geom.get("type") == "Polygon":
                shape_geom = shape(geom)
                wkt_geom = WKTElement(shape_geom.wkt, srid=4326)
            elif geom and geom.get("type") == "Point":
                shape_geom = shape(geom)
                buffered_geom = shape_geom.buffer(0.0001)
                wkt_geom = WKTElement(buffered_geom.wkt, srid=4326)
            else:
                return None

            storage_location = StorageLocation(
                storage_area_id=storage_area_id,
                code=code,
                name=name,
                qr_code=qr_code,
                geojson_coordinates=wkt_geom,
            )
            return storage_location
        except Exception as e:
            logger.error(f"Error parsing storage location feature: {str(e)}")
            return None

    # =========================================================================
    # ProductCategory Loading (from CSV)
    # =========================================================================

    async def load_product_categories(self) -> int:
        """Load product categories from CSV files.

        Loads from categories.csv and categories_2.csv, plus generic categories
        for price list compatibility.

        Returns:
            Number of product categories loaded/updated
        """
        count = 0

        # Load from categories.csv
        csv_file = PRODUCTION_DATA_DIR / "product_category" / "categories.csv"
        if csv_file.exists():
            count += await self._load_categories_from_file(csv_file)

        # Load from categories_2.csv
        csv_file = PRODUCTION_DATA_DIR / "product_category" / "categories_2.csv"
        if csv_file.exists():
            count += await self._load_categories_from_file(csv_file)

        # Add generic categories needed for price list
        # Note: codes will be normalized (spaces/hyphens → underscores)
        generic_categories = [
            ("CACTUS", "Cactus"),
            ("SUCULENTAS", "Suculentas"),
            ("AGAVES", "Agaves"),
            ("PIEDRA_FLUO", "Piedra Fluo"),
            ("PIEDRA_MATE", "Piedra Mate"),
        ]

        for code, name in generic_categories:
            try:
                stmt = select(ProductCategory).where(ProductCategory.code == code)
                result = await self.session.execute(stmt)
                existing = result.scalar_one_or_none()

                if not existing:
                    category = ProductCategory(
                        code=code,
                        name=name,
                        description=f"Category: {name}",
                    )
                    self.session.add(category)
                    count += 1
                    logger.debug(f"  ✓ Generic category: {code}")
            except Exception as e:
                logger.debug(f"  ⊘ Error adding generic category {code}: {str(e)}")

        await self.session.commit()
        self.loaded_count["product_categories"] = count
        logger.info(f"✅ Loaded {count} product categories")
        return count

    async def _load_categories_from_file(self, csv_file: Path) -> int:
        """Load categories from a single CSV file.

        Args:
            csv_file: Path to CSV file

        Returns:
            Number of categories loaded
        """
        logger.info(f"Loading categories from {csv_file}...")
        count = 0

        try:
            df = pd.read_csv(csv_file, header=None)

            # Extract unique categories from column 0
            for idx, row in df.iterrows():
                try:
                    # Column 0: Category type (SUCCULENT, CACTUS, etc.)
                    category_type = str(row.iloc[0]).strip().upper() if len(row) > 0 else None
                    if not category_type or category_type == "NAN":
                        continue

                    code = self._sanitize_code(category_type)

                    stmt = select(ProductCategory).where(ProductCategory.code == code)
                    result = await self.session.execute(stmt)
                    existing = result.scalar_one_or_none()

                    if not existing:
                        category = ProductCategory(
                            code=code,
                            name=category_type,
                            description=f"Category: {category_type}",
                        )
                        self.session.add(category)
                        count += 1
                        logger.info(f"  ✓ Category: {code}")

                except Exception as e:
                    logger.debug(f"  ⊘ Error parsing row {idx}: {str(e)}")
                    continue

            await self.session.commit()

        except Exception as e:
            logger.error(f"Error loading categories from {csv_file}: {str(e)}", exc_info=True)

        return count

    def _generate_hex_for_color(self, color_name: str) -> str:
        """Generate a hex color code from a color name.

        Maps common Spanish color names to hex codes.

        Args:
            color_name: Color name (e.g., "TERRACOTA")

        Returns:
            Hex color code (e.g., "#8B4513")
        """
        color_map = {
            "TERRACOTA": "#8B4513",  # Brown
            "DORADA": "#FFD700",  # Gold
            "GRIS": "#808080",  # Gray
            "BLANCO": "#FFFFFF",  # White
            "AZUL": "#0000FF",  # Blue
            "NEGRA": "#000000",  # Black
            "NEGRO": "#000000",  # Black
            "VIOLETA": "#EE82EE",  # Violet
            "ROJO": "#FF0000",  # Red
            "VERDE": "#008000",  # Green
        }
        # Return mapped color or a default gray
        return color_map.get(color_name.upper(), "#A9A9A9")

    def _sanitize_code(self, value: str) -> str:
        """Sanitize string for use as category code.

        Args:
            value: Original string

        Returns:
            Sanitized code (uppercase, alphanumeric + underscores, max 50 chars)
        """
        # Remove non-alphanumeric characters except underscores
        code = re.sub(r"[^A-Za-z0-9_]", "_", value).upper()[:50]
        # Remove leading/trailing underscores
        code = code.strip("_")
        return code or "UNKNOWN"

    # =========================================================================
    # StorageBinType Loading (Hardcoded Seed Data)
    # =========================================================================

    async def load_storage_bin_types(self) -> int:
        """Load storage bin types from seed data.

        Creates the 4 required types:
        - SEGMENTO (Segment)
        - PLUGS (Plug tray)
        - ALMACIGOS (Seedling tray)
        - CAJONES (Box)

        Returns:
            Number of bin types loaded/updated
        """
        logger.info("Loading storage bin types...")

        bin_types = [
            {
                "code": "SEGMENTO",
                "name": "Segmento Individual",
                "category": BinCategoryEnum.SEGMENT,
                "is_grid": False,
                "description": "Individual segment detected by ML (no fixed dimensions)",
            },
            {
                "code": "PLUGS",
                "name": "Plug Tray",
                "category": BinCategoryEnum.PLUG,
                "is_grid": True,
                "rows": 18,
                "columns": 16,
                "capacity": 288,
                "length_cm": 54.0,
                "width_cm": 27.5,
                "height_cm": 5.5,
                "description": "Standard 288-cell plug tray",
            },
            {
                "code": "ALMACIGOS",
                "name": "Almácigos/Seedling Tray",
                "category": BinCategoryEnum.SEEDLING_TRAY,
                "is_grid": True,
                "rows": 10,
                "columns": 10,
                "capacity": 100,
                "length_cm": 40.0,
                "width_cm": 30.0,
                "height_cm": 8.0,
                "description": "Seedling/almácigos tray",
            },
            {
                "code": "CAJONES",
                "name": "Cajones/Transport Box",
                "category": BinCategoryEnum.BOX,
                "is_grid": False,
                "length_cm": 60.0,
                "width_cm": 40.0,
                "height_cm": 20.0,
                "description": "Transport/storage box (no fixed grid)",
            },
        ]

        count = 0
        for bin_type_data in bin_types:
            try:
                stmt = select(StorageBinType).where(StorageBinType.code == bin_type_data["code"])
                result = await self.session.execute(stmt)
                existing = result.scalar_one_or_none()

                if not existing:
                    bin_type = StorageBinType(**bin_type_data)
                    self.session.add(bin_type)
                    count += 1
                    logger.info(f"  ✓ StorageBinType: {bin_type_data['code']}")
                else:
                    logger.info(f"  ⊘ StorageBinType already exists: {bin_type_data['code']}")

            except Exception as e:
                logger.error(f"  ✗ Error creating storage bin type: {str(e)}", exc_info=True)

        await self.session.commit()
        self.loaded_count["storage_bin_types"] = count
        logger.info(f"✅ Loaded {count} storage bin types")
        return count

    # =========================================================================
    # Packaging & PriceList Loading (from CSV)
    # =========================================================================

    async def load_price_list(self) -> int:
        """Load complete pricing catalog from CSV file.

        Loads:
        1. PackagingTypes (Rígida, Soplada, Termoformada, etc.)
        2. PackagingSizes (5, 8, 11, etc.)
        3. PackagingColors (Terracota, Dorada, Gris, etc.)
        4. PackagingCatalog (combinations of type+size+color)
        5. PriceList (ProductCategory + PackagingCatalog + prices)

        Returns:
            Number of price list entries loaded
        """
        csv_file = PRODUCTION_DATA_DIR / "price_list" / "price_list.csv"

        if not csv_file.exists():
            logger.warning(f"Price list file not found: {csv_file}")
            return 0

        logger.info(f"Loading pricing catalog from {csv_file}...")

        # Read CSV (skip header rows)
        df = pd.read_csv(csv_file, header=None)
        df_data = df.iloc[3:].reset_index(drop=True)

        # Extract unique packaging types, colors, sizes
        await self._load_packaging_metadata(df_data)

        # Load packaging catalog and prices
        count = await self._load_pricing_entries(df_data)

        self.loaded_count["price_list"] = count
        logger.info(f"✅ Loaded {count} price list entries")
        return count

    async def _load_packaging_metadata(self, df_data) -> None:
        """Load packaging types, colors, and sizes from data."""
        import re

        # Collect unique packaging descriptions
        packagings = set()
        colors_found = set()
        sizes_found = set()

        for _, row in df_data.iterrows():
            maceta = row[1]
            if pd.notna(maceta) and isinstance(maceta, str) and maceta:
                packagings.add(maceta)

                # Extract colors
                for color in [
                    "terracota",
                    "dorada",
                    "gris",
                    "blanco",
                    "azul",
                    "negra",
                    "negro",
                    "violeta",
                    "rojo",
                    "verde",
                ]:
                    if color.lower() in maceta.lower():
                        colors_found.add(color.upper())

                # Extract sizes (R5, R8, R9, T11, S10, etc.)
                match = re.search(r"(\d+|5LTS|10LTS|3LTS|20KG)", maceta)
                if match:
                    sizes_found.add(match.group(1))

        # Load colors
        logger.info(f"Loading {len(colors_found)} packaging colors...")
        for color in sorted(colors_found):
            try:
                stmt = select(PackagingColor).where(PackagingColor.name == color)
                result = await self.session.execute(stmt)
                existing = result.scalar_one_or_none()

                if not existing:
                    # PackagingColor only requires name and hex_code
                    # Generate a simple hex code based on color name
                    hex_code = self._generate_hex_for_color(color)
                    pkg_color = PackagingColor(name=color, hex_code=hex_code)
                    self.session.add(pkg_color)
                    logger.debug(f"  ✓ Color: {color} ({hex_code})")
            except Exception as e:
                logger.debug(f"  ⊘ Error adding color {color}: {str(e)}")

        await self.session.commit()

    async def _load_pricing_entries(self, df_data) -> int:
        """Load PackagingCatalog and PriceList entries."""
        count = 0
        skipped_categories = set()
        skipped_prices = 0

        for idx, row in df_data.iterrows():
            try:
                categoria = row[0]
                maceta = row[1]
                precio_str = row[2]
                sku = row[3]

                # Skip invalid rows
                if not (pd.notna(categoria) and pd.notna(maceta) and pd.notna(precio_str)):
                    continue

                categoria = str(categoria).strip().upper()
                maceta = str(maceta).strip()
                sku = str(sku).strip() if pd.notna(sku) else None

                # Clean category name (convert spaces/hyphens to underscores)
                # This ensures "PIEDRA FLUO" becomes "PIEDRA_FLUO"
                categoria_clean = re.sub(r"[\s\-]+", "_", categoria).upper()
                categoria_clean = re.sub(r"[^A-Za-z0-9_]", "", categoria_clean).upper()

                # Get product category (try exact match first, then other strategies)
                product_category = None

                # Strategy 1: Exact code match
                stmt = select(ProductCategory).where(ProductCategory.code == categoria_clean)
                result = await self.session.execute(stmt)
                product_category = result.scalar_one_or_none()

                # Strategy 2: Name match
                if not product_category:
                    stmt = select(ProductCategory).where(ProductCategory.name == categoria)
                    result = await self.session.execute(stmt)
                    product_category = result.scalar_one_or_none()

                # Strategy 3: Like match (case-insensitive substring)
                if not product_category:
                    stmt = select(ProductCategory).where(
                        ProductCategory.code.ilike(f"%{categoria_clean}%")
                    )
                    result = await self.session.execute(stmt)
                    product_category = result.scalar_one_or_none()

                # Strategy 4: Partial match on first 5 chars
                if not product_category and len(categoria_clean) >= 3:
                    search_prefix = categoria_clean[:5]
                    stmt = select(ProductCategory).where(
                        ProductCategory.code.startswith(search_prefix)
                    )
                    result = await self.session.execute(stmt)
                    product_category = result.scalar_one_or_none()

                if not product_category:
                    skipped_categories.add(categoria)
                    logger.debug(f"  ⊘ Row {idx}: Category not found: {categoria}")
                    skipped_prices += 1
                    continue

                # Parse price (remove $ and convert to cents)
                precio_str = str(precio_str).replace("$", "").replace(",", ".").strip()
                try:
                    unit_price = float(precio_str)
                    # Handle prices < 100 (e.g., 1.05 = $1.05, not $0.0105)
                    if unit_price < 100:
                        unit_price_cents = int(unit_price * 100)
                    else:
                        # Already in cents
                        unit_price_cents = int(unit_price)
                except ValueError:
                    logger.debug(f"  ⊘ Row {idx}: Invalid price: {precio_str}")
                    skipped_prices += 1
                    continue

                # Get or create packaging catalog
                stmt = select(PackagingCatalog).where(
                    PackagingCatalog.description.ilike(f"%{maceta}%")
                )
                result = await self.session.execute(stmt)
                packaging = result.scalar_one_or_none()

                if not packaging:
                    # Create new packaging catalog entry
                    packaging = PackagingCatalog(
                        code=sku[:20] if sku else f"PKG{count:04d}",
                        description=maceta[:200],
                    )
                    self.session.add(packaging)
                    await self.session.flush()  # Get the ID
                    logger.debug(f"  ✓ New packaging: {maceta[:50]}")

                # Create price list entry
                try:
                    stmt = select(PriceList).where(
                        (PriceList.packaging_catalog_id == packaging.id)
                        & (PriceList.product_categories_id == product_category.id)
                    )
                    result = await self.session.execute(stmt)
                    existing_price = result.scalar_one_or_none()

                    if not existing_price:
                        price_entry = PriceList(
                            packaging_catalog_id=packaging.id,
                            product_categories_id=product_category.id,
                            wholesale_unit_price=unit_price_cents,
                            retail_unit_price=unit_price_cents,
                            SKU=sku,
                        )
                        self.session.add(price_entry)
                        count += 1
                        logger.debug(
                            f"  ✓ Price: {categoria[:10]} - {maceta[:30]} - ${unit_price_cents / 100:.2f}"
                        )
                    else:
                        logger.debug("  ⊘ Price already exists")

                except Exception as e:
                    logger.debug(f"  ⊘ Row {idx}: Error creating price entry: {str(e)}")

            except Exception as e:
                logger.debug(f"  ⊘ Row {idx}: Error processing: {str(e)}")

        try:
            await self.session.commit()
            logger.info(f"  Loaded {count} price list entries")
            if skipped_categories:
                logger.info(
                    f"  Skipped {skipped_prices} entries with missing categories: {sorted(skipped_categories)}"
                )
        except Exception as e:
            logger.error(f"  ✗ Error committing price list: {str(e)}")
            await self.session.rollback()

        return count

    # =========================================================================
    # Main Load Methods
    # =========================================================================

    async def load_all_async(self) -> dict[str, int]:
        """Load all production data.

        Loads in dependency order:
        1. Warehouses
        2. StorageAreas
        3. StorageLocations
        4. ProductCategories
        5. StorageBinTypes
        6. PriceList

        Returns:
            Dictionary with counts of loaded items
        """
        logger.info("=" * 80)
        logger.info("🚀 Loading production data...")
        logger.info("=" * 80)

        try:
            await self.load_warehouses()
            await self.load_storage_areas()
            await self.load_storage_locations()
            await self.load_product_categories()
            await self.load_storage_bin_types()
            await self.load_price_list()

            logger.info("=" * 80)
            logger.info("✅ Production data load complete!")
            logger.info(f"Loaded: {self.loaded_count}")
            logger.info("=" * 80)

            return self.loaded_count

        except Exception as e:
            logger.error(
                "❌ Production data load failed",
                error=str(e),
                exc_info=True,
            )
            raise
