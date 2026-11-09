# Putting Tally online

Two pieces: the **API** (Python, on Google Cloud Run, like DocSift) and the **page** (Next.js, on Vercel).

## 1. The API on Cloud Run

```powershell
copy deploy.env.example.yaml deploy.env.yaml
notepad deploy.env.yaml          # READER_DATABASE_URL and GROQ_API_KEY: the same values as in .env
gcloud run deploy tally --source . --region us-west1 --allow-unauthenticated `
  --memory 512Mi --cpu 1 --min-instances 0 --max-instances 2 --concurrency 20 --timeout 60 `
  --cpu-boost --env-vars-file deploy.env.yaml
```

It ends with a Service URL, e.g. `https://tally-XXXX.us-west1.run.app`. Check `<that URL>/health` says `{"status":"ok"}`.

| Option | Why |
| --- | --- |
| `--memory 512Mi` | The API only builds queries and reads results; no OCR or embeddings like the other projects. |
| `--min-instances 0` | Free when nobody's using it; the first question after a quiet spell takes a few extra seconds. |
| `--max-instances 2` | A ceiling on cost if the demo gets busy. |
| `--timeout 60` | A question takes 2 to 10 seconds; 60 is plenty. |

## 2. The page on Vercel

1. Push the repo to GitHub (see the README).
2. Go to **vercel.com**, **Sign up with GitHub**, then **Add New → Project** and **Import** the `tally` repo.
3. **Root Directory:** click **Edit** and choose `web`. Vercel detects Next.js by itself.
4. **Environment Variables:** add `NEXT_PUBLIC_API_URL` = your Cloud Run URL from step 1 (no slash at the end).
5. Click **Deploy**. You get an address like `https://tally-xxxx.vercel.app`.

Every later `git push` redeploys the page automatically.

## 3. Let the page call the API

Browsers only let a page call an API that names the page's address. Put the Vercel address in
`deploy.env.yaml`:

```yaml
ALLOWED_ORIGINS: "https://tally-xxxx.vercel.app,http://localhost:3000"
```

and run the same `gcloud run deploy` command again. Open the Vercel address and ask a question.

## If something's wrong

| What you see | Likely cause |
| --- | --- |
| "Couldn't reach Tally's server" on the page | `NEXT_PUBLIC_API_URL` is wrong (redeploy on Vercel after fixing it), or `ALLOWED_ORIGINS` doesn't list the page's exact address. |
| "The database isn't reachable right now" | `READER_DATABASE_URL` in `deploy.env.yaml` is wrong, or the Supabase project is paused. |
| "The demo isn't set up correctly right now" | `GROQ_API_KEY` or `READER_DATABASE_URL` is missing from `deploy.env.yaml`. |
| Logs | `gcloud run services logs read tally --region us-west1 --limit 50` |
