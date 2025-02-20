"""Vision tools for OpenHands ACI."""

import base64
import io
import os
from dataclasses import dataclass
from typing import Optional, Union

import requests
from PIL import Image

from ..utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ImageInspectorTool:
    """Tool for inspecting images."""

    def inspect_image(self, image_path_or_url: str) -> str:
        """Inspect an image and return its properties."""
        try:
            image = self._load_image(image_path_or_url)
            return self._get_image_info(image)
        except Exception as e:
            logger.error(f"Error inspecting image {image_path_or_url}: {e}")
            return f"Error: {str(e)}"

    def _load_image(self, image_path_or_url: str) -> Image.Image:
        """Load image from path or URL."""
        if image_path_or_url.startswith(("http://", "https://")):
            response = requests.get(image_path_or_url)
            response.raise_for_status()
            return Image.open(io.BytesIO(response.content))
        return Image.open(image_path_or_url)

    def _get_image_info(self, image: Image.Image) -> str:
        """Get image information."""
        info = {
            "format": image.format,
            "mode": image.mode,
            "size": image.size,
            "width": image.width,
            "height": image.height,
        }
        if hasattr(image, "info"):
            info.update(
                {k: str(v) for k, v in image.info.items() if isinstance(v, (str, int, float))}
            )
        return str(info)


@dataclass
class VisualQATool:
    """Tool for visual question answering."""

    model_name: str = "Salesforce/blip2-flan-t5-xl"
    device: str = "cuda" if os.environ.get("CUDA_VISIBLE_DEVICES") else "cpu"
    max_new_tokens: int = 100

    def __post_init__(self):
        """Initialize the model."""
        try:
            from transformers import AutoModelForVisionEncoderDecoder, AutoProcessor
            self.processor = AutoProcessor.from_pretrained(self.model_name)
            self.model = AutoModelForVisionEncoderDecoder.from_pretrained(
                self.model_name
            ).to(self.device)
        except Exception as e:
            logger.error(f"Error loading model {self.model_name}: {e}")
            self.processor = None
            self.model = None

    def ask(
        self,
        image_path_or_url: str,
        question: str,
        context: Optional[str] = None,
    ) -> str:
        """Ask a question about an image."""
        if not self.model or not self.processor:
            return "Model not initialized"

        try:
            image = self._load_image(image_path_or_url)
            prompt = f"Question: {question}"
            if context:
                prompt = f"Context: {context}\n{prompt}"

            inputs = self.processor(
                images=image,
                text=prompt,
                return_tensors="pt",
            ).to(self.device)

            outputs = self.model.generate(
                **inputs,
                max_new_tokens=self.max_new_tokens,
                do_sample=False,
            )

            return self.processor.batch_decode(
                outputs,
                skip_special_tokens=True,
            )[0].strip()

        except Exception as e:
            logger.error(f"Error processing visual QA: {e}")
            return f"Error: {str(e)}"

    def _load_image(self, image_path_or_url: Union[str, bytes]) -> Image.Image:
        """Load image from path, URL or base64 string."""
        if isinstance(image_path_or_url, bytes):
            return Image.open(io.BytesIO(image_path_or_url))

        if image_path_or_url.startswith(("http://", "https://")):
            response = requests.get(image_path_or_url)
            response.raise_for_status()
            return Image.open(io.BytesIO(response.content))

        if image_path_or_url.startswith("data:image"):
            # Handle base64 encoded images
            header, encoded = image_path_or_url.split(",", 1)
            data = base64.b64decode(encoded)
            return Image.open(io.BytesIO(data))

        return Image.open(image_path_or_url)