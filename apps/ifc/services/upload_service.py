"""
IFC Upload Service (ADR-041 Service Layer).

Handles file validation, size checks, and IFC model creation from uploads.
"""

import logging
import os

from django.core.files.uploadedfile import UploadedFile

from ..models import IFCModel, IFCProject

logger = logging.getLogger(__name__)

# Max file size: 500 MB
MAX_IFC_FILE_SIZE_BYTES = 500 * 1024 * 1024
ALLOWED_EXTENSIONS = {".ifc"}


class UploadValidationError(Exception):
    """Raised when upload validation fails."""

    def __init__(self, message: str, code: str = "invalid"):
        self.message = message
        self.code = code
        super().__init__(message)


def validate_ifc_file(file: UploadedFile) -> None:
    """Validate an uploaded IFC file.

    Raises UploadValidationError if validation fails.
    """
    if not file:
        raise UploadValidationError(
            "Keine Datei ausgewählt.",
            code="no_file",
        )

    # Extension check
    _, ext = os.path.splitext(file.name)
    if ext.lower() not in ALLOWED_EXTENSIONS:
        raise UploadValidationError(
            f"Ungültiges Dateiformat: {ext}. Nur .ifc Dateien werden unterstützt.",
            code="invalid_extension",
        )

    # Size check
    if file.size > MAX_IFC_FILE_SIZE_BYTES:
        max_mb = MAX_IFC_FILE_SIZE_BYTES // (1024 * 1024)
        file_mb = file.size / (1024 * 1024)
        raise UploadValidationError(
            f"Datei zu groß: {file_mb:.1f} MB. Maximum: {max_mb} MB.",
            code="file_too_large",
        )

    # IFC magic bytes check (ISO-10303-21 starts with "ISO-10303-21;")
    first_bytes = file.read(64)
    file.seek(0)

    if not first_bytes:
        raise UploadValidationError(
            "Datei ist leer.",
            code="empty_file",
        )

    # IFC files start with ISO-10303-21 header or STEP marker
    header = first_bytes.decode("ascii", errors="ignore").strip()
    if not (header.startswith("ISO-10303-21") or header.startswith("STEP;")):
        raise UploadValidationError(
            "Ungültige IFC-Datei: Header nicht erkannt. "
            "Unterstützt werden IFC2x3 und IFC4 Dateien.",
            code="invalid_header",
        )


def create_ifc_model_from_upload(
    project: IFCProject,
    file: UploadedFile,
    tenant_id,
) -> IFCModel:
    """Create an IFCModel record and trigger async processing.

    Args:
        project: The parent project.
        file: Validated uploaded IFC file.
        tenant_id: Tenant UUID.

    Returns:
        The created IFCModel instance (status=UPLOADING).
    """
    from .ifc_query_service import get_next_version

    version = get_next_version(project)

    ifc_model = IFCModel.objects.create(
        tenant_id=tenant_id,
        project=project,
        version=version,
        ifc_file=file,
        status=IFCModel.Status.UPLOADING,
    )

    logger.info(
        "IFC upload created: model=%s, project=%s, version=%d, size=%d bytes",
        ifc_model.pk,
        project.pk,
        version,
        file.size,
    )

    # Trigger async processing
    from ..tasks import process_ifc_upload

    process_ifc_upload.delay(str(ifc_model.pk))

    return ifc_model
