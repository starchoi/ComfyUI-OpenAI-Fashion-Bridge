# ComfyUI OpenAI Fashion Bridge

This package gives you a simple test bridge from ComfyUI to OpenAI image generation / editing.

## What is included
- `openai_fashion_bridge.py` — custom node
- `requirements.txt`
- `workflows/01_openai_text_to_image.json`
- `workflows/02_openai_fabric_to_garment.json`
- `workflows/03_openai_fabric_replace.json`
- `workflows/04_openai_ootd.json`
- `workflows/05_openai_image_edit.json`
- `workflows/06_openai_front_to_back.json`

## 1. Copy the custom node into ComfyUI

Copy the whole folder into:

```bash
ComfyUI/custom_nodes/ComfyUI-OpenAI-Fashion-Bridge
```

## 2. Install Python packages

Open terminal in your ComfyUI Python environment and run:

```bash
pip install -r ComfyUI/custom_nodes/ComfyUI-OpenAI-Fashion-Bridge/requirements.txt
```

## 3. Set your OpenAI API key

### Windows PowerShell
```powershell
setx OPENAI_API_KEY "YOUR_OPENAI_API_KEY"
```

Then fully close and reopen ComfyUI.

### Or paste key directly in the node
You can also paste the key into the `api_key` field of the node for quick testing.

## 4. Restart ComfyUI

After restart, search for this node:

```text
OpenAI Fashion Bridge
```

Category:

```text
OpenAI/Fashion
```

## 5. Import a workflow

In ComfyUI:
1. Drag the JSON file into the canvas, or
2. Use Load / Import workflow

## 6. Replace the demo images

For workflows with `LoadImage`, change the image filenames to your own test files.

## 7. First test settings

Recommended first test:
- model: `gpt-image-2`
- if it fails, fallback to: `gpt-image-1`
- quality: `medium`
- size: `1024x1536`

## 8. Task mapping

- `text_to_image` → `/v1/images/generations`
- `fabric_to_garment` → `/v1/images/edits`
- `fabric_replace` → `/v1/images/edits`
- `ootd` → `/v1/images/edits`
- `image_edit` → `/v1/images/edits`
- `front_to_back` → `/v1/images/edits`

## 9. Important note

This is a simple bridge for testing. It does not do mask-based editing.
For `fabric_replace`, `OOTD`, and `front_to_back`, success depends heavily on the prompt and source images.

## 10. If you get an error

Read the second output of the node (`debug_json`) or open the ComfyUI console.

Most common fixes:
- wrong API key
- no prepaid balance
- `gpt-image-2` not yet enabled for your account
- switch model to `gpt-image-1`
- image too large or request timed out
