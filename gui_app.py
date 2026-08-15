"""
YouTube 채널/재생목록 대본 추출기 - 데스크톱 팝업 프로그램 (GUI App)
"""

import os
import sys
import asyncio
import threading
import subprocess
from typing import List, Dict, Optional

# 경로 설정: backend 모듈 임포트 가능하도록 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.join(current_dir, "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

import customtkinter as ctk
from tkinter import filedialog, messagebox

from app.url_parser import detect_url_type
from app.video_lister import list_videos
from app.transcript_fetcher import fetch_transcript, YoutubeBlockedError
from app.text_cleaner import sanitize_filename
from app.exporter import export_zip, export_markdown, export_json
from app.models import VideoInfo, VideoJobStatus, VideoStatus


ctk.set_appearance_mode("System")  # "System", "Dark", "Light"
ctk.set_default_color_theme("blue")  # Themes: "blue", "green", "dark-blue"


class YouTubeTranscriptApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("📺 YouTube 채널/재생목록 대본 추출기")
        self.geometry("960x780")
        self.minsize(800, 600)

        # 데이터 상태
        self.videos: List[VideoInfo] = []
        self.video_vars: Dict[str, ctk.BooleanVar] = {}
        self.video_widgets: Dict[str, dict] = {}
        self.source_title: str = "YouTube_대본"
        self.cookie_path: Optional[str] = None
        self.output_dir: str = os.path.join(current_dir, "output")
        self.is_processing: bool = False

        os.makedirs(self.output_dir, exist_ok=True)
        os.environ["OUTPUT_DIR"] = self.output_dir

        # 현재 폴더에 cookies.txt가 있으면 자동 감지
        for default_cookie in ["cookies.txt", "youtube.com_cookies.txt", "youtube_cookies.txt"]:
            cp = os.path.join(current_dir, default_cookie)
            if os.path.exists(cp):
                self.cookie_path = cp
                os.environ["COOKIE_FILE_PATH"] = cp
                break

        self._build_ui()

    def _build_ui(self):
        # 최상위 컨테이너 그리드 설정
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # ── 1. 헤더 영역 ──
        header_frame = ctk.CTkFrame(self, corner_radius=10)
        header_frame.grid(row=0, column=0, padx=15, pady=(15, 10), sticky="ew")

        title_label = ctk.CTkLabel(
            header_frame,
            text="📺 YouTube 채널 / 재생목록 대본 추출기",
            font=ctk.CTkFont(size=20, weight="bold"),
        )
        title_label.pack(side="left", padx=15, pady=10)

        theme_btn = ctk.CTkOptionMenu(
            header_frame,
            values=["System", "Dark", "Light"],
            command=self._change_theme,
            width=100,
        )
        theme_btn.pack(side="right", padx=15, pady=10)

        # ── 2. 입력 및 옵션 영역 ──
        input_frame = ctk.CTkFrame(self, corner_radius=10)
        input_frame.grid(row=1, column=0, padx=15, pady=5, sticky="ew")
        input_frame.grid_columnconfigure(0, weight=1)

        # URL 입력창
        url_subframe = ctk.CTkFrame(input_frame, fg_color="transparent")
        url_subframe.grid(row=0, column=0, columnspan=2, padx=15, pady=(10, 5), sticky="ew")
        url_subframe.grid_columnconfigure(0, weight=1)

        self.url_entry = ctk.CTkEntry(
            url_subframe,
            placeholder_text="YouTube 채널 URL(@handle, /channel/...) 또는 재생목록 링크를 붙여넣으세요",
            height=40,
            font=ctk.CTkFont(size=13),
        )
        self.url_entry.grid(row=0, column=0, padx=(0, 10), sticky="ew")
        self.url_entry.bind("<Return>", lambda e: self._on_fetch_videos())

        self.fetch_btn = ctk.CTkButton(
            url_subframe,
            text="🔍 영상 목록 가져오기",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=40,
            width=160,
            command=self._on_fetch_videos,
        )
        self.fetch_btn.grid(row=0, column=1)

        # 필터 & 쿠키 옵션
        options_subframe = ctk.CTkFrame(input_frame, fg_color="transparent")
        options_subframe.grid(row=1, column=0, columnspan=2, padx=15, pady=(5, 10), sticky="ew")

        self.shorts_var = ctk.BooleanVar(value=False)
        self.shorts_check = ctk.CTkCheckBox(options_subframe, text="쇼츠 포함", variable=self.shorts_var)
        self.shorts_check.pack(side="left", padx=(0, 15))

        self.live_var = ctk.BooleanVar(value=False)
        self.live_check = ctk.CTkCheckBox(options_subframe, text="라이브 스트림 포함", variable=self.live_var)
        self.live_check.pack(side="left", padx=(0, 20))

        self.cookie_btn = ctk.CTkButton(
            options_subframe,
            text="🍪 cookies.txt 선택",
            font=ctk.CTkFont(size=12),
            fg_color="#555555",
            hover_color="#666666",
            height=28,
            command=self._on_select_cookie,
        )
        self.cookie_btn.pack(side="left", padx=3)

        self.cookie_help_btn = ctk.CTkButton(
            options_subframe,
            text="❓ 쿠키 얻는 법",
            font=ctk.CTkFont(size=11),
            fg_color="#333333",
            hover_color="#444444",
            width=85,
            height=28,
            command=self._show_cookie_help,
        )
        self.cookie_help_btn.pack(side="left", padx=3)

        cookie_txt = f"적용됨: {os.path.basename(self.cookie_path)}" if self.cookie_path else ""
        cookie_col = "green" if self.cookie_path else "gray"
        self.cookie_label = ctk.CTkLabel(options_subframe, text=cookie_txt, font=ctk.CTkFont(size=11), text_color=cookie_col)
        self.cookie_label.pack(side="left", padx=5)

        # ── 3. 영상 목록 영역 (스크롤) ──
        list_container = ctk.CTkFrame(self, corner_radius=10)
        list_container.grid(row=2, column=0, padx=15, pady=5, sticky="nsew")
        list_container.grid_columnconfigure(0, weight=1)
        list_container.grid_rowconfigure(1, weight=1)

        # 목록 헤더 및 선택 도구
        list_header = ctk.CTkFrame(list_container, fg_color="transparent")
        list_header.grid(row=0, column=0, padx=15, pady=(10, 5), sticky="ew")

        self.status_title_label = ctk.CTkLabel(
            list_header,
            text="영상 목록이 여기에 표시됩니다 (0개)",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        self.status_title_label.pack(side="left")

        tool_frame = ctk.CTkFrame(list_header, fg_color="transparent")
        tool_frame.pack(side="right")

        self.select_all_btn = ctk.CTkButton(
            tool_frame, text="전체 선택", width=80, height=28, command=self._select_all
        )
        self.select_all_btn.pack(side="left", padx=3)

        self.deselect_all_btn = ctk.CTkButton(
            tool_frame, text="선택 해제", width=80, height=28, fg_color="#555555", command=self._deselect_all
        )
        self.deselect_all_btn.pack(side="left", padx=3)

        ctk.CTkLabel(tool_frame, text="최근").pack(side="left", padx=(10, 2))
        self.recent_count_entry = ctk.CTkEntry(tool_frame, width=50, height=28)
        self.recent_count_entry.insert(0, "10")
        self.recent_count_entry.pack(side="left", padx=2)
        ctk.CTkLabel(tool_frame, text="개").pack(side="left", padx=2)

        self.select_recent_btn = ctk.CTkButton(
            tool_frame, text="선택", width=50, height=28, command=self._select_recent
        )
        self.select_recent_btn.pack(side="left", padx=3)

        # 스크롤 가능한 영상 리스트 프레임
        self.scroll_frame = ctk.CTkScrollableFrame(list_container)
        self.scroll_frame.grid(row=1, column=0, padx=15, pady=(5, 10), sticky="nsew")
        self.scroll_frame.grid_columnconfigure(1, weight=1)

        self.empty_label = ctk.CTkLabel(
            self.scroll_frame,
            text="YouTube URL을 입력하고 [영상 목록 가져오기]를 클릭하세요.",
            text_color="gray",
        )
        self.empty_label.pack(pady=40)

        # ── 4. 하단 설정 및 실행 영역 ──
        bottom_frame = ctk.CTkFrame(self, corner_radius=10)
        bottom_frame.grid(row=3, column=0, padx=15, pady=(5, 15), sticky="ew")
        bottom_frame.grid_columnconfigure(0, weight=1)

        # 설정 행
        config_row = ctk.CTkFrame(bottom_frame, fg_color="transparent")
        config_row.grid(row=0, column=0, padx=15, pady=(10, 5), sticky="ew")

        ctk.CTkLabel(config_row, text="🌐 자막 언어:").pack(side="left", padx=(0, 5))
        self.lang_entry = ctk.CTkEntry(config_row, width=100, height=30)
        self.lang_entry.insert(0, "ko, en")
        self.lang_entry.pack(side="left", padx=(0, 20))

        ctk.CTkLabel(config_row, text="📁 출력 포맷:").pack(side="left", padx=(0, 5))
        self.format_var = ctk.StringVar(value="all")
        self.format_menu = ctk.CTkOptionMenu(
            config_row,
            variable=self.format_var,
            values=["모두 생성 (ZIP+MD+JSON)", "ZIP (개별 txt)", "Markdown (.md 통합)", "JSON (.json 정형)"],
            width=180,
            height=30,
        )
        self.format_menu.pack(side="left", padx=(0, 20))

        self.open_dir_btn = ctk.CTkButton(
            config_row,
            text="📂 저장 폴더 열기",
            height=30,
            fg_color="#444444",
            hover_color="#555555",
            command=self._open_output_dir,
        )
        self.open_dir_btn.pack(side="right")

        # 프로그레스 바 & 상태 텍스트
        self.progress_bar = ctk.CTkProgressBar(bottom_frame)
        self.progress_bar.grid(row=1, column=0, padx=15, pady=5, sticky="ew")
        self.progress_bar.set(0)

        status_row = ctk.CTkFrame(bottom_frame, fg_color="transparent")
        status_row.grid(row=2, column=0, padx=15, pady=(0, 10), sticky="ew")

        self.progress_label = ctk.CTkLabel(
            status_row,
            text="준비 완료",
            font=ctk.CTkFont(size=12),
            text_color="gray",
        )
        self.progress_label.pack(side="left")

        self.start_btn = ctk.CTkButton(
            status_row,
            text="🚀 대본 추출 시작",
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color="#e53935",
            hover_color="#c62828",
            height=42,
            width=200,
            command=self._on_start_extraction,
        )
        self.start_btn.pack(side="right")

    def _change_theme(self, mode: str):
        ctk.set_appearance_mode(mode)

    def _show_cookie_help(self):
        msg = (
            "🍪 cookies.txt 추출 및 적용 방법 (30초 완료):\n\n"
            "1. Chrome 또는 Edge 브라우저 확장 프로그램 설치:\n"
            "   • 'Get cookies.txt LOCALLY' (무료)\n\n"
            "2. 유튜브(youtube.com) 사이트 접속 후 확장 프로그램 클릭:\n"
            "   • [Export] 버튼 클릭 → 'cookies.txt' 다운로드\n\n"
            "3. 이 프로그램 상단의 [🍪 cookies.txt 선택] 클릭 후 다운받은 파일 선택!\n\n"
            "※ 쿠키를 등록하면 YouTube 봇 감지(429/IP 차단)를 100% 우회하여 모든 자막이 정상 추출됩니다."
        )
        messagebox.showinfo("쿠키 파일(cookies.txt) 추출 안내", msg)

    def _on_select_cookie(self):
        path = filedialog.askopenfilename(
            title="cookies.txt 파일 선택",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
        )
        if path:
            self.cookie_path = path
            os.environ["COOKIE_FILE_PATH"] = path
            filename = os.path.basename(path)
            self.cookie_label.configure(text=f"적용됨: {filename}", text_color="green")

    def _open_output_dir(self):
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir, exist_ok=True)
        if sys.platform == "win32":
            os.startfile(self.output_dir)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", self.output_dir])
        else:
            subprocess.Popen(["xdg-open", self.output_dir])

    # ── 영상 목록 가져오기 비동기 처리 ──
    def _on_fetch_videos(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("입력 필요", "YouTube URL을 입력해주세요.")
            return

        url_type = detect_url_type(url)
        if url_type == "invalid":
            messagebox.showerror(
                "유효하지 않은 URL",
                "유효한 YouTube 채널 또는 재생목록 URL이 아닙니다.\n(예: https://www.youtube.com/@채널명)",
            )
            return

        self.fetch_btn.configure(state="disabled", text="⏳ 가져오는 중...")
        self.progress_label.configure(text="영상 목록을 수집하고 있습니다...")

        thread = threading.Thread(
            target=self._async_fetch_videos_worker,
            args=(url, self.shorts_var.get(), self.live_var.get()),
            daemon=True,
        )
        thread.start()

    def _async_fetch_videos_worker(self, url: str, include_shorts: bool, include_live: bool):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            title, videos = loop.run_until_complete(list_videos(url, include_shorts, include_live))
            self.after(0, self._render_video_list, title, videos)
        except Exception as e:
            self.after(0, self._on_fetch_error, str(e))
        finally:
            loop.close()

    def _on_fetch_error(self, err_msg: str):
        self.fetch_btn.configure(state="normal", text="🔍 영상 목록 가져오기")
        self.progress_label.configure(text=f"목록 수집 실패: {err_msg}")
        messagebox.showerror("오류 발생", f"영상 목록을 가져오지 못했습니다:\n{err_msg}")

    def _render_video_list(self, title: str, videos: List[VideoInfo]):
        self.fetch_btn.configure(state="normal", text="🔍 영상 목록 가져오기")
        self.videos = videos
        self.source_title = title or "YouTube_대본"

        for widget in self.scroll_frame.winfo_children():
            widget.destroy()

        self.video_vars.clear()
        self.video_widgets.clear()

        if not videos:
            ctk.CTkLabel(
                self.scroll_frame,
                text="영상 목록이 비어있습니다. (쇼츠/라이브 필터 옵션을 확인해보세요)",
                text_color="gray",
            ).pack(pady=40)
            self.status_title_label.configure(text=f"{title} (0개)")
            return

        self.status_title_label.configure(text=f"{title} (총 {len(videos)}개 영상)")
        self.progress_label.configure(text=f"{len(videos)}개 영상 로드 완료. 추출할 영상을 선택하세요.")

        for idx, video in enumerate(videos):
            item_frame = ctk.CTkFrame(self.scroll_frame, corner_radius=6)
            item_frame.pack(fill="x", padx=5, pady=3)
            item_frame.grid_columnconfigure(1, weight=1)

            var = ctk.BooleanVar(value=(idx < 50))
            self.video_vars[video.video_id] = var

            chk = ctk.CTkCheckBox(
                item_frame,
                text="",
                variable=var,
                width=24,
                command=self._update_selected_count,
            )
            chk.grid(row=0, column=0, rowspan=2, padx=(10, 5), pady=8)

            title_label = ctk.CTkLabel(
                item_frame,
                text=video.title,
                font=ctk.CTkFont(size=13, weight="bold"),
                anchor="w",
            )
            title_label.grid(row=0, column=1, sticky="w", padx=5, pady=(6, 0))

            duration_str = self._format_duration(video.duration)
            date_str = self._format_date(video.upload_date)
            meta_text = f"업로드: {date_str}" if date_str else ""
            if duration_str:
                meta_text += f" • 길이: {duration_str}"

            meta_label = ctk.CTkLabel(
                item_frame,
                text=meta_text,
                font=ctk.CTkFont(size=11),
                text_color="gray",
                anchor="w",
            )
            meta_label.grid(row=1, column=1, sticky="w", padx=5, pady=(0, 6))

            status_label = ctk.CTkLabel(
                item_frame,
                text="대기중",
                font=ctk.CTkFont(size=12),
                text_color="gray",
                width=110,
            )
            status_label.grid(row=0, column=2, rowspan=2, padx=10, pady=8)

            self.video_widgets[video.video_id] = {
                "frame": item_frame,
                "status_label": status_label,
            }

        self._update_selected_count()

    def _select_all(self):
        for var in self.video_vars.values():
            var.set(True)
        self._update_selected_count()

    def _deselect_all(self):
        for var in self.video_vars.values():
            var.set(False)
        self._update_selected_count()

    def _select_recent(self):
        try:
            count = int(self.recent_count_entry.get().strip())
        except ValueError:
            count = 10
        self._deselect_all()
        for idx, video in enumerate(self.videos):
            if idx < count:
                if video.video_id in self.video_vars:
                    self.video_vars[video.video_id].set(True)
        self._update_selected_count()

    def _update_selected_count(self):
        selected_count = sum(1 for v in self.video_vars.values() if v.get())
        total_count = len(self.videos)
        self.start_btn.configure(text=f"🚀 대본 추출 시작 ({selected_count}개)")

    def _format_duration(self, seconds: Optional[int]) -> str:
        if not seconds:
            return ""
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        if h > 0:
            return f"{h}:{m:02d}:{s:02d}"
        return f"{m}:{s:02d}"

    def _format_date(self, date_str: Optional[str]) -> str:
        if not date_str or len(date_str) != 8:
            return date_str or ""
        return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"

    # ── 대본 추출 비동기 실행 ──
    def _on_start_extraction(self):
        if self.is_processing:
            messagebox.showinfo("알림", "이미 작업이 진행 중입니다.")
            return

        selected_video_ids = [vid for vid, var in self.video_vars.items() if var.get()]
        if not selected_video_ids:
            messagebox.showwarning("선택 필요", "대본을 추출할 영상을 1개 이상 선택해주세요.")
            return

        self.is_processing = True
        self.start_btn.configure(state="disabled", text="⏳ 추출 진행 중...")
        self.fetch_btn.configure(state="disabled")
        self.progress_bar.set(0)

        langs = [l.strip() for l in self.lang_entry.get().split(",") if l.strip()]
        if not langs:
            langs = ["ko", "en"]

        selected_videos = [v for v in self.videos if v.video_id in selected_video_ids]

        thread = threading.Thread(
            target=self._extraction_worker,
            args=(selected_videos, langs, self.format_var.get()),
            daemon=True,
        )
        thread.start()

    def _extraction_worker(self, selected_videos: List[VideoInfo], languages: List[str], export_fmt_choice: str):
        import uuid

        job_id = str(uuid.uuid4())
        job_dir = self.output_dir
        os.makedirs(job_dir, exist_ok=True)

        total = len(selected_videos)
        completed = 0
        success_count = 0
        no_sub_count = 0
        blocked_count = 0
        fail_count = 0

        results: List[VideoJobStatus] = []

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            for idx, video in enumerate(selected_videos):
                vid = video.video_id
                self.after(0, self._update_video_ui_status, vid, "🔄 추출중...", "#2196f3")
                self.after(
                    0,
                    self._update_progress_ui,
                    completed / total,
                    f"진행 중 ({completed}/{total}) - '{video.title[:25]}...'",
                )

                res = VideoJobStatus(
                    video_id=vid,
                    title=video.title,
                    status=VideoStatus.PENDING,
                    upload_date=video.upload_date,
                )

                try:
                    transcript, lang = loop.run_until_complete(
                        fetch_transcript(vid, languages)
                    )

                    if transcript:
                        res.status = VideoStatus.COMPLETED
                        res.language = lang
                        safe_title = sanitize_filename(video.title) or vid
                        filename = f"{video.upload_date}_{safe_title}.txt" if video.upload_date else f"{safe_title}.txt"
                        res.file_name = filename
                        filepath = os.path.join(job_dir, filename)

                        with open(filepath, "w", encoding="utf-8") as f:
                            f.write(transcript)

                        success_count += 1
                        self.after(0, self._update_video_ui_status, vid, "✅ 완료", "#4caf50")
                    else:
                        res.status = VideoStatus.NO_SUBTITLE
                        no_sub_count += 1
                        self.after(0, self._update_video_ui_status, vid, "⚠️ 자막없음", "#ff9800")

                except YoutubeBlockedError as e:
                    res.status = VideoStatus.BLOCKED
                    res.error = str(e)
                    blocked_count += 1
                    self.after(0, self._update_video_ui_status, vid, "🚫 봇차단(쿠키필요)", "#e65100")

                except Exception as e:
                    res.status = VideoStatus.FAILED
                    res.error = str(e)
                    fail_count += 1
                    self.after(0, self._update_video_ui_status, vid, "❌ 실패", "#f44336")

                results.append(res)
                completed += 1
                self.after(
                    0,
                    self._update_progress_ui,
                    completed / total,
                    f"진행 중 ({completed}/{total}) | 성공: {success_count}, 자막없음: {no_sub_count}, 봇차단: {blocked_count}, 실패: {fail_count}",
                )

            # ── 파일 내보내기 ──
            exported_files = []
            if success_count > 0:
                if "ZIP" in export_fmt_choice or "모두" in export_fmt_choice:
                    zip_path = loop.run_until_complete(export_zip(job_id, results, self.source_title))
                    exported_files.append(os.path.basename(zip_path))

                if "Markdown" in export_fmt_choice or "모두" in export_fmt_choice:
                    md_path = loop.run_until_complete(export_markdown(job_id, results, self.source_title))
                    exported_files.append(os.path.basename(md_path))

                if "JSON" in export_fmt_choice or "모두" in export_fmt_choice:
                    json_path = loop.run_until_complete(export_json(job_id, results, self.source_title))
                    exported_files.append(os.path.basename(json_path))

            self.after(
                0,
                self._on_extraction_completed,
                job_dir,
                total,
                success_count,
                no_sub_count,
                blocked_count,
                fail_count,
                exported_files,
            )

        finally:
            loop.close()

    def _update_video_ui_status(self, video_id: str, text: str, color: str):
        if video_id in self.video_widgets:
            lbl = self.video_widgets[video_id]["status_label"]
            lbl.configure(text=text, text_color=color)

    def _update_progress_ui(self, progress: float, status_text: str):
        self.progress_bar.set(progress)
        self.progress_label.configure(text=status_text)

    def _on_extraction_completed(
        self, job_dir: str, total: int, success: int, no_sub: int, blocked: int, fail: int, exported_files: List[str]
    ):
        self.is_processing = False
        self.start_btn.configure(state="normal", text="🚀 대본 추출 시작")
        self.fetch_btn.configure(state="normal")
        self.progress_bar.set(1.0)
        self.progress_label.configure(
            text=f"완료! 총 {total}개 중 성공 {success}개, 자막없음 {no_sub}개, 봇차단 {blocked}개, 실패 {fail}개"
        )

        if blocked > 0:
            msg_blocked = (
                f"⚠️ YouTube 봇 감지(429 / IP 차단) 발생 알림\n\n"
                f"{blocked}개 영상의 자막 추출이 YouTube IP 제한으로 인해 일시 차단되었습니다.\n\n"
                f"👉 해결 방법:\n"
                f"1. 브라우저에서 'cookies.txt' 파일을 추출합니다. (상단 [❓ 쿠키 얻는 법] 참고)\n"
                f"2. 상단 [🍪 cookies.txt 선택]에 등록 후 다시 [대본 추출 시작]을 누르면 100% 정상 추출됩니다."
            )
            messagebox.showwarning("YouTube 봇 차단 감지", msg_blocked)

        msg = (
            f"대본 추출 작업이 완료되었습니다!\n\n"
            f"• 전체 영상: {total}개\n"
            f"• ✅ 성공: {success}개\n"
            f"• ⚠️ 자막 없음: {no_sub}개\n"
            f"• 🚫 봇 차단(쿠키필요): {blocked}개\n"
            f"• ❌ 실패: {fail}개\n\n"
            f"생성된 파일:\n{', '.join(exported_files) if exported_files else '개별 txt 파일 저장됨'}\n\n"
            f"결과 폴더(output)를 여시겠습니까?"
        )
        if messagebox.askyesno("추출 완료", msg):
            if sys.platform == "win32":
                os.startfile(job_dir)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", job_dir])
            else:
                subprocess.Popen(["xdg-open", job_dir])


def main():
    app = YouTubeTranscriptApp()
    app.mainloop()


if __name__ == "__main__":
    main()
