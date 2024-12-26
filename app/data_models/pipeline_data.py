# app/data_models/pipeline_data.py
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class PipelineData:
    """
    Structured data model for pipeline operations.
    """

    audio_file_path: Optional[str] = None
    audio_intro_path: Optional[str] = None
    audio_outro_path: Optional[str] = None

    active_file_path: Optional[str] = None
    final_output_path: Optional[str] = None
    downloaded_files: List[str] = field(default_factory=list)
