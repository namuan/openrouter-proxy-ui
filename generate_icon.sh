#!/bin/bash

# High-Resolution Icon Generator Script
# Usage: ./generate_icon.sh <input_png_file> [output_name]
# Example: ./generate_icon.sh my-app-icon.png my-app

set -e  # Exit on any error

# Check if ImageMagick is installed
if ! command -v magick &> /dev/null; then
    echo "Error: ImageMagick is not installed. Please install it first:"
    echo "  brew install imagemagick"
    exit 1
fi

# Check if iconutil is available (macOS only)
if ! command -v iconutil &> /dev/null; then
    echo "Warning: iconutil not found. This script is designed for macOS."
fi

# Parse command line arguments
if [ $# -lt 1 ]; then
    echo "Usage: $0 <input_png_file> [output_name]"
    echo "Example: $0 my-app-icon.png my-app"
    exit 1
fi

INPUT_FILE="$1"
OUTPUT_NAME="${2:-icon}"

# Check if input file exists
if [ ! -f "$INPUT_FILE" ]; then
    echo "Error: Input file '$INPUT_FILE' not found."
    exit 1
fi

echo "🎨 Generating high-resolution icons from: $INPUT_FILE"
echo "📦 Output name: $OUTPUT_NAME"

# Create output directories
ICONSET_DIR="${OUTPUT_NAME}.iconset"
OUTPUT_DIR="generated_icons"

mkdir -p "$OUTPUT_DIR"
rm -rf "$OUTPUT_DIR/$ICONSET_DIR"
mkdir -p "$OUTPUT_DIR/$ICONSET_DIR"

echo "📁 Created iconset directory: $OUTPUT_DIR/$ICONSET_DIR"

# Get image dimensions to check if it's square
DIMENSIONS=$(magick identify -format "%wx%h" "$INPUT_FILE")
WIDTH=$(echo $DIMENSIONS | cut -d'x' -f1)
HEIGHT=$(echo $DIMENSIONS | cut -d'x' -f2)

echo "📏 Input image dimensions: ${WIDTH}x${HEIGHT}"

# Prepare the base command for cropping if needed
if [ "$WIDTH" != "$HEIGHT" ]; then
    echo "⚠️  Input image is not square. Will crop to square using center gravity."
    MIN_DIM=$(( WIDTH < HEIGHT ? WIDTH : HEIGHT ))
    CROP_CMD="-gravity center -crop ${MIN_DIM}x${MIN_DIM}+0+0 +repage"
    echo "✂️  Cropping to: ${MIN_DIM}x${MIN_DIM}"
else
    echo "✅ Input image is already square."
    CROP_CMD=""
fi

# Define all required icon sizes for macOS
declare -a SIZES=(
    "16:icon_16x16.png"
    "32:icon_16x16@2x.png"
    "32:icon_32x32.png"
    "64:icon_32x32@2x.png"
    "128:icon_128x128.png"
    "256:icon_128x128@2x.png"
    "256:icon_256x256.png"
    "512:icon_256x256@2x.png"
    "512:icon_512x512.png"
    "1024:icon_512x512@2x.png"
)

echo "🔄 Generating icon sizes..."

# Generate all icon sizes
for size_info in "${SIZES[@]}"; do
    SIZE=$(echo $size_info | cut -d':' -f1)
    FILENAME=$(echo $size_info | cut -d':' -f2)
    OUTPUT_PATH="$OUTPUT_DIR/$ICONSET_DIR/$FILENAME"

    echo "  📐 Creating ${SIZE}x${SIZE}: $FILENAME"

    if [ -n "$CROP_CMD" ]; then
        magick "$INPUT_FILE" $CROP_CMD -resize "${SIZE}x${SIZE}" "$OUTPUT_PATH"
    else
        magick "$INPUT_FILE" -resize "${SIZE}x${SIZE}" "$OUTPUT_PATH"
    fi
done

echo "✅ All icon sizes generated successfully!"

# Verify all files were created
echo "🔍 Verifying generated files..."
for size_info in "${SIZES[@]}"; do
    FILENAME=$(echo $size_info | cut -d':' -f2)
    OUTPUT_PATH="$OUTPUT_DIR/$ICONSET_DIR/$FILENAME"

    if [ -f "$OUTPUT_PATH" ]; then
        ACTUAL_SIZE=$(magick identify -format "%wx%h" "$OUTPUT_PATH")
        echo "  ✅ $FILENAME: $ACTUAL_SIZE"
    else
        echo "  ❌ $FILENAME: MISSING"
    fi
done

# Generate .icns file (macOS)
if command -v iconutil &> /dev/null; then
    echo "🍎 Generating macOS .icns file..."
    ICNS_OUTPUT="$OUTPUT_DIR/${OUTPUT_NAME}.icns"
    iconutil -c icns "$OUTPUT_DIR/$ICONSET_DIR" --output "$ICNS_OUTPUT"
    echo "✅ Created: $ICNS_OUTPUT"
else
    echo "⚠️  Skipping .icns generation (iconutil not available)"
fi

# Generate .ico file for Windows (if needed)
echo "🪟 Generating Windows .ico file..."
ICO_OUTPUT="$OUTPUT_DIR/${OUTPUT_NAME}.ico"
# Create ico with multiple sizes
magick "$OUTPUT_DIR/$ICONSET_DIR/icon_16x16.png" \
       "$OUTPUT_DIR/$ICONSET_DIR/icon_32x32.png" \
       "$OUTPUT_DIR/$ICONSET_DIR/icon_128x128.png" \
       "$OUTPUT_DIR/$ICONSET_DIR/icon_256x256.png" \
       "$ICO_OUTPUT"
echo "✅ Created: $ICO_OUTPUT"

# Create individual PNG files for web/other uses
echo "🌐 Creating individual PNG files..."
PNG_DIR="$OUTPUT_DIR/png_files"
mkdir -p "$PNG_DIR"

declare -a COMMON_SIZES=("16" "32" "48" "64" "128" "256" "512" "1024")

for size in "${COMMON_SIZES[@]}"; do
    PNG_OUTPUT="$PNG_DIR/${OUTPUT_NAME}-${size}.png"
    if [ -n "$CROP_CMD" ]; then
        magick "$INPUT_FILE" $CROP_CMD -resize "${size}x${size}" "$PNG_OUTPUT"
    else
        magick "$INPUT_FILE" -resize "${size}x${size}" "$PNG_OUTPUT"
    fi
    echo "  📐 Created: ${OUTPUT_NAME}-${size}.png"
done

# Generate summary
echo ""
echo "🎉 Icon generation complete!"
echo "📂 Output directory: $OUTPUT_DIR/"
echo ""
echo "Generated files:"
echo "  📁 $ICONSET_DIR/ - Complete iconset for macOS"
if [ -f "$OUTPUT_DIR/${OUTPUT_NAME}.icns" ]; then
    echo "  🍎 ${OUTPUT_NAME}.icns - macOS icon file"
fi
echo "  🪟 ${OUTPUT_NAME}.ico - Windows icon file"
echo "  📁 png_files/ - Individual PNG files for web/other uses"
echo ""
echo "To use in your app:"
echo "  • Copy ${OUTPUT_NAME}.icns to your assets folder"
echo "  • Update your PyInstaller spec file to reference the new icon"
echo "  • Rebuild your app bundle"
echo ""
echo "File sizes:"
du -sh "$OUTPUT_DIR"/*

mv $OUTPUT_DIR/*.icns assets/
mv $OUTPUT_DIR/*.ico assets/

rm -rf $OUTPUT_DIR

echo ""
echo "✨ Done! Your high-resolution icons are ready to use."
