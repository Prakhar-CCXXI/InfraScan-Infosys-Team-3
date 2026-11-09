"""FastAPI router for infrastructure damage analysis and AI predictions."""

from datetime import datetime
import io
import logging
from pathlib import Path
from typing import Any
from uuid import uuid4

import aiofiles
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from PIL import Image
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings
from backend.db.session import get_async_db
from backend.models.prediction import Prediction
from backend.schemas.prediction import PredictionResponse
from backend.services.ai_inference import AIInferenceService, get_ai_inference_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/predictions", tags=["Predictions"])
images_router = APIRouter(prefix="/images", tags=["Images"])


def parse_asset_id(raw_val: Any) -> int:
    """Parse asset identifier into an integer matching the predictions table schema."""
    if raw_val is None:
        return 1
    if isinstance(raw_val, int):
        if raw_val <= 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Asset ID must be a positive integer.",
            )
        return raw_val

    s = str(raw_val).strip()
    if not s:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Field 'asset_id' cannot be blank.",
        )

    # Check for prefix like 'INF-001'
    if s.upper().startswith("INF-"):
        digits = "".join(c for c in s if c.isdigit())
        if digits:
            val = int(digits)
            if val > 0:
                return val

    try:
        val = int(s)
        if val <= 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Asset ID must be a positive integer.",
            )
        return val
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid asset identifier '{raw_val}'. Expected positive integer or 'INF-XXX'.",
        ) from exc


async def process_and_store_image(
    file: UploadFile,
    asset_id: int,
    db: AsyncSession,
    ai_service: AIInferenceService,
) -> tuple[Prediction, str]:
    """Validate, asynchronously store image on disk, execute AI pipeline, and persist to database."""
    # 1. Filename validation
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No filename provided in upload payload.",
        )

    # 2. Content-type (MIME) validation
    if file.content_type not in settings.ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                f"Unsupported image media type '{file.content_type}'. "
                f"Allowed types are: {', '.join(settings.ALLOWED_IMAGE_TYPES)}"
            ),
        )

    # 3. Read image bytes asynchronously
    try:
        image_bytes = await file.read()
    except Exception as exc:
        logger.error(f"Failed to read uploaded file: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to read uploaded image asynchronously.",
        ) from exc

    # 4. Size validation
    file_size = len(image_bytes)
    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded image file is empty (0 bytes).",
        )

    if file_size > settings.max_image_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds maximum allowed threshold of {settings.MAX_IMAGE_SIZE_MB}MB.",
        )

    # 5. Deep Format & Integrity Verification (using Pillow)
    try:
        with Image.open(io.BytesIO(image_bytes)) as pil_img:
            pil_img.verify()
            detected_format = (pil_img.format or "").upper()
            if detected_format not in {"JPEG", "JPG", "PNG", "WEBP"}:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid image structure or unrecognized image format: {detected_format}",
                )
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning(f"Image verification failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is corrupted or not a valid image format.",
        ) from exc

    # 6. Store image on backend storage asynchronously
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)

    file_suffix = Path(file.filename).suffix.lower() or ".jpg"
    unique_filename = f"{uuid4().hex}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{file_suffix}"
    destination_path = upload_dir / unique_filename

    try:
        async with aiofiles.open(destination_path, "wb") as buffer:
            await buffer.write(image_bytes)
    except Exception as exc:
        logger.error(f"Error persisting file to disk: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to persist uploaded image file on storage.",
        ) from exc

    # 7. Decoupled AI Model Inference
    try:
        inference_output = await ai_service.analyze(
            image_bytes=image_bytes,
            filename=unique_filename,
        )
    except Exception as exc:
        logger.error(f"AI inference pipeline failure: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during AI computer vision inference.",
        ) from exc

    # 8. Asynchronously Persist Record to 'predictions' Table
    prediction_record = Prediction(
        asset_id=asset_id,
        image_path=str(destination_path),
        image_filename=unique_filename,
        predicted_failure_date=inference_output.predicted_failure_date,
        confidence_score=inference_output.confidence_score,
        recommended_action=inference_output.recommended_action,
        severity_level=inference_output.severity_level,
        defect_summary=inference_output.defect_summary,
        defect_details=inference_output.defect_details,
    )

    db.add(prediction_record)
    await db.commit()
    await db.refresh(prediction_record)

    relative_url = f"/uploads/{unique_filename}"
    return prediction_record, relative_url


@router.post(
    "/analyze",
    response_model=PredictionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload image and perform AI crack detection & segmentation",
    description="Accepts an infrastructure image and an asset_id, executes AI defect detection, stores image, and saves prediction.",
)
async def analyze_infrastructure_image(
    asset_id: Any = Form(..., description="Unique infrastructure asset identifier (e.g. 1 or INF-001)"),
    file: UploadFile = File(..., description="Uploaded infrastructure inspection image"),
    db: AsyncSession = Depends(get_async_db),
    ai_service: AIInferenceService = Depends(get_ai_inference_service),
) -> Prediction:
    """Validate image, run AI crack detection/segmentation, persist prediction, and return analysis."""
    parsed_id = parse_asset_id(asset_id)
    prediction_record, _ = await process_and_store_image(
        file=file,
        asset_id=parsed_id,
        db=db,
        ai_service=ai_service,
    )
    return prediction_record


@images_router.post(
    "/upload",
    status_code=status.HTTP_201_CREATED,
    summary="Upload inspection images from frontend form, store on backend, and run AI analysis",
)
async def upload_frontend_images(
    images: list[UploadFile] = File(None, description="Multiple uploaded images"),
    file: UploadFile = File(None, description="Single uploaded image"),
    assetId: str | None = Form(None),
    asset_id: str | None = Form(None),
    date: str | None = Form(None),
    inspector: str | None = Form(None),
    notes: str | None = Form(None),
    db: AsyncSession = Depends(get_async_db),
    ai_service: AIInferenceService = Depends(get_ai_inference_service),
) -> dict[str, Any]:
    """Endpoint consumed by frontend Upload form. Receives image(s), saves to backend, and returns AI findings."""
    raw_asset = assetId or asset_id or "1"
    parsed_asset_id = parse_asset_id(raw_asset)

    # Consolidate uploaded files
    file_list: list[UploadFile] = []
    if images:
        file_list.extend(images)
    if file and file not in file_list:
        file_list.append(file)

    if not file_list:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please provide at least one valid image to upload.",
        )

    saved_images = []
    predictions_data = []

    for item in file_list:
        record, image_url = await process_and_store_image(
            file=item,
            asset_id=parsed_asset_id,
            db=db,
            ai_service=ai_service,
        )

        saved_images.append({
            "filename": record.image_filename,
            "image_path": record.image_path,
            "image_url": image_url,
        })

        predictions_data.append({
            "id": record.id,
            "asset_id": record.asset_id,
            "severity_level": record.severity_level,
            "confidence_score": record.confidence_score,
            "recommended_action": record.recommended_action,
            "predicted_failure_date": record.predicted_failure_date.isoformat() if record.predicted_failure_date else None,
            "defect_summary": record.defect_summary,
            "defect_details": record.defect_details,
            "image_url": image_url,
            "created_at": record.created_at.isoformat() if record.created_at else None,
        })

    primary_prediction = predictions_data[0]
    return {
        "status": "success",
        "message": (
            f"Successfully stored {len(file_list)} image(s) in backend storage! "
            f"AI Assessment: {primary_prediction['severity_level']} "
            f"(Confidence: {int(primary_prediction['confidence_score'] * 100)}%). "
            f"Action: {primary_prediction['recommended_action'][:80]}..."
        ),
        "count": len(file_list),
        "asset_id": parsed_asset_id,
        "inspector": inspector,
        "date": date,
        "stored_images": saved_images,
        "predictions": predictions_data,
    }


@router.get(
    "/{prediction_id}",
    response_model=PredictionResponse,
    summary="Retrieve prediction by record ID",
)
async def get_prediction_by_id(
    prediction_id: int,
    db: AsyncSession = Depends(get_async_db),
) -> Prediction:
    """Retrieve an existing AI damage prediction by its primary key ID."""
    query = select(Prediction).where(Prediction.id == prediction_id)
    result = await db.execute(query)
    prediction = result.scalar_one_or_none()

    if prediction is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prediction with ID {prediction_id} not found.",
        )
    return prediction


@router.get(
    "/asset/{asset_id}",
    response_model=list[PredictionResponse],
    summary="Retrieve all predictions for a specific infrastructure asset",
)
async def get_predictions_for_asset(
    asset_id: int,
    db: AsyncSession = Depends(get_async_db),
) -> list[Prediction]:
    """Retrieve all historic AI predictions linked to a given asset_id."""
    query = (
        select(Prediction)
        .where(Prediction.asset_id == asset_id)
        .order_by(Prediction.created_at.desc())
    )
    result = await db.execute(query)
    predictions = result.scalars().all()
    return list(predictions)
