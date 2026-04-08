"""
System Tray Integration
Minimize to tray and tray menu controls
"""

import threading
from pathlib import Path
from typing import Callable, Optional

try:
    import pystray
    from PIL import Image
    TRAY_AVAILABLE = True
except ImportError:
    TRAY_AVAILABLE = False
    pystray = None
    Image = None


class SystemTray:
    """System tray icon and menu"""
    
    def __init__(
        self,
        on_show: Callable,
        on_quit: Callable,
        on_preset: Optional[Callable] = None,
        icon_path: Optional[Path] = None
    ):
        self.on_show = on_show
        self.on_quit = on_quit
        self.on_preset = on_preset
        self.icon_path = icon_path
        
        self.icon: Optional["pystray.Icon"] = None
        self._running = False
    
    def _create_image(self) -> "Image.Image":
        """Create or load the tray icon"""
        if self.icon_path and self.icon_path.exists():
            try:
                return Image.open(self.icon_path)
            except:
                pass
        
        # Create a simple default icon
        img = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
        
        # Draw a simple "D" shape
        from PIL import ImageDraw
        draw = ImageDraw.Draw(img)
        
        # Background circle
        draw.ellipse([4, 4, 60, 60], fill=(139, 92, 246))  # Purple
        
        # "D" letter
        draw.text((20, 12), "D", fill=(255, 255, 255))
        
        return img
    
    def _create_menu(self) -> "pystray.Menu":
        """Create the tray context menu"""
        items = [
            pystray.MenuItem("Show Window", self._on_show_click, default=True),
            pystray.Menu.SEPARATOR,
        ]
        
        # Quick preset submenu
        if self.on_preset:
            preset_items = [
                pystray.MenuItem("🥔 Potato", lambda: self._on_preset_click("potato")),
                pystray.MenuItem("⚖️ Balanced", lambda: self._on_preset_click("balanced")),
                pystray.MenuItem("💎 Quality", lambda: self._on_preset_click("quality")),
                pystray.MenuItem("🎯 Competitive", lambda: self._on_preset_click("competitive")),
            ]
            items.append(pystray.MenuItem("Quick Apply", pystray.Menu(*preset_items)))
            items.append(pystray.Menu.SEPARATOR)
        
        items.append(pystray.MenuItem("Quit", self._on_quit_click))
        
        return pystray.Menu(*items)
    
    def _on_show_click(self, icon=None, item=None):
        """Handle show window click"""
        if self.on_show:
            self.on_show()
    
    def _on_quit_click(self, icon=None, item=None):
        """Handle quit click"""
        self.stop()
        if self.on_quit:
            self.on_quit()
    
    def _on_preset_click(self, preset_name: str):
        """Handle preset click from tray"""
        if self.on_preset:
            self.on_preset(preset_name)
    
    def start(self):
        """Start the system tray icon"""
        if not TRAY_AVAILABLE:
            print("System tray not available (pystray not installed)")
            return
        
        if self._running:
            return
        
        def run_tray():
            self.icon = pystray.Icon(
                "DeadlockConfigManager",
                self._create_image(),
                "Deadlock Config Manager",
                self._create_menu()
            )
            self._running = True
            self.icon.run()
        
        thread = threading.Thread(target=run_tray, daemon=True)
        thread.start()
    
    def stop(self):
        """Stop the system tray icon"""
        self._running = False
        if self.icon:
            try:
                self.icon.stop()
            except:
                pass
            self.icon = None
    
    def update_icon(self, icon_path: Path):
        """Update the tray icon"""
        self.icon_path = icon_path
        if self.icon:
            try:
                self.icon.icon = self._create_image()
            except:
                pass
    
    def notify(self, title: str, message: str):
        """Show a notification from the tray"""
        if self.icon:
            try:
                self.icon.notify(message, title)
            except:
                pass


# Global tray instance
_tray_instance: Optional[SystemTray] = None


def get_tray() -> Optional[SystemTray]:
    """Get the global tray instance"""
    return _tray_instance


def init_tray(
    on_show: Callable,
    on_quit: Callable,
    on_preset: Optional[Callable] = None,
    icon_path: Optional[Path] = None
) -> Optional[SystemTray]:
    """Initialize and start the system tray"""
    global _tray_instance
    
    if not TRAY_AVAILABLE:
        return None
    
    _tray_instance = SystemTray(on_show, on_quit, on_preset, icon_path)
    _tray_instance.start()
    return _tray_instance


def stop_tray():
    """Stop the system tray"""
    global _tray_instance
    if _tray_instance:
        _tray_instance.stop()
        _tray_instance = None
