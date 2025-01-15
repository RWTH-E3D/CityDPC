CALC_ROOF_VOLUME_ON_IMPORT = False


def set_roof_volume_calculation(value: bool) -> None:
    global CALC_ROOF_VOLUME_ON_IMPORT
    print("setting roof volume calculation to", value)
    CALC_ROOF_VOLUME_ON_IMPORT = value
