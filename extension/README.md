# Custos Quick Capture Browser Extension

A browser extension for capturing context from any browser tab to your Custos backend.

## Features

- **Quick Capture**: Capture notes from any browser tab without switching apps
- **Secure Connection**: Connect to your local Custos instance via API key
- **Connection Status**: Visual indicator shows connection health
- **Keyboard Shortcut**: Press Ctrl/Cmd + Enter to submit captures quickly

## Installation

### Chrome

1. Open Chrome and navigate to `chrome://extensions/`
2. Enable "Developer mode" in the top right
3. Click "Load unpacked"
4. Select the `extension` directory from your Custos installation

### Firefox

1. Open Firefox and navigate to `about:debugging#/runtime/this-firefox`
2. Click "Load Temporary Add-on..."
3. Select the `manifest.json` file from the `extension` directory

**Note**: Firefox temporary add-ons are removed when Firefox closes. For persistent installation, the extension needs to be signed.

## Configuration

1. Click the Custos icon in your browser toolbar
2. Click "Open Settings" or the Settings link in the footer
3. Enter your Custos backend URL (e.g., `http://localhost:8000`)
4. Enter your API key if authentication is enabled
5. Click "Test Connection" to verify
6. Click "Save Settings"

## Usage

1. Click the Custos icon in your browser toolbar
2. Enter your notes in the text area
3. Select the capture type (Notes, Transcript, Observation)
4. Click "Capture" or press Ctrl/Cmd + Enter

## Development

### Directory Structure

```
extension/
├── manifest.json          # Extension manifest (MV3)
├── popup/
│   ├── popup.html         # Popup UI
│   ├── popup.js           # Popup logic
│   └── popup.css          # Popup styles
├── options/
│   ├── options.html       # Settings page
│   ├── options.js         # Settings logic
│   └── options.css        # Settings styles
├── background/
│   └── service-worker.js  # Background tasks
└── icons/
    ├── icon16.png         # Toolbar icon (16x16)
    ├── icon48.png         # Extension page (48x48)
    └── icon128.png        # Chrome Web Store (128x128)
```

### Creating Icons

Before loading the extension, create icon files:

```bash
# Using ImageMagick
convert -size 16x16 xc:#2563eb icons/icon16.png
convert -size 48x48 xc:#2563eb icons/icon48.png
convert -size 128x128 xc:#2563eb icons/icon128.png
```

Or use any image editor to create PNG files with the Custos logo.

### Testing

1. Make changes to the source files
2. Go to `chrome://extensions/`
3. Click the refresh icon on the Custos extension card
4. Test your changes

## Security

- API keys are stored in Chrome's sync storage (encrypted at rest)
- All communication with the Custos backend uses the configured URL
- No data is sent to any third-party servers

## Troubleshooting

### "Cannot connect to backend"

- Verify Custos is running (`curl http://localhost:8000/api/health`)
- Check the URL in settings matches your Custos instance
- Ensure no firewall is blocking the connection

### "Authentication failed"

- Verify your API key is correct
- Check if `CUSTOS_API_KEY` is set on your Custos instance

### Extension icon not visible

- Click the puzzle piece icon in Chrome toolbar
- Pin the Custos Quick Capture extension

## License

Part of Custos Core - MIT License
