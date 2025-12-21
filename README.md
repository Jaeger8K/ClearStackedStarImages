Image Processing Workflow (Phone Astrophotography)

This project documents my workflow for processing and enhancing star images captured with a smartphone. The pipeline combines stacking, custom Python-based enhancement, and final export using open-source tools.

1. Image Capture (Input)

Images are captured using a smartphone mounted on a tripod.

Multiple exposures of the night sky are taken to improve signal-to-noise ratio.

The individual frames are later stacked to create a single high-quality image.

2. Stacking with DeepSkyStacker

I use DeepSkyStacker (DSS) to align and stack the individual phone images.

DSS handles:

Star alignment

Noise reduction through stacking

Output in a high bit-depth format

The stacked result is saved as a 16-bit Autosave.tif file.

Output:

Autosave.tif

3. Star Enhancement Pipeline (Python Script)

The stacked Autosave.tif is processed using the provided Python script (combined.py).

The script performs a full star-field enhancement pipeline, including:

Background modeling using overlapping tiles with smooth blending

Star detection using high-pass filtering on the luminance channel

Creation of a soft, shared star mask to preserve star shapes

Separation of stars and background (starless image)

Adaptive enhancement that boosts dim stars more than bright ones

Asinh (arcsinh) stretching for astrophotography-friendly contrast

Mild sharpening for clarity without harsh artifacts

The script preserves color balance for RGB images and supports grayscale inputs.

How it’s run:

python combined.py


You will be prompted to enter the folder containing Autosave.tif.

Output:

final_star_enhanced_rgb16.tif


This output is a 16-bit linear RGB TIFF, suitable for further manual editing.

4. Final Export with GIMP 3

The enhanced 16-bit TIFF is opened in GIMP 3.

Final adjustments may include:

Minor curves or levels tweaks

Color balance refinement

Cropping or rotation

The final image is exported as a JPEG for sharing or publishing.

Final Output:

final_image.jpg

Summary

Pipeline overview:

Capture star images on a phone

Stack images in DeepSkyStacker → Autosave.tif

Enhance stars with custom Python script → final_star_enhanced_rgb16.tif

Export final JPEG using GIMP 3

This workflow prioritizes preserving natural star shapes, boosting faint stars, and maintaining color accuracy while working entirely with open-source tools.
