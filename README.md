# x-quote-bot-aws

A serverless bot that posts a quote to X using AWS Lambda + S3 + DynamoDB + Secrets Manager.

## Architecture
- S3: stores `quotes.csv`
- DynamoDB: stores `next_index`
- Secrets Manager: stores X OAuth 1.0a credentials
- Lambda: reads quote, posts to X, increments index
- EventBridge: schedules daily runs (optional)

## Setup (high level)
1. Upload `quotes.csv` to S3
2. Create DynamoDB table `x_quote_bot_state` with pk `pk` and item `{ pk: "har_vmat", next_index: 0 }`
3. Store X credentials in Secrets Manager as `x-bot-credentials`
4. Create Lambda layer for dependencies (`requests`, `requests-oauthlib`)
5. Deploy Lambda with env vars:
   - BUCKET, KEY, SECRET_ID, TABLE, PK_VALUE
6. Test, then schedule via EventBridge

## Security
Do NOT commit your X keys. Keep them in AWS Secrets Manager.
