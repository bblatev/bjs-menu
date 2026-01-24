#!/usr/bin/env python3
"""
Export YOLOv8 model to TFLite format for mobile deployment.

Usage:
    python scripts/export_yolo_tflite.py

This exports the YOLOv8n model to TFLite format suitable for mobile inference.
The exported model can be used with tflite_flutter in the mobile app.
"""

import sys
from pathlib import Path

def export_yolo_to_tflite():
    """Export YOLOv8 to TFLite format."""
    try:
        from ultralytics import YOLO
    except ImportError:
        print("Error: ultralytics not installed. Run: pip install ultralytics")
        sys.exit(1)

    # Use the pre-trained YOLOv8n model
    model_path = "yolov8n.pt"

    # Check if custom model exists
    custom_model = Path("models/detector/best.pt")
    if custom_model.exists():
        print(f"Using custom model: {custom_model}")
        model_path = str(custom_model)
    else:
        print(f"Using pre-trained model: {model_path}")

    # Load model
    model = YOLO(model_path)

    # Export to TFLite
    # Note: TFLite export requires specific settings for mobile compatibility
    output_dir = Path("../inventory-system/mobile/assets/models")
    output_dir.mkdir(parents=True, exist_ok=True)

    print("Exporting to TFLite format...")
    print("This may take a few minutes...")

    try:
        # Export with FP16 quantization for smaller model size
        model.export(
            format="tflite",
            imgsz=640,
            half=False,  # FP32 for better compatibility
            int8=False,
        )

        # Find the exported file
        exported_path = Path(model_path).with_suffix(".tflite")
        if not exported_path.exists():
            # Check in the model directory
            exported_path = Path(model_path).parent / f"{Path(model_path).stem}_saved_model" / f"{Path(model_path).stem}_float32.tflite"

        if exported_path.exists():
            # Copy to mobile assets
            import shutil
            dest_path = output_dir / "yolo_bar_detection.tflite"
            shutil.copy(exported_path, dest_path)
            print(f"Model exported to: {dest_path}")
            print(f"Model size: {dest_path.stat().st_size / 1024 / 1024:.2f} MB")
        else:
            print("Warning: Could not find exported TFLite file")
            print("Check the ultralytics output for the export location")

    except Exception as e:
        print(f"Export failed: {e}")
        print("\nAlternative: Download pre-exported model")
        print("Or use the ML Kit fallback in the mobile app")
        sys.exit(1)

    print("\nExport complete!")
    print("\nTo use in mobile app:")
    print("1. The model is at: mobile/assets/models/yolo_bar_detection.tflite")
    print("2. Run 'flutter pub get' to update assets")
    print("3. The app will automatically use TFLite if model is present")


if __name__ == "__main__":
    export_yolo_to_tflite()
