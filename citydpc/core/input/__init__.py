CALC_ROOF_VOLUME_ON_IMPORT = False
CHECK_IF_SURFACES_ARE_PLANAR = True
FIX_GROUNDSURFACE_OUTLIERS = False


def set_roof_volume_calculation(value: bool) -> None:
    global CALC_ROOF_VOLUME_ON_IMPORT
    print("setting roof volume calculation to", value)
    CALC_ROOF_VOLUME_ON_IMPORT = value


def set_check_if_surfaces_are_planar(value: bool) -> None:
    global CHECK_IF_SURFACES_ARE_PLANAR
    print("setting check if surfaces are planar to", value)
    CHECK_IF_SURFACES_ARE_PLANAR = value


def set_fix_groundsurface_outliers(value: bool) -> None:
    global FIX_GROUNDSURFACE_OUTLIERS
    print("setting fix ground surface outliers to", value)
    FIX_GROUNDSURFACE_OUTLIERS = value
