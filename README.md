# Camera PiP for LG webOS

A tiny homebrew app for rooted LG webOS TVs that shows a live camera feed in a corner of the screen,
**on top of whatever is playing** — Netflix, an HDMI input, live TV. Press a remote button, glance at the
baby monitor or the front door, press it again to dismiss.

```
camera (RTSP/RTSPS) ──► go2rtc ──MJPEG over HTTP──► Camera PiP (overlay window on the TV)
```

- **Overlay window.** The app uses webOS's transparent `overlay` window type, so the programme underneath
  keeps playing and stays visible around the picture.
- **No video decoder needed.** The feed arrives as MJPEG and is drawn by a plain `<img>`. A `<video>`
  element would ask webOS for a hardware decoder, and the one the programme underneath is using is not
  the app's to take. JPEG frames are drawn by the browser like any other image.
- **Watchdog.** An `<img>` gives no error when a multipart stream dies mid-way — it just goes blank or
  keeps showing the last frame. The app samples the picture every 2 s and reconnects (with a visible
  "reconnecting…" message) when it goes blank, stops changing for 10 s, or never starts.
- **Toggle.** Launching the app again while it is open closes it, so one remote button opens and closes it.

## Requirements

- An LG TV running webOS, **rooted** with the [Homebrew Channel](https://github.com/webosbrew/webos-homebrew-channel)
  installed, and its telnet root shell enabled (used by `scripts/install.sh`). Developed on a 2022 C2 (webOS 22).
- [go2rtc](https://github.com/AlexxIT/go2rtc) somewhere the TV can reach, serving each camera as MJPEG.
- Python 3 on the machine you build and install from. No webOS SDK needed.
- Optional: [Glasshouse](https://github.com/rorygallagher2024/glasshouse) to bind the app to a remote
  button, and/or Home Assistant to open it from automations.

## Setup

### 1. go2rtc

Add an MJPEG stream per camera next to the camera's normal stream. Transcoding only runs while the app is open.

```yaml
streams:
  front_door: rtsp://user:pass@192.168.1.20:554/stream1
  # Downscaled MJPEG for the TV: 960 px wide is plenty for a 640x360 picture-in-picture.
  front_door_mjpeg: "ffmpeg:front_door#video=mjpeg#width=960#raw=-r 12 -q:v 6"
```

For UniFi Protect, enable an RTSPS stream on the camera (Settings → Advanced → RTSPS) and use go2rtc's
`rtspx://` scheme with the `?enableSrtp` suffix removed: `rtspx://<nvr-ip>:7441/<alias>`.

Check it in a browser: `http://<go2rtc-host>:1984/api/stream.mjpeg?src=front_door_mjpeg`.

### 2. Configure

```sh
cp app/config.example.js app/config.js     # git-ignored
```

```js
window.CAMPIP_CONFIG = {
  server: 'http://192.168.1.10:1984',                         // go2rtc, as the TV reaches it
  cameras: [{ name: 'Front door', src: 'front_door_mjpeg' }], // CH +/- cycles through these
  size: 'm',        // s 480x270 · m 640x360 · l 960x540 · full
  corner: 'br',     // tl · tr · bl · br
  timeout: 0        // seconds until it closes by itself; 0 = stays until Back
};
```

### 3. Build and install

```sh
scripts/install.sh <tv-ip>
```

This builds `dist/<id>_<version>_all.ipk` (`scripts/build-ipk.py`, no SDK) and installs it through the
TV's own installer (`com.webos.appInstallService/dev/install`), sending the package over the telnet
shell. To only build, run `python3 scripts/build-ipk.py`; the `.ipk` can also be installed with
`ares-install` or the Homebrew Channel.

### 4. Bind a button

- **Glasshouse:** Apps → Remote keys → point a button at **Camera PiP**.
- **Home Assistant:** any way of launching an app works, e.g. Glasshouse's *Launch App* select
  (`select.select_option` with option `Camera PiP`), triggered from a remote-button event. Launching it
  again closes it.

## Using it

| Key | Action |
|---|---|
| OK / Magic Remote click | Cycle size: S → M → L → full screen |
| ◀ ▲ ▼ ▶ | Move to that corner |
| CH + / CH − | Next / previous camera (when more than one is configured) |
| Back | Close |
| Launching it again | Close |

Size, corner and camera choices are remembered on the TV.

While it is open the overlay has the remote's focus — that is how webOS overlay windows work — so the app
underneath doesn't get key presses until you press Back.

### Launch parameters

Open it with options, e.g. from an automation when motion is detected:

```sh
luna-send -n 1 luna://com.webos.applicationManager/launch \
  '{"id":"com.homelab.campip","params":{"camera":"front_door_mjpeg","size":"l","corner":"tr","timeout":30}}'
```

| Param | Meaning |
|---|---|
| `camera` | Camera `src` or `name` from the config, or its index |
| `size` | `s`, `m`, `l`, `full` |
| `corner` | `tl`, `tr`, `bl`, `br` |
| `timeout` | Close after this many seconds unless a key is pressed |

A launch with parameters while it is open re-applies them; a launch without parameters closes it.

## Development

Open the app in a desktop browser against your go2rtc:

```sh
cd app && python3 -m http.server 8000
# http://localhost:8000/index.html?server=http://<go2rtc-host>:1984
```

In a desktop browser the frozen-picture check only works if go2rtc sends CORS headers
(`api: { origin: "*" }`); otherwise only a dropped stream is detected. On the TV this doesn't matter:
webOS doesn't apply CORS to apps loaded from `file://`.

`scripts/tvshell.py <tv-ip> '<command>'` runs a command in the TV's root shell and prints the output.

## Security notes

- go2rtc's API has **no authentication** by default. Anyone who can reach it can watch the cameras and
  change its configuration. Keep it on a trusted LAN, never port-forward it, and think twice before
  setting `origin: "*"` on a go2rtc that a browser on the same network could be tricked into calling.
- The Homebrew Channel's telnet shell is an unauthenticated **root** shell on the TV. Same advice.

## Limitations

- No audio (MJPEG is video only).
- The overlay holds the remote's focus while it is open (see above).
- `config.js` is baked into the package, so changing it means rebuilding and reinstalling.

## License

[MIT](LICENSE)
