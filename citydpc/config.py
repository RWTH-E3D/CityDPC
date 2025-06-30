
from typing import Set, Type

# only show one warning per category
WARN_ONCE_PER_CATEGORY = False

# Suppress specific warning categories
SUPPRESSED_WARNING_CATEGORIES: Set[Type[Warning]] = set()
