import os
import sys
import argparse
import mimetypes
import re
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Load environment variables from parent directory (.env)
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(current_dir, ".."))
dotenv_path = os.path.join(root_dir, ".env")
load_dotenv(dotenv_path)

def get_api_key():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "your_api_key_here":
        print("Error: GEMINI_API_KEY is not set in the .env file.")
        sys.exit(1)
    return api_key

def analyze_image_name(image_path, model_name, custom_prompt=None):
    if not os.path.exists(image_path):
        print(f"Error: File not found: {image_path}")
        sys.exit(1)

    # Resolve MIME type
    mime_type, _ = mimetypes.guess_type(image_path)
    if not mime_type:
        # Fallback
        ext = os.path.splitext(image_path)[1].lower()
        if ext == '.png':
            mime_type = 'image/png'
        elif ext in ('.jpg', '.jpeg'):
            mime_type = 'image/jpeg'
        elif ext == '.webp':
            mime_type = 'image/webp'
        else:
            mime_type = 'application/octet-stream'

    # Read file bytes
    with open(image_path, "rb") as f:
        image_bytes = f.read()

    client = genai.Client(api_key=get_api_key())

    # Formulate prompt
    default_prompt = (
        "You are an expert file organizer and AI assistant.\n"
        "Analyze the provided image and generate an appropriate, descriptive, and concise filename for it.\n\n"
        "Requirements for the filename:\n"
        "1. Must be in English.\n"
        "2. Use lowercase letters, numbers, and hyphens only (kebab-case).\n"
        "3. Do not include spaces or special characters.\n"
        "4. Keep it concise (typically 2-5 words).\n"
        "5. Append the correct file extension based on the image type (e.g., .png, .jpg).\n"
        "6. Output ONLY the filename, with no extra explanation, markdown formatting, or quotes.\n\n"
        "Context:\n"
        "This image is part of a computer graphics portfolio repository. It contains topics like DirectX 11, "
        "Ray Tracing, shaders, coordinate transformations, and image processing. If the image is a technical diagram "
        "or illustration, try to use terms related to these computer graphics concepts."
    )

    prompt = custom_prompt if custom_prompt else default_prompt

    image_part = types.Part.from_bytes(
        data=image_bytes,
        mime_type=mime_type
    )

    print(f"Analyzing image using model {model_name}...")
    try:
        response = client.models.generate_content(
            model=model_name,
            contents=[image_part, prompt]
        )
        return response.text.strip()
    except Exception as e:
        print(f"Error during API call: {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Analyze image content using Gemini API and rename the file accordingly.")
    parser.add_argument("image_path", help="Path to the image file to analyze and rename.")
    parser.add_argument("-d", "--dry-run", action="store_true", help="Print the suggested name and exit without renaming.")
    parser.add_argument("-f", "--force", action="store_true", help="Rename the file immediately without prompting for confirmation.")
    parser.add_argument("-m", "--model", default="gemini-2.5-flash", help="Gemini model to use (default: gemini-2.5-flash).")
    parser.add_argument("-p", "--prompt", help="Provide a custom prompt for name generation.")

    args = parser.parse_args()

    suggested_name = analyze_image_name(args.image_path, args.model, args.prompt)
    
    # Strip any markdown formatting block if the model output wrapped it in ``` or `
    if suggested_name.startswith("```"):
        lines = [line.strip() for line in suggested_name.split("\n") if line.strip()]
        for line in lines:
            if not line.startswith("```"):
                suggested_name = line
                break
    suggested_name = suggested_name.strip("`'\" \n\r\t")
    
    # Extract only the base name if there's any text around it
    match = re.search(r'([\w\-]+\.(?:png|jpg|jpeg|webp|gif))', suggested_name, re.IGNORECASE)
    if match:
        suggested_name = match.group(1).lower()
    else:
        # Fallback cleanup
        suggested_name = suggested_name.lower()
        suggested_name = re.sub(r'[^a-z0-9\.\-]', '-', suggested_name)
        suggested_name = re.sub(r'-+', '-', suggested_name)
        suggested_name = suggested_name.strip('-')

    print(f"Suggested name: {suggested_name}")

    if args.dry_run:
        sys.exit(0)

    # Perform rename
    old_dir = os.path.dirname(args.image_path)
    new_path = os.path.join(old_dir, suggested_name)

    if os.path.abspath(args.image_path) == os.path.abspath(new_path):
        print("The file already has the suggested name.")
        sys.exit(0)

    if not args.force:
        try:
            confirm = input(f"Rename '{args.image_path}' -> '{new_path}'? [y/N]: ").strip().lower()
            if confirm not in ('y', 'yes'):
                print("Cancelled.")
                sys.exit(0)
        except KeyboardInterrupt:
            print("\nCancelled.")
            sys.exit(0)

    try:
        os.rename(args.image_path, new_path)
        print(f"Successfully renamed to: {new_path}")
    except Exception as e:
        print(f"Error renaming file: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
