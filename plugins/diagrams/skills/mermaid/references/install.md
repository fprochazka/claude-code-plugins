# Installing `mmdc`

Everything here is a proposal for the user. Never run an install unasked.

## The tool

```bash
npm install -g @mermaid-js/mermaid-cli
command -v mmdc && mmdc --version
```

`@mermaid-js/mermaid-cli` provides the `mmdc` binary. Version 11.17.0 is current.

## When `command -v mmdc` still finds nothing

1. Print the global prefix: `npm prefix -g`.
2. Check that `<prefix>/bin` is on `PATH`.
3. If it is not, propose the exact line for the user's shell profile: `export PATH="<prefix>/bin:$PATH"`.

Under `nvm`, `fnm` or `volta` the binary is installed for one node version only. A shell that selects a different version does not see it. Propose a shell reload first, then the version check (`node --version` in the shell that fails against the one that installed it).

## Do not fall back to `npx`

`npx --no-install @mermaid-js/mermaid-cli mmdc` runs from the npx cache, so a machine can render a diagram while `mmdc` is absent from `PATH`. That is why the check is `command -v mmdc` and not "does npx work": the cache is not an installation, it is evicted without warning, and the validator subagent's command line is plain `mmdc`.

## Chromium

`mmdc` renders in a real browser. Puppeteer is a peer dependency and downloads a Chromium of roughly 300 to 500 MB during the install. To reuse a Chromium that is already on the machine, set `PUPPETEER_SKIP_DOWNLOAD=1` before installing and point at the system binary in a puppeteer config file.

The launch fails on several common setups — as root, in a container, and on any distro that restricts unprivileged user namespaces through AppArmor (Ubuntu 23.10 and later, among others). The error names the cause:

```
Error: Failed to launch the browser process!
[FATAL:zygote_host_impl_linux.cc] No usable sandbox!
```

The fix is a puppeteer config file passed with `-p`:

```json
{ "args": ["--no-sandbox", "--disable-dev-shm-usage"] }
```

```bash
mmdc -p puppeteer-config.json -i diagram.mmd -o diagram.png -s 2
```

Add `"executablePath": "/usr/bin/chromium"` to that file to use a system Chromium instead of the downloaded one.

## Docker instead of an install

The published image carries Chromium and a no-sandbox puppeteer config in its entrypoint, with `/data` as the working directory:

```bash
docker run --rm -v "$PWD:/data" ghcr.io/mermaid-js/mermaid-cli/mermaid-cli -i /data/diagram.mmd -o /data/diagram.png -s 2
```

This costs one image pull and no npm state. It needs a wrapper script or an alias named `mmdc` on `PATH` before the validator subagent can use it.
