"""
IFC background tasks — Celery @shared_task wrappers.

Source: bfagent/apps/cad_hub/tasks.py (212 lines, plain functions).
Converted to @shared_task during extraction.
"""
from celery import shared_task


@shared_task
def process_ifc_upload(model_id: str) -> None:
    """Process an IFC upload (floors, rooms, DIN 277 classification)."""
    # Will be populated from bfagent/apps/cad_hub/tasks.py
    pass
