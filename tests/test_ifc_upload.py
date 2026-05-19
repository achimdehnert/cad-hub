"""
Tests for IFC file upload (Issue #1).

Tests upload validation, API endpoint, and service layer.
"""

import io
import uuid

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory

from apps.ifc.services.upload_service import (
    MAX_IFC_FILE_SIZE_BYTES,
    UploadValidationError,
    validate_ifc_file,
)


class TestValidateIFCFile:
    """Tests for validate_ifc_file service function."""

    def test_should_reject_no_file(self):
        with pytest.raises(UploadValidationError) as exc_info:
            validate_ifc_file(None)
        assert exc_info.value.code == "no_file"

    def test_should_reject_wrong_extension(self):
        file = SimpleUploadedFile(
            "model.dwg", b"some content", content_type="application/octet-stream"
        )
        with pytest.raises(UploadValidationError) as exc_info:
            validate_ifc_file(file)
        assert exc_info.value.code == "invalid_extension"
        assert ".dwg" in exc_info.value.message

    def test_should_reject_empty_file(self):
        file = SimpleUploadedFile("model.ifc", b"", content_type="application/octet-stream")
        with pytest.raises(UploadValidationError) as exc_info:
            validate_ifc_file(file)
        assert exc_info.value.code == "empty_file"

    def test_should_reject_invalid_header(self):
        file = SimpleUploadedFile(
            "model.ifc",
            b"This is not a valid IFC file content at all",
            content_type="application/octet-stream",
        )
        with pytest.raises(UploadValidationError) as exc_info:
            validate_ifc_file(file)
        assert exc_info.value.code == "invalid_header"

    def test_should_accept_valid_ifc2x3_header(self):
        content = b"ISO-10303-21;\nHEADER;\nFILE_DESCRIPTION(('ViewDefinition [CoordinationView]'),'2;1');\n"
        file = SimpleUploadedFile("model.ifc", content, content_type="application/octet-stream")
        # Should not raise
        validate_ifc_file(file)

    def test_should_accept_valid_step_header(self):
        content = b"STEP;\nHEADER;\nFILE_DESCRIPTION(('IFC4'),'2;1');\n"
        file = SimpleUploadedFile("model.ifc", content, content_type="application/octet-stream")
        validate_ifc_file(file)

    def test_should_reject_oversized_file(self):
        # Create a file that reports as too large via .size attribute
        content = b"ISO-10303-21;\n" + b"x" * 100
        file = SimpleUploadedFile("big.ifc", content, content_type="application/octet-stream")
        # Monkey-patch size to exceed limit
        file.size = MAX_IFC_FILE_SIZE_BYTES + 1
        with pytest.raises(UploadValidationError) as exc_info:
            validate_ifc_file(file)
        assert exc_info.value.code == "file_too_large"

    def test_should_accept_ifc_extension_case_insensitive(self):
        content = b"ISO-10303-21;\nHEADER;\n"
        file = SimpleUploadedFile("MODEL.IFC", content, content_type="application/octet-stream")
        validate_ifc_file(file)
