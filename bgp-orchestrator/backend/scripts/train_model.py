#!/usr/bin/env python3
"""
Manual model training script for BGP flap predictor.
"""
import argparse
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ml.bgp_flap_predictor import BGPFlapPredictor


def main():
    parser = argparse.ArgumentParser(description="Train BGP flap prediction model")
    parser.add_argument(
        "--n-samples",
        type=int,
        default=10000,
        help="Number of training samples (default: 10000)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="./models",
        help="Output directory for trained models (default: ./models)",
    )
    parser.add_argument(
        "--use-synthetic",
        action="store_true",
        default=True,
        help="Use synthetic data for training (default: True)",
    )

    args = parser.parse_args()

    print("Training BGP Flap Predictor model...")
    print(f"  Samples: {args.n_samples}")
    print(f"  Output directory: {args.output_dir}")
    print(f"  Use synthetic data: {args.use_synthetic}")

    # Create output directory
    Path(args.output_dir).mkdir(parents=True, exist_ok=True)

    # Initialize predictor
    predictor = BGPFlapPredictor(model_dir=args.output_dir)

    # Train model
    try:
        if args.use_synthetic:
            metrics = predictor.train(use_synthetic=True, n_samples=args.n_samples)
        else:
            print("Real data training not implemented yet. Use --use-synthetic flag.")
            sys.exit(1)

        print("\nModel training completed successfully.")
        print(f"  Accuracy: {metrics.get('accuracy', 'N/A'):.4f}")
        print(f"  Precision: {metrics.get('precision', 'N/A'):.4f}")
        print(f"  Recall: {metrics.get('recall', 'N/A'):.4f}")
        print(f"  F1 Score: {metrics.get('f1_score', 'N/A'):.4f}")
        print(f"\nModel saved to: {args.output_dir}")

    except Exception as e:
        print(f"\nTraining failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

