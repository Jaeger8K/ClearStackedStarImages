from PIL import Image, ExifTags


from PIL import Image, ExifTags

def get_image_properties(img_path):
    """
    Extract extensive image properties from an image file.

    Returns dict with:
    Width, Height, Format, Exposure, ISO, Device, F-stop, Flash,
    Focal Length, White Balance, Metering Mode, Exposure Program,
    DateTimeOriginal, GPSInfo, and more if available.
    """
    props = {}

    # Mapping EXIF tag names for quick access
    TAGS = ExifTags.TAGS

    try:
        with Image.open(img_path) as img:
            props["Width"], props["Height"] = img.size
            props["Format"] = img.format

            exif = img._getexif()
            if not exif:
                return props

            exif_data = {TAGS.get(k, k): v for k, v in exif.items()}

            # Exposure Time
            if "ExposureTime" in exif_data:
                exp = exif_data["ExposureTime"]
                if isinstance(exp, tuple):
                    props["Exposure"] = round(exp[0] / exp[1], 6)
                else:
                    props["Exposure"] = float(exp)

            # ISO Speed
            if "ISOSpeedRatings" in exif_data:
                props["ISO"] = exif_data["ISOSpeedRatings"]

            # Camera Model
            if "Model" in exif_data:
                props["Device"] = exif_data["Model"]

            # F-stop (Aperture)
            if "FNumber" in exif_data:
                fnum = exif_data["FNumber"]
                if isinstance(fnum, tuple):
                    props["F-stop"] = round(fnum[0] / fnum[1], 2)
                else:
                    props["F-stop"] = float(fnum)

            # Flash Fired
            if "Flash" in exif_data:
                flash_val = exif_data["Flash"]
                flash_desc = {
                    0: "Flash did not fire",
                    1: "Flash fired",
                    5: "Strobe return light not detected",
                    7: "Strobe return light detected",
                    9: "Flash fired, compulsory flash mode",
                    13: "Flash fired, compulsory flash mode, return light not detected",
                    15: "Flash fired, compulsory flash mode, return light detected",
                    16: "Flash did not fire, compulsory flash mode",
                    24: "Flash did not fire, auto mode",
                    25: "Flash fired, auto mode",
                    29: "Flash fired, auto mode, return light not detected",
                    31: "Flash fired, auto mode, return light detected",
                    32: "No flash function",
                    65: "Flash fired, red-eye reduction mode",
                    69: "Flash fired, red-eye reduction mode, return light not detected",
                    71: "Flash fired, red-eye reduction mode, return light detected",
                    73: "Flash fired, compulsory flash mode, red-eye reduction mode",
                    77: "Flash fired, compulsory flash mode, red-eye reduction mode, return light not detected",
                    79: "Flash fired, compulsory flash mode, red-eye reduction mode, return light detected",
                    89: "Flash fired, auto mode, red-eye reduction mode",
                    93: "Flash fired, auto mode, return light not detected, red-eye reduction mode",
                    95: "Flash fired, auto mode, return light detected, red-eye reduction mode"
                }
                props["Flash"] = flash_desc.get(flash_val, f"Unknown ({flash_val})")

            # Focal Length (in mm)
            if "FocalLength" in exif_data:
                fl = exif_data["FocalLength"]
                if isinstance(fl, tuple):
                    props["Focal Length"] = round(fl[0] / fl[1], 2)
                else:
                    props["Focal Length"] = float(fl)

            # White Balance
            if "WhiteBalance" in exif_data:
                wb = exif_data["WhiteBalance"]
                wb_desc = {0: "Auto", 1: "Manual"}
                props["White Balance"] = wb_desc.get(wb, f"Unknown ({wb})")

            # Metering Mode
            if "MeteringMode" in exif_data:
                mm = exif_data["MeteringMode"]
                mm_desc = {
                    0: "Unknown",
                    1: "Average",
                    2: "Center-weighted average",
                    3: "Spot",
                    4: "Multi-spot",
                    5: "Pattern",
                    6: "Partial",
                    255: "Other"
                }
                props["Metering Mode"] = mm_desc.get(mm, f"Unknown ({mm})")

            # Exposure Program
            if "ExposureProgram" in exif_data:
                ep = exif_data["ExposureProgram"]
                ep_desc = {
                    0: "Not defined",
                    1: "Manual",
                    2: "Normal program",
                    3: "Aperture priority",
                    4: "Shutter priority",
                    5: "Creative program",
                    6: "Action program",
                    7: "Portrait mode",
                    8: "Landscape mode"
                }
                props["Exposure Program"] = ep_desc.get(ep, f"Unknown ({ep})")

            # Date and time original
            if "DateTimeOriginal" in exif_data:
                props["Date Taken"] = exif_data["DateTimeOriginal"]

            # GPS Info (if any)
            if "GPSInfo" in exif_data:
                gps_info = exif_data["GPSInfo"]
                # Decode GPS tags into human-readable form
                gps_tags = {}
                for key in gps_info.keys():
                    name = ExifTags.GPSTAGS.get(key, key)
                    gps_tags[name] = gps_info[key]
                props["GPSInfo"] = gps_tags

    except Exception:
        pass

    return props
