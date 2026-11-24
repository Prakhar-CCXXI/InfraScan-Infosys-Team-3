from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field

InferenceProfile = Literal["close_up", "road_scene"]


class BoundingBox(BaseModel):
    """Axis-aligned box in ORIGINAL-image pixels (top-left origin)."""

    x_min: float = Field(..., description="Minimum X coordinate")
    y_min: float = Field(..., description="Minimum Y coordinate")
    x_max: float = Field(..., description="Maximum X coordinate")
    y_max: float = Field(..., description="Maximum Y coordinate")
    class_name: str = Field(..., description="Defect class: RDD2022 code (D00/D10/D20/D40) or 'crack'")
    confidence: float | None = Field(
        default=None, ge=0.0, le=1.0,
        description="Detector confidence; null when the box is derived from a segmentation mask",
    )


class SegmentationMask(BaseModel):
    """Simplified polygon contour (original-image pixels) derived from the U-Net mask."""

    polygon: list[list[float]] = Field(
        ...,
        description="Ordered list of [x, y] coordinates defining defect boundary contour",
    )
    area_pixels: float = Field(..., description="Pixel area of the connected crack component (original-image px)")
    estimated_length_px: float | None = Field(default=None, description="Not computed per component")
    estimated_width_px: float | None = Field(default=None, description="Not computed per component")
    mask_confidence: float | None = Field(default=None, ge=0.0, le=1.0, description="Not produced by the U-Net")


class DefectItem(BaseModel):
    """Detailed defect occurrence combining detection bounding box and optional mask polygon."""

    id: int = Field(..., description="Defect identifier index")
    defect_type: str = Field(..., description="Category of damage identified")
    severity: str = Field(..., description="Overall severity (per-defect severity is not modelled)")
    bounding_box: BoundingBox = Field(..., description="Bounding box localization")
    segmentation_mask: SegmentationMask | None = Field(
        default=None, description="close_up only; null for road_scene"
    )


class DefectAnalysis(BaseModel):
    """Aggregated computer vision defect assessment (backwards-compatible superset)."""

    model_config = ConfigDict(extra="allow")

    total_defects: int = Field(..., description="Total count of defects detected")
    severity_level: str = Field(..., description="Overall damage severity classification")
    crack_density_percentage: float | None = Field(
        default=None, ge=0.0, le=100.0,
        description="close_up only (measurements.crack_density_percent); null for road_scene",
    )
    defects: list[DefectItem] = Field(default_factory=list, description="List of detected defect instances")
    summary: str = Field(..., description="Human-readable inspection summary")

    # --- additive, optional traceability fields ---
    source: Literal["model", "mock"] | None = Field(default=None, description="'mock' means NOT real model output")
    profile: InferenceProfile | None = None
    confidence_basis: str | None = Field(
        default=None, description="How confidence_score was derived (max_detection_confidence | not_available | mock)"
    )
    class_counts: dict[str, int] | None = None
    measurements: dict[str, Any] | None = None
    warnings: list[str] = Field(default_factory=list)
    models: list[dict[str, Any]] | None = Field(default=None, description="Model ids + SHA-256 used")
    coordinate_frame: dict[str, Any] | None = None
    artifacts: dict[str, str | None] | None = Field(default=None, description="mask_uri / overlay_uri")
    severity_assessment: dict[str, Any] | None = None
    preprocessing: dict[str, Any] | None = None
    raw_inference: dict[str, Any] | None = Field(default=None, description="Full InferenceService result JSON")


class PredictionResponse(BaseModel):
    """Structured response schema returned after AI analysis and database persistence."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Database record ID in the predictions table")
    asset_id: int = Field(..., description="Linked infrastructure asset identifier")
    predicted_failure_date: datetime | None = Field(
        default=None,
        description="Always null for model-based results: no validated failure-date model exists",
    )
    confidence_score: float = Field(
        ..., ge=0.0, le=1.0,
        description="Max detector confidence; 0.0 when none is available (see defect_details.confidence_basis)",
    )
    recommended_action: str = Field(..., description="Advisory recommendation (requires engineering review)")
    severity_level: str = Field(..., description="Overall structural damage severity")
    image_filename: str = Field(..., description="Stored image filename")
    image_path: str = Field(..., description="Relative or absolute file path of the uploaded image")
    defect_summary: str | None = Field(default=None, description="Concise overview of detected defects")
    defect_details: DefectAnalysis | dict[str, Any] | None = Field(
        default=None,
        description="Defects, boxes/polygons, model hashes, warnings and the raw inference result",
    )
    created_at: datetime = Field(..., description="Timestamp when prediction was analyzed and saved")
