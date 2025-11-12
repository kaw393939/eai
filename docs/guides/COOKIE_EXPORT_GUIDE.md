# How to Export YouTube Cookies from Safari

## Quick Method: Use Developer Console + Script

1. Open Safari and go to **https://www.youtube.com**
2. Make sure you're logged in with your YouTube Premium account
3. Open Developer Console: **Develop → Show Web Inspector** (Cmd+Option+I)
4. Click the **Console** tab
5. Paste this JavaScript code and press Enter:

```javascript
// Export cookies in Netscape format
var cookies = document.cookie.split(";");
var netscapeCookies =
  "# Netscape HTTP Cookie File\n# This is a generated file! Do not edit.\n\n";

cookies.forEach(function (cookie) {
  var parts = cookie.trim().split("=");
  var name = parts[0];
  var value = parts.slice(1).join("=");

  // YouTube cookie format for Netscape
  netscapeCookies +=
    ".youtube.com\tTRUE\t/\tTRUE\t0\t" + name + "\t" + value + "\n";
});

console.log(netscapeCookies);
```

6. Copy the output (it will look like this):

```
# Netscape HTTP Cookie File
.youtube.com TRUE / TRUE 0 CONSENT YES+...
.youtube.com TRUE / TRUE 0 VISITOR_INFO1_LIVE ...
```

7. Save to a file: `/Users/kwilliams/Desktop/218hosting/cli/youtube_cookies.txt`

## Then use the cookies file:

```bash
cd /Users/kwilliams/Desktop/218hosting/cli
python -m ei_cli.cli.commands.transcribe_video \
  "https://youtu.be/-aT3Uh1hyis" \
  -f text \
  -o ../workflow_outputs/google_ai_video_transcript.txt \
  --cookies-file youtube_cookies.txt
```

## Alternative: Use Chrome (Easier)

If you also have Chrome with YouTube logged in:

1. Grant Terminal Full Disk Access (see above)
2. Use: `--cookies-from-browser chrome`

Chrome's cookie access doesn't require as many permissions as Safari.
