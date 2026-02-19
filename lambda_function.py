import os, json, csv, io, datetime
import boto3
import requests
from requests_oauthlib import OAuth1

s3 = boto3.client("s3")
ddb = boto3.resource("dynamodb")
secrets = boto3.client("secretsmanager")

BUCKET = os.environ["BUCKET"]
KEY = os.environ["KEY"]
SECRET_ID = os.environ["SECRET_ID"]
TABLE = os.environ["TABLE"]
PK_VALUE = os.environ.get("PK_VALUE", "har_vmat")

X_CREATE_POST_URL = "https://api.x.com/2/tweets"

def get_secret():
    resp = secrets.get_secret_value(SecretId=SECRET_ID)
    return json.loads(resp["SecretString"])

def load_quotes_from_s3():
    obj = s3.get_object(Bucket=BUCKET, Key=KEY)
    data = obj["Body"].read()
    try:
        raw = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        raw = data.decode("cp1252")

    f = io.StringIO(raw)
    reader = csv.DictReader(f)

    quotes = []
    for row in reader:
        q = (row.get("quote") or "").strip()
        if q:
            quotes.append(q)
    return quotes

def get_next_index(table, n_quotes):
    resp = table.get_item(Key={"pk": PK_VALUE})
    idx = int(resp.get("Item", {}).get("next_index", 0))
    return idx % max(n_quotes, 1)

def set_next_index(table, next_idx):
    table.put_item(Item={
        "pk": PK_VALUE,
        "next_index": int(next_idx),
        "updated_at": datetime.datetime.utcnow().isoformat() + "Z"
    })

def post_to_x(creds, text):
    auth = OAuth1(
        creds["consumer_key"],
        creds["consumer_secret"],
        creds["access_token"],
        creds["access_token_secret"],
    )
    payload = {"text": text}
    r = requests.post(X_CREATE_POST_URL, auth=auth, json=payload, timeout=20)
    if r.status_code >= 300:
        raise RuntimeError(f"X post failed: {r.status_code} {r.text}")
    return r.json()

def lambda_handler(event, context):
    creds = get_secret()
    quotes = load_quotes_from_s3()
    if not quotes:
        return {"status": "no_quotes"}

    table = ddb.Table(TABLE)
    idx = get_next_index(table, len(quotes))

    text = " ".join(quotes[idx].split())
    if len(text) > 280:
        text = text[:277] + "…"

    resp = post_to_x(creds, text)
    set_next_index(table, idx + 1)

    return {"status": "posted", "index": idx, "tweet": resp}
