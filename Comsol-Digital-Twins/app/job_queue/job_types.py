from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class ActiveJob:
    job: Dict[str, Any]
    input_params: str
    input_temperature_table: str
    output_pl: str
    output_values: str
