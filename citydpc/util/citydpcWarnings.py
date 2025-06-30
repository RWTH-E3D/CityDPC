import warnings
import inspect
import os

from ..config import WARN_ONCE_PER_CATEGORY, SUPPRESSED_WARNING_CATEGORIES

# Get the absolute path of the directory containing this file
_LIBRARY_ROOT_PATH = os.path.abspath(
    os.path.dirname(os.path.dirname(__file__))
)

_WARNED_CATEGORIES = set()


def warn(message: str, category: type[Warning]):
    """for finding the right stacklevel for warnings in the library.

    Parameters
    ----------
    message : str
        content of the warning message
    category : type[Warning]
        the warning category, e.g. UserWarning, DeprecationWarning, etc.
    """
    if category in SUPPRESSED_WARNING_CATEGORIES:
        return
    if WARN_ONCE_PER_CATEGORY and category in _WARNED_CATEGORIES:
        return
    _WARNED_CATEGORIES.add(category)
    try:
        stack = inspect.stack()

        # Walk up the stack frames to find the first one outside our library
        for frame_info in stack:
            frame_filename = os.path.abspath(frame_info.filename)

            # If the file path of the frame is NOT inside our library's root
            if not frame_filename.startswith(_LIBRARY_ROOT_PATH):
                warnings.warn(
                    message, category, stacklevel=stack.index(frame_info) + 1
                )
                return

        # fallback
        warnings.warn(message, category, stacklevel=2)

    except Exception:
        # make sure to warn if something fails
        warnings.warn(message, category, stacklevel=2)
