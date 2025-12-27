import exifread  # Make sure this is imported at the top
from pathlib import Path

def get_image_properties(img_path):
    """
    Extract extensive image properties from an image file.
    Works with both standard images and DNG files.
    """
    props = {}
    img_path = Path(img_path)
    
    try:
        with open(img_path, 'rb') as f:
            tags = exifread.process_file(f, details=False)
            
            # For DNG files, check Image tags first, then EXIF tags
            if img_path.suffix.lower() == '.dng':
                # DNG stores most data in Image tags
                prefix = 'Image '
            else:
                # Standard images use EXIF tags
                prefix = 'EXIF '
            
            # Dimensions (DNG uses Image ImageWidth/ImageLength)
            if 'Image ImageWidth' in tags:
                props['Width'] = int(str(tags['Image ImageWidth']))
            if 'Image ImageLength' in tags:
                props['Height'] = int(str(tags['Image ImageLength']))
            
            # Camera info
            if 'Image Make' in tags:
                props['Make'] = str(tags['Image Make']).strip()
            if 'Image Model' in tags:
                props['Device'] = str(tags['Image Model']).strip()
            
            # Try multiple possible tag names for exposure settings
            exposure_tags = ['Image ExposureTime', 'EXIF ExposureTime']
            for tag in exposure_tags:
                if tag in tags:
                    exp = str(tags[tag])
                    props['Exposure'] = exp + 's' if not exp.endswith('s') else exp
                    break
            
            # Aperture (F-number)
            fnumber_tags = ['Image FNumber', 'EXIF FNumber']
            for tag in fnumber_tags:
                if tag in tags:
                    fnum = str(tags[tag])
                    if '/' in fnum:
                        try:
                            num, den = fnum.split('/')
                            props['Aperture'] = f"f/{float(num)/float(den):.1f}"
                        except:
                            props['Aperture'] = f"f/{fnum}"
                    else:
                        props['Aperture'] = f"f/{fnum}"
                    break
            
            # ISO
            iso_tags = ['Image ISOSpeedRatings', 'EXIF ISOSpeedRatings']
            for tag in iso_tags:
                if tag in tags:
                    props['ISO'] = str(tags[tag])
                    break
            
            # Focal length
            focal_tags = ['Image FocalLength', 'EXIF FocalLength']
            for tag in focal_tags:
                if tag in tags:
                    fl = str(tags[tag])
                    if '/' in fl:
                        try:
                            num, den = fl.split('/')
                            props['Focal Length'] = f"{float(num)/float(den):.1f}mm"
                        except:
                            props['Focal Length'] = f"{fl}mm"
                    else:
                        props['Focal Length'] = f"{fl}mm"
                    break
            
            # Date/Time
            date_tags = ['Image DateTimeOriginal', 'EXIF DateTimeOriginal', 'Image DateTime']
            for tag in date_tags:
                if tag in tags:
                    props['Date Taken'] = str(tags[tag])
                    break
            
            # Orientation
            if 'Image Orientation' in tags:
                orient = str(tags['Image Orientation'])
                orientation_map = {
                    'Horizontal (normal)': 'Normal',
                    'Rotated 90 CW': '90° Clockwise',
                    'Rotated 180': '180°',
                    'Rotated 90 CCW': '90° Counter-Clockwise'
                }
                props['Orientation'] = orientation_map.get(orient, orient)
            
            # Additional DNG-specific properties from your debug output
            if img_path.suffix.lower() == '.dng':
                props['Format'] = 'DNG'
                props['Is RAW'] = True
                
                # Bits per sample
                if 'Image BitsPerSample' in tags:
                    props['Bits Per Sample'] = str(tags['Image BitsPerSample'])
                
                # Black level
                if 'Image BlackLevel' in tags:
                    props['Black Level'] = str(tags['Image BlackLevel'])
                
                # CFA Pattern
                if 'Image CFAPattern' in tags:
                    cfa = str(tags['Image CFAPattern'])
                    cfa_map = {'[1, 0, 2, 1]': 'RGGB', '[0, 1, 1, 2]': 'GRBG', 
                              '[2, 1, 1, 0]': 'BGGR', '[1, 2, 0, 1]': 'GBRG'}
                    props['Bayer Pattern'] = cfa_map.get(cfa, cfa)
                
                # Compression
                if 'Image Compression' in tags:
                    props['Compression'] = str(tags['Image Compression'])
                
                # Software
                if 'Image Software' in tags:
                    props['Software'] = str(tags['Image Software'])
                
                # Image Description
                if 'Image ImageDescription' in tags:
                    desc = str(tags['Image ImageDescription']).strip()
                    if desc:
                        props['Description'] = desc
                
                # Copyright
                if 'Image Copyright' in tags:
                    copyright_text = str(tags['Image Copyright']).strip()
                    if copyright_text:
                        props['Copyright'] = copyright_text
                
                # Resolution
                if 'Image XResolution' in tags and 'Image YResolution' in tags:
                    x_res = str(tags['Image XResolution'])
                    y_res = str(tags['Image YResolution'])
                    props['Resolution'] = f"{x_res} x {y_res} DPI"
            
            else:
                # For non-DNG files
                props['Format'] = img_path.suffix.upper().replace('.', '')
                props['Is RAW'] = False
            
            # File info
            props['Filename'] = img_path.name
            props['File Size'] = f"{img_path.stat().st_size / 1024 / 1024:.2f} MB"
            
    except Exception as e:
        print(f"Error reading {img_path}: {e}")
        import traceback
        traceback.print_exc()
    
    return props


def get_detailed_dng_properties(img_path):
    """
    Get very detailed DNG properties including camera-specific tags
    """
    props = {}
    img_path = Path(img_path)
    
    try:
        with open(img_path, 'rb') as f:
            tags = exifread.process_file(f, details=False)
            
            # Basic properties
            basic_props = get_image_properties(img_path)
            props.update(basic_props)
            
            # Add all DNG-specific tags (0xC6xx series)
            dng_tags = {}
            for tag_name in tags.keys():
                if 'Tag 0x' in tag_name:
                    dng_tags[tag_name] = str(tags[tag_name])
            
            if dng_tags:
                props['DNG Specific Tags'] = dng_tags
            
            # Add all other tags for debugging
            all_tags = {}
            for tag_name in sorted(tags.keys()):
                # Skip very long values
                value_str = str(tags[tag_name])
                if len(value_str) < 200:
                    all_tags[tag_name] = value_str
            
            props['All Tags'] = all_tags
            
    except Exception as e:
        print(f"Error in detailed read: {e}")
    
    return props
