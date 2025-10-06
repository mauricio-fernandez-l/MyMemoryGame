import copy
import math
import os
import random
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk, ImageOps
from pathlib import Path
import yaml

from i18n import I18n

try:
    import winsound
except ImportError:
    winsound = None

try:
    import vlc
except Exception:
    vlc = None


BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.yaml"

DEFAULT_CONFIG = {
    "language": "de",
    "title": {
        "text": "Memory-Spiel",
        "image": {
            "path": "",
            "max_width": 520,
            "max_height": 220,
        },
    },
    "layout": {
        "bottom_border_fraction": 0.1,
    },
    "ui": {
        "font": {
            "family": "Helvetica",
            "title": {
                "size": 24,
                "weight": "bold",
            },
            "emphasis": {
                "size": 14,
                "weight": "bold",
            },
            "body": {
                "size": 12,
                "weight": "normal",
            },
        },
    },
    "media": {
        "sounds": {
            "folder": "data/sounds",
            "extensions": [".opus", ".wav"],
        },
        "avatars": {
            "folder": "data/avatars",
            "extensions": [".png", ".jpg", ".jpeg"],
        },
        "images": {
            "folder": "data/images",
        },
    },
}


def _deep_merge(base, override):
    result = copy.deepcopy(base)
    for key, value in override.items():
        if value is None:
            continue
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _resolve_folder(path_value):
    if not path_value:
        return ""
    candidate = Path(path_value)
    if not candidate.is_absolute():
        candidate = BASE_DIR / candidate
    return str(candidate)


def _normalize_extensions(values, fallback):
    if not values:
        return list(fallback)
    if isinstance(values, str):
        values = [values]
    normalized = []
    for item in values:
        if not item:
            continue
        ext = item if item.startswith(".") else f".{item}"
        normalized.append(ext.lower())
    return normalized or list(fallback)


def _resolve_path(path_value):
    if not path_value:
        return ""
    candidate = Path(path_value)
    if not candidate.is_absolute():
        candidate = BASE_DIR / candidate
    return str(candidate)


def _list_media_files(folder, extensions=None):
    if not folder:
        return []
    try:
        base_path = Path(folder)
    except TypeError:
        return []
    if not base_path.is_dir():
        return []
    allowed = None
    if extensions:
        allowed = {ext.lower() for ext in extensions}
    files = []
    for entry in base_path.iterdir():
        if not entry.is_file():
            continue
        if allowed and entry.suffix.lower() not in allowed:
            continue
        files.append(str(entry))
    return files


def load_config(config_path=CONFIG_PATH):
    data = {}
    if config_path.exists():
        try:
            with config_path.open("r", encoding="utf-8") as cfg_file:
                data = yaml.safe_load(cfg_file) or {}
        except (yaml.YAMLError, OSError):
            data = {}

    merged = _deep_merge(DEFAULT_CONFIG, data)

    title_cfg = merged.setdefault("title", {})
    if not isinstance(title_cfg, dict):
        title_cfg = {}
        merged["title"] = title_cfg
    raw_image_cfg = title_cfg.get("image", {})
    if isinstance(raw_image_cfg, str):
        raw_image_cfg = {"path": raw_image_cfg}
    elif not isinstance(raw_image_cfg, dict):
        raw_image_cfg = {}
    title_cfg["image"] = raw_image_cfg
    image_cfg = raw_image_cfg
    image_cfg["path"] = _resolve_path(image_cfg.get("path", ""))

    layout_cfg = merged.get("layout")
    if not isinstance(layout_cfg, dict):
        layout_cfg = {}
    merged["layout"] = layout_cfg
    layout_cfg["bottom_border_fraction"] = layout_cfg.get(
        "bottom_border_fraction",
        DEFAULT_CONFIG["layout"]["bottom_border_fraction"],
    )

    ui_cfg = merged.get("ui")
    if not isinstance(ui_cfg, dict):
        ui_cfg = {}
    merged["ui"] = ui_cfg
    font_cfg = ui_cfg.get("font")
    if not isinstance(font_cfg, dict):
        font_cfg = {}
    ui_cfg["font"] = font_cfg

    default_font_cfg = DEFAULT_CONFIG["ui"]["font"]

    family = font_cfg.get("family")
    if not isinstance(family, str) or not family.strip():
        family = default_font_cfg["family"]
    font_cfg["family"] = family.strip()

    def _normalize_font_section(section_name):
        section = font_cfg.get(section_name)
        if not isinstance(section, dict):
            section = {}

        default_section = default_font_cfg.get(section_name, {})

        size_value = section.get("size", default_section.get("size"))
        try:
            size_int = int(size_value)
        except (TypeError, ValueError):
            size_int = default_section.get(
                "size", DEFAULT_CONFIG["ui"]["font"]["emphasis"]["size"]
            )
        section["size"] = max(1, size_int)

        weight_value = section.get("weight", default_section.get("weight"))
        if not isinstance(weight_value, str) or not weight_value.strip():
            weight_value = default_section.get("weight", "normal")
        section["weight"] = weight_value.strip()

        return section

    font_cfg["title"] = _normalize_font_section("title")
    font_cfg["emphasis"] = _normalize_font_section("emphasis")
    font_cfg["body"] = _normalize_font_section("body")

    media_cfg = merged.get("media")
    if not isinstance(media_cfg, dict):
        media_cfg = {}
    merged["media"] = media_cfg

    sounds_cfg = media_cfg.get("sounds")
    if not isinstance(sounds_cfg, dict):
        sounds_cfg = {}
    media_cfg["sounds"] = sounds_cfg
    sounds_folder = _resolve_folder(sounds_cfg.get("folder", ""))
    sounds_cfg["folder"] = sounds_folder
    sounds_cfg["extensions"] = _normalize_extensions(
        sounds_cfg.get("extensions"),
        DEFAULT_CONFIG["media"]["sounds"]["extensions"],
    )

    avatars_cfg = media_cfg.get("avatars")
    if not isinstance(avatars_cfg, dict):
        avatars_cfg = {}
    media_cfg["avatars"] = avatars_cfg
    avatars_folder = _resolve_folder(avatars_cfg.get("folder", ""))
    avatars_cfg["folder"] = avatars_folder
    avatars_cfg["extensions"] = _normalize_extensions(
        avatars_cfg.get("extensions"),
        DEFAULT_CONFIG["media"]["avatars"]["extensions"],
    )

    images_cfg = media_cfg.get("images")
    if not isinstance(images_cfg, dict):
        images_cfg = {}
    media_cfg["images"] = images_cfg
    images_cfg["folder"] = _resolve_folder(images_cfg.get("folder", ""))

    sounds_cfg["files"] = _list_media_files(
        sounds_cfg["folder"], sounds_cfg["extensions"]
    )

    language = merged.get("language")
    if not isinstance(language, str) or not language.strip():
        language = DEFAULT_CONFIG.get("language", "de")
    merged["language"] = language.strip().lower()

    return merged


CONFIG = load_config()

LOCALE_DIR = BASE_DIR / "locale"
I18N = I18n(LOCALE_DIR, default=DEFAULT_CONFIG.get("language", "de"))
CONFIG_LANGUAGE = CONFIG.get("language", DEFAULT_CONFIG.get("language", "de"))
I18N.set_language(CONFIG_LANGUAGE)
_ = I18N.t

TITLE_CONFIG = CONFIG.get("title", {})
TITLE = TITLE_CONFIG.get("text", DEFAULT_CONFIG["title"]["text"])
TITLE_IMAGE_CONFIG = TITLE_CONFIG.get("image", {})
TITLE_IMAGE_PATH = TITLE_IMAGE_CONFIG.get("path", "")
TITLE_IMAGE_MAX_WIDTH = TITLE_IMAGE_CONFIG.get(
    "max_width", DEFAULT_CONFIG["title"]["image"]["max_width"]
)
TITLE_IMAGE_MAX_HEIGHT = TITLE_IMAGE_CONFIG.get(
    "max_height", DEFAULT_CONFIG["title"]["image"]["max_height"]
)

LAYOUT_CONFIG = CONFIG.get("layout", {})
BOTTOM_BORDER_FRACTION = LAYOUT_CONFIG.get(
    "bottom_border_fraction", DEFAULT_CONFIG["layout"]["bottom_border_fraction"]
)

MEDIA_CONFIG = CONFIG.get("media", {})
SOUNDS_CONFIG = MEDIA_CONFIG.get("sounds", {})
SOUNDS = SOUNDS_CONFIG.get("files", [])
AVATARS_CONFIG = MEDIA_CONFIG.get("avatars", {})
AVATAR_FOLDER = AVATARS_CONFIG.get("folder", "")
AVATAR_EXTENSIONS = tuple(AVATARS_CONFIG.get("extensions", []))
IMAGES_CONFIG = MEDIA_CONFIG.get("images", {})
DEFAULT_IMAGE_FOLDER = IMAGES_CONFIG.get("folder", "")

UI_CONFIG = CONFIG.get("ui", {})
FONT_CONFIG = UI_CONFIG.get("font", DEFAULT_CONFIG["ui"]["font"])


class MemoryApp:
    PLAYER_COLORS = [
        "#ff6b6b",
        "#4ecdc4",
        "#ffe66d",
        "#5d8cf6",
        "#ff9f1c",
        "#9b5de5",
    ]

    def __init__(self, root):
        self.root = root
        self.root.title(TITLE)
        self.root.configure(bg="#1a1a1a")
        self.image_cache = {}
        self.names_window = None
        self.settings_window = None
        self.available_avatar_options = self.load_avatar_options()
        self.avatar_lookup = {
            os.path.abspath(path): name for name, path in self.available_avatar_options
        }
        self.default_avatar_path = (
            next(iter(self.avatar_lookup.keys())) if self.avatar_lookup else ""
        )
        if vlc is not None:
            try:
                self.vlc_instance = vlc.Instance()
            except Exception:
                self.vlc_instance = None
        else:
            self.vlc_instance = None
        self.vlc_player = None
        self.last_settings = {
            "players": 1,
            "folder": DEFAULT_IMAGE_FOLDER,
            "pairs": 1,
            "names": [],
            "avatars": [],
            "sound_enabled": True,
            "language": I18N.lang,
        }
        self.sound_enabled = self.last_settings.get("sound_enabled", True)
        self.language_code = self.last_settings.get("language", I18N.lang)
        default_font_cfg = DEFAULT_CONFIG["ui"]["font"]
        self.ui_font_family = FONT_CONFIG.get("family", default_font_cfg["family"])

        title_cfg = FONT_CONFIG.get("title", default_font_cfg["title"])
        emphasis_cfg = FONT_CONFIG.get("emphasis", default_font_cfg["emphasis"])
        body_cfg = FONT_CONFIG.get("body", default_font_cfg["body"])

        def _build_font_tuple(section_cfg, fallback_cfg):
            size_value = section_cfg.get("size", fallback_cfg.get("size"))
            try:
                size_int = int(size_value)
            except (TypeError, ValueError):
                size_int = fallback_cfg.get("size", 12)
            weight_value = section_cfg.get("weight", fallback_cfg.get("weight"))
            if not isinstance(weight_value, str) or not weight_value.strip():
                weight_value = fallback_cfg.get("weight", "normal")
            return (
                self.ui_font_family,
                max(1, size_int),
                weight_value.strip(),
            )

        self.ui_font_title = _build_font_tuple(
            title_cfg,
            default_font_cfg["title"],
        )

        self.ui_font_emphasis = _build_font_tuple(
            emphasis_cfg,
            default_font_cfg["emphasis"],
        )
        self.ui_font_body = _build_font_tuple(body_cfg, default_font_cfg["body"])
        self.reset_game_state()
        self.init_menu_state()
        self.build_menu()
        self.center_window()

    def reset_game_state(self):
        self.folder = ""
        self.image_paths = []
        self.num_pairs = 0
        self.num_cards = 0

        self.num_players = 1
        self.player_colors = []
        self.current_player = 0
        self.player_scores = []
        self.card_owner = {}
        self.player_names = []
        self.player_avatars = []

        self.cards = []
        self.buttons = []
        self.card_slots = []
        self.card_paths = []
        self.flipped = []
        self.matched = set()

        self.sidebar_frame = None
        self.board_frame = None
        self.board_grid = None
        self.score_frame = None
        self.player_containers = []
        self.score_labels = []
        self.score_avatar_labels = []
        self.score_avatar_images = []
        self.card_back_image = None

        self.review_button = None
        self.post_game_frame = None
        self.menu_button = None
        self.title_photo = None
        self.matched_paths = []
        self.image_summary_window = None
        self.summary_images = []
        self.sound_toggle_button = None
        self.sound_count_label = None
        self.language_button = None
        self.settings_window = None
        if getattr(self, "vlc_player", None) is not None:
            try:
                self.vlc_player.stop()
            except Exception:
                pass
            try:
                self.vlc_player.release()
            except Exception:
                pass
        self.vlc_player = None

    def load_avatar_options(self):
        options = []
        if not AVATAR_FOLDER:
            return options
        folder = Path(AVATAR_FOLDER)
        if not folder.is_dir():
            return options
        allowed = (
            {ext.lower() for ext in AVATAR_EXTENSIONS} if AVATAR_EXTENSIONS else None
        )
        for entry in folder.iterdir():
            if not entry.is_file():
                continue
            if allowed and entry.suffix.lower() not in allowed:
                continue
            options.append((entry.stem, str(entry)))
        options.sort(key=lambda item: item[0].lower())
        return options

    def init_menu_state(self):
        initial_players = max(
            1, min(self.last_settings.get("players", 1), len(self.PLAYER_COLORS))
        )
        initial_folder = self.last_settings.get("folder", "")
        initial_pairs = max(1, self.last_settings.get("pairs", 1))

        self.language_code = self.last_settings.get("language", self.language_code)
        I18N.set_language(self.language_code)

        self.player_var = tk.IntVar(value=initial_players)
        self.folder_var = tk.StringVar(value=initial_folder)
        self.pairs_var = tk.IntVar(value=initial_pairs)
        self.available_images = 0

        self.menu_frame = None
        self.image_info_label = None
        self.start_button = None
        self.player_minus_btn = None
        self.player_plus_btn = None
        self.player_value_label = None
        self.pairs_minus_btn = None
        self.pairs_plus_btn = None
        self.pairs_value_label = None
        self.menu_form = None
        self.player_name_vars = []
        self.player_names_entries_frame = None
        self.player_avatar_vars = []
        self.player_avatar_buttons = {}
        self.player_avatar_preview_labels = {}
        self.player_avatar_preview_images = {}
        self.language_button = None
        self.last_player_names = list(self.last_settings.get("names", []))
        raw_avatars = self.last_settings.get("avatars", [])
        self.last_player_avatars = [
            self.normalize_avatar_path(path) for path in raw_avatars
        ]
        self.sound_enabled = self.last_settings.get("sound_enabled", self.sound_enabled)
        self.ensure_player_name_vars(initial_players)
        self.ensure_player_avatar_vars(initial_players)

    def build_menu(self):
        self.menu_frame = tk.Frame(self.root, bg="#1a1a1a")
        self.menu_frame.pack(fill="both", expand=True, padx=40, pady=40)

        self.title_photo = None
        if TITLE_IMAGE_PATH:
            title_path = os.path.abspath(TITLE_IMAGE_PATH)
            title_image = self.load_title_image(
                title_path,
                max_width=TITLE_IMAGE_MAX_WIDTH,
                max_height=TITLE_IMAGE_MAX_HEIGHT,
            )
            if title_image is not None:
                self.title_photo = title_image
                tk.Label(
                    self.menu_frame,
                    image=self.title_photo,
                    bg="#1a1a1a",
                ).pack(pady=(0, 20))

        title = tk.Label(
            self.menu_frame,
            text=TITLE,
            fg="#f5f5f5",
            bg="#1a1a1a",
            font=self.ui_font_title,
        )
        title.pack(pady=(0, 24))

        form = tk.Frame(self.menu_frame, bg="#1a1a1a")
        form.pack()
        self.menu_form = form

        player_row = tk.Frame(form, bg="#1a1a1a")
        player_row.pack(fill="x", pady=8)
        tk.Label(
            player_row,
            text=_("menu.players_label"),
            fg="#f5f5f5",
            bg="#1a1a1a",
            font=self.ui_font_emphasis,
        ).pack(side="left")
        player_controls = tk.Frame(player_row, bg="#1a1a1a")
        player_controls.pack(side="right")

        btn_style = {
            "bg": "#3d3d3d",
            "fg": "#f5f5f5",
            "activebackground": "#555555",
            "activeforeground": "#f5f5f5",
            "relief": "flat",
            "font": self.ui_font_emphasis,
            "width": 2,
            "height": 1,
            "padx": 12,
            "pady": 8,
        }

        self.player_minus_btn = tk.Button(
            player_controls,
            text="-",
            command=lambda: self.change_player_count(-1),
            **btn_style,
        )
        self.player_minus_btn.pack(side="left", padx=6)

        self.player_value_label = tk.Label(
            player_controls,
            text=str(self.player_var.get()),
            fg="#f5f5f5",
            bg="#1a1a1a",
            font=self.ui_font_emphasis,
            width=4,
            anchor="center",
        )
        self.player_value_label.pack(side="left", padx=6)

        self.player_plus_btn = tk.Button(
            player_controls,
            text="+",
            command=lambda: self.change_player_count(1),
            **btn_style,
        )
        self.player_plus_btn.pack(side="left", padx=6)

        folder_row = tk.Frame(form, bg="#1a1a1a")
        folder_row.pack(fill="x", pady=8)
        tk.Label(
            folder_row,
            text=_("menu.folder_label"),
            fg="#f5f5f5",
            bg="#1a1a1a",
            font=self.ui_font_emphasis,
        ).pack(side="left")

        folder_controls = tk.Frame(folder_row, bg="#1a1a1a")
        folder_controls.pack(side="right", fill="x", expand=True)

        folder_entry = tk.Entry(
            folder_controls,
            textvariable=self.folder_var,
            width=40,
            font=self.ui_font_body,
            bg="#2b2b2b",
            fg="#f5f5f5",
            insertbackground="#f5f5f5",
            relief="flat",
        )
        folder_entry.pack(side="left", fill="x", expand=True)
        folder_entry.bind("<FocusOut>", lambda _event: self.refresh_image_stats())

        tk.Button(
            folder_controls,
            text=_("menu.browse_button"),
            command=self.browse_folder,
            bg="#3d3d3d",
            fg="#f5f5f5",
            activebackground="#555555",
            activeforeground="#f5f5f5",
            relief="flat",
            padx=10,
            pady=6,
            font=self.ui_font_emphasis,
        ).pack(side="left", padx=(8, 0))

        self.image_info_label = tk.Label(
            form,
            text=_("menu.images_found", count=0),
            fg="#ff9f1c",
            bg="#1a1a1a",
            font=self.ui_font_body,
        )
        self.image_info_label.pack(fill="x", pady=(4, 12))

        pairs_row = tk.Frame(form, bg="#1a1a1a")
        pairs_row.pack(fill="x", pady=8)
        tk.Label(
            pairs_row,
            text=_("menu.pairs_label"),
            fg="#f5f5f5",
            bg="#1a1a1a",
            font=self.ui_font_emphasis,
        ).pack(side="left")
        pairs_controls = tk.Frame(pairs_row, bg="#1a1a1a")
        pairs_controls.pack(side="right")

        self.pairs_minus_btn = tk.Button(
            pairs_controls,
            text="-",
            command=lambda: self.change_pair_count(-1),
            **btn_style,
        )
        self.pairs_minus_btn.pack(side="left", padx=6)

        self.pairs_value_label = tk.Label(
            pairs_controls,
            text=str(self.pairs_var.get()),
            fg="#f5f5f5",
            bg="#1a1a1a",
            font=self.ui_font_emphasis,
            width=4,
            anchor="center",
        )
        self.pairs_value_label.pack(side="left", padx=6)

        self.pairs_plus_btn = tk.Button(
            pairs_controls,
            text="+",
            command=lambda: self.change_pair_count(1),
            **btn_style,
        )
        self.pairs_plus_btn.pack(side="left", padx=6)

        button_row = tk.Frame(self.menu_frame, bg="#1a1a1a")
        button_row.pack(pady=(24, 0))

        self.start_button = tk.Button(
            button_row,
            text=_("menu.start_button"),
            command=self.start_game,
            bg="#5d8cf6",
            fg="#1a1a1a",
            activebackground="#81a9fb",
            activeforeground="#1a1a1a",
            relief="flat",
            padx=20,
            pady=10,
            state="disabled",
            font=self.ui_font_emphasis,
        )
        self.start_button.pack(side="left", padx=8)

        tk.Button(
            button_row,
            text=_("menu.names_button"),
            command=self.open_names_dialog,
            bg="#3d3d3d",
            fg="#f5f5f5",
            activebackground="#555555",
            activeforeground="#f5f5f5",
            relief="flat",
            padx=16,
            pady=8,
            font=self.ui_font_emphasis,
        ).pack(side="left", padx=8)

        tk.Button(
            button_row,
            text=_("menu.other_settings_button"),
            command=self.open_settings_dialog,
            bg="#3d3d3d",
            fg="#f5f5f5",
            activebackground="#555555",
            activeforeground="#f5f5f5",
            relief="flat",
            padx=16,
            pady=8,
            font=self.ui_font_emphasis,
        ).pack(side="left", padx=8)

        tk.Button(
            button_row,
            text=_("menu.quit_button"),
            command=self.root.destroy,
            bg="#3d3d3d",
            fg="#f5f5f5",
            activebackground="#555555",
            activeforeground="#f5f5f5",
            relief="flat",
            padx=16,
            pady=8,
            font=self.ui_font_emphasis,
        ).pack(side="left", padx=8)

        self.folder_var.trace_add("write", lambda *_: self.update_start_state())
        self.pairs_var.trace_add("write", lambda *_: self.update_start_state())
        self.player_var.trace_add("write", lambda *_: self.update_start_state())
        self.refresh_image_stats(self.folder_var.get())
        self.center_window()

    def destroy_game_ui(self):
        if self.image_summary_window is not None:
            try:
                if self.image_summary_window.winfo_exists():
                    self.image_summary_window.destroy()
            except tk.TclError:
                pass
            finally:
                self.image_summary_window = None
                self.summary_images = []
        if self.board_frame is not None:
            self.board_frame.unbind("<Configure>")
            self.board_frame.destroy()
            self.board_frame = None
        if self.board_grid is not None:
            self.board_grid.destroy()
            self.board_grid = None
        if self.sidebar_frame is not None:
            self.sidebar_frame.destroy()
            self.sidebar_frame = None

        self.root.rowconfigure(0, weight=0)
        self.root.columnconfigure(0, weight=0)
        self.root.columnconfigure(1, weight=0)

    def return_to_menu(self):
        self.destroy_game_ui()
        self.close_settings_window()
        self.close_names_window()
        self.reset_game_state()
        self.init_menu_state()
        self.build_menu()
        self.center_window()

    def play_match_sound(self):
        if not self.sound_enabled:
            return
        if not SOUNDS:
            return

        sound_path = random.choice(SOUNDS)
        if not sound_path:
            return

        abs_path = os.path.abspath(sound_path)
        if not os.path.isfile(abs_path):
            return

        _, ext = os.path.splitext(abs_path)
        ext = ext.lower()

        if self.vlc_instance is not None:
            try:
                media = self.vlc_instance.media_new_path(abs_path)
                player = self.vlc_instance.media_player_new()
                player.set_media(media)
                if self.vlc_player is not None:
                    try:
                        self.vlc_player.stop()
                    except Exception:
                        pass
                    try:
                        self.vlc_player.release()
                    except Exception:
                        pass
                self.vlc_player = player
                player.play()
                return
            except Exception:
                self.vlc_player = None

        if winsound is not None and ext == ".wav":
            try:
                winsound.PlaySound(None, winsound.SND_PURGE)
                winsound.PlaySound(abs_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
            except Exception:
                pass

    def browse_folder(self):
        selected = filedialog.askdirectory(title=_("menu.select_folder_title"))
        if selected:
            self.folder_var.set(selected)
            self.refresh_image_stats(selected)

    def refresh_image_stats(self, folder_path=None):
        folder = folder_path or self.folder_var.get()
        if folder and os.path.isdir(folder):
            image_paths = self.get_image_paths(folder)
            self.available_images = len(image_paths)
        else:
            image_paths = []
            self.available_images = 0

        if self.available_images > 0:
            info_text = _("menu.images_found", count=self.available_images)
            info_color = "#a4f9c8"
            current_pairs = self.pairs_var.get()
            if current_pairs < 1 or current_pairs > self.available_images:
                self.pairs_var.set(min(max(current_pairs, 1), self.available_images))
        else:
            info_text = _("menu.images_missing")
            info_color = "#ff6b6b"
            if self.pairs_var.get() != 0:
                self.pairs_var.set(0)

        self.image_paths = image_paths
        self.image_info_label.config(text=info_text, fg=info_color)
        self.update_start_state()

    def update_start_state(self, *_):
        try:
            player_count = int(self.player_var.get())
        except Exception:
            player_count = 1
        player_count = max(1, min(player_count, len(self.PLAYER_COLORS)))
        if player_count != self.player_var.get():
            self.player_var.set(player_count)

        try:
            pair_count = int(self.pairs_var.get())
        except Exception:
            pair_count = 0

        if self.available_images > 0:
            pair_count = max(1, min(pair_count, self.available_images))
            if pair_count != self.pairs_var.get():
                self.pairs_var.set(pair_count)
        else:
            pair_count = 0
            if self.pairs_var.get() != 0:
                self.pairs_var.set(0)

        folder_ok = bool(self.folder_var.get()) and os.path.isdir(self.folder_var.get())
        pairs_ok = pair_count >= 1 and pair_count <= self.available_images

        if folder_ok and pairs_ok:
            self.start_button.config(state="normal")
        else:
            self.start_button.config(state="disabled")

        self.update_player_controls()
        self.update_pairs_controls()

    def update_player_controls(self):
        if self.player_value_label is not None:
            self.player_value_label.config(text=str(self.player_var.get()))
        if self.player_minus_btn is not None:
            state = "normal" if self.player_var.get() > 1 else "disabled"
            self.player_minus_btn.config(state=state)
        if self.player_plus_btn is not None:
            state = (
                "normal"
                if self.player_var.get() < len(self.PLAYER_COLORS)
                else "disabled"
            )
            self.player_plus_btn.config(state=state)
        self.rebuild_player_name_inputs()

    def update_pairs_controls(self):
        if self.pairs_value_label is not None:
            self.pairs_value_label.config(text=str(self.pairs_var.get()))
        if self.pairs_minus_btn is not None:
            state = (
                "normal"
                if self.available_images > 0 and self.pairs_var.get() > 1
                else "disabled"
            )
            self.pairs_minus_btn.config(state=state)
        if self.pairs_plus_btn is not None:
            state = (
                "normal"
                if self.available_images > 0
                and self.pairs_var.get() < self.available_images
                else "disabled"
            )
            self.pairs_plus_btn.config(state=state)

    def update_sound_toggle_button(self):
        if self.sound_toggle_button is None:
            return
        bg_active = "#5d8cf6" if self.sound_enabled else "#3d3d3d"
        fg_active = "#1a1a1a" if self.sound_enabled else "#f5f5f5"
        active_bg = "#81a9fb" if self.sound_enabled else "#555555"
        self.sound_toggle_button.config(
            text=(
                _("menu.sound_toggle_on")
                if self.sound_enabled
                else _("menu.sound_toggle_off")
            ),
            bg=bg_active,
            fg=fg_active,
            activebackground=active_bg,
            activeforeground="#1a1a1a" if self.sound_enabled else "#f5f5f5",
        )

    def toggle_sound_enabled(self):
        self.sound_enabled = not self.sound_enabled
        self.last_settings["sound_enabled"] = self.sound_enabled
        self.update_sound_toggle_button()

    def ensure_player_name_vars(self, desired):
        desired = max(1, min(desired, len(self.PLAYER_COLORS)))
        while len(self.player_name_vars) < desired:
            idx = len(self.player_name_vars)
            default = ""
            if idx < len(self.last_player_names):
                default = self.last_player_names[idx]
            if not default:
                default = _("players.default_name", index=idx + 1)
            self.player_name_vars.append(tk.StringVar(value=default))

    def normalize_avatar_path(self, path):
        if not path:
            return ""
        abs_path = os.path.abspath(path)
        return abs_path if abs_path in self.avatar_lookup else ""

    def ensure_player_avatar_vars(self, desired):
        desired = max(1, min(desired, len(self.PLAYER_COLORS)))
        while len(self.player_avatar_vars) < desired:
            idx = len(self.player_avatar_vars)
            default = ""
            if idx < len(self.last_player_avatars):
                default = self.normalize_avatar_path(self.last_player_avatars[idx])
            if not default:
                default = self.default_avatar_path
            self.player_avatar_vars.append(tk.StringVar(value=default or ""))

    def is_valid_avatar_path(self, path):
        return bool(self.normalize_avatar_path(path))

    def get_avatar_label(self, path):
        normalized = self.normalize_avatar_path(path)
        if not normalized:
            return _("avatars.default_label")
        return self.avatar_lookup.get(normalized, _("avatars.default_label"))

    def get_avatar_photo(self, path, size=56):
        normalized = self.normalize_avatar_path(path)
        if not normalized:
            return None
        cache_key = ("avatar", normalized, size)
        cached = self.image_cache.get(cache_key)
        if cached is not None:
            return cached
        try:
            with Image.open(normalized) as img:
                img = ImageOps.exif_transpose(img)
                img = img.convert("RGBA")
                img.thumbnail((size, size), Image.LANCZOS)

                canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
                offset = ((size - img.width) // 2, (size - img.height) // 2)
                canvas.paste(img, offset, img)

                photo = ImageTk.PhotoImage(canvas)
                self.image_cache[cache_key] = photo
                return photo
        except Exception:
            return None

    def get_avatar_placeholder(self, index, size=56):
        color = self.PLAYER_COLORS[index % len(self.PLAYER_COLORS)]
        cache_key = ("avatar_placeholder", color, size)
        cached = self.image_cache.get(cache_key)
        if cached is not None:
            return cached
        img = Image.new("RGB", (size, size), color)
        photo = ImageTk.PhotoImage(img)
        self.image_cache[cache_key] = photo
        return photo

    def set_player_avatar(self, index, path):
        if index >= len(self.player_avatar_vars):
            return
        normalized = self.normalize_avatar_path(path)
        if not normalized and self.default_avatar_path:
            normalized = self.default_avatar_path
        self.player_avatar_vars[index].set(normalized)
        display_name = ""
        if normalized:
            display_name = self.avatar_lookup.get(normalized, "").strip()
        if display_name:
            if index < len(self.player_name_vars):
                self.player_name_vars[index].set(display_name)
            while len(self.last_player_names) < len(self.player_name_vars):
                self.last_player_names.append("")
            self.last_player_names[index] = display_name
            if self.player_names and index < len(self.player_names):
                self.player_names[index] = display_name
                self.update_score_labels()
        self.update_avatar_button_label(index)
        self.update_avatar_preview(index)

    def update_avatar_button_label(self, index):
        button = self.player_avatar_buttons.get(index)
        if button is None:
            return
        label = self.get_avatar_label(
            self.player_avatar_vars[index].get()
            if index < len(self.player_avatar_vars)
            else ""
        )
        button.config(text=label)

    def update_avatar_preview(self, index):
        label_widget = self.player_avatar_preview_labels.get(index)
        if label_widget is None:
            return
        path = (
            self.player_avatar_vars[index].get()
            if index < len(self.player_avatar_vars)
            else ""
        )
        photo = self.get_avatar_photo(path, size=54)
        if photo is None:
            photo = self.get_avatar_placeholder(index, size=54)
        label_widget.config(image=photo)
        label_widget.image = photo
        self.player_avatar_preview_images[index] = photo

    def rebuild_player_name_inputs(self):
        desired = int(self.player_var.get()) if self.player_var is not None else 1
        desired = max(1, min(desired, len(self.PLAYER_COLORS)))

        self.ensure_player_name_vars(desired)
        self.ensure_player_avatar_vars(desired)

        if self.player_names_entries_frame is None:
            return

        for widget in self.player_names_entries_frame.winfo_children():
            widget.destroy()

        for i in range(desired):
            row = tk.Frame(self.player_names_entries_frame, bg="#1a1a1a")
            row.pack(fill="x", pady=6)

            left = tk.Frame(row, bg="#1a1a1a")
            left.pack(side="left", fill="x", expand=True)

            tk.Label(
                left,
                text=_("names_dialog.player_label", index=i + 1),
                fg="#f5f5f5",
                bg="#1a1a1a",
                font=self.ui_font_emphasis,
                anchor="w",
            ).pack(anchor="w")

            tk.Entry(
                left,
                textvariable=self.player_name_vars[i],
                bg="#2b2b2b",
                fg="#f5f5f5",
                insertbackground="#f5f5f5",
                relief="flat",
                font=self.ui_font_body,
            ).pack(fill="x", pady=(4, 0))

            right = tk.Frame(row, bg="#1a1a1a")
            right.pack(side="left", padx=(12, 0))

            preview = tk.Label(right, bg="#1a1a1a")
            preview.pack()
            self.player_avatar_preview_labels[i] = preview

            button = tk.Menubutton(
                right,
                text=_("avatars.menu_label"),
                bg="#3d3d3d",
                fg="#f5f5f5",
                activebackground="#555555",
                activeforeground="#f5f5f5",
                relief="flat",
                font=self.ui_font_emphasis,
                padx=12,
                pady=6,
                direction="below",
            )
            button.pack(fill="x", pady=(6, 0))
            self.player_avatar_buttons[i] = button

            menu = tk.Menu(button, tearoff=0, bg="#2b2b2b", fg="#f5f5f5")
            if self.available_avatar_options:
                for option_name, option_path in self.available_avatar_options:
                    menu.add_command(
                        label=option_name,
                        command=lambda p=option_path, idx=i: self.set_player_avatar(
                            idx, p
                        ),
                    )
            else:
                menu.add_command(label=_("avatars.none_available"), state="disabled")
            button.config(menu=menu)

            self.update_avatar_button_label(i)
            self.update_avatar_preview(i)

    def close_names_window(self):
        window = self.names_window
        if window is None:
            return
        self.names_window = None
        self.player_names_entries_frame = None
        self.player_avatar_buttons = {}
        self.player_avatar_preview_labels = {}
        self.player_avatar_preview_images = {}
        try:
            if window.winfo_exists():
                window.destroy()
        except tk.TclError:
            pass

    def close_settings_window(self):
        window = self.settings_window
        if window is None:
            return
        self.settings_window = None
        self.language_button = None
        self.sound_toggle_button = None
        self.sound_count_label = None
        try:
            if window.winfo_exists():
                window.destroy()
        except tk.TclError:
            pass

    def open_names_dialog(self):
        desired = int(self.player_var.get()) if self.player_var is not None else 1
        self.ensure_player_name_vars(desired)
        self.ensure_player_avatar_vars(desired)

        if self.names_window is not None and self.names_window.winfo_exists():
            self.rebuild_player_name_inputs()
            self.names_window.lift()
            self.names_window.focus_force()
            return

        window = tk.Toplevel(self.root)
        window.title(_("names_dialog.title"))
        window.configure(bg="#1a1a1a")
        window.geometry("520x420")
        window.transient(self.root)

        container = tk.Frame(window, bg="#1a1a1a", padx=24, pady=24)
        container.pack(fill="both", expand=True)

        tk.Label(
            container,
            text=_("names_dialog.subtitle"),
            fg="#f5f5f5",
            bg="#1a1a1a",
            font=self.ui_font_emphasis,
        ).pack(anchor="w")

        info = tk.Label(
            container,
            text=_("names_dialog.hint"),
            fg="#cfcfcf",
            bg="#1a1a1a",
            font=self.ui_font_body,
        )
        info.pack(anchor="w", pady=(4, 12))

        frame = tk.Frame(container, bg="#1a1a1a")
        frame.pack(fill="both", expand=True)
        self.player_names_entries_frame = frame
        self.names_window = window

        self.rebuild_player_name_inputs()

        button_bar = tk.Frame(container, bg="#1a1a1a")
        button_bar.pack(fill="x", pady=(18, 0))

        tk.Button(
            button_bar,
            text=_("names_dialog.done_button"),
            command=self.close_names_window,
            bg="#5d8cf6",
            fg="#1a1a1a",
            activebackground="#81a9fb",
            activeforeground="#1a1a1a",
            relief="flat",
            padx=20,
            pady=8,
            font=self.ui_font_emphasis,
        ).pack(side="right")

        window.protocol("WM_DELETE_WINDOW", self.close_names_window)

    def open_settings_dialog(self):
        if self.settings_window is not None and self.settings_window.winfo_exists():
            self.settings_window.lift()
            self.settings_window.focus_force()
            return

        window = tk.Toplevel(self.root)
        window.title(_("settings_dialog.title"))
        window.configure(bg="#1a1a1a")
        window.geometry("420x300")
        window.transient(self.root)

        container = tk.Frame(window, bg="#1a1a1a", padx=24, pady=24)
        container.pack(fill="both", expand=True)

        tk.Label(
            container,
            text=_("settings_dialog.subtitle"),
            fg="#f5f5f5",
            bg="#1a1a1a",
            font=self.ui_font_emphasis,
        ).pack(anchor="w")

        tk.Label(
            container,
            text=_("settings_dialog.hint"),
            fg="#cfcfcf",
            bg="#1a1a1a",
            font=self.ui_font_body,
        ).pack(anchor="w", pady=(4, 16))

        language_row = tk.Frame(container, bg="#1a1a1a")
        language_row.pack(fill="x", pady=(0, 12))

        tk.Label(
            language_row,
            text=_("menu.language_label"),
            fg="#f5f5f5",
            bg="#1a1a1a",
            font=self.ui_font_emphasis,
        ).pack(side="left")

        self.language_button = tk.Menubutton(
            language_row,
            text=I18N.get_language_label(self.language_code),
            bg="#3d3d3d",
            fg="#f5f5f5",
            activebackground="#555555",
            activeforeground="#f5f5f5",
            relief="flat",
            font=self.ui_font_emphasis,
            padx=12,
            pady=6,
            direction="below",
        )
        self.language_button.pack(side="right")

        language_menu = tk.Menu(
            self.language_button,
            tearoff=0,
            bg="#2b2b2b",
            fg="#f5f5f5",
            activebackground="#555555",
            activeforeground="#f5f5f5",
        )
        for code, label in I18N.get_language_options():
            language_menu.add_command(
                label=label,
                command=lambda c=code: self.set_language(c),
            )
        self.language_button.config(menu=language_menu)

        sounds_row = tk.Frame(container, bg="#1a1a1a")
        sounds_row.pack(fill="x")

        self.sound_count_label = tk.Label(
            sounds_row,
            text=_("menu.sounds_found", count=len(SOUNDS)),
            fg="#f5f5f5",
            bg="#1a1a1a",
            font=self.ui_font_body,
        )
        self.sound_count_label.pack(side="left")

        sound_btn_style = {
            "bg": "#3d3d3d",
            "fg": "#f5f5f5",
            "activebackground": "#555555",
            "activeforeground": "#f5f5f5",
            "relief": "flat",
            "font": self.ui_font_emphasis,
            "padx": 12,
            "pady": 6,
        }

        self.sound_toggle_button = tk.Button(
            sounds_row,
            command=self.toggle_sound_enabled,
            **sound_btn_style,
        )
        self.sound_toggle_button.pack(side="right")
        self.update_sound_toggle_button()

        button_bar = tk.Frame(container, bg="#1a1a1a")
        button_bar.pack(fill="x", pady=(24, 0))

        tk.Button(
            button_bar,
            text=_("settings_dialog.done_button"),
            command=self.close_settings_window,
            bg="#5d8cf6",
            fg="#1a1a1a",
            activebackground="#81a9fb",
            activeforeground="#1a1a1a",
            relief="flat",
            padx=20,
            pady=8,
            font=self.ui_font_emphasis,
        ).pack(side="right")

        self.settings_window = window
        window.protocol("WM_DELETE_WINDOW", self.close_settings_window)

    def change_player_count(self, delta):
        new_value = self.player_var.get() + delta
        new_value = max(1, min(new_value, len(self.PLAYER_COLORS)))
        if new_value != self.player_var.get():
            self.player_var.set(new_value)
        self.update_player_controls()

    def change_pair_count(self, delta):
        if self.available_images <= 0:
            return
        new_value = self.pairs_var.get() + delta
        new_value = max(1, min(new_value, self.available_images))
        if new_value != self.pairs_var.get():
            self.pairs_var.set(new_value)
        else:
            self.update_pairs_controls()

    def start_game(self):
        folder = self.folder_var.get()
        if not folder or not os.path.isdir(folder):
            messagebox.showerror(_("dialogs.error_title"), _("dialogs.invalid_folder"))
            return

        image_paths = self.get_image_paths(folder)
        if not image_paths:
            messagebox.showerror(
                _("dialogs.error_title"),
                _("dialogs.no_images"),
            )
            self.refresh_image_stats(folder)
            return

        try:
            num_pairs = int(self.pairs_var.get())
        except Exception:
            num_pairs = 0

        if num_pairs < 1 or num_pairs > len(image_paths):
            messagebox.showerror(
                _("dialogs.error_title"),
                _("dialogs.invalid_pair_count", max_pairs=len(image_paths)),
            )
            self.refresh_image_stats(folder)
            return

        try:
            num_players = int(self.player_var.get())
        except Exception:
            num_players = 1
        num_players = max(1, min(num_players, len(self.PLAYER_COLORS)))

        self.ensure_player_name_vars(num_players)
        self.ensure_player_avatar_vars(num_players)
        self.close_names_window()
        self.close_settings_window()

        player_names = []
        player_avatars = []
        for idx in range(num_players):
            var = self.player_name_vars[idx]
            name = var.get().strip()
            if not name:
                name = _("players.default_name", index=idx + 1)
                var.set(name)
            player_names.append(name)

            avatar_var = self.player_avatar_vars[idx]
            avatar_path = self.normalize_avatar_path(avatar_var.get())
            if not avatar_path:
                avatar_path = self.default_avatar_path or ""
                avatar_var.set(avatar_path)
            player_avatars.append(avatar_path)
        self.player_names = player_names
        self.player_avatars = player_avatars

        self.last_settings = {
            "players": num_players,
            "folder": folder,
            "pairs": num_pairs,
            "names": player_names,
            "avatars": player_avatars,
            "sound_enabled": self.sound_enabled,
            "language": self.language_code,
        }

        self.last_player_names = list(player_names)
        self.last_player_avatars = list(player_avatars)

        self.menu_frame.destroy()
        self.menu_frame = None

        self.folder = folder
        self.image_paths = image_paths
        self.available_images = len(image_paths)
        self.num_pairs = num_pairs
        self.num_cards = num_pairs * 2

        self.num_players = num_players
        self.player_colors = self.PLAYER_COLORS[: self.num_players]
        self.current_player = 0
        self.player_scores = [0] * self.num_players
        self.card_owner = {}
        self.flipped = []
        self.matched = set()

        self.build_game_ui()

    def build_game_ui(self):
        self.root.rowconfigure(0, weight=1)
        self.root.columnconfigure(0, weight=0)
        self.root.columnconfigure(1, weight=1)

        self.sidebar_frame = tk.Frame(self.root, bg="#1a1a1a")
        self.sidebar_frame.grid(row=0, column=0, sticky="ns", padx=(24, 12), pady=24)
        self.setup_scoreboard(self.sidebar_frame)

        self.board_frame = tk.Frame(self.root, bg="#1a1a1a")
        self.board_frame.grid(row=0, column=1, sticky="nsew", padx=(12, 24), pady=24)
        self.board_frame.grid_rowconfigure(0, weight=1)
        self.board_frame.grid_columnconfigure(0, weight=1)

        self.board_grid = tk.Frame(self.board_frame, bg="#1a1a1a")
        self.board_grid.grid(row=0, column=0)

        self.center_window()
        self.root.update_idletasks()

        self.rows, self.cols = self.calculate_grid(self.num_cards)
        sidebar_width = self.sidebar_frame.winfo_width()
        self.card_size = self.calculate_card_size(
            self.rows, self.cols, header_height=0, sidebar_width=sidebar_width
        )
        self.card_back_image = self.create_card_back(self.card_size)

        shuffled_paths = self.image_paths[:]
        random.shuffle(shuffled_paths)
        loaded_images = []
        for path in shuffled_paths:
            photo = self.load_image(path, self.card_size)
            if photo is not None:
                loaded_images.append((photo, path))
            if len(loaded_images) == self.num_pairs:
                break

        if len(loaded_images) < self.num_pairs:
            messagebox.showerror(
                _("dialogs.error_title"),
                _("dialogs.loading_error", count=len(loaded_images)),
            )
            self.return_to_menu()
            return

        self.image_pool = loaded_images
        self.cards = self.prepare_cards()
        self.buttons = []
        self.card_slots = []
        self.flipped = []
        self.matched = set()

        self.create_board()
        self.board_frame.bind("<Configure>", self.position_board)
        self.position_board()
        self.update_turn_indicator()
        self.update_score_labels()

    def get_image_paths(self, folder=None):
        valid_ext = (".png", ".jpg", ".jpeg", ".gif", ".bmp")
        paths = []
        search_folder = folder or self.folder
        if not search_folder or not os.path.isdir(search_folder):
            return []
        for root_dir, _, files in os.walk(search_folder):
            for file in files:
                if file.lower().endswith(valid_ext):
                    paths.append(os.path.join(root_dir, file))
        paths.sort()
        return paths

    def load_image(self, img_path, target_size):
        cache_key = (img_path, target_size)
        cached = self.image_cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            with Image.open(img_path) as img:
                img = ImageOps.exif_transpose(img)
                img = img.convert("RGBA")
                img.thumbnail((target_size, target_size), Image.LANCZOS)

                canvas = Image.new("RGBA", (target_size, target_size), "#2b2b2b")
                offset_x = (target_size - img.width) // 2
                offset_y = (target_size - img.height) // 2
                canvas.paste(
                    img,
                    (offset_x, offset_y),
                    img if img.mode == "RGBA" else None,
                )

                photo = ImageTk.PhotoImage(canvas.convert("RGB"))
                self.image_cache[cache_key] = photo
                return photo
        except Exception:
            return None

    def load_title_image(
        self,
        img_path,
        max_width=TITLE_IMAGE_MAX_WIDTH,
        max_height=TITLE_IMAGE_MAX_HEIGHT,
    ):
        cache_key = ("title", img_path, max_width, max_height)
        cached = self.image_cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            with Image.open(img_path) as img:
                img = ImageOps.exif_transpose(img)
                img = img.convert("RGBA")
                img.thumbnail((max_width, max_height), Image.LANCZOS)
                photo = ImageTk.PhotoImage(img.convert("RGB"))
                self.image_cache[cache_key] = photo
                return photo
        except Exception:
            return None

    def prepare_cards(self):
        paired = random.sample(self.image_pool, self.num_pairs)
        cards = []
        self.card_paths = []
        for entry in paired:
            if isinstance(entry, tuple):
                img, path = entry
            else:
                img = entry
                path = None
            cards.extend([img, img])
            self.card_paths.extend([path, path])
        combined = list(zip(cards, self.card_paths))
        random.shuffle(combined)
        shuffled_cards, shuffled_paths = zip(*combined)
        self.card_paths = list(shuffled_paths)
        return list(shuffled_cards)

    def setup_scoreboard(self, parent):
        self.score_frame = tk.Frame(parent, bg="#1a1a1a")
        self.score_frame.pack(fill="both", expand=True)

        self.player_containers = []
        self.score_labels = []
        self.score_avatar_labels = []
        self.score_avatar_images = []

        players_wrapper = tk.Frame(self.score_frame, bg="#1a1a1a")
        players_wrapper.pack(fill="both", expand=True)

        for i in range(self.num_players):
            display_name = self.resolve_player_name(i)
            container = tk.Frame(
                players_wrapper,
                bg="#1a1a1a",
                padx=4,
                pady=4,
                highlightthickness=2,
                highlightbackground="#1a1a1a",
                highlightcolor="#1a1a1a",
                bd=0,
            )
            container.pack(fill="x", pady=6)

            inner = tk.Frame(
                container,
                bg=self.player_colors[i],
                padx=10,
                pady=6,
            )
            inner.pack(fill="x")

            avatar_label = tk.Label(inner, bg=self.player_colors[i])
            avatar_label.pack(side="left", padx=(0, 10))

            label = tk.Label(
                inner,
                text=_("scoreboard.entry", name=display_name, score=0),
                fg="#f5f5f5",
                bg=self.player_colors[i],
                font=self.ui_font_emphasis,
            )
            label.pack(side="left", fill="x", expand=True)

            self.player_containers.append(container)
            self.score_labels.append(label)
            self.score_avatar_labels.append(avatar_label)
            self.score_avatar_images.append(None)
            self.update_scoreboard_avatar(i)

        self.post_game_frame = tk.Frame(self.score_frame, bg="#1a1a1a")
        self.post_game_frame.pack(fill="x", pady=(12, 0))

        self.review_button = tk.Button(
            self.post_game_frame,
            text=_("buttons.review_gallery"),
            command=self.show_image_summary,
            bg="#5d8cf6",
            fg="#1a1a1a",
            activebackground="#81a9fb",
            activeforeground="#1a1a1a",
            relief="flat",
            padx=12,
            pady=10,
            font=self.ui_font_emphasis,
        )
        self.review_button.config(state="disabled")

        self.menu_button = tk.Button(
            self.post_game_frame,
            text=_("buttons.back_to_menu"),
            command=self.return_to_menu,
            bg="#3d3d3d",
            fg="#f5f5f5",
            activebackground="#555555",
            activeforeground="#f5f5f5",
            relief="flat",
            padx=12,
            pady=8,
            font=self.ui_font_emphasis,
        )
        self.menu_button.pack(fill="x")

    def enable_review_button(self):
        if self.review_button is None:
            return
        if self.review_button.winfo_ismapped():
            self.review_button.pack_forget()

        pack_kwargs = {"fill": "x", "pady": (0, 10)}
        if (
            self.menu_button is not None
            and str(self.menu_button.winfo_manager()) == "pack"
        ):
            pack_kwargs["before"] = self.menu_button

        self.review_button.pack(**pack_kwargs)
        self.review_button.config(state="normal" if self.matched_paths else "disabled")

    def show_image_summary(self):
        if not self.matched_paths:
            messagebox.showinfo(
                _("dialogs.gallery_empty_title"),
                _("dialogs.gallery_empty_body"),
            )
            return

        if (
            self.image_summary_window is not None
            and self.image_summary_window.winfo_exists()
        ):
            self.image_summary_window.lift()
            self.image_summary_window.focus_force()
            return

        self.summary_images = []
        self.image_summary_window = tk.Toplevel(self.root)
        self.image_summary_window.title(_("gallery.window_title"))
        self.image_summary_window.configure(bg="#1a1a1a")
        self.image_summary_window.geometry("900x720")

        # Maximize the window immediately
        try:
            self.image_summary_window.state("zoomed")
        except tk.TclError:
            # Fallback for systems that don't support "zoomed"
            screen_w = self.image_summary_window.winfo_screenwidth()
            screen_h = self.image_summary_window.winfo_screenheight()
            self.image_summary_window.geometry(f"{screen_w}x{screen_h}+0+0")

        container = tk.Frame(self.image_summary_window, bg="#1a1a1a")
        container.pack(fill="both", expand=True, padx=16, pady=16)

        canvas = tk.Canvas(
            container,
            bg="#1a1a1a",
            highlightthickness=0,
            relief="flat",
        )
        scrollbar = tk.Scrollbar(container, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        content = tk.Frame(canvas, bg="#1a1a1a")
        window_id = canvas.create_window((0, 0), window=content, anchor="nw")

        def on_content_configure(_event):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def on_canvas_configure(event):
            canvas.itemconfigure(window_id, width=event.width)

        content.bind("<Configure>", on_content_configure)
        canvas.bind("<Configure>", on_canvas_configure)

        def on_mousewheel(event):
            if event.delta:
                delta = -int(event.delta / 120)
                if delta == 0:
                    delta = -1 if event.delta > 0 else 1
            elif getattr(event, "num", None) in (4, 5):
                delta = -1 if event.num == 4 else 1
            else:
                delta = 0
            if delta:
                canvas.yview_scroll(delta, "units")

        bind_targets = [self.image_summary_window, canvas, content]
        for target in bind_targets:
            target.bind("<MouseWheel>", on_mousewheel)
            target.bind("<Button-4>", on_mousewheel)
            target.bind("<Button-5>", on_mousewheel)

        heading = tk.Label(
            content,
            text=_("gallery.heading"),
            fg="#f5f5f5",
            bg="#1a1a1a",
            font=self.ui_font_emphasis,
        )
        heading.pack(anchor="w", pady=(0, 12))

        grid_frame = tk.Frame(content, bg="#1a1a1a")
        grid_frame.pack(fill="both", expand=True)

        seen_paths = set()
        folder_abs = os.path.abspath(self.folder) if self.folder else None
        entries = []

        for entry in self.matched_paths:
            path = entry.get("path")
            if not path or path in seen_paths:
                continue
            seen_paths.add(path)
            entries.append((path, entry.get("player")))

        if folder_abs:

            def sort_key(item):
                abs_path = os.path.abspath(item[0])
                try:
                    if os.path.commonpath([folder_abs, abs_path]) == folder_abs:
                        return os.path.relpath(abs_path, folder_abs)
                except (ValueError, OSError):
                    pass
                return abs_path

            entries.sort(key=lambda item: sort_key(item).lower())
        else:
            entries.sort(key=lambda item: os.path.abspath(item[0]).lower())

        if not entries:
            tk.Label(
                grid_frame,
                text=_("gallery.no_unique_paths"),
                fg="#ff9f1c",
                bg="#1a1a1a",
                font=self.ui_font_body,
            ).pack(anchor="w", pady=8)
        else:
            for col in range(3):
                grid_frame.grid_columnconfigure(col, weight=1, uniform="gallery")

            base_size = getattr(self, "card_size", 220) or 220
            thumb_size = min(max(base_size + 80, 260), 360)

            for index, (path, player_idx) in enumerate(entries, start=1):
                row = (index - 1) // 3
                col = (index - 1) % 3
                item_frame = tk.Frame(
                    grid_frame,
                    bg="#2b2b2b",
                    padx=12,
                    pady=12,
                )
                item_frame.grid(row=row, column=col, padx=12, pady=12, sticky="n")

                image = self.load_image(path, thumb_size)
                if image is not None:
                    img_label = tk.Label(item_frame, image=image, bg="#2b2b2b")
                    img_label.image = image
                    img_label.pack()
                    self.summary_images.append(image)
                else:
                    placeholder = tk.Frame(
                        item_frame,
                        width=thumb_size,
                        height=thumb_size,
                        bg="#1a1a1a",
                    )
                    placeholder.pack_propagate(False)
                    placeholder.pack()
                    tk.Label(
                        placeholder,
                        text=_("gallery.not_loaded"),
                        fg="#ff9f1c",
                        bg="#1a1a1a",
                        font=self.ui_font_body,
                        justify="center",
                    ).pack(expand=True)

                abs_path = os.path.abspath(path)
                display_path = abs_path
                if folder_abs:
                    try:
                        if os.path.commonpath([folder_abs, abs_path]) == folder_abs:
                            # Get the relative path from the folder
                            rel_path = os.path.relpath(abs_path, folder_abs)
                            # Get the folder name and combine it with the relative path
                            folder_name = os.path.basename(folder_abs)
                            display_path = os.path.join(folder_name, rel_path)
                    except (ValueError, OSError):
                        display_path = abs_path

                tk.Label(
                    item_frame,
                    text=f"{index}. {display_path}",
                    fg="#f5f5f5",
                    bg="#2b2b2b",
                    font=self.ui_font_body,
                    wraplength=thumb_size + 80,
                    justify="center",
                ).pack(pady=(10, 0))

                if player_idx is not None and 0 <= player_idx < len(self.player_colors):
                    player_text = _(
                        "gallery.found_by",
                        player=self.resolve_player_name(player_idx),
                    )
                    tk.Label(
                        item_frame,
                        text=player_text,
                        fg=self.player_colors[player_idx],
                        bg="#2b2b2b",
                        font=self.ui_font_emphasis,
                    ).pack(pady=(6, 0))

        def close_window():
            if self.image_summary_window is not None:
                try:
                    self.image_summary_window.destroy()
                except tk.TclError:
                    pass
            self.image_summary_window = None
            self.summary_images = []

        self.image_summary_window.protocol("WM_DELETE_WINDOW", close_window)

    def create_board(self):
        for i in range(self.num_cards):
            slot = tk.Frame(
                self.board_grid,
                bg="#1a1a1a",
                padx=4,
                pady=4,
                highlightthickness=3,
                highlightbackground="#1a1a1a",
                highlightcolor="#1a1a1a",
            )
            slot.grid(row=i // self.cols, column=i % self.cols, padx=6, pady=6)

            btn = tk.Button(
                slot,
                image=self.card_back_image,
                command=lambda i=i: self.flip_card(i),
                relief="flat",
                bd=0,
                highlightthickness=0,
                bg="#1a1a1a",
                activebackground="#1a1a1a",
            )
            btn.pack()

            self.card_slots.append(slot)
            self.buttons.append(btn)

    def flip_card(self, idx):
        if idx in self.matched or idx in self.flipped:
            return
        if len(self.flipped) >= 2:
            return
        self.buttons[idx].config(image=self.cards[idx])
        self.flipped.append(idx)
        if len(self.flipped) == 2:
            self.root.after(1000, self.check_match)

    def check_match(self):
        if len(self.flipped) != 2:
            return
        i1, i2 = self.flipped
        if self.cards[i1] == self.cards[i2]:
            self.matched.update(self.flipped)
            self.card_owner[i1] = self.current_player
            self.card_owner[i2] = self.current_player
            for idx in self.flipped:
                self.buttons[idx].config(state="disabled")
            self.color_matched_cards(self.flipped, self.current_player)
            self.player_scores[self.current_player] += 1
            self.play_match_sound()
            if self.card_paths:
                path = self.card_paths[i1]
                if path and not any(
                    entry["path"] == path for entry in self.matched_paths
                ):
                    self.matched_paths.append(
                        {
                            "path": path,
                            "player": self.current_player,
                        }
                    )
            self.update_score_labels()
        else:
            for i in self.flipped:
                self.buttons[i].config(image=self.card_back_image)
            self.next_player()
        self.flipped = []
        if len(self.matched) == self.num_cards:
            self.finish_game()

    def calculate_grid(self, total_cards):
        cols = math.ceil(math.sqrt(total_cards))
        rows = math.ceil(total_cards / cols)
        return rows, cols

    def calculate_card_size(self, rows, cols, header_height=0, sidebar_width=0):
        self.root.update_idletasks()
        screen_w = max(self.root.winfo_width(), self.root.winfo_screenwidth())
        screen_h = max(self.root.winfo_height(), self.root.winfo_screenheight())

        available_w = max(320, screen_w - sidebar_width - 160)
        available_h = max(320, screen_h - header_height - 160)
        available_h = int(available_h * (1 - BOTTOM_BORDER_FRACTION))

        size_w = available_w / cols
        size_h = available_h / rows
        base_size = int(min(size_w, size_h))
        if base_size <= 0:
            base_size = 60

        return min(base_size, 240)

    def create_card_back(self, size):
        img = Image.new("RGB", (size, size), "#2b2b2b")
        return ImageTk.PhotoImage(img)

    def update_turn_indicator(self):
        for i, container in enumerate(self.player_containers):
            if i == self.current_player:
                container.config(
                    highlightbackground="#f5f5f5", highlightcolor="#f5f5f5"
                )
            else:
                container.config(
                    highlightbackground="#1a1a1a", highlightcolor="#1a1a1a"
                )

    def resolve_player_name(self, index):
        if 0 <= index < len(self.player_names):
            name = self.player_names[index].strip()
            if name:
                return name
        return _("players.default_name", index=index + 1)

    def resolve_player_avatar(self, index):
        path = ""
        if 0 <= index < len(self.player_avatars):
            path = self.player_avatars[index]
        elif 0 <= index < len(self.player_avatar_vars):
            path = self.player_avatar_vars[index].get()
        normalized = self.normalize_avatar_path(path)
        if normalized:
            return normalized
        if self.default_avatar_path:
            return self.default_avatar_path
        return ""

    def update_scoreboard_avatar(self, index):
        if index >= len(self.score_avatar_labels):
            return
        label = self.score_avatar_labels[index]
        if label is None:
            return
        path = self.resolve_player_avatar(index)
        photo = self.get_avatar_photo(path, size=48)
        if photo is None:
            photo = self.get_avatar_placeholder(index, size=48)
        label.config(image=photo)
        label.image = photo
        self.score_avatar_images[index] = photo

    def update_score_labels(self):
        for i, label in enumerate(self.score_labels):
            label.config(
                text=_(
                    "scoreboard.entry",
                    name=self.resolve_player_name(i),
                    score=self.player_scores[i],
                )
            )
            self.update_scoreboard_avatar(i)

    def color_matched_cards(self, indices, player_index):
        color = self.player_colors[player_index]
        for idx in indices:
            slot = self.card_slots[idx]
            slot.config(highlightbackground=color, highlightcolor=color)

    def next_player(self):
        if self.num_players <= 1:
            return
        self.current_player = (self.current_player + 1) % self.num_players
        self.update_turn_indicator()

    def finish_game(self):
        self.enable_review_button()
        if self.num_players == 1:
            name = self.resolve_player_name(0)
            messagebox.showinfo(
                _("dialogs.congrats_title"),
                _("dialogs.single_player_win", name=name),
            )
            return

        best_score = max(self.player_scores)
        winners = [
            i + 1 for i, score in enumerate(self.player_scores) if score == best_score
        ]
        if len(winners) == 1:
            player_index = winners[0] - 1
            winner_name = self.resolve_player_name(player_index)
            header = _(
                "dialogs.multi_player_header_single",
                name=winner_name,
                pairs=best_score,
            )
        else:
            winner_str = ", ".join(
                self.resolve_player_name(winner - 1) for winner in winners
            )
            header = _(
                "dialogs.multi_player_header_multi",
                names=winner_str,
                pairs=best_score,
            )

        scoreboard = "\n".join(
            _(
                "dialogs.multi_player_score_line",
                name=self.resolve_player_name(i),
                pairs=score,
            )
            for i, score in enumerate(self.player_scores)
        )
        messagebox.showinfo(_("dialogs.congrats_title"), f"{header}\n\n{scoreboard}")

    def center_window(self):
        try:
            self.root.state("zoomed")
        except tk.TclError:
            screen_w = self.root.winfo_screenwidth()
            screen_h = self.root.winfo_screenheight()
            self.root.geometry(f"{screen_w}x{screen_h}")
        self.root.update_idletasks()

    def position_board(self, event=None):
        self.board_frame.update_idletasks()
        frame_w = self.board_frame.winfo_width()
        frame_h = self.board_frame.winfo_height()
        board_w = self.board_grid.winfo_reqwidth()
        board_h = self.board_grid.winfo_reqheight()

        pad_x = max(0, (frame_w - board_w) // 2)
        pad_y = max(0, (frame_h - board_h) // 2)
        self.board_grid.grid_configure(padx=pad_x, pady=pad_y)

    def set_language(self, code):
        previous_language = self.language_code
        changed = I18N.set_language(code)
        self.language_code = I18N.lang
        self.last_settings["language"] = self.language_code
        CONFIG["language"] = self.language_code
        if self.language_button is not None:
            self.language_button.config(
                text=I18N.get_language_label(self.language_code)
            )
        reopen_names_dialog = (
            self.names_window is not None and self.names_window.winfo_exists()
        )
        reopen_settings_dialog = (
            self.settings_window is not None and self.settings_window.winfo_exists()
        )
        if reopen_names_dialog:
            self.close_names_window()
        if reopen_settings_dialog:
            self.close_settings_window()
        if self.menu_frame is not None:
            self.menu_frame.destroy()
            self.build_menu()
        elif changed or previous_language != self.language_code:
            self.refresh_game_texts()
        if reopen_names_dialog:
            self.root.after(0, self.open_names_dialog)
        if reopen_settings_dialog:
            self.root.after(0, self.open_settings_dialog)

    def refresh_game_texts(self):
        if self.score_labels:
            self.update_score_labels()
        if self.review_button is not None:
            self.review_button.config(text=_("buttons.review_gallery"))
        if self.menu_button is not None:
            self.menu_button.config(text=_("buttons.back_to_menu"))
        if self.language_button is not None:
            self.language_button.config(
                text=I18N.get_language_label(self.language_code)
            )
        if self.sound_count_label is not None:
            self.sound_count_label.config(
                text=_("menu.sounds_found", count=len(SOUNDS))
            )
        if self.sound_toggle_button is not None:
            self.update_sound_toggle_button()
        if (
            self.image_summary_window is not None
            and self.image_summary_window.winfo_exists()
        ):
            try:
                self.image_summary_window.destroy()
            except tk.TclError:
                pass
            finally:
                self.image_summary_window = None
                self.summary_images = []


if __name__ == "__main__":
    root = tk.Tk()
    MemoryApp(root)
    root.mainloop()
