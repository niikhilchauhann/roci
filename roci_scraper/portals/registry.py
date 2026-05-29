from .igrsup import CachedIgrsupAdapter
from .bhunaksha import BhunakshaAdapter
from .bhulekh import BhulekhAdapter
from .cppp_gem import CpppGemAdapter
from .rera_up import ReraUpAdapter

ALL_PORTALS = [
    CachedIgrsupAdapter(),
    BhunakshaAdapter(),
    BhulekhAdapter(),
    CpppGemAdapter(),
    ReraUpAdapter(),
]
