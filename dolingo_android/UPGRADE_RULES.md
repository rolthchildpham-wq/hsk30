# In-place Android updates for Dolingo

Android accepts an APK as an update only if:
1. Application ID is unchanged: `org.dolingo.study.dolingohskfix`.
2. Signing certificate is identical to the already-installed app.
3. New `android.numeric_version` (versionCode) is not lower than the installed one. Always increment it.

Dolingo's existing GitHub Actions workflow uses `buildozer android debug`, which by default signs APKs with a *runner-specific debug key*. A new GitHub runner may use a different key. **The repository alone cannot recover the key that signed a previously installed APK.** The same package name and a larger versionCode are necessary but insufficient.

## Set up persistent debug signing for future updates
1. Locate the **original** `debug.keystore` used to sign the app currently installed on your device. If it is unavailable, you cannot guarantee updating that existing installation in place.
2. Do not commit or upload the keystore in a public repository.
3. Convert it locally to a single-line Base64 string, e.g. `base64 -w0 debug.keystore` on Linux or `[Convert]::ToBase64String([IO.File]::ReadAllBytes("debug.keystore"))` in PowerShell.
4. In GitHub repo **Settings > Secrets and variables > Actions**, create a repository secret named `DOLINGO_DEBUG_KEYSTORE_BASE64` with that value.
5. New CI runs restore this keystore into `~/.android/debug.keystore` before Buildozer creates the APK. This expects Android's standard debug keystore alias `androiddebugkey` and password `android`. Other signing keys require a release-signing workflow.
6. Inspect the APK signing certificate on the Android device and new APK, using `apksigner verify --print-certs dolingo.apk`; matching SHA-256 fingerprints are required. You can query an installed APK's signing certificate using Android tooling when available.
7. Install the signed update on top of the existing app; do NOT uninstall the current app.

## Important
When the secret is missing, GitHub Actions emits a warning and publishes a **test build**, not an APK guaranteed to update previous installs. Such an APK may fail with `INSTALL_FAILED_UPDATE_INCOMPATIBLE`. Preserve the original app's data before attempting any migration.

Never change `package.domain` or `package.name` for this app. Increment `version` and `android.numeric_version` for each release. Keep `user_data_dir/progress.json` compatible.
