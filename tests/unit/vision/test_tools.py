"""Tests for vision tools."""

import base64
import io
import os
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from openhands_aci.vision.tools import ImageInspectorTool, VisualQATool


@pytest.fixture
def sample_image():
    """Create a sample image for testing."""
    img = Image.new("RGB", (100, 100), color="red")
    img_io = io.BytesIO()
    img.save(img_io, format="PNG")
    img_io.seek(0)
    return img_io.getvalue()


def test_image_inspector_local_file(tmp_path, sample_image):
    """Test ImageInspectorTool with local file."""
    image_path = tmp_path / "test.png"
    with open(image_path, "wb") as f:
        f.write(sample_image)

    inspector = ImageInspectorTool()
    result = inspector.inspect_image(str(image_path))

    assert "format" in result
    assert "size" in result
    assert "(100, 100)" in result


@patch("requests.get")
def test_image_inspector_url(mock_get, sample_image):
    """Test ImageInspectorTool with URL."""
    mock_response = MagicMock()
    mock_response.content = sample_image
    mock_get.return_value = mock_response

    inspector = ImageInspectorTool()
    result = inspector.inspect_image("http://example.com/image.png")

    assert "format" in result
    assert "size" in result
    assert "(100, 100)" in result


def test_image_inspector_error():
    """Test ImageInspectorTool error handling."""
    inspector = ImageInspectorTool()
    result = inspector.inspect_image("nonexistent.png")
    assert "Error" in result


@pytest.mark.skipif(
    not os.environ.get("CUDA_VISIBLE_DEVICES"),
    reason="CUDA not available"
)
def test_visual_qa_tool_init():
    """Test VisualQATool initialization."""
    qa_tool = VisualQATool()
    assert qa_tool.model is not None
    assert qa_tool.processor is not None


def test_visual_qa_tool_base64(sample_image):
    """Test VisualQATool with base64 image."""
    base64_image = f"data:image/png;base64,{base64.b64encode(sample_image).decode()}"
    qa_tool = VisualQATool()

    # Skip if model initialization failed
    if not qa_tool.model:
        pytest.skip("Model initialization failed")

    result = qa_tool.ask(base64_image, "What color is this image?")
    assert isinstance(result, str)
    assert len(result) > 0


@patch("requests.get")
def test_visual_qa_tool_url(mock_get, sample_image):
    """Test VisualQATool with URL."""
    mock_response = MagicMock()
    mock_response.content = sample_image
    mock_get.return_value = mock_response

    qa_tool = VisualQATool()

    # Skip if model initialization failed
    if not qa_tool.model:
        pytest.skip("Model initialization failed")

    result = qa_tool.ask("http://example.com/image.png", "What color is this image?")
    assert isinstance(result, str)
    assert len(result) > 0