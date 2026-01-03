# Bird Classification Model

This directory should contain your TFLite bird classification model.

## Getting a Model

### Option 1: iNaturalist Birds (Recommended for Swiss birds)

1. Download from TensorFlow Hub or Kaggle
2. Convert to TFLite if needed
3. Place as `birds_model.tflite`

### Option 2: Caltech-UCSD Birds 200

1. Download pre-trained model
2. Convert to TFLite
3. Place as `birds_model.tflite`

### Option 3: Custom Model

Train your own model on Swiss bird species:
- Great Tit (Kohlmeise)
- Blue Tit (Blaumeise)
- House Sparrow (Haussperling)
- Common Blackbird (Amsel)
- European Robin (Rotkehlchen)
- And more...

## Labels File

Create a `labels.txt` file with one species per line:
```
Great_Tit
Blue_Tit
House_Sparrow
Common_Blackbird
European_Robin
...
```

## Quick Start

For testing, you can use a generic bird detector initially and add species classification later.

## Model Requirements

- Format: TensorFlow Lite (.tflite)
- Input: RGB image (224x224 or 320x320 typical)
- Output: Classification probabilities
- Labels: Species names (scientific or common)
