# Transcription Service

This Python-based service allows you to transcribe audio files using Google Cloud Speech-to-Text, generate summaries and meeting minutes with OpenAI's text-davinci-003, and manage files using Google Cloud Storage.

## Features

- Audio transcription from .mp4 and .m4a files.
- Conversion of audio to .wav format.
- Generation of summaries and meeting minutes.
- Uploading, managing, and deleting files on Google Cloud Storage.

## Requirements

- Python 3.7+
- Google Cloud SDK
- openai
- pydub
- textwrap
- google-cloud-speech
- google-cloud-storage
- concurrent.futures

## Installation

1. Install the required Python packages with pip:

```bash
pip install google-cloud-speech google-cloud-storage pydub openai
```

2. Clone the repository:

```bash
git clone https://github.com/davidtsui1/transcription_service.git
```

3. Navigate to the project directory:

```bash
cd transcription_service
```

4. Set up your Google Cloud and OpenAI configurations:

   - For Google Cloud, follow the instructions [here](https://cloud.google.com/docs/authentication/getting-started).
   - For OpenAI, follow the instructions [here](https://platform.openai.com/docs/guides/api-keys).

5. Replace 'YOUR_PROJECT_ID' and 'YOUR_BUCKET_NAME' in the transcription_service.py file with your actual project ID and bucket name.

## Usage

```bash
python transcription_service.py
```

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

## License

[MIT License](LICENSE)

---

## About the Author

This Transcription Service project was developed by David Rich Tsui. You can find more about him and his work on his [GitHub profile](https://github.com/davidtsui1).
