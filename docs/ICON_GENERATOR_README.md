# High-Resolution Icon Generator

This script automatically generates all necessary icon files from a single PNG source image for creating high-resolution icons across different platforms.

## Prerequisites

- **ImageMagick**: Required for image processing

  ```bash
  brew install imagemagick
  ```

- **macOS**: For `.icns` generation (uses built-in `iconutil`)

## Usage

```bash
./generate_icon.sh <input_png_file> [output_name]
```

### Examples

```bash
# Basic usage
./generate_icon.sh my-app-logo.png

# With custom output name
./generate_icon.sh my-app-logo.png MyApp
```

## What It Generates

The script creates a `generated_icons/` directory containing:

### 1. Complete macOS Iconset

- `[name].iconset/` - Properly structured iconset with all required sizes:
  - `icon_16x16.png` (16×16)
  - `icon_16x16@2x.png` (32×32)
  - `icon_32x32.png` (32×32)
  - `icon_32x32@2x.png` (64×64)
  - `icon_128x128.png` (128×128)
  - `icon_128x128@2x.png` (256×256)
  - `icon_256x256.png` (256×256)
  - `icon_256x256@2x.png` (512×512)
  - `icon_512x512.png` (512×512)
  - `icon_512x512@2x.png` (1024×1024)

### 2. Platform-Specific Files

- `[name].icns` - macOS icon file (ready for app bundles)
- `[name].ico` - Windows icon file (multi-size)

### 3. Individual PNG Files

- `png_files/` directory with common sizes:
  - 16×16, 32×32, 48×48, 64×64, 128×128, 256×256, 512×512, 1024×1024

## Features

✅ **Smart Cropping**: Automatically crops non-square images to square using center gravity

✅ **Quality Preservation**: Uses high-quality ImageMagick processing

✅ **Complete Coverage**: Generates all sizes needed for modern high-DPI displays

✅ **Cross-Platform**: Creates icons for macOS, Windows, and web use

✅ **Verification**: Checks and reports the actual dimensions of generated files

✅ **Error Handling**: Validates input and dependencies before processing

## Integration with PyInstaller

After generating your icons:

1. Copy the `.icns` file to your `assets/` directory
2. Update your PyInstaller spec file:
   ```python
   app = BUNDLE(
       coll,
       name='YourApp.app',
       icon='assets/your-icon.icns',  # Update this path
       bundle_identifier='com.yourcompany.yourapp',
       # ... other settings
   )
   ```
3. Rebuild your app bundle:
   ```bash
   make package
   ```

## Troubleshooting

### ImageMagick Not Found

```bash
brew install imagemagick
```

### Permission Denied

```bash
chmod +x generate_icon.sh
```

### Non-Square Input Images

The script automatically handles non-square images by cropping them to square dimensions using center gravity. For best results, use a square source image.

## Tips for Best Results

1. **Use High-Resolution Source**: Start with at least 1024×1024 pixels
2. **Square Aspect Ratio**: Use square images for best results
3. **Simple Designs**: Icons work best with simple, clear designs
4. **Test at Small Sizes**: Ensure your icon is readable at 16×16 pixels
5. **Avoid Text**: Text often becomes unreadable at small sizes

## Output Structure

```
generated_icons/
├── [name].iconset/          # macOS iconset directory
│   ├── icon_16x16.png
│   ├── icon_16x16@2x.png
│   └── ... (all required sizes)
├── [name].icns              # macOS icon file
├── [name].ico               # Windows icon file
└── png_files/               # Individual PNG files
    ├── [name]-16.png
    ├── [name]-32.png
    └── ... (common sizes)
```

This structure provides everything you need for professional app icon deployment across all platforms!
