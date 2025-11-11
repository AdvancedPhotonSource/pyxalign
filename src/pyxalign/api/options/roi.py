import dataclasses
from dataclasses import field
from enum import StrEnum, auto
from typing import Optional


class ROIType(StrEnum):
    RECTANGULAR = auto()
    ELLIPTICAL = auto()


@dataclasses.dataclass
class RectangularROIOptions:
    horizontal_range: Optional[int] = None

    vertical_range: Optional[int] = None

    horizontal_offset: int = 0

    vertical_offset: int = 0


@dataclasses.dataclass
class EllipticalROIOptions:
    pass


@dataclasses.dataclass
class ROIOptions:
    shape: ROIType = ROIType.RECTANGULAR

    rectangle: RectangularROIOptions = field(default_factory=RectangularROIOptions)