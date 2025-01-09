import pandas as pd
from datasets import load_dataset
from google.cloud import storage
from dotenv import load_dotenv
import os
load_dotenv()

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "service-account-key.json"
def upload_to_gcs(local_file, bucket_name, destination_blob_name):
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_filename(local_file)
    print(f"File {local_file} uploaded to {bucket_name}/{destination_blob_name}.")

def get_datas():
    dataset = load_dataset("open-llm-leaderboard/contents", split="train").sort("Average ⬆️", reverse=True)
    return pd.DataFrame(dataset)

def main():
    bucket_name = os.getenv("BUCKET_NAME")
    destination_blob_name = "llm_leaderboard.csv"
    local_file = "llm_leaderboard.csv"

    data = get_datas()
    data.to_csv(local_file, index=False)
    upload_to_gcs(local_file, bucket_name, destination_blob_name)
    return "Leaderboard updated successfully!"


# gcloud scheduler jobs create http update-leaderboard-job \
#     --schedule "0 */2 * * *" \
#     --uri "https://us-central1-PROJECT_ID.cloudfunctions.net/update_leaderboard" \
#     --http-method GET

# gcloud projects add-iam-policy-binding PROJECT_ID \
#     --member="serviceAccount:PROJECT_ID@appspot.gserviceaccount.com" \
#     --role="roles/cloudfunctions.invoker"

