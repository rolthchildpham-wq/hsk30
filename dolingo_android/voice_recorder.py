"""Android microphone recorder with permission-aware start/stop/playback.

Recordings never leave the phone. Playback requires a completed local file.
"""
import os
import sys
import time

class VoiceRecorder:
    def __init__(self, directory):
        self.directory = directory
        self.recorder = None
        self.player = None
        self.last_file = ""
        self.error = ""
        if sys.platform != "android":
            self.error = "Ghi âm chỉ khả dụng trong APK Android."
            return
        try:
            from jnius import autoclass
            self.MediaRecorder = autoclass("android.media.MediaRecorder")
            self.MediaPlayer = autoclass("android.media.MediaPlayer")
        except Exception as exc:
            self.error = "Không khởi tạo được microphone: " + str(exc)

    def request_permission(self, callback):
        if sys.platform != "android":
            callback(False)
            return
        try:
            from android.permissions import Permission, request_permissions
            def on_response(perms, grants):
                callback(bool(grants) and all(grants))
            request_permissions([Permission.RECORD_AUDIO], on_response)
        except Exception as exc:
            self.error = str(exc)
            callback(False)

    def start(self):
        if not hasattr(self, "MediaRecorder"):
            return False, self.error or "Microphone không có sẵn."
        try:
            os.makedirs(self.directory, exist_ok=True)
            self.last_file = os.path.join(self.directory, "practice_%d.m4a" % int(time.time()*1000))
            self.recorder = self.MediaRecorder()
            self.recorder.setAudioSource(self.MediaRecorder.AudioSource.MIC)
            self.recorder.setOutputFormat(self.MediaRecorder.OutputFormat.MPEG_4)
            self.recorder.setAudioEncoder(self.MediaRecorder.AudioEncoder.AAC)
            self.recorder.setOutputFile(self.last_file)
            self.recorder.prepare()
            self.recorder.start()
            return True, "Đang ghi âm. Nhấn DỪNG khi đọc xong."
        except Exception as exc:
            self.stop(discard=True)
            return False, "Không thể ghi âm: " + str(exc)

    def stop(self, discard=False):
        if self.recorder is None:
            return False, "Chưa bắt đầu ghi âm."
        try:
            self.recorder.stop()
            ok = True
            message = "Đã lưu bản ghi trên máy."
        except Exception as exc:
            ok = False
            message = "Ghi âm quá ngắn hoặc bị lỗi: " + str(exc)
        finally:
            try:
                self.recorder.reset()
                self.recorder.release()
            except Exception:
                pass
            self.recorder = None
        if discard or not ok:
            try:
                os.remove(self.last_file)
            except OSError:
                pass
            self.last_file = ""
        return ok and not discard, message

    def play(self):
        if not self.last_file or not os.path.isfile(self.last_file):
            return False, "Chưa có bản ghi để nghe."
        try:
            if self.player:
                self.player.release()
            self.player = self.MediaPlayer()
            self.player.setDataSource(self.last_file)
            self.player.prepare()
            self.player.start()
            return True, "Đang phát bản ghi của bạn."
        except Exception as exc:
            return False, "Lỗi phát lại: " + str(exc)

    def close(self):
        if self.recorder:
            self.stop()
        if self.player:
            try:
                self.player.release()
            except Exception:
                pass
            self.player = None
