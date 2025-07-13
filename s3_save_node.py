import os
import json
import boto3
from PIL import Image
import io
import torch
import numpy as np
import secrets
import string
import time
import random

class S3SaveNode:
    def __init__(self):
        self.type = "output"
        self.s3_client = boto3.client(
            "s3",
            endpoint_url=os.environ.get("CLOUDFLARE_R2_ENDPOINT_URL", ""),
            aws_access_key_id=os.environ.get("CLOUDFLARE_ACCESS_KEY_ID", ""),
            aws_secret_access_key=os.environ.get("CLOUDFLARE_SECRET_ACCESS_KEY", ""),
        )
        self.cloudflare_r2_url = os.environ.get("CLOUDFLARE_R2_URL", "https://img-dev.fantasy.ai/")
        self.cloudflare_r2_bucket = os.environ.get("CLOUDFLARE_R2_BUCKET", "fan-dev")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE",),
                "file_prefix": ("STRING", {"default": ""})
            }
        }


    RETURN_TYPES = ("STRING",)
    FUNCTION = "save_to_s3"
    OUTPUT_NODE = True
    CATEGORY = "image/s3"

    def save_to_s3(self, images, file_prefix):
        bucket = self.cloudflare_r2_bucket
        prefix = file_prefix
        results = []

        try:
            for i, image in enumerate(images):
                try:
                    print(f"Processing image {i + 1}/{len(images)}")

                    # Convert image to numpy
                    if isinstance(image, torch.Tensor):
                        if image.ndim == 4:
                            image = image[0]
                        image = image.cpu().numpy()
                        if image.shape[0] == 3:
                            image = np.transpose(image, (1, 2, 0))
                        image = (image * 255).astype(np.uint8) if image.max() <= 1.0 else image.astype(np.uint8)
                    elif isinstance(image, np.ndarray):
                        if image.shape[0] == 3 and image.ndim == 3:
                            image = np.transpose(image, (1, 2, 0))
                        image = (image * 255).astype(np.uint8) if image.max() <= 1.0 else image.astype(np.uint8)
                    else:
                        raise ValueError("Unsupported image type")

                    pil_img = Image.fromarray(image)
                    buffer = io.BytesIO()
                    pil_img.save(buffer, format="WEBP", quality=95)
                    buffer.seek(0)

                    filename = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(20)) + '.webp'
                    key = prefix + filename

                    print(f"Uploading to R2: {bucket}/{key}")
                    self.s3_client.put_object(
                        Bucket=bucket,
                        Key=key,
                        Body=buffer.getvalue(),
                        ContentType="image/webp"
                    )
                    
                    # Build public URL using the correct public domain: CF > R2 > bucket > Settings > Custom Domains
                    public_url = f"{self.cloudflare_r2_url}{key}"
                    
                    # Append URL and status to results
                    results.append({
                        "url": public_url,
                        "status": "success"
                    })
                    
                    print(f"   Uploaded: {filename}")
                    print(f"   URL: {public_url}")
                    
                except Exception as e:
                    print(f"   Failed to upload image {i}: {e}")
                    
                    # Append failed result
                    results.append({
                        "url": None,
                        "status": "failed"
                    })

            # Return JSON string of results
            return {"STRING": json.dumps(results)}

        except Exception as e:
            error_msg = f"Fatal error: {str(e)}"
            print(error_msg)
            return {json.dumps([{"url": None, "status": "failed"}])}
