from .s3_save_node import S3SaveNode

NODE_CLASS_MAPPINGS = {
    "S3SaveNode": S3SaveNode
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "S3SaveNode": "Save to S3"
}

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS'] 