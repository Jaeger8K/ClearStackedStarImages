from pathlib import Path
from .image_props import get_image_properties


SUPPORTED_EXTS = [".tif", ".tiff", ".fits", ".fit", ".jpg", ".jpeg", ".png", ".dng"]


def parse_dss_processed_images(folder: Path):
    """
    Parse DSS processed frames in a folder.

    Returns:
        frame_properties: list[dict]
        zero_star_frames: int
        no_stacked_images_found: bool
    """
    frame_properties = []
    zero_star_frames = 0

    for info_file in folder.glob("*.info.txt"):
        image_file = _find_matching_image(folder, info_file)
        if not image_file:
            continue

        props = get_image_properties(image_file)
        props["Filename"] = image_file.name

        stars = _parse_star_count(info_file)
        props["Stars"] = stars

        if stars == 0:
            zero_star_frames += 1

        frame_properties.append(props)

    return frame_properties, zero_star_frames


def _find_matching_image(folder: Path, info_file: Path):
    base = info_file.stem.replace(".info", "")
    for ext in SUPPORTED_EXTS:
        candidate = folder / f"{base}{ext}"
        if candidate.exists():
            return candidate
    return None


def _parse_star_count(info_file: Path) -> int:
    try:
        with info_file.open("r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if line.startswith("NrStars"):
                    return int(line.split("=")[1].strip())
    except Exception:
        pass
    return 0
