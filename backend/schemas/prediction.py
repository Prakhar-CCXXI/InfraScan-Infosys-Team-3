from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class BoundingBox(BaseModel):
    """Normalized or pixel coordinates for detected defects."""

    x_min: float = Field(..., description="Minimum X coordinate")
    y_min: float = Field(..., description="Minimum Y coordinate")
    x_max: float = Field(..., description="Maximum X coordinate")
    y_max: float = Field(..., description="Maximum Y coordinate")
    class_name: str = Field(..., description="Defect class (e.g. crack, spalling, exposed_rebar)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Detection confidence score")


class SegmentationMask(BaseModel):
    """Pixel-level polygon contour segmentation mask for cracks."""

    polygon: list[list[float]] = Field(
        ...,
        description="Ordered list of [x, y] coordinates defining defect boundary contour",
    )
    area_pixels: float = Field(..., description="Total pixel area covered by the defect mask")
    estimated_length_px: float | None = Field(default=None, description="Estimated crack length in pixels")
    estimated_width_px: float | None = Field(default=None, description="Estimated maximum crack width in pixels")
    mask_confidence: float = Field(..., ge=0.0, le=1.0, description="Pixel-level segmentation confidence")


class DefectItem(BaseModel):
    """Detailed defect occurrence combining detection bounding box and segmentation mask."""

    id: int = Field(..., description="Defect identifier index")
    defect_type: str = Field(..., description="Category of damage identified")
    severity: str = Field(..., description="Severity classification for this defect")
    bounding_box: BoundingBox = Field(..., description="Bounding box localization")
    segmentation_mask: SegmentationMask | None = Field(
        default=None, description="Optional fine-grained pixel mask"
    )


class DefectAnalysis(BaseModel):
    """Aggregated computer vision defect assessment."""

    total_defects: int = Field(..., description="Total count of defects detected")
    severity_level: str = Field(..., description="Overall damage severity classification")
    crack_density_percentage: float = Field(..., ge=0.0, le=100.0, description="Percentage of surface impacted")
    defects: list[DefectItem] = Field(default_factory=list, description="List of detected defect instances")
    summary: str = Field(..., description="Human-readable inspection summary")


class PredictionResponse(BaseModel):
    """Structured response schema returned after AI analysis and database persistence."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Database record ID in the predictions table")
    asset_id: int = Field(..., description="Linked infrastructure asset identifier")
    predicted_failure_date: datetime | None = Field(
        default=None,
        description="Forecasted failure or maintenance deadline date based on damage progression",
    )
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Overall AI confidence score")
    recommended_action: str = Field(..., description="Prescriptive engineering recommendation")
    severity_level: str = Field(..., description="Overall structural damage severity")
    image_filename: str = Field(..., description="Stored image filename")
    image_path: str = Field(..., description="Relative or absolute file path of the uploaded image")
    defect_summary: str | None = Field(default=None, description="Concise overview of detected defects")
    defect_details: DefectAnalysis | dict[str, Any] | None = Field(
        default=None,
        description="Fine-grained defect coordinates, bounding boxes, and segmentation masks",
    )
    created_at: datetime = Field(..., description="Timestamp when prediction was analyzed and saved")
