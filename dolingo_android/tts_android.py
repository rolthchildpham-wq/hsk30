"""Android native bilingual text-to-speech.

Uses the installed Android TTS engine and supports zh-CN and en-US voices.
Offline sound requires those voice packs to be installed on the device.
No permissions, network requests, or external API keys.
"""
import sys

class Pronouncer:
    def __init__(self):
        self.engine = None
        self.listener = None
        self.ready = False
        self.error = ""
        if sys.platform != "android":
            self.error = "Chỉ phát âm trực tiếp trên Android."
            return
        try:
            from jnius import autoclass, PythonJavaClass, java_method
            self._tts_cls = autoclass("android.speech.tts.TextToSpeech")
            self._locale_cls = autoclass("java.util.Locale")
            activity = autoclass("org.kivy.android.PythonActivity").mActivity
            parent = self

            class InitListener(PythonJavaClass):
                __javainterfaces__ = ["android/speech/tts/TextToSpeech$OnInitListener"]
                __javacontext__ = "app"

                @java_method("(I)V")
                def onInit(self, status):
                    parent.ready = status == 0
                    if not parent.ready:
                        parent.error = "Bộ đọc của Android chưa sẵn sàng."

            self.listener = InitListener()
            self.engine = self._tts_cls(activity, self.listener)
        except Exception as exc:
            self.error = "Không thể khởi động phát âm: " + str(exc)

    def speak(self, text, language):
        text = (text or "").strip()
        if not text:
            return False, "Không có văn bản để đọc."
        if self.engine is None or not self.ready:
            return False, self.error or "Bộ đọc đang khởi động. Hãy thử lại."
        try:
            locale = self._locale_cls("zh", "CN") if language == "zh" else self._locale_cls("en", "US")
            result = self.engine.setLanguage(locale)
            if result in (-1, -2):
                return False, ("Thiếu giọng " + ("Trung" if language == "zh" else "Anh") +
                               ". Cài dữ liệu giọng nói trong Cài đặt Android.")
            utterance_id = "dolingo-" + language
            code = self.engine.speak(text, self._tts_cls.QUEUE_FLUSH, None, utterance_id)
            if code != 0:
                return False, "Android chưa phát được giọng nói."
            return True, "Đang phát âm"
        except Exception as exc:
            return False, "Lỗi phát âm: " + str(exc)

    def close(self):
        try:
            if self.engine is not None:
                self.engine.stop()
                self.engine.shutdown()
        except Exception:
            pass
        self.engine = None
