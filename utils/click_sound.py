# utils/click_sound.py
import os
from PyQt5.QtCore    import QObject, QEvent
from PyQt5.QtWidgets import QPushButton
from PyQt5.QtMultimedia import QSound 

_SOUND_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "assets", "data", "sound",
    "mixkit-modern-technology-select-3124.wav"
)

class ClickSoundFilter(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._sound = QSound(_SOUND_PATH) if os.path.isfile(_SOUND_PATH) else None
        if self._sound is None:
            print(f"[SOUND] File tidak ditemukan: {_SOUND_PATH}")

    def eventFilter(self, obj, event):
        if (
            self._sound
            and isinstance(obj, QPushButton)
            and event.type() == QEvent.MouseButtonPress
        ):
            self._sound.play()
        return False