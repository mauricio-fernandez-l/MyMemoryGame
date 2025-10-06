# My Memory Game

A customizable memory card game built with Python and Tkinter, featuring multilingual support and configurable settings.

## Features

- **Multiplayer Support**: Up to 6 players with individual scoring and avatars
- **Multilingual**: Supports German, English, and Spanish
- **Customizable**: Configure images, sounds, avatars, and UI elements
- **Sound Effects**: Optional audio feedback for matches
- **Image Gallery**: Review matched images after completing the game

## Quick Start

1. **Install Dependencies**:
   Create local environment `.venv` in the repo root folder
   ```shell
   python -m venv .venv
   ```
   and install in it the dependencies
   ```bash
   pip install pillow pyyaml python-vlc
   ```
   Install VLC on your own for .opus audio file support.

2. **Create a configuration file**:
   Creta a `config.yaml` file in this folder, see [Configuration](#configuration).

3. **Run the Game**:
   ```bash
   python memory.py
   ```

4. **Select Image Folder**: Choose a folder containing your images (PNG, JPG, GIF, BMP)
5. **Configure Players**: Set number of players, names, and avatars
6. **Start Playing**: Match pairs of cards to score points!

## Configuration

The game behavior can be customized through the `config.yaml` file:

### Key Settings

- **`language`**: Set to `"de"`, `"en"`, or `"es"`
- **`title.text`**: Custom game title
- **`title.image.path`**: Path to title image
- **`media.images.folder`**: Default image folder
- **`media.sounds.folder`**: Sound effects folder
- **`media.avatars.folder`**: Player avatars folder
- **`ui.font`**: Customize font family and sizes

### Example Configuration

```yaml
language: en
title:
  text: "My Memory Game"
  image:
    path: 'data/avatars/star.png'
    max_width: 520
    max_height: 220
shortcut:
  image: 'data/avatars/star.png'
layout:
  bottom_border_fraction: 0.1
media:
  sounds:
    folder: 'data/sounds'
  avatars:
    folder: 'data/avatars'
  images:
    folder: 'data/images'
ui:
  font:
    title:
      size: 20
      weight: bold
    emphasis:
      size: 12
      weight: bold
    body:
      size: 10
      weight: normal
```

## Desktop Shortcut

Create a Windows desktop shortcut with a custom icon:

```bash
python create_shortcut.py
```

**Requirements**:
- Windows OS
- The shortcut relies on a `.venv` locally created in the repo root folder.
- Configure `shortcut.image` path in `config.yaml` (must be PNG format)
- The script automatically converts PNG to ICO and creates the shortcut

## File Structure

```
├── memory.py           # Main game application
├── .venv/              # Python virtual environment
├── config.yaml         # Configuration file
├── create_shortcut.py  # Desktop shortcut creator
├── i18n.py            # Internationalization module
└── locale/            # Translation files
    ├── de.yaml        # German translations
    ├── en.yaml        # English translations
    └── es.yaml        # Spanish translations
```

## Controls

- **Click cards** to flip them
- **Match pairs** to score points
- **Review Gallery** button appears after game completion
- **Menu navigation** for settings and player configuration

## Tips

- Organize images in subfolders for better management
- Use square images for best card appearance
- Enable sounds for enhanced gameplay experience
- Customize player avatars for personalization
