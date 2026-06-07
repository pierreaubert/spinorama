// Background removal via transformers.js + RMBG-1.4 (local model, runs in-browser).
// Lazy-loaded so opening the app's grid does not pull in ~50 MB of weights.

import {
  AutoModel,
  AutoProcessor,
  RawImage,
  env,
  type PreTrainedModel,
  type Processor,
} from '@huggingface/transformers';

env.allowLocalModels = false;

const MODEL_ID = 'briaai/RMBG-1.4';

interface Pipeline {
  model: PreTrainedModel;
  processor: Processor;
}

let pipelinePromise: Promise<Pipeline> | null = null;

export function loadPipeline(onProgress?: (msg: string) => void): Promise<Pipeline> {
  if (pipelinePromise) return pipelinePromise;
  onProgress?.('Loading background removal model (~44 MB, cached after first load)…');
  pipelinePromise = (async () => {
    const model = await AutoModel.from_pretrained(MODEL_ID, {
      config: { model_type: 'custom' } as never,
      device: 'webgpu',
      dtype: 'fp32',
    });
    const processor = await AutoProcessor.from_pretrained(MODEL_ID, {
      config: {
        do_normalize: true,
        do_pad: false,
        do_rescale: true,
        do_resize: true,
        image_mean: [0.5, 0.5, 0.5],
        feature_extractor_type: 'ImageFeatureExtractor',
        image_std: [1, 1, 1],
        resample: 2,
        rescale_factor: 0.00392156862745098,
        size: { width: 1024, height: 1024 },
      },
    } as never);
    onProgress?.('Model ready.');
    return { model, processor };
  })();
  return pipelinePromise;
}

/**
 * Take an RGBA ImageData and return a new ImageData with the alpha channel
 * replaced by the foreground mask predicted by RMBG-1.4. Pixels outside the
 * subject become transparent.
 */
export async function removeBackground(
  source: ImageData,
  onProgress?: (msg: string) => void,
): Promise<ImageData> {
  const { model, processor } = await loadPipeline(onProgress);

  const rawImage = new RawImage(
    new Uint8ClampedArray(source.data),
    source.width,
    source.height,
    4,
  );

  onProgress?.('Running segmentation…');
  const callable = processor as unknown as (img: RawImage) => Promise<{ pixel_values: unknown }>;
  const { pixel_values } = await callable(rawImage);
  const inferenceOutput = (await model({ input: pixel_values })) as {
    output: { mul(scalar: number): unknown }[];
  };

  const maskTensorRaw = await RawImage.fromTensor(
    inferenceOutput.output[0].mul(255) as never,
  );
  const mask = await maskTensorRaw.resize(source.width, source.height);

  const out = new Uint8ClampedArray(source.data);
  for (let i = 0; i < mask.data.length; i++) {
    out[i * 4 + 3] = mask.data[i];
  }
  onProgress?.('Background removed.');
  return new ImageData(out, source.width, source.height);
}
