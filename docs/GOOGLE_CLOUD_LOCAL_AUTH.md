# Google Cloud local authentication

Use the supported Google Cloud CLI credential store for local human management work. It lives in the user's gcloud configuration directory (normally `~/.config/gcloud` on macOS) and is reused by later CLI processes. Do not put credentials in this repository, `.env` files, shell history, or project scripts.

## Verify or renew CLI access

From the repository root, run:

```sh
./scripts/ensure_gcloud_auth.sh
```

The helper checks the active DTD management account, makes a read-only project lookup against `dogtrainersdirectory-dev`, and starts `gcloud auth login admin@dogtrainersdirectory.com.au` only if the account is wrong or that scoped read shows saved credentials need renewal. It does not use `--force`, change IAM, or alter a gcloud project setting. The scoped lookup both refreshes credentials and verifies that access to the intended sandbox works. Run it before a local workflow when CLI access may have gone stale.

Google controls credential validity. Stored CLI credentials are reused until they expire or are revoked, so no project setting can guarantee that Google will never ask for sign-in or owner verification again. When that happens, complete the official browser/password/MFA prompt in the trusted local flow; never provide a password or verification code to a script or chat.

## Google SDKs and Application Default Credentials

Google client libraries use Application Default Credentials (ADC), a credential store separate from `gcloud auth login`. Production DTD workloads use their attached least-privilege service identity; local CLI login is not a runtime credential and must not be copied into a deployment.

Only when a local SDK workflow actually needs user ADC, set it up separately with the official command:

```sh
gcloud auth application-default login
```

SDK libraries then discover the local ADC file automatically. Do not assume that a successful `gcloud auth login` proves ADC works, and do not overwrite ADC as a side effect of the CLI helper. Keep SDK checks scoped to the development project and use a read-only API operation before claiming SDK access is verified.

## Official references

- [Authenticate for the gcloud CLI](https://docs.cloud.google.com/sdk/docs/authenticate)
- [gcloud auth login reference](https://docs.cloud.google.com/sdk/gcloud/reference/auth/login)
- [How Application Default Credentials works](https://docs.cloud.google.com/docs/authentication/application-default-credentials)
