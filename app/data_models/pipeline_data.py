# app/data_models/pipeline_data.py
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class PipelineData:
    """
    Structured data model for pipeline operations.
    """

    main_file_path: Optional[str] = None
    intro_file_path: Optional[str] = None
    outro_file_path: Optional[str] = None

    active_file_path: Optional[str] = None
    final_output_path: Optional[str] = None
    downloaded_files: List[str] = field(default_factory=list)
    intermediate_files: List[str] = field(default_factory=list)
