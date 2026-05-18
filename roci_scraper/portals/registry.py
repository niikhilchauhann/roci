from .igrsup import IgrsupAdapter
from .bhunaksha import BhunakshaAdapter
from .bhulekh import BhulekhAdapter
from .cppp_gem import CpppGemAdapter
from .rera_up import ReraUpAdapter

ALL_PORTALS = [
    IgrsupAdapter(),
    BhunakshaAdapter(),
    BhulekhAdapter(),
    CpppGemAdapter(),
    ReraUpAdapter(),
]
