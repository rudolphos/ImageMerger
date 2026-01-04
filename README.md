# ImageMerger
GUI tool to merge images or create grids from hundreds of files using ImageMagick.

# Dependencies

- ImageMagick must be installed and in your System PATH.
- Python installation on Windows.
	- Package dependencies: `pip install pillow tkinterdnd2`

# Features
- Mass Merging: Combine hundreds of images into a single file.
- Layouts:
	- Horizontal/Vertical: Simple side-by-side or top-to-bottom stitching.
	- Grid: Uniform rows and columns with optional cropping/scaling.
	- Ashlar: Smart layout for packing various image sizes into one canvas.
- Drag-and-Drop: Directly drop files into the application.
- Live Preview: Scaled preview updates as you change settings.
- Format control: Supports JPG, PNG, WEBP, and GIF with adjustable quality.
- Timestamp sync: Output files inherit the timestamp of the source images.

# Screenshots
Vertical merge
<img width="900" height="680" alt="image" src="https://github.com/user-attachments/assets/db474485-e3b4-4829-b64f-5b0990121951" />

Grid mode
<img width="900" height="680" alt="image" src="https://github.com/user-attachments/assets/f50ab484-f8bf-4411-83fa-7a1979538de8" />
