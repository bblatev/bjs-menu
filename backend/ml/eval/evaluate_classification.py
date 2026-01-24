"""
Evaluate Classification Accuracy Using Stored Embeddings

Since training images may not exist on disk, this evaluates
the classification accuracy using the stored CLIP embeddings.

Usage:
    python -m ml.eval.evaluate_classification --num-samples 200
"""

import argparse
import json
import logging
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_embeddings_from_db(num_samples: int = 200):
    """Load test embeddings from database."""
    from sqlalchemy import create_engine, text
    from app.core.config import settings

    engine = create_engine(settings.database_url)

    with engine.connect() as conn:
        # Get training images with embeddings
        result = conn.execute(text("""
            SELECT
                ti.id,
                ti.stock_item_id,
                ti.feature_vector,
                si.name as product_name,
                si.sku
            FROM training_images ti
            JOIN stock_items si ON ti.stock_item_id = si.id
            WHERE ti.feature_vector IS NOT NULL
              AND length(ti.feature_vector) = 2048
            ORDER BY RANDOM()
            LIMIT :limit
        """), {"limit": num_samples})

        samples = []
        for row in result:
            # Parse embedding from bytes
            feature_bytes = row[2]
            try:
                embedding = np.frombuffer(feature_bytes, dtype=np.float32)
                if len(embedding) == 512:  # Valid CLIP embedding
                    samples.append({
                        'id': row[0],
                        'product_id': row[1],
                        'embedding': embedding,
                        'product_name': row[3],
                        'sku': row[4],
                    })
            except Exception as e:
                logger.warning(f"Failed to parse embedding: {e}")

    logger.info(f"Loaded {len(samples)} test samples with embeddings")
    return samples


def load_reference_embeddings():
    """Load reference embeddings from exported file."""
    embeddings_path = Path("models/classifier/embeddings.npy")
    mapping_path = Path("models/classifier/sku_mapping.json")

    if not embeddings_path.exists():
        logger.error(f"Embeddings file not found: {embeddings_path}")
        return None, None

    embeddings = np.load(embeddings_path, allow_pickle=True).item()

    sku_mapping = {}
    if mapping_path.exists():
        with open(mapping_path, "r") as f:
            sku_mapping = json.load(f)

    logger.info(f"Loaded reference embeddings for {len(embeddings)} products")
    return embeddings, sku_mapping


def classify_embedding(embedding: np.ndarray, reference_embeddings: dict, sku_mapping: dict):
    """Classify an embedding against reference embeddings."""
    # Normalize query embedding
    embedding = embedding / (np.linalg.norm(embedding) + 1e-7)

    # Compute similarities
    similarities = {}
    for sku_key, ref_emb in reference_embeddings.items():
        ref_emb = ref_emb / (np.linalg.norm(ref_emb) + 1e-7)
        sim = float(np.dot(embedding, ref_emb))
        similarities[sku_key] = sim

    # Sort by similarity
    sorted_results = sorted(similarities.items(), key=lambda x: x[1], reverse=True)

    if not sorted_results:
        return None, 0.0, []

    top_sku, top_conf = sorted_results[0]
    top5 = sorted_results[:5]

    # Get product name from mapping
    product_name = top_sku
    if top_sku in sku_mapping:
        info = sku_mapping[top_sku]
        if isinstance(info, dict):
            product_name = info.get('name', top_sku)

    return {
        'sku': top_sku,
        'name': product_name,
        'confidence': top_conf,
    }, top_conf, top5


def run_evaluation(samples: list, reference_embeddings: dict, sku_mapping: dict):
    """Run classification evaluation."""
    results = {
        'total': len(samples),
        'correct_top1': 0,
        'correct_top5': 0,
        'confidences': [],
        'per_product': defaultdict(lambda: {'total': 0, 'correct': 0}),
        'confusion': [],
    }

    for i, sample in enumerate(samples):
        if i % 50 == 0:
            logger.info(f"Processing {i+1}/{len(samples)}...")

        # Classify
        prediction, confidence, top5 = classify_embedding(
            sample['embedding'],
            reference_embeddings,
            sku_mapping
        )

        if prediction is None:
            continue

        results['confidences'].append(confidence)

        # Build expected key
        expected_key = f"{sample['product_id']}_{sample['sku']}"

        # Track per-product
        results['per_product'][expected_key]['total'] += 1
        results['per_product'][expected_key]['name'] = sample['product_name']

        # Check if correct (match by product_id prefix)
        predicted_sku = prediction['sku']
        is_correct = (
            str(sample['product_id']) in predicted_sku or
            expected_key == predicted_sku or
            sample['sku'] in predicted_sku
        )

        if is_correct:
            results['correct_top1'] += 1
            results['per_product'][expected_key]['correct'] += 1
        else:
            results['confusion'].append({
                'expected': sample['product_name'],
                'predicted': prediction['name'],
                'confidence': confidence,
            })

        # Check top-5
        for sku_key, _ in top5:
            if str(sample['product_id']) in sku_key or sample['sku'] in sku_key:
                results['correct_top5'] += 1
                break

    return results


def print_report(results: dict):
    """Print evaluation report."""
    total = results['total']
    correct1 = results['correct_top1']
    correct5 = results['correct_top5']

    top1_acc = correct1 / total if total > 0 else 0
    top5_acc = correct5 / total if total > 0 else 0

    print("\n" + "=" * 60)
    print("CLASSIFICATION EVALUATION REPORT")
    print("=" * 60)

    print("\nACCURACY:")
    print(f"  Total samples:     {total}")
    print(f"  Top-1 Correct:     {correct1}")
    print(f"  Top-1 Accuracy:    {top1_acc:.1%} (target: >= 93%)")
    status = "✓ PASS" if top1_acc >= 0.93 else "✗ FAIL"
    print(f"  Status:            {status}")

    print(f"\n  Top-5 Correct:     {correct5}")
    print(f"  Top-5 Accuracy:    {top5_acc:.1%}")

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
        print(f"  >60%:   {sum(1 for c in confs if c > 0.6)} ({sum(1 for c in confs if c > 0.6)/len(confs):.1%})")

    # Per-product breakdown (worst performers)
    print("\nPER-PRODUCT ACCURACY (worst 10):")
    per_product = results['per_product']
    product_accs = []
    for key, stats in per_product.items():
        if stats['total'] > 0:
            acc = stats['correct'] / stats['total']
            product_accs.append((stats['name'], stats['correct'], stats['total'], acc))

    product_accs.sort(key=lambda x: x[3])
    for name, correct, total, acc in product_accs[:10]:
        print(f"  {name[:35]:<35} {correct:>3}/{total:<3} ({acc:.0%})")

    # Common confusions
    if results['confusion']:
        print("\nCOMMON MISCLASSIFICATIONS (sample):")
        for conf in results['confusion'][:5]:
            print(f"  {conf['expected'][:25]:<25} -> {conf['predicted'][:25]:<25} ({conf['confidence']:.0%})")

    print("\n" + "=" * 60)
    print("OVERALL RESULT:")
    if top1_acc >= 0.93:
        print("  ✓ TOP-1 ACCURACY TARGET MET (>= 93%)")
    else:
        print(f"  ✗ TOP-1 ACCURACY TARGET NOT MET ({top1_acc:.1%} < 93%)")
    print("=" * 60)

    return {
        'top1_accuracy': top1_acc,
        'top5_accuracy': top5_acc,
        'mean_confidence': np.mean(results['confidences']) if results['confidences'] else 0,
        'passed': top1_acc >= 0.93,
    }


def main():
    parser = argparse.ArgumentParser(description="Evaluate classification accuracy")
    parser.add_argument("--num-samples", type=int, default=200, help="Number of test samples")
    parser.add_argument("--output", type=str, help="Save results to JSON file")

    args = parser.parse_args()

    # Load reference embeddings
    reference_embeddings, sku_mapping = load_reference_embeddings()
    if reference_embeddings is None:
        logger.error("Could not load reference embeddings")
        return

    # Load test data
    samples = load_embeddings_from_db(args.num_samples)

    if not samples:
        logger.error("No test samples found")
        return

    # Run evaluation
    logger.info("Running classification evaluation...")
    results = run_evaluation(samples, reference_embeddings, sku_mapping)

    # Print report
    metrics = print_report(results)

    # Save results
    if args.output:
        output_data = {
            'num_samples': len(samples),
            'metrics': metrics,
            'per_product': {k: dict(v) for k, v in results['per_product'].items()},
        }
        with open(args.output, 'w') as f:
            json.dump(output_data, f, indent=2)
        logger.info(f"Results saved to {args.output}")


if __name__ == "__main__":
    main()
