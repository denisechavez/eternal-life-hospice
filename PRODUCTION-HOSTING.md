# Production hosting map

Verified on 2026-08-26. This is a discovery record only; no DNS, custom-domain,
deployment, or production configuration was changed.

## Authoritative production path

| Item | Confirmed value |
| --- | --- |
| Public URL | `https://eternallifehospice.com` |
| Public IPv4 | `34.111.179.208` |
| Hosting owner | This Replit project, not a separately managed Eternal Life Hospice Google Cloud project |
| Replit project ID | `e1b2f643-7869-4565-af0e-10c34575ee8d` |
| Deployment type | Replit Autoscale, public, with a successful active build |
| Generated production URL | `https://eternal-life-hospice.replit.app` |
| Replit deployment ID | `cd913248-33e7-4d6e-8881-2602bfae082a` |
| Serving resource | Replit-managed Google Cloud Run service `d-cd913248-33e7-4d6e-8881-2602bfae082a-hrjr7zshoa-ue.a.run.app` |
| Google Cloud project | Replit's provider-managed platform project. Its internal GCP project ID is not exposed to this workspace and is not an ELH-controlled project. |
| Production run command | `python3 website/devserver.py`, through the `.replit` Autoscale deployment configuration |

The custom domain and the generated `replit.app` URL return byte-identical
homepage responses. The live HTML also carries the same Replit project and
deployment IDs listed above. A request to `/_ah/warmup` exposes the private
`a.run.app` service hostname; direct requests to that hostname are forbidden,
which is consistent with Replit's managed ingress.

## Source and release mechanism

| Item | Confirmed value |
| --- | --- |
| Source repository | `https://github.com/denisechavez/eternal-life-hospice.git` |
| Branch at the active publish | `fix/content-reorg` |
| Source revision captured for the active publish | `b5a9ec5fa9140e1ea724aca359cb7835f2a7db5f` |
| Replit publication marker | `4344de405d731b33906084946c6cf9af51955d25` |
| Replit build ID | `cc0eb12d-d235-4655-a748-4e90fea56a67` |
| Deployment mechanism | A user-initiated Replit Publish creates a snapshot of the current workspace files and releases it as an Autoscale deployment. It is not a branch-triggered Google Cloud or Netlify build. |
| Operational owner | The Eternal Life Hospice Replit project owner/collaborators control publishing. Replit owns and operates the underlying Google Cloud infrastructure. |

The branch name documents the Git state that contained the active publication,
but Replit publishes a workspace snapshot rather than continuously deploying a
Git branch. Pushing to GitHub or syncing a branch alone does not update this
production deployment.

## Netlify status

The repository still contains Netlify configuration for
`website/elh-preview/`, but Netlify is not serving the public domain. Treat it
as a parallel deployment path unless and until hosting is intentionally
consolidated. Do not infer production status from a successful Netlify build.

## Evidence collected

- DNS resolution: both the apex and `www` host resolve to `34.111.179.208`.
- Live headers: `server: Google Frontend`, `via: 1.1 google`, and
  `x-cloud-trace-context`.
- Replit deployment service: active, healthy, public Autoscale deployment;
  primary URL is the custom domain and the generated URL is additional.
- Generated URL and custom domain: identical homepage SHA-256.
- Live and repository content: homepage is identical except for Replit's
  injected feedback-widget script; `robots.txt` and `sitemap.xml` are exact
  matches.
- Git history: the active publish marker and build ID are on
  `fix/content-reorg`; the marker has the same tree as its source revision.
- Google Cloud CLI: no ELH Google Cloud account or project is configured in
  this workspace.
