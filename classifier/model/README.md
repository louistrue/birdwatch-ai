# Bird Classification Model

This directory contains the Google AIY Vision Bird Classifier model for identifying bird species.

## Quick Start

### 1. Download the Model

Run the download script to automatically fetch the model and labels:

```bash
./download_model.sh
```

This will download:
- `birds_model.tflite` - The bird classification model (~ 4MB)
- `labels.txt` - Bird species labels (~965 species)

### 2. Test the Model

Verify the model works correctly:

```bash
python3 test_model.py
```

### 3. Start Bird Watching

Once the model is downloaded and tested:

```bash
cd ../..
docker-compose up -d
```

## Model Details

### Google AIY Vision Classifier Birds V1

- **Model**: MobileNet V2 based bird classifier
- **Dataset**: iNaturalist birds (curated subset)
- **Species Count**: ~965 bird species from around the world
- **Input**: 224x224 RGB image (uint8)
- **Output**: 965-dimensional probability vector
- **Format**: TensorFlow Lite (quantized INT8)
- **Size**: ~4 MB
- **Performance**: Optimized for edge devices (Raspberry Pi, Coral TPU)

### Download Links

**Model (Version 3 - Latest):**
```
https://storage.googleapis.com/tfhub-lite-models/google/lite-model/aiy/vision/classifier/birds_V1/3.tflite
```

**Labels:**
```
https://raw.githubusercontent.com/google-coral/test_data/master/inat_bird_labels.txt
```

### Supported Bird Species

The model recognizes approximately 965 bird species from the iNaturalist dataset, including many common European and Swiss species:

**Swiss/European Birds Included:**
- Great Tit (Parus major)
- Blue Tit (Cyanistes caeruleus)
- House Sparrow (Passer domesticus)
- European Robin (Erithacus rubecula)
- Common Blackbird (Turdus merula)
- European Goldfinch (Carduelis carduelis)
- European Starling (Sturnus vulgaris)
- Common Chaffinch (Fringilla coelebs)
- European Greenfinch (Chloris chloris)
- Great Spotted Woodpecker (Dendrocopos major)
- And many more...

**Also includes:**
- North American birds (cardinals, jays, warblers, etc.)
- Tropical birds (parrots, toucans, hummingbirds, etc.)
- Waterfowl (ducks, geese, herons, etc.)
- Raptors (hawks, eagles, owls, etc.)

## Manual Download

If the script doesn't work, download manually:

### Using wget:
```bash
wget -O birds_model.tflite \
  https://storage.googleapis.com/tfhub-lite-models/google/lite-model/aiy/vision/classifier/birds_V1/3.tflite

wget -O labels.txt \
  https://raw.githubusercontent.com/google-coral/test_data/master/inat_bird_labels.txt
```

### Using curl:
```bash
curl -L -o birds_model.tflite \
  https://storage.googleapis.com/tfhub-lite-models/google/lite-model/aiy/vision/classifier/birds_V1/3.tflite

curl -L -o labels.txt \
  https://raw.githubusercontent.com/google-coral/test_data/master/inat_bird_labels.txt
```

### Using a web browser:
1. Visit the URLs above
2. Save files to this directory
3. Rename to `birds_model.tflite` and `labels.txt`

## Model Versions

The Google AIY bird classifier has multiple versions available:

- **Version 1**: Original release
- **Version 2**: Updated with improved accuracy
- **Version 3**: Latest (recommended) - Better quantization, smaller size

All versions use the same architecture (MobileNet V2) and label set.

## Performance Expectations

### Accuracy
- **Top-1 Accuracy**: ~70% on iNaturalist test set
- **Top-5 Accuracy**: ~90% on iNaturalist test set
- **Real-world performance**: Varies based on image quality, lighting, bird pose

### Speed
- **CPU (Raspberry Pi 5)**: ~200-300ms per inference
- **With Coral USB Accelerator**: ~10-20ms per inference
- **Recommended FPS**: 1-5 fps for bird feeder monitoring

### Best Results

For optimal classification accuracy:
- **Clear, well-lit images** - Natural daylight works best
- **Bird in center frame** - Full or partial body visible
- **Minimal background clutter** - Focus on the bird
- **Side or front view** - Better than back view
- **Close distance** - Bird should fill significant portion of frame

## Preprocessing

The classifier expects:
```python
Input shape: [1, 224, 224, 3]
Input type: uint8 (0-255)
Color format: RGB
```

Example preprocessing:
```python
from PIL import Image
import numpy as np

# Load and resize image
image = Image.open('bird.jpg').convert('RGB')
image = image.resize((224, 224), Image.LANCZOS)

# Convert to numpy array
input_data = np.array(image, dtype=np.uint8)
input_data = np.expand_dims(input_data, axis=0)

# Run inference
interpreter.set_tensor(input_details[0]['index'], input_data)
interpreter.invoke()
output = interpreter.get_tensor(output_details[0]['index'])
```

## Alternative Models

If you want to use a different bird classification model:

### 1. Custom Model
Train your own model focused on local species:
- Collect images of birds at your feeder
- Use transfer learning with MobileNet or EfficientNet
- Convert to TFLite format
- Replace `birds_model.tflite`

### 2. Caltech-UCSD Birds 200
Focuses on 200 North American species:
- Download from Kaggle or TensorFlow Hub
- Convert to TFLite
- Update labels.txt accordingly

### 3. Other iNaturalist Models
Various species coverage:
- iNaturalist 2017/2018/2019 models
- Different architectures (EfficientNet, ResNet)
- Trade-offs between accuracy and speed

## Troubleshooting

### Model not downloading
```bash
# Check internet connection
ping google.com

# Try manual download with browser
# See "Manual Download" section above
```

### Model file size wrong
Expected size: ~3.5-4.5 MB

If smaller, download may be incomplete. Delete and re-download.

### Import errors
```bash
# Install TFLite runtime
pip3 install tflite-runtime

# Or full TensorFlow
pip3 install tensorflow
```

### Low accuracy
- Improve image quality (lighting, focus, resolution)
- Tune detection zones to capture birds better
- Consider training custom model on local species
- Use Coral TPU accelerator for faster, more accurate inference

## Citations

If you use this model in research or publications:

```bibtex
@misc{aiy-birds-classifier,
  title={Google AIY Vision Classifier Birds V1},
  author={Google LLC},
  year={2018},
  url={https://tfhub.dev/google/aiy/vision/classifier/birds_V1/1}
}

@misc{inaturalist-dataset,
  title={The iNaturalist Challenge 2017 Dataset},
  author={Grant Van Horn and others},
  year={2017},
  url={https://github.com/visipedia/inat_comp}
}
```

## Resources

- [TensorFlow Hub Model Page](https://tfhub.dev/google/aiy/vision/classifier/birds_V1/1)
- [Google Coral AI Projects](https://coral.ai/)
- [Google AIY Projects](https://aiyprojects.withgoogle.com/)
- [iNaturalist Dataset](https://www.inaturalist.org/)
- [Model on Kaggle](https://www.kaggle.com/models/google/aiy/tfLite/vision-classifier-birds-v1)

## License

The model is distributed under Apache License 2.0.
The iNaturalist dataset images have various Creative Commons licenses.

---

**Note**: The model file and labels are not included in the git repository due to size. You must download them separately using the instructions above.
