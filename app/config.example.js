/*
 * Camera PiP configuration. Copy this file to config.js (git-ignored) and edit.
 *
 * server  - go2rtc base URL, as the TV reaches it (no trailing slash needed).
 * cameras - one entry per go2rtc stream that outputs MJPEG; CH +/- cycles them.
 * size    - default size: "s" 480x270, "m" 640x360, "l" 960x540, "full".
 * corner  - default corner: "tl", "tr", "bl", "br".
 * timeout - seconds until it closes by itself; 0 = stays open until Back.
 *
 * Size, corner and camera changes made with the remote are remembered on the TV
 * and override the defaults here.
 */
window.CAMPIP_CONFIG = {
  server: 'http://192.168.1.10:1984',
  cameras: [
    { name: 'Front door', src: 'front_door_mjpeg' }
  ],
  size: 'm',
  corner: 'br',
  timeout: 0
};
