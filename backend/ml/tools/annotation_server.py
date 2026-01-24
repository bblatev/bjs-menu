#!/usr/bin/env python3
"""
Simple Annotation Server for YOLO Training Data

Provides a web interface to annotate bounding boxes for bar item detection.
Generates YOLO format annotations.

Usage:
    python -m ml.tools.annotation_server --images data/yolo_training_prep --output data/annotations

Then open http://localhost:8080 in your browser.
"""

import argparse
import json
import logging
import os
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from typing import Dict, List
from urllib.parse import parse_qs, urlparse
import base64

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

# Class definitions
CLASSES = {
    0: "bottle",
    1: "glass",
    2: "cup",
    3: "can",
}

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>YOLO Annotation Tool</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #1a1a2e; color: #eee; }}
        h1 {{ color: #00d4ff; }}
        .container {{ display: flex; gap: 20px; }}
        .image-panel {{ flex: 2; }}
        .control-panel {{ flex: 1; background: #16213e; padding: 20px; border-radius: 8px; }}
        #canvas {{ border: 2px solid #00d4ff; cursor: crosshair; max-width: 100%; }}
        .btn {{ background: #00d4ff; color: #1a1a2e; border: none; padding: 10px 20px;
               margin: 5px; cursor: pointer; border-radius: 4px; font-weight: bold; }}
        .btn:hover {{ background: #00b4d8; }}
        .btn-danger {{ background: #e63946; color: white; }}
        .btn-success {{ background: #2a9d8f; color: white; }}
        select {{ padding: 10px; margin: 5px; width: 100%; background: #0f3460; color: #eee; border: 1px solid #00d4ff; }}
        .annotation {{ background: #0f3460; padding: 10px; margin: 5px 0; border-radius: 4px; }}
        .progress {{ color: #00d4ff; margin: 20px 0; }}
        .shortcuts {{ font-size: 12px; color: #888; margin-top: 20px; }}
        .file-list {{ max-height: 200px; overflow-y: auto; background: #0f3460; padding: 10px; border-radius: 4px; }}
        .file-item {{ padding: 5px; cursor: pointer; }}
        .file-item:hover {{ background: #16213e; }}
        .file-item.current {{ background: #00d4ff; color: #1a1a2e; }}
        .file-item.done {{ color: #2a9d8f; }}
    </style>
</head>
<body>
    <h1>YOLO Annotation Tool</h1>
    <div class="progress">
        Image <span id="currentIdx">1</span> of <span id="totalImages">{total_images}</span>
        | Annotated: <span id="annotatedCount">0</span>
    </div>

    <div class="container">
        <div class="image-panel">
            <canvas id="canvas"></canvas>
        </div>

        <div class="control-panel">
            <h3>Current Class</h3>
            <select id="classSelect">
                <option value="0">bottle</option>
                <option value="1">glass</option>
                <option value="2">cup</option>
                <option value="3">can</option>
            </select>

            <h3>Annotations</h3>
            <div id="annotationList"></div>

            <h3>Actions</h3>
            <button class="btn btn-success" onclick="saveAnnotations()">Save (S)</button>
            <button class="btn" onclick="prevImage()">Previous (A)</button>
            <button class="btn" onclick="nextImage()">Next (D)</button>
            <button class="btn btn-danger" onclick="clearAnnotations()">Clear All (C)</button>
            <button class="btn" onclick="undoLast()">Undo (Z)</button>

            <h3>Files</h3>
            <div class="file-list" id="fileList"></div>

            <div class="shortcuts">
                <h4>Keyboard Shortcuts</h4>
                <p>S - Save | A - Previous | D - Next</p>
                <p>C - Clear | Z - Undo | 1-4 - Select class</p>
                <p>Click and drag to draw bounding box</p>
            </div>
        </div>
    </div>

    <script>
        const images = {images_json};
        let currentIdx = 0;
        let annotations = {{}};
        let currentBox = null;
        let isDrawing = false;
        let startX, startY;

        const canvas = document.getElementById('canvas');
        const ctx = canvas.getContext('2d');
        let img = new Image();

        // Colors for each class
        const colors = ['#00d4ff', '#ff6b6b', '#4ecdc4', '#ffe66d'];

        function loadImage(idx) {{
            currentIdx = idx;
            img.onload = () => {{
                canvas.width = img.width;
                canvas.height = img.height;
                redraw();
                document.getElementById('currentIdx').textContent = idx + 1;
                updateFileList();
            }};
            img.src = '/image/' + images[idx];

            // Load existing annotations
            fetch('/annotations/' + images[idx])
                .then(r => r.json())
                .then(data => {{
                    annotations[images[idx]] = data.annotations || [];
                    redraw();
                    updateAnnotationList();
                }});
        }}

        function redraw() {{
            ctx.drawImage(img, 0, 0);
            const anns = annotations[images[currentIdx]] || [];
            anns.forEach((ann, i) => {{
                const color = colors[ann.class_id];
                ctx.strokeStyle = color;
                ctx.lineWidth = 3;
                ctx.strokeRect(ann.x1, ann.y1, ann.x2 - ann.x1, ann.y2 - ann.y1);
                ctx.fillStyle = color;
                ctx.font = '14px Arial';
                ctx.fillText(Object.values({classes_json})[ann.class_id], ann.x1, ann.y1 - 5);
            }});

            if (currentBox) {{
                ctx.strokeStyle = '#fff';
                ctx.lineWidth = 2;
                ctx.setLineDash([5, 5]);
                ctx.strokeRect(currentBox.x1, currentBox.y1,
                              currentBox.x2 - currentBox.x1, currentBox.y2 - currentBox.y1);
                ctx.setLineDash([]);
            }}
        }}

        function updateAnnotationList() {{
            const list = document.getElementById('annotationList');
            const anns = annotations[images[currentIdx]] || [];
            list.innerHTML = anns.map((ann, i) => `
                <div class="annotation">
                    ${{Object.values({classes_json})[ann.class_id]}}
                    <button class="btn btn-danger" onclick="deleteAnnotation(${{i}})" style="float:right;padding:2px 8px;">X</button>
                </div>
            `).join('');
        }}

        function updateFileList() {{
            const list = document.getElementById('fileList');
            list.innerHTML = images.map((f, i) => {{
                const hasAnns = (annotations[f] || []).length > 0;
                const isCurrent = i === currentIdx;
                return `<div class="file-item ${{isCurrent ? 'current' : ''}} ${{hasAnns ? 'done' : ''}}"
                            onclick="loadImage(${{i}})">${{f}}</div>`;
            }}).join('');

            // Update annotated count
            let count = 0;
            images.forEach(f => {{ if ((annotations[f] || []).length > 0) count++; }});
            document.getElementById('annotatedCount').textContent = count;
        }}

        canvas.addEventListener('mousedown', (e) => {{
            const rect = canvas.getBoundingClientRect();
            const scaleX = canvas.width / rect.width;
            const scaleY = canvas.height / rect.height;
            startX = (e.clientX - rect.left) * scaleX;
            startY = (e.clientY - rect.top) * scaleY;
            isDrawing = true;
        }});

        canvas.addEventListener('mousemove', (e) => {{
            if (!isDrawing) return;
            const rect = canvas.getBoundingClientRect();
            const scaleX = canvas.width / rect.width;
            const scaleY = canvas.height / rect.height;
            const x = (e.clientX - rect.left) * scaleX;
            const y = (e.clientY - rect.top) * scaleY;
            currentBox = {{
                x1: Math.min(startX, x),
                y1: Math.min(startY, y),
                x2: Math.max(startX, x),
                y2: Math.max(startY, y)
            }};
            redraw();
        }});

        canvas.addEventListener('mouseup', () => {{
            if (currentBox && (currentBox.x2 - currentBox.x1 > 10) && (currentBox.y2 - currentBox.y1 > 10)) {{
                if (!annotations[images[currentIdx]]) annotations[images[currentIdx]] = [];
                annotations[images[currentIdx]].push({{
                    ...currentBox,
                    class_id: parseInt(document.getElementById('classSelect').value)
                }});
                updateAnnotationList();
                updateFileList();
            }}
            currentBox = null;
            isDrawing = false;
            redraw();
        }});

        function deleteAnnotation(idx) {{
            annotations[images[currentIdx]].splice(idx, 1);
            redraw();
            updateAnnotationList();
            updateFileList();
        }}

        function clearAnnotations() {{
            annotations[images[currentIdx]] = [];
            redraw();
            updateAnnotationList();
            updateFileList();
        }}

        function undoLast() {{
            if (annotations[images[currentIdx]] && annotations[images[currentIdx]].length > 0) {{
                annotations[images[currentIdx]].pop();
                redraw();
                updateAnnotationList();
                updateFileList();
            }}
        }}

        function saveAnnotations() {{
            const anns = annotations[images[currentIdx]] || [];
            fetch('/save/' + images[currentIdx], {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify({{
                    annotations: anns,
                    image_width: img.width,
                    image_height: img.height
                }})
            }}).then(r => r.json()).then(data => {{
                if (data.success) {{
                    alert('Saved!');
                }}
            }});
        }}

        function nextImage() {{
            if (currentIdx < images.length - 1) loadImage(currentIdx + 1);
        }}

        function prevImage() {{
            if (currentIdx > 0) loadImage(currentIdx - 1);
        }}

        document.addEventListener('keydown', (e) => {{
            switch(e.key.toLowerCase()) {{
                case 's': saveAnnotations(); break;
                case 'a': prevImage(); break;
                case 'd': nextImage(); break;
                case 'c': clearAnnotations(); break;
                case 'z': undoLast(); break;
                case '1': document.getElementById('classSelect').value = '0'; break;
                case '2': document.getElementById('classSelect').value = '1'; break;
                case '3': document.getElementById('classSelect').value = '2'; break;
                case '4': document.getElementById('classSelect').value = '3'; break;
            }}
        }});

        // Initial load
        document.getElementById('totalImages').textContent = images.length;
        loadImage(0);
    </script>
</body>
</html>
"""


class AnnotationHandler(SimpleHTTPRequestHandler):
    """HTTP handler for annotation server."""

    images_dir: Path = None
    output_dir: Path = None
    images: List[str] = []

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/":
            self.send_html()
        elif parsed.path.startswith("/image/"):
            self.send_image(parsed.path[7:])
        elif parsed.path.startswith("/annotations/"):
            self.send_annotations(parsed.path[13:])
        else:
            self.send_error(404)

    def do_POST(self):
        parsed = urlparse(self.path)

        if parsed.path.startswith("/save/"):
            self.save_annotations(parsed.path[6:])
        else:
            self.send_error(404)

    def send_html(self):
        html = HTML_TEMPLATE.format(
            total_images=len(self.images),
            images_json=json.dumps(self.images),
            classes_json=json.dumps(CLASSES),
        )
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(html.encode())

    def send_image(self, filename):
        img_path = self.images_dir / filename
        if not img_path.exists():
            self.send_error(404)
            return

        self.send_response(200)
        self.send_header("Content-type", "image/jpeg")
        self.end_headers()
        with open(img_path, "rb") as f:
            self.wfile.write(f.read())

    def send_annotations(self, filename):
        ann_path = self.output_dir / (Path(filename).stem + ".json")
        annotations = []

        if ann_path.exists():
            with open(ann_path) as f:
                data = json.load(f)
                annotations = data.get("annotations", [])

        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"annotations": annotations}).encode())

    def save_annotations(self, filename):
        content_length = int(self.headers["Content-Length"])
        post_data = self.rfile.read(content_length)
        data = json.loads(post_data.decode())

        annotations = data.get("annotations", [])
        img_width = data.get("image_width", 1)
        img_height = data.get("image_height", 1)

        # Save as JSON
        json_path = self.output_dir / (Path(filename).stem + ".json")
        with open(json_path, "w") as f:
            json.dump(data, f, indent=2)

        # Save as YOLO format
        yolo_path = self.output_dir / (Path(filename).stem + ".txt")
        with open(yolo_path, "w") as f:
            for ann in annotations:
                x1, y1, x2, y2 = ann["x1"], ann["y1"], ann["x2"], ann["y2"]
                # Convert to YOLO format (normalized center x, y, width, height)
                cx = (x1 + x2) / 2 / img_width
                cy = (y1 + y2) / 2 / img_height
                w = (x2 - x1) / img_width
                h = (y2 - y1) / img_height
                f.write(f"{ann['class_id']} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}\n")

        logger.info(f"Saved {len(annotations)} annotations for {filename}")

        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"success": True}).encode())

    def log_message(self, format, *args):
        pass  # Suppress default logging


def run_server(images_dir: Path, output_dir: Path, port: int = 8080):
    """Run the annotation server."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # Find images
    images = []
    for ext in [".jpg", ".jpeg", ".png"]:
        images.extend([f.name for f in images_dir.glob(f"*{ext}")])
        images.extend([f.name for f in images_dir.glob(f"*{ext.upper()}")])

    if not images:
        logger.error(f"No images found in {images_dir}")
        return

    images = sorted(set(images))
    logger.info(f"Found {len(images)} images")

    # Set up handler
    AnnotationHandler.images_dir = images_dir
    AnnotationHandler.output_dir = output_dir
    AnnotationHandler.images = images

    # Start server
    server = HTTPServer(("localhost", port), AnnotationHandler)
    logger.info(f"Annotation server running at http://localhost:{port}")
    logger.info(f"Images: {images_dir}")
    logger.info(f"Output: {output_dir}")
    logger.info("Press Ctrl+C to stop")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("\nShutting down...")
        server.shutdown()


def main():
    parser = argparse.ArgumentParser(description="YOLO Annotation Server")
    parser.add_argument(
        "--images",
        type=str,
        default="data/yolo_training_prep",
        help="Directory with images to annotate",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="data/annotations",
        help="Output directory for annotations",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Server port",
    )

    args = parser.parse_args()
    run_server(Path(args.images), Path(args.output), args.port)


if __name__ == "__main__":
    main()
