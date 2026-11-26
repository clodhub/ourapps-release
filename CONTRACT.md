# Ourapps release component

## Purpose and facilities
The release side of an application. It renders GitHub Actions workflows and build scripts for the enabled client targets (web, Android, iPhone and iPad, Mac, Apple TV, Windows) and ships the scripts those workflows run: the store's per-target switches read fail-closed and merged into the manifest (a switched-off target keeps the previous release's entry), the application manifest (`my-app.json`, schema 1) built and validated, verified direct Mac and Windows packages checked against their metadata, Apple archive and export checks, Windows installer evidence, and the publisher that creates a draft GitHub Release, uploads every asset and makes the manifest the last upload before the draft goes public.

Facilities: `release-pipeline` (Build, sign and publish client targets to ourapps.app).

## User inputs
The installer collects `targets` (required; any of `ios`, `android`, `web`, `macos`, `windows`, `tvos`, separated by spaces: the targets the pipeline builds), `applicationId` (required; a short lower-case name, letters, digits and hyphens, such as `ourpoker`, used for file and worker names), `applicationName` (required; the name in the store listing and on the release, such as `OurPoker`), `bundleIdentifier` (required for Apple targets), `storeAddress` (the store's address, default `https://ourapps.app`), `repository` (the application's repository, `https://github.com/<owner>/<name>`) and `manifestUrl` (where the store reads `my-app.json`: the repository's latest release, `https://api.github.com/repos/<owner>/<name>/releases/latest`). Four settings are reference names, never values (letters, digits and hyphens; default `none`, which is unset): `storeCredentials` (repository secrets `<NAME>_APP_ID` and `<NAME>_BUILD_TOKEN`; without them the pipeline makes no store call: every target the pipeline builds is on, there is no iPhone build, TestFlight upload or Apple TestFlight run, and the release still publishes to GitHub with `STORE_MODE: "none"`), `androidSigning` (`<NAME>_KEYSTORE_BASE64`, `_KEYSTORE_PASSWORD`, `_KEY_ALIAS`, `_KEY_PASSWORD`), `webDeploy` (Cloudflare hosting for the web build: `<NAME>_API_TOKEN`, `<NAME>_ACCOUNT_ID`) and `hostingAccount` (the Cloudflare account the server deploys to: `<NAME>_API_TOKEN`, `<NAME>_ACCOUNT_ID`). A reference such as `demo-android-signing` names the secrets `DEMO_ANDROID_SIGNING_...`; the repository's secret store holds the values. They are plain settings because a template cannot render a secret setting.

- `targets` (string, label; required)
- `applicationId` (string, slug; required)
- `applicationName` (string, label; required)
- `storeAddress` (string, address; optional; default `https://ourapps.app`)
- `manifestUrl` (string, address; optional)
- `repository` (string, address; optional)
- `storeCredentials` (string, slug; optional; default `none`; a reference name, never a value)
- `bundleIdentifier` (string, qualified; optional)
- `androidSigning` (string, slug; optional; default `none`; a reference name, never a value)
- `webDeploy` (string, slug; optional; default `none`; a reference name, never a value)
- `hostingAccount` (string, slug; optional; default `none`; a reference name, never a value)

## Artefacts and dependencies
`component.json` maps every `implementation/` source into `components/ourapps-release/`:

- `implementation/server/render.ts` -> `components/ourapps-release/server/render.ts`
- `implementation/server/release.json` -> `components/ourapps-release/server/release.json` (template: clod renders the settings into it at install)
- `implementation/server/scripts/clod_update.py` -> `components/ourapps-release/server/scripts/clod_update.py`
- `implementation/server/scripts/android_screen.py` -> `components/ourapps-release/server/scripts/android_screen.py`
- `implementation/server/scripts/app_manifest.py` -> `components/ourapps-release/server/scripts/app_manifest.py`
- `implementation/server/scripts/platform_artifacts.py` -> `components/ourapps-release/server/scripts/platform_artifacts.py`
- `implementation/server/scripts/platform_manifest.py` -> `components/ourapps-release/server/scripts/platform_manifest.py`
- `implementation/server/scripts/publish_release.py` -> `components/ourapps-release/server/scripts/publish_release.py`
- `implementation/server/scripts/release_plan.py` -> `components/ourapps-release/server/scripts/release_plan.py`
- `implementation/server/scripts/release_targets.py` -> `components/ourapps-release/server/scripts/release_targets.py`
- `implementation/server/templates/scripts/build-apple-testflight.sh.template` -> `components/ourapps-release/server/templates/scripts/build-apple-testflight.sh.template`
- `implementation/server/templates/scripts/build-windows.sh.template` -> `components/ourapps-release/server/templates/scripts/build-windows.sh.template`
- `implementation/server/templates/scripts/inspect-windows.ps1.template` -> `components/ourapps-release/server/templates/scripts/inspect-windows.ps1.template`
- `implementation/server/templates/workflows/clod-update.yml.template` -> `components/ourapps-release/server/templates/workflows/clod-update.yml.template`
- `implementation/server/templates/workflows/apple-builds.yml.template` -> `components/ourapps-release/server/templates/workflows/apple-builds.yml.template`
- `implementation/server/templates/workflows/apple-testflight.yml.template` -> `components/ourapps-release/server/templates/workflows/apple-testflight.yml.template`
- `implementation/server/templates/workflows/ci-android.yml.template` -> `components/ourapps-release/server/templates/workflows/ci-android.yml.template`
- `implementation/server/templates/workflows/ci-server.yml.template` -> `components/ourapps-release/server/templates/workflows/ci-server.yml.template`
- `implementation/server/templates/workflows/ci-web.yml.template` -> `components/ourapps-release/server/templates/workflows/ci-web.yml.template`
- `implementation/server/templates/workflows/platform-packages.yml.template` -> `components/ourapps-release/server/templates/workflows/platform-packages.yml.template`
- `implementation/server/templates/workflows/release.yml.template` -> `components/ourapps-release/server/templates/workflows/release.yml.template`

Dependencies: none.
`tools.lock.json` pins verification tools: node 26.5, python3 3.12. Licence wording remains deferred.

## Provided interfaces
- `interfaces/release-pipeline.json` defines `release-pipeline` (com.clodhub/release-pipeline) version 1.0.0 as an OpenRPC 1.3.2 document. Methods tagged `typescript` are the build-time functions of `server/render.ts` (`renderRelease`, `writeRelease`, `validateSettings`, `parseTargets`, `secretName`); methods tagged `command` are the subcommands of the Python scripts the workflows run (`release_plan.py`, `release_targets.py read`, `app_manifest.py build`, `publish_release.py` and the others), with command-line arguments as parameters and the exit status as result. Settings, render result, `release/app.json`, the store's target switches and `my-app.json` are JSON Schema 2020-12 under `components.schemas`.

## Required interfaces
None.

## Integration
At build time call `renderRelease(settings, options)` from `server/render.ts` and write the result with `writeRelease` into the application repository: `.github/workflows/*.yml`, `scripts/*` and `release/app.json`. The shipped Python scripts install under `components/ourapps-release/server/scripts/` and are what the workflows call. `options` names the application's directories (web, android, desktop, Apple), the Node and Java versions, runners, the icon, screenshots, changelog, extra manifest fields (for example `minPlayers`) and the signing prefix, which must equal the Android and Apple hosts' prefix. `result.notes` lists what the rendered files expect the repository to provide. The web build comes from web-host, the Android project from android-host, the Apple project from apple-host, the Windows package from windows-desktop and the server check from server-host; this component names them only through directories and environment variable prefixes. `examples/consumer.ts` renders a pipeline without a game. At install clod renders `components/ourapps-release/server/release.json` from the settings (application id and name, targets, store address and the four reference names); in the application's release workflow `release_plan.py` reads it and gives the version, the targets to build and the repository secret name of each reference. clod places only the recipe's own files outside `components/<name>/`, so a recipe that installs workflows at the application root ships them itself and has them call these scripts; `renderRelease` writes a set from the templates at build time instead.

The check workflows can each be started by hand. With `serverDirectory`, `ci-web.yml` starts the server on the runner, builds the web client against it and runs the application's `test/browser.mjs` in headless Chrome when the web folder has one; with `androidCheck` too, `ci-android.yml` builds the debug app against the runner's server (`http://10.0.2.2:8788`), starts it in an Android 36 emulator (KVM) and runs `android_screen.py` until the given text is on screen. `renderMaintenance(settings, options)` renders two more workflows outside the release pipeline's files: `apple-builds.yml` (unsigned iOS Simulator, Mac Catalyst and tvOS Simulator builds by Apple target on GitHub's Xcode 27 image, on a version tag or by hand; options `appleBuildRunner` (default `xcode-27`; the `macos-26` image carries Xcode 26 only), `xcodeVersion`, `appleProject`, `appleScheme`, `appleTvScheme`) and `clod-update.yml`, which weekly runs `clod_update.py run`: it follows the update policy in `.clod/definition.json` channel by channel, security first, then features, then preview; `auto` proposes, approves with `CLOD_OWNER_KEY`, applies and commits in one run when every check passes, `manual` opens the pull request described next, and `hold` does nothing. By hand with optional `version` and `answers` (a JSON object of answer changes) inputs it runs `clod_update.py propose` (the newest or given recipe version designed with the answers and substitutions in `.clod/definition.json` and the given changes; nothing when neither the version nor an answer changes; proposed with `--trusted --allow-network`, opened as a pull request carrying `.clod/update/definition.json` and `summary.md`) and, when that pull request is merged, `clod_update.py apply` (proposed again, approved with the owner's private key from the `CLOD_OWNER_KEY` repository secret, applied and committed to main). Pull requests need the repository setting that lets GitHub Actions create them, or the optional `CLOD_PUSH_TOKEN` secret (a fine-grained token with Contents, Pull requests and Workflows write), which then pushes and opens them; GitHub refuses a push with the workflow's own token that changes `.github/workflows/`, so an update that changes a workflow is committed only with `CLOD_PUSH_TOKEN`, and without it the apply job stops naming those files.

## Visual definition and connected examples
`visual/definition.json` maps its ports to the provided and required interfaces. `visual/examples/connected.json` connects the component to an illustrative application consumer. Both image formats and a text description are in `visual/output/`.

## Infrastructure
Everything runs in the application's GitHub Actions on the runners named in the options (Ubuntu for web, Android, publishing; macOS for iOS, Mac and Apple TV; Windows for the Windows installer). When store credentials are set, the store at `storeAddress` is read for target switches and signing, and receives TestFlight uploads; it reads `my-app.json` from the GitHub Release. Without them the store is never called. GitHub Actions minutes, macOS runner minutes and store terms were not checked and no cost is stated.

## Verification
`node --test tests/release.test.ts` renders every target combination and checks the workflows (jobs, needs, guard order, secrets only as names, options refused when unsafe), parses them as YAML when PyYAML is installed, runs actionlint on them when it is installed (the maintenance workflows and an `androidCheck` included), checks that every check workflow can be started by hand, runs `bash -n` on the scripts, builds a manifest from the rendered application description, and runs `tests/test_release.py`: the store's switches against a local stand-in server (including refused redirects and malformed answers), manifest merging, manifest building and validation, verified package checks, Apple export and archive checks with stand-in `xcrun` and `codesign`, Windows installer evidence from a synthetic executable header, and the publisher end to end with a stand-in `gh` (switched-off targets, switches changing during the run, first release, draft removal, upload order). Without store credentials the suite renders the whole target set and checks that no file names a store secret, address, route or TestFlight step, that the workflows parse and have the expected jobs, and runs the target reader and publisher with `STORE_MODE=none` against the stand-in server, which must see no request. Real GitHub Actions runs, a real store, `gh`, signing, notarization, TestFlight and the Apple, Windows and Android builds were not exercised, and `installer-certificate` (needs `openssl`) is untested.

- `node --test tests/release.test.ts` (release, required-local; tools: node 26.5, python3 3.12)

## Scenarios and presentation
A web-only application renders a release workflow with only the version, web and publish jobs; adding Android adds its signing secrets and job. An application with no store account leaves `storeCredentials` unset: the release builds Android and web from the pipeline targets and publishes to GitHub, and iPhone, Mac and Apple TV signed uploads are not rendered (unsigned Mac and Apple TV evidence is). A store owner switches Android off: the next release keeps the last APK entry in the manifest. Everything is switched off during a run: the draft release is deleted and nothing is published. A verified Windows package is uploaded and listed only when its target is switched on.

## Updates and removal
Patch updates replace the owned files; render the pipeline again after each update and review the diff, because the workflows are generated files. No application data is held; the manifest of the previous release is read from GitHub at publish time. Removal deletes the owned sources; the rendered workflows and scripts in the application repository remain until the owner deletes them.
