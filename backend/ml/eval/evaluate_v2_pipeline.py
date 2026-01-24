"""
Evaluate V2 Pipeline Performance

Measures:
- Detection recall (target >= 0.98)
- SKU Top-1 accuracy (target >= 93%)
- Classification confidence distribution

Usage:
    python -m ml.eval.evaluate_v2_pipeline --num-samples 100
"""

import argparse
import json
import logging
import random
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_test_data(num_samples: int = 100):
    """Load test images from database."""
    from sqlalchemy import create_engine, text
    from app.core.config import settings

    engine = create_engine(settings.database_url)

    with engine.connect() as conn:
        # Get all training images with their labels
        result = conn.execute(text("""
            SELECT
                ti.id,
                ti.stock_item_id,
                ti.storage_path,
                si.name as product_name,
                si.sku
            FROM training_images ti
            JOIN stock_items si ON ti.stock_item_id = si.id
            WHERE ti.feature_vector IS NOT NULL
            ORDER BY RANDOM()
            LIMIT :limit
        """), {"limit": num_samples})

        samples = []
        for row in result:
            samples.append({
                'id': row[0],
                'product_id': row[1],
                'image_path': row[2],  # storage_path
                'product_name': row[3],
                'sku': row[4],
            })

    logger.info(f"Loaded {len(samples)} test samples")
    return samples


def run_evaluation(samples: list, pipeline):
    """Run evaluation on samples."""
    import cv2

    results = {
        'total': len(samples),
        'detected': 0,
        'correctly_classified': 0,
        'top5_correct': 0,
        'confidences': [],
        'errors': [],
        'per_product': defaultdict(lambda: {'total': 0, 'correct': 0}),
    }

    for i, sample in enumerate(samples):
        if i % 10 == 0:
            logger.info(f"Processing {i+1}/{len(samples)}...")

        try:
            # Load image
            image_path = sample['image_path']
            if not Path(image_path).exists():
                # Try relative path
                image_path = Path("training_images") / Path(image_path).name
                if not image_path.exists():
                    results['errors'].append(f"Image not found: {sample['image_path']}")
                    continue

            image = cv2.imread(str(image_path))
            if image is None:
                results['errors'].append(f"Could not read: {image_path}")
                continue

            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

            # Run pipeline
            result = pipeline.process(image_rgb)

            # Track per-product stats
            product_key = f"{sample['product_id']}_{sample['sku']}"
            results['per_product'][product_key]['total'] += 1
            results['per_product'][product_key]['name'] = sample['product_name']

            # Check detection
            if result.total_items > 0:
                results['detected'] += 1

                # Check classification
                if result.items:
                    top_item = result.items[0]
                    if top_item.classification:
                        conf = top_item.classification.confidence
                        results['confidences'].append(conf)

                        # Check if correct (match product_id in sku_id)
                        predicted_sku = top_item.classification.sku_id
                        expected_key = f"{sample['product_id']}_{sample['sku']}"

                        # Match by product_id prefix or full key
                        is_correct = (
                            str(sample['product_id']) in predicted_sku or
                            expected_key == predicted_sku or
                            sample['sku'] in predicted_sku
                        )

                        if is_correct:
                            results['correctly_classified'] += 1
                            results['per_product'][product_key]['correct'] += 1

        except Exception as e:
            results['errors'].append(f"Error processing {sample['image_path']}: {e}")

    return results


def print_report(results: dict):
    """Print evaluation report."""
    total = results['total']
    detected = results['detected']
    correct = results['correctly_classified']

    detection_recall = detected / total if total > 0 else 0
    classification_acc = correct / detected if detected > 0 else 0
    overall_acc = correct / total if total > 0 else 0

    print("\n" + "=" * 60)
    print("V2 PIPELINE EVALUATION REPORT")
    print("=" * 60)

    print("\nDETECTION:")
    print(f"  Total samples:     {total}")
    print(f"  Detected:          {detected}")
    print(f"  Detection Recall:  {detection_recall:.1%} (target: >= 98%)")
    status = "✓ PASS" if detection_recall >= 0.98 else "✗ FAIL"
    print(f"  Status:            {status}")

    print("\nCLASSIFICATION:")
    print(f"  Correctly classified: {correct}/{detected}")
    print(f"  Top-1 Accuracy:       {classification_acc:.1%} (target: >= 93%)")
    status = "✓ PASS" if classification_acc >= 0.93 else "✗ FAIL"
    print(f"  Status:               {status}")

    if results['confidences']:
        confs = results['confidences']
        print("\nCONFIDENCE DISTRIBUTION:")
        print(f"  Mean:   {np.mean(confs):.1%}")
        print(f"  Median: {np.median(confs):.1%}")
        print(f"  Min:    {np.min(confs):.1%}")
        print(f"  Max:    {np.max(confs):.1%}")
        print(f"  >90%:   {sum(1 for c in confs if c > 0.9)} ({sum(1 for c in confs if c > 0.9)/len(confs):.1%})")
        print(f"  >80%:   {sum(1 for c in confs if c > 0.8)} ({sum(1 for c in confs if c > 0.8)/len(confs):.1%})")
        print(f"  >70%:   {sum(1 for c in confs if c > 0.7)} ({sum(1 for c in confs if c > 0.7)/len(confs):.1%})")

    # Per-product breakdown (top 10 worst performers)
    print("\nPER-PRODUCT ACCURACY (worst 10):")
    per_product = results['per_product']
    product_accs = []
    for key, stats in per_product.items():
        if stats['total'] > 0:
            acc = stats['correct'] / stats['total']
            product_accs.append((stats['name'], stats['correct'], stats['total'], acc))

    product_accs.sort(key=lambda x: x[3])
    for name, correct, total, acc in product_accs[:10]:
        print(f"  {name[:30]:<30} {correct:>3}/{total:<3} ({acc:.0%})")

    if results['errors']:
        print(f"\nERRORS ({len(results['errors'])}):")
        for err in results['errors'][:5]:
            print(f"  - {err[:70]}")
        if len(results['errors']) > 5:
            print(f"  ... and {len(results['errors']) - 5} more")

    print("\n" + "=" * 60)
    print("OVERALL RESULT:")
    overall_pass = detection_recall >= 0.98 and classification_acc >= 0.93
    if overall_pass:
        print("  ✓ ALL TARGETS MET")
    else:
        print("  ✗ TARGETS NOT MET")
        if detection_recall < 0.98:
            print(f"    - Detection recall {detection_recall:.1%} < 98%")
        if classification_acc < 0.93:
            print(f"    - Classification accuracy {classification_acc:.1%} < 93%")
    print("=" * 60)

    return {
        'detection_recall': detection_recall,
        'classification_accuracy': classification_acc,
        'overall_accuracy': overall_acc,
        'mean_confidence': np.mean(results['confidences']) if results['confidences'] else 0,
        'passed': overall_pass,
    }


def main():
    parser = argparse.ArgumentParser(description="Evaluate V2 pipeline")
    parser.add_argument("--num-samples", type=int, default=100, help="Number of test samples")
    parser.add_argument("--config", type=str, default="ml/configs/pipeline.yaml", help="Pipeline config")
    parser.add_argument("--output", type=str, help="Save results to JSON file")

    args = parser.parse_args()

    # Load pipeline
    from ml.inference.pipeline_v2 import PipelineV2
    logger.info(f"Loading pipeline from {args.config}")
    pipeline = PipelineV2.from_config(args.config)

    # Load test data
    samples = load_test_data(args.num_samples)

    if not samples:
        logger.error("No test samples found")
        return

    # Run evaluation
    logger.info("Running evaluation...")
    results = run_evaluation(samples, pipeline)

    # Print report
    metrics = print_report(results)

    # Save results
    if args.output:
        output_data = {
            'num_samples': len(samples),
            'metrics': metrics,
            'per_product': dict(results['per_product']),
            'errors': results['errors'],
        }
        with open(args.output, 'w') as f:
            json.dump(output_data, f, indent=2)
        logger.info(f"Results saved to {args.output}")


if __name__ == "__main__":
    main()
