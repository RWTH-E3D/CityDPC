from citydpc.dataset import Dataset
from citydpc.logger import logger

from . import config


def configure_warnings(warn_always: bool = False):
    """Configure the warning behavior of the library.

    Parameters
    ----------
    warn_always : bool, optional
        If True, the library will always show warnings for each occurrence.
        If False, it will only show one warning per category (default is False)
    """
    config.WARN_ONCE_PER_CATEGORY = not warn_always
    logger.info(
        f"Configured warnings: {'always' if warn_always else 'once per category'}"
    )
