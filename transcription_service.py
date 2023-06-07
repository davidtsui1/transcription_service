"""
MIT License

Copyright (c) 2023 David Tsui

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import os
import openai
import textwrap
import time
from google.cloud import speech
from google.cloud import storage
from concurrent.futures import ThreadPoolExecutor
from pydub import AudioSegment
from os.path import expanduser

# Load OpenAI API key from environment variable
openai.api_key = os.getenv('OPENAI_API_KEY', '')

class TranscriptionService:
    def __init__(self, project_id, bucket_name):
        self.project_id = project_id
        self.bucket_name = bucket_name
        self.storage_client = storage.Client(project=project_id)
        self.speech_client = speech.SpeechClient()
        self.input_extensions = [".mp4", ".m4a"]
        self.max_length = 2458  # Make max_length a class attribute instead of a global variable

    def audio_to_wav(self, audio_file_name, output_file):
        file_extension = os.path.splitext(audio_file_name)[-1][1:]
        stereo = AudioSegment.from_file(audio_file_name, format=file_extension)
        mono = stereo.set_channels(1)
        mono_16k = mono.set_frame_rate(16000)
        mono_16k.export(output_file, format='wav')
        return output_file

    def google_transcribe(self, filepath, audio_file_name):
        filepath = os.path.join(filepath, audio_file_name)
        wav_file_name = self.audio_to_wav(filepath, filepath.replace(os.path.splitext(audio_file_name)[-1], ".wav"))
        destination_blob_name = audio_file_name.replace(os.path.splitext(audio_file_name)[-1], ".wav")

        self.upload_blob(wav_file_name, destination_blob_name)

        gcs_uri = 'gs://' + self.bucket_name + '/' + destination_blob_name
        transcript = self.transcribe_audio(gcs_uri)
        self.delete_blob(destination_blob_name)

        return transcript

    def transcribe_audio(self, gcs_uri):
        transcript = ''
        audio = speech.RecognitionAudio(uri=gcs_uri)
        diarization_config = speech.SpeakerDiarizationConfig(
            enable_speaker_diarization=True,
            min_speaker_count=1,
            max_speaker_count=10,
        )
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            language_code="en-US",
            diarization_config=diarization_config,
            model="latest_long"
        )
        operation = self.speech_client.long_running_recognize(config=config, audio=audio)
        response = operation.result(timeout=3600)
        transcript = self.speaker_diarization(response)
        return transcript

    def speaker_diarization(self, response):
        transcript = ''
        result = response.results[-1]
        words_info = result.alternatives[0].words
        tag = 1
        speaker = ""
        for word_info in words_info:
            if word_info.speaker_tag == tag:
                speaker = speaker + " " + word_info.word
            else:
                transcript += f"speaker {tag}: {speaker}\n\n"
                tag = word_info.speaker_tag
                speaker = "" + word_info.word
        transcript += f"speaker {tag}: {speaker}"
        return transcript

    def upload_blob(self, source_file_name, destination_blob_name):
        bucket = self.storage_client.get_bucket(self.bucket_name)
        blob = bucket.blob(destination_blob_name)
        blob.upload_from_filename(source_file_name)

    def delete_blob(self, blob_name):
        bucket = self.storage_client.get_bucket(self.bucket_name)
        blob = bucket.blob(blob_name)
        blob.delete()

    def write_transcripts(self, transcript_filename, transcript, output_filepath):
        with open(os.path.join(output_filepath, transcript_filename), "w") as transcript_file:
            transcript_file.write(transcript)

    def chunk_transcript(self, text, length):
        return textwrap.wrap(text, length)

    def generate_summary(self, text):
        response = None

        while True:
            try:
                chunks = self.chunk_transcript(text, self.max_length)
                for chunk in chunks:
                    response = openai.Completion.create(
                        engine="text-davinci-003",
                        prompt=f"{chunk}\n\nSummarize the above text.",
                        temperature=0.5,
                        max_tokens=1228,
                        top_p=1.0,
                    )
                    print("summary: "+ response.choices[0].text.strip())
                    return response.choices[0].text.strip()
                    break
            except openai.error.RateLimitError:
                print("Rate limit hit. Waiting before retrying.")
                time.sleep(60)
            except openai.error.OpenAIError as e:
                if "maximum content length" in str(e):
                    self.max_length = self.max_length // 2
                    print(f"New max_length: {self.max_length}")
                else:
                    raise e

    def generate_minutes(self, text):
        max_length = 1842
        response = None

        while True:
            try:
                chunks = self.chunk_transcript(text, max_length)
                for chunk in chunks:
                    response = openai.Completion.create(
                        engine="text-davinci-003",
                        prompt=f"{chunk}\n\nUse the text above and generate in meeting minutes format with next step action items.",
                        max_tokens=1842,
                        temperature=0.5,
                        top_p=1.0,
                    )
                    print("minute: " + response.choices[0].text.strip())
                    return response.choices[0].text.strip()
                    break
            except openai.error.RateLimitError:
                print("Rate limit hit. Waiting before retrying.")
                time.sleep(60)
            except openai.error.OpenAIError as e:
                if "maximum content length" in str(e):
                    max_length = max_length // 2
                    print(f"New max_length: {max_length}")
                else:
                    raise e

    def summarize_transcript(self, transcript):
        with ThreadPoolExecutor(max_workers=2) as executor:
            future_summary = executor.submit(self.generate_summary, transcript)
            future_minutes = executor.submit(self.generate_minutes, transcript)
            summary = future_summary.result()
            minutes = future_minutes.result()
            return summary, minutes

if __name__ == "__main__":
    # These are placeholder values, replace with your actual project ID and bucket name
    project_id = "YOUR_PROJECT_ID"
    bucketname = "YOUR_BUCKET_NAME"
    # You should store file paths as environment variables for better security and configurability
    filepath = os.getenv('SOURCE_PATH', expanduser("~/transcribe/source"))
    output_filepath = os.getenv('OUTPUT_PATH', expanduser("~/transcribe/transcripts/"))
    service = TranscriptionService(project_id, bucketname)

    for audio_file_name_orig in os.listdir(filepath):
        if any(audio_file_name_orig.endswith(ext) for ext in service.input_extensions):
            transcript = service.google_transcribe(filepath, audio_file_name_orig)
            transcript_filename = audio_file_name_orig.replace(os.path.splitext(audio_file_name_orig)[-1], ".txt")
            service.write_transcripts(transcript_filename, transcript, output_filepath)
            print(transcript)

            summary, minutes = service.summarize_transcript(transcript)

            service.write_transcripts(transcript_filename.replace(".txt", "_summary.txt"), summary, output_filepath)
            service.write_transcripts(transcript_filename.replace(".txt", "_minutes.txt"), minutes, output_filepath)
