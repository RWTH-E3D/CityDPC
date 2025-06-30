from citydpc.dataset import Dataset

from citydpc.logger import logger
from . import config

from typing import List, Type, Optional


def configure_warnings(
    warn_always: bool = None,
    suppress_warnings: Optional[List[Type[Warning]]] = None,
):
    """Configure the warning behavior of the library.

    Parameters
    ----------
    warn_always : bool, optional
        If True, the library will always show warnings for each occurrence.
        If False, it will only show one warning per category (default is False)
    """
    if warn_always is not None:
        config.WARN_ONCE_PER_CATEGORY = not warn_always
        logger.info(
            "Configured warnings: "
            + f"{'always' if warn_always else 'once per category'}"
        )

    if suppress_warnings is not None:
        config.SUPPRESSED_WARNING_CATEGORIES = set(suppress_warnings)
        logger.info(
            "Configured suppressed warnings: "
            + f"{', '.join([w.__name__ for w in suppress_warnings])}"
        )
