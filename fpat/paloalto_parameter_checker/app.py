import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, ttk
import os
from datetime import datetime
import logging
import json
import threading
import yaml

from ssh_connector import PaloAltoSSHConnector
from parameter_checker import ParameterChecker
from report_generator import ReportGenerator

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LoadingDialog(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        
        # 대화상자 설정
        self.title("")
        window_width = 300
        window_height = 100
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        center_x = int(screen_width/2 - window_width/2)
        center_y = int(screen_height/2 - window_height/2)
        self.geometry(f'{window_width}x{window_height}+{center_x}+{center_y}')
        
        self.transient(parent)
        self.grab_set()
        
        # 프로그레스 바
        self.progress = ctk.CTkProgressBar(self)
        self.progress.pack(pady=10)
        self.progress.configure(mode="indeterminate")
        self.progress.start()
        
        # 메시지 레이블
        self.message = ctk.CTkLabel(self, text="점검 중...")
        self.message.pack(pady=5)

class ParameterCheckerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # 앱 설정
        self.title("Palo Alto Parameter Checker")
        self.geometry("800x600")
        
        # 테마 설정
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # 변수 초기화
        self.parameter_checker = None
        self.report_generator = None
        self.connection_info = None
        self.check_results = None
        self.loading_dialog = None
        
        # 매개변수 설정 로드
        self.parameters_config = self._load_parameters_config()

        # UI 초기화
        self.setup_ui()
        
        # 초기 매개변수 표시
        self._display_initial_parameters()

    def setup_ui(self):
        """UI 구성"""
        # 연결 프레임
        self.connection_frame = ctk.CTkFrame(self)
        self.connection_frame.pack(fill="x", padx=10, pady=(5, 0))

        # 입력 필드와 버튼을 담을 프레임
        content_frame = ctk.CTkFrame(self.connection_frame, fg_color="transparent")
        content_frame.pack(pady=5)

        # 입력 필드들을 그리드로 배치
        row = 0
        col = 0

        # 호스트 입력
        ctk.CTkLabel(content_frame, text="호스트:").grid(row=row, column=col, padx=5)
        col += 1
        self.host_entry = ctk.CTkEntry(content_frame, width=150)
        self.host_entry.grid(row=row, column=col, padx=5)
        col += 1

        # 사용자 입력
        ctk.CTkLabel(content_frame, text="사용자:").grid(row=row, column=col, padx=5)
        col += 1
        self.username_entry = ctk.CTkEntry(content_frame, width=150)
        self.username_entry.grid(row=row, column=col, padx=5)
        col += 1

        # 비밀번호 입력
        ctk.CTkLabel(content_frame, text="비밀번호:").grid(row=row, column=col, padx=5)
        col += 1
        self.password_entry = ctk.CTkEntry(content_frame, show="*", width=150)
        self.password_entry.grid(row=row, column=col, padx=5)
        col += 1

        # 버튼들
        self.connect_button = ctk.CTkButton(content_frame, text="연결 및 점검", command=self.connect_and_check)
        self.connect_button.grid(row=row, column=col, padx=5)
        col += 1

        self.report_button = ctk.CTkButton(content_frame, text="리포트 생성", command=self.generate_report)
        self.report_button.grid(row=row, column=col, padx=5)
        self.report_button.configure(state="disabled")

        # 결과 표시 프레임
        self.results_frame = ctk.CTkFrame(self)
        self.results_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # 트리뷰와 세로 스크롤바를 담을 프레임
        tree_frame = ttk.Frame(self.results_frame)
        tree_frame.pack(fill="both", expand=True)

        # 결과 트리뷰 설정
        columns = ("Parameter", "Expected", "Current", "Status", "Query", "Modify")
        self.results_tree = ttk.Treeview(
            tree_frame,
            columns=columns,
            show="headings",
            selectmode="browse"
        )
        
        # 스크롤바 추가
        tree_scroll_y = ttk.Scrollbar(tree_frame, orient="vertical", command=self.results_tree.yview)
        tree_scroll_x = ttk.Scrollbar(self.results_frame, orient="horizontal", command=self.results_tree.xview)
        
        # 스크롤바 연결
        self.results_tree.configure(yscrollcommand=tree_scroll_y.set, xscrollcommand=tree_scroll_x.set)
        
        # 컬럼 설정
        self.results_tree.heading("Parameter", text="매개변수")
        self.results_tree.heading("Expected", text="기대값")
        self.results_tree.heading("Current", text="현재값")
        self.results_tree.heading("Status", text="상태")
        self.results_tree.heading("Query", text="조회 방법")
        self.results_tree.heading("Modify", text="변경 방법")
        
        # 컬럼 너비 설정
        self.results_tree.column("Parameter", width=150, minwidth=100)
        self.results_tree.column("Expected", width=150, minwidth=100)
        self.results_tree.column("Current", width=150, minwidth=100)
        self.results_tree.column("Status", width=80, minwidth=70)
        self.results_tree.column("Query", width=300, minwidth=200)
        self.results_tree.column("Modify", width=300, minwidth=200)
        
        # 태그 설정 (상태값 색상)
        self.results_tree.tag_configure('pass', foreground='#00ff00')  # 초록색
        self.results_tree.tag_configure('fail', foreground='#ff0000')  # 빨간색
        self.results_tree.tag_configure('error', foreground='#ff8c00') # 주황색
        
        # 배치 (pack 사용)
        self.results_tree.pack(side="left", fill="both", expand=True)
        tree_scroll_y.pack(side="right", fill="y")
        tree_scroll_x.pack(side="bottom", fill="x", before=tree_frame)

        # 키보드 단축키 바인딩
        self.results_tree.bind("<Control-c>", self.copy_selected_content)
        
        # 선택 이벤트 바인딩
        self.results_tree.bind("<<TreeviewSelect>>", self.on_select)



    def _load_parameters_config(self):
        """parameters.yaml 설정 파일 로드"""
        try:
            config_path = os.path.join(os.path.dirname(__file__), 'parameters.yaml')
            
            with open(config_path, 'r', encoding='utf-8') as file:
                config = yaml.safe_load(file)
            
            return config.get('parameters', [])
            
        except Exception as e:
            logger.error(f"설정 파일 로드 오류: {str(e)}")
            messagebox.showerror("오류", f"설정 파일 로드 오류: {str(e)}")
            return []

    def _display_initial_parameters(self):
        """초기 매개변수 정보 표시"""
        # 기존 항목 삭제
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)
        
        # 매개변수 정보 추가
        for param in self.parameters_config:
            self.results_tree.insert("", tk.END, values=(
                param.get('name', ''),
                param.get('expected_value', ''),
                '점검 필요',  # 현재값
                '-',         # 상태
                param.get('query_command', ''),
                param.get('modify_command', '')
            ))

    def _update_parameter_status(self, item_id, current_value, status):
        """매개변수 상태 업데이트"""
        values = list(self.results_tree.item(item_id)['values'])
        values[2] = current_value  # 현재값
        values[3] = status        # 상태
        
        # 상태값에 따른 태그 적용
        self.results_tree.item(item_id, values=values, tags=(status.lower(),))
        self.update_idletasks()

    def connect_and_check(self):
        """SSH 연결 및 매개변수 점검"""
        try:
            host = self.host_entry.get()
            username = self.username_entry.get()
            password = self.password_entry.get()
            port = 22

            if not all([host, username, password]):
                messagebox.showerror("오류", "호스트, 사용자명, 비밀번호는 필수입니다.")
                return

            # 로딩 대화상자 표시
            self.loading_dialog = LoadingDialog(self)
            self.update_idletasks()

            def check_parameters():
                try:
                    # SSH 연결 테스트
                    ssh_connector = PaloAltoSSHConnector(host, username, password, port)
                    connection_result = ssh_connector.connect()

                    if not connection_result['success']:
                        self.loading_dialog.destroy()
                        messagebox.showerror("오류", f"SSH 연결 실패: {connection_result['error']}")
                        return

                    # Parameter Checker 초기화
                    self.parameter_checker = ParameterChecker(ssh_connector)
                    self.report_generator = ReportGenerator()
                    self.connection_info = {
                        'host': host,
                        'username': username,
                        'port': port,
                        'connected_at': datetime.now().isoformat()
                    }

                    # 각 매개변수 점검
                    results = []
                    for param in self.parameters_config:
                        param_name = param.get('name')
                        result = self.parameter_checker.check_single_parameter_by_name(param_name)
                        results.append(result)
                        
                        # UI 업데이트
                        self._update_parameter_status(
                            param_name,
                            result.get('current_value', '오류'),
                            result['status']
                        )

                    self.check_results = results
                    ssh_connector.disconnect()
                    self.report_button.configure(state="normal")
                    
                    # 로딩 대화상자 닫기
                    self.loading_dialog.destroy()
                    messagebox.showinfo("성공", "매개변수 점검이 완료되었습니다.")

                except Exception as e:
                    logger.error(f"연결/점검 오류: {str(e)}")
                    self.loading_dialog.destroy()
                    messagebox.showerror("오류", f"연결/점검 오류: {str(e)}")

            # 별도 스레드에서 점검 실행
            threading.Thread(target=check_parameters, daemon=True).start()

        except Exception as e:
            if self.loading_dialog:
                self.loading_dialog.destroy()
            logger.error(f"연결/점검 오류: {str(e)}")
            messagebox.showerror("오류", f"연결/점검 오류: {str(e)}")

    def generate_report(self):
        """리포트 생성"""
        try:
            if not self.check_results:
                messagebox.showerror("오류", "리포트 생성할 데이터가 없습니다.")
                return

            # 리포트 생성
            report_info = self.report_generator.generate_report(self.check_results, 'html')
            
            messagebox.showinfo("성공", f"리포트가 생성되었습니다.\n파일: {report_info['filename']}")

        except Exception as e:
            logger.error(f"리포트 생성 오류: {str(e)}")
            messagebox.showerror("오류", f"리포트 생성 오류: {str(e)}")

    def on_select(self, event):
        """트리뷰 선택 이벤트 핸들러"""
        try:
            # 선택된 항목이 있는지 확인
            selected_items = self.results_tree.selection()
            if not selected_items:
                return
                
            # 선택된 항목 정보 저장
            item = selected_items[0]
            self.current_selection = {
                'item': item,
                'values': self.results_tree.item(item)['values']
            }
            
        except Exception as e:
            logger.error(f"선택 이벤트 처리 오류: {str(e)}")

    def copy_selected_content(self, event=None):
        """선택된 내용 복사 (Ctrl+C)"""
        try:
            if not hasattr(self, 'current_selection') or not self.current_selection:
                return

            values = self.current_selection['values']
            # 조회 방법과 변경 방법 명령어 복사
            query_command = values[4]
            modify_command = values[5]
            copy_text = f"조회 명령어:\n{query_command}\n\n변경 방법:\n{modify_command}"
            
            # 클립보드에 복사
            self.clipboard_clear()
            self.clipboard_append(copy_text)
            
        except Exception as e:
            logger.error(f"내용 복사 오류: {str(e)}")

if __name__ == '__main__':
    # 필요한 디렉토리 생성
    os.makedirs('reports', exist_ok=True)
    
    # 앱 실행
    app = ParameterCheckerApp()
    app.mainloop()