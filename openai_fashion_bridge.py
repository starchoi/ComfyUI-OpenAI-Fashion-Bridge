import os
import io
import json
import base64
from typing import Optional, Tuple

import numpy as np
import requests
import torch
from PIL import Image


OPENAI_API_BASE = "https://api.openai.com/v1"


def _tensor_to_png_bytes(image_tensor: torch.Tensor) -> bytes:
    """ComfyUI IMAGE tensor -> PNG bytes."""
    if image_tensor is None:
        raise ValueError("image_tensor is None")

    if image_tensor.ndim == 4:
        image_tensor = image_tensor[0]

    image_tensor = image_tensor.detach().cpu().clamp(0, 1)
    image_np = (image_tensor.numpy() * 255.0).astype(np.uint8)
    pil_img = Image.fromarray(image_np)

    buf = io.BytesIO()
    pil_img.save(buf, format="PNG")
    return buf.getvalue()


def _b64_to_tensor(b64_data: str) -> torch.Tensor:
    image_bytes = base64.b64decode(b64_data)
    pil_img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    image_np = np.array(pil_img).astype(np.float32) / 255.0
    image_tensor = torch.from_numpy(image_np)[None,]
    return image_tensor


def _build_headers(api_key: str) -> dict:
    if not api_key:
        raise ValueError("OPENAI_API_KEY is empty. Please paste it into the node or set it in the environment.")
    return {
        "Authorization": f"Bearer {api_key}",
    }


class OpenAIFashionBridge:
    """
    A simple ComfyUI bridge node for OpenAI image generation/edit testing.

    Notes:
    - text_to_image -> POST /v1/images/generations
    - all other tasks -> POST /v1/images/edits
    - Default model is gpt-image-2. If your account / SDK access is not ready,
      switch to gpt-image-1 in the node UI.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "task": (
                    [
                        "text_to_image",
                        "fabric_to_garment",
                        "fabric_replace",
                        "ootd",
                        "image_edit",
                        "front_to_back",
                    ],
                ),
                "prompt": ("STRING", {"multiline": True, "default": "A high-fashion editorial image."}),
                "model": ("STRING", {"default": "gpt-image-2"}),
                "size": (["1024x1024", "1024x1536", "1536x1024", "auto"], {"default": "1024x1536"}),
                "quality": (["low", "medium", "high", "auto"], {"default": "high"}),
                "output_format": (["png", "webp", "jpeg"], {"default": "png"}),
                "api_key": ("STRING", {"multiline": False, "default": ""}),
                "timeout_seconds": ("INT", {"default": 180, "min": 30, "max": 600}),
            },
            "optional": {
                "image1": ("IMAGE",),
                "image2": ("IMAGE",),
            },
        }

    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("image", "debug_json")
    FUNCTION = "run"
    CATEGORY = "OpenAI/Fashion"

    def _call_image_generation(
        self,
        api_key: str,
        model: str,
        prompt: str,
        size: str,
        quality: str,
        output_format: str,
        timeout_seconds: int,
    ) -> Tuple[torch.Tensor, str]:
        url = f"{OPENAI_API_BASE}/images/generations"
        headers = _build_headers(api_key)
        headers["Content-Type"] = "application/json"

        payload = {
            "model": model,
            "prompt": prompt,
            "size": size,
            "quality": quality,
            "output_format": output_format,
        }

        resp = requests.post(url, headers=headers, json=payload, timeout=timeout_seconds)
        resp.raise_for_status()
        data = resp.json()

        if not data.get("data"):
            raise RuntimeError(f"OpenAI returned no image data: {json.dumps(data, ensure_ascii=False)[:1000]}")

        b64 = data["data"][0].get("b64_json")
        if not b64:
            raise RuntimeError(f"OpenAI returned no b64_json. Response: {json.dumps(data, ensure_ascii=False)[:1000]}")

        image_tensor = _b64_to_tensor(b64)
        debug = {
            "endpoint": "/v1/images/generations",
            "model": model,
            "size": size,
            "quality": quality,
            "output_format": output_format,
        }
        return image_tensor, json.dumps(debug, ensure_ascii=False, indent=2)

    def _call_image_edit(
        self,
        api_key: str,
        model: str,
        prompt: str,
        size: str,
        quality: str,
        output_format: str,
        image1: Optional[torch.Tensor],
        image2: Optional[torch.Tensor],
        timeout_seconds: int,
    ) -> Tuple[torch.Tensor, str]:
        if image1 is None:
            raise ValueError("image1 is required for this task.")

        url = f"{OPENAI_API_BASE}/images/edits"
        headers = _build_headers(api_key)

        files = []
        files.append(("image[]", ("image1.png", _tensor_to_png_bytes(image1), "image/png")))
        if image2 is not None:
            files.append(("image[]", ("image2.png", _tensor_to_png_bytes(image2), "image/png")))

        data = {
            "model": model,
            "prompt": prompt,
            "size": size,
            "quality": quality,
            "output_format": output_format,
        }

        resp = requests.post(url, headers=headers, data=data, files=files, timeout=timeout_seconds)
        resp.raise_for_status()
        body = resp.json()

        if not body.get("data"):
            raise RuntimeError(f"OpenAI returned no image data: {json.dumps(body, ensure_ascii=False)[:1000]}")

        b64 = body["data"][0].get("b64_json")
        if not b64:
            raise RuntimeError(f"OpenAI returned no b64_json. Response: {json.dumps(body, ensure_ascii=False)[:1000]}")

        image_tensor = _b64_to_tensor(b64)
        debug = {
            "endpoint": "/v1/images/edits",
            "model": model,
            "size": size,
            "quality": quality,
            "output_format": output_format,
            "input_images": 1 if image2 is None else 2,
        }
        return image_tensor, json.dumps(debug, ensure_ascii=False, indent=2)

    def run(
        self,
        task: str,
        prompt: str,
        model: str,
        size: str,
        quality: str,
        output_format: str,
        api_key: str,
        timeout_seconds: int,
        image1: Optional[torch.Tensor] = None,
        image2: Optional[torch.Tensor] = None,
    ):
        api_key = (api_key or "").strip() or os.getenv("OPENAI_API_KEY", "").strip()

        try:
            if task == "text_to_image":
                image_tensor, debug_json = self._call_image_generation(
                    api_key=api_key,
                    model=model,
                    prompt=prompt,
                    size=size,
                    quality=quality,
                    output_format=output_format,
                    timeout_seconds=timeout_seconds,
                )
            else:
                image_tensor, debug_json = self._call_image_edit(
                    api_key=api_key,
                    model=model,
                    prompt=prompt,
                    size=size,
                    quality=quality,
                    output_format=output_format,
                    image1=image1,
                    image2=image2,
                    timeout_seconds=timeout_seconds,
                )

            return (image_tensor, debug_json)
        except Exception as e:
            # Return a 1x1 black image so ComfyUI does not crash the graph output slot.
            dummy = torch.zeros((1, 1, 1, 3), dtype=torch.float32)
            debug = {
                "error": str(e),
                "task": task,
                "model": model,
                "hint": "If gpt-image-2 is unavailable in your account, switch model to gpt-image-1 and test again.",
            }
            return (dummy, json.dumps(debug, ensure_ascii=False, indent=2))


NODE_CLASS_MAPPINGS = {
    "OpenAIFashionBridge": OpenAIFashionBridge,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "OpenAIFashionBridge": "OpenAI Fashion Bridge",
}
