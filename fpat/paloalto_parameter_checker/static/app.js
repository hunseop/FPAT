// Palo Alto Parameter Checker - 클라이언트 JavaScript

class ParameterChecker {
    constructor() {
        this.currentParameters = [];
        this.isEditing = false;
        this.editingId = null;
        this.init();
    }

    init() {
        this.bindEvents();
        this.loadParameters();
    }

    bindEvents() {
        // 점검 관련 이벤트
        document.getElementById('checkButton').addEventListener('click', () => this.runCheck());
        document.getElementById('downloadExcelBtn').addEventListener('click', () => this.downloadReport('excel'));
        document.getElementById('downloadHtmlBtn').addEventListener('click', () => this.downloadReport('html'));

        // 매개변수 관리 이벤트
        document.getElementById('saveParameterBtn').addEventListener('click', () => this.saveParameter());
        document.getElementById('parameters-tab').addEventListener('click', () => this.loadParameters());

        // 설정 관리 이벤트
        document.getElementById('exportBtn').addEventListener('click', () => this.exportSettings());
        document.getElementById('importBtn').addEventListener('click', () => this.importSettings());
        document.getElementById('resetBtn').addEventListener('click', () => this.resetSettings());

        // 모달 초기화 이벤트
        document.getElementById('parameterModal').addEventListener('hidden.bs.modal', () => this.resetParameterForm());
    }

    // 유틸리티 함수들
    showAlert(message, type = 'info') {
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        const container = document.querySelector('.container-fluid');
        container.insertBefore(alertDiv, container.firstChild);
        
        // 5초 후 자동 제거
        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.remove();
            }
        }, 5000);
    }

    async apiCall(url, options = {}) {
        try {
            const response = await fetch(url, {
                headers: {
                    'Content-Type': 'application/json',
                    ...options.headers
                },
                ...options
            });

            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.message || '요청 실패');
            }

            return data;
        } catch (error) {
            console.error('API 호출 실패:', error);
            throw error;
        }
    }

    // 점검 관련 함수들
    async runCheck() {
        const host = document.getElementById('hostInput').value.trim();
        const username = document.getElementById('usernameInput').value.trim();
        const password = document.getElementById('passwordInput').value.trim();

        if (!host || !username || !password) {
            this.showAlert('모든 필드를 입력해주세요.', 'warning');
            return;
        }

        this.setCheckingState(true);

        try {
            const result = await this.apiCall('/api/check', {
                method: 'POST',
                body: JSON.stringify({ host, username, password })
            });

            if (result.success) {
                this.displayResults(result.results, result.summary);
                this.showAlert('점검이 완료되었습니다.', 'success');
                
                // 다운로드 버튼 활성화
                document.getElementById('downloadExcelBtn').disabled = false;
                document.getElementById('downloadHtmlBtn').disabled = false;
            } else {
                this.showAlert(result.message, 'danger');
            }
        } catch (error) {
            this.showAlert(`점검 실행 실패: ${error.message}`, 'danger');
        } finally {
            this.setCheckingState(false);
        }
    }

    setCheckingState(checking) {
        const button = document.getElementById('checkButton');
        const buttonText = document.getElementById('checkButtonText');
        const spinner = document.getElementById('checkSpinner');

        if (checking) {
            button.disabled = true;
            buttonText.textContent = '점검 중...';
            spinner.classList.remove('d-none');
        } else {
            button.disabled = false;
            buttonText.textContent = '🚀 점검 시작';
            spinner.classList.add('d-none');
        }
    }

    displayResults(results, summary) {
        // 요약 정보 업데이트
        document.getElementById('totalCount').textContent = summary.total;
        document.getElementById('passCount').textContent = summary.pass;
        document.getElementById('failCount').textContent = summary.fail;
        document.getElementById('errorCount').textContent = summary.error;
        document.getElementById('summarySection').classList.remove('d-none');

        // 결과 테이블 업데이트
        const tbody = document.getElementById('resultsTableBody');
        tbody.innerHTML = '';

        results.forEach(result => {
            const row = document.createElement('tr');
            row.className = `status-${result.status}`;
            
            const statusIcon = {
                'PASS': '✅',
                'FAIL': '❌', 
                'ERROR': '⚠️'
            }[result.status] || '❓';

            row.innerHTML = `
                <td><strong>${result.parameter}</strong></td>
                <td>${result.expected}</td>
                <td>${result.current}</td>
                <td>${statusIcon} ${result.status}</td>
                <td><span class="command-text">${result.query_method}</span></td>
                <td><span class="command-text">${result.modify_method}</span></td>
            `;
            
            tbody.appendChild(row);
        });
    }

    async downloadReport(format) {
        try {
            const response = await fetch(`/api/download/${format}`);
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.message);
            }

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            
            const filename = response.headers.get('content-disposition')?.split('filename=')[1]?.replace(/"/g, '') 
                || `report.${format === 'excel' ? 'xlsx' : 'html'}`;
            
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);

            this.showAlert(`${format.toUpperCase()} 리포트 다운로드 완료`, 'success');
        } catch (error) {
            this.showAlert(`리포트 다운로드 실패: ${error.message}`, 'danger');
        }
    }

    // 매개변수 관리 함수들
    async loadParameters() {
        try {
            const result = await this.apiCall('/api/parameters');
            
            if (result.success) {
                this.currentParameters = result.parameters;
                this.displayParameters();
            } else {
                this.showAlert('매개변수 로딩 실패', 'danger');
            }
        } catch (error) {
            this.showAlert(`매개변수 로딩 실패: ${error.message}`, 'danger');
        }
    }

    displayParameters() {
        const tbody = document.getElementById('parametersTableBody');
        tbody.innerHTML = '';

        if (this.currentParameters.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="6" class="text-center text-muted py-4">
                        등록된 매개변수가 없습니다. 새 매개변수를 추가하세요.
                    </td>
                </tr>
            `;
            return;
        }

        this.currentParameters.forEach(param => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td><strong>${param.name}</strong></td>
                <td>${param.description}</td>
                <td>${param.expected_value}</td>
                <td><span class="command-text">${param.command}</span></td>
                <td><code>${param.pattern}</code></td>
                <td>
                    <button class="btn btn-sm btn-outline-primary me-1" onclick="app.editParameter(${param.id})">
                        ✏️ 수정
                    </button>
                    <button class="btn btn-sm btn-outline-danger" onclick="app.deleteParameter(${param.id})">
                        🗑️ 삭제
                    </button>
                </td>
            `;
            tbody.appendChild(row);
        });
    }

    editParameter(id) {
        const param = this.currentParameters.find(p => p.id === id);
        if (!param) return;

        this.isEditing = true;
        this.editingId = id;

        // 모달 제목 변경
        document.getElementById('parameterModalTitle').textContent = '매개변수 수정';
        
        // 폼에 데이터 채우기
        document.getElementById('parameterIdInput').value = param.id;
        document.getElementById('nameInput').value = param.name;
        document.getElementById('descriptionInput').value = param.description;
        document.getElementById('expectedValueInput').value = param.expected_value;
        document.getElementById('commandInput').value = param.command;
        document.getElementById('modifyCommandInput').value = param.modify_command;
        document.getElementById('patternInput').value = param.pattern;

        // 모달 표시
        const modal = new bootstrap.Modal(document.getElementById('parameterModal'));
        modal.show();
    }

    async deleteParameter(id) {
        if (!confirm('이 매개변수를 삭제하시겠습니까?')) {
            return;
        }

        try {
            const result = await this.apiCall(`/api/parameters/${id}`, {
                method: 'DELETE'
            });

            if (result.success) {
                this.showAlert(result.message, 'success');
                this.loadParameters();
            } else {
                this.showAlert(result.message, 'danger');
            }
        } catch (error) {
            this.showAlert(`삭제 실패: ${error.message}`, 'danger');
        }
    }

    async saveParameter() {
        const formData = {
            name: document.getElementById('nameInput').value.trim(),
            description: document.getElementById('descriptionInput').value.trim(),
            expected_value: document.getElementById('expectedValueInput').value.trim(),
            command: document.getElementById('commandInput').value.trim(),
            modify_command: document.getElementById('modifyCommandInput').value.trim(),
            pattern: document.getElementById('patternInput').value.trim()
        };

        // 필수 필드 검증
        const requiredFields = Object.keys(formData);
        for (const field of requiredFields) {
            if (!formData[field]) {
                this.showAlert(`${field} 필드는 필수입니다.`, 'warning');
                return;
            }
        }

        try {
            let result;
            
            if (this.isEditing) {
                // 수정
                result = await this.apiCall(`/api/parameters/${this.editingId}`, {
                    method: 'PUT',
                    body: JSON.stringify(formData)
                });
            } else {
                // 추가
                result = await this.apiCall('/api/parameters', {
                    method: 'POST',
                    body: JSON.stringify(formData)
                });
            }

            if (result.success) {
                this.showAlert(result.message, 'success');
                this.loadParameters();
                
                // 모달 닫기
                const modal = bootstrap.Modal.getInstance(document.getElementById('parameterModal'));
                modal.hide();
            } else {
                this.showAlert(result.message, 'danger');
            }
        } catch (error) {
            this.showAlert(`저장 실패: ${error.message}`, 'danger');
        }
    }

    resetParameterForm() {
        this.isEditing = false;
        this.editingId = null;
        
        document.getElementById('parameterModalTitle').textContent = '매개변수 추가';
        document.getElementById('parameterForm').reset();
        document.getElementById('parameterIdInput').value = '';
    }

    // 설정 관리 함수들
    async exportSettings() {
        try {
            const result = await this.apiCall('/api/export');
            
            // JSON 파일로 다운로드
            const blob = new Blob([JSON.stringify(result, null, 2)], {
                type: 'application/json'
            });
            
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `palo_alto_parameters_${new Date().toISOString().split('T')[0]}.json`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);

            this.showAlert('설정 내보내기 완료', 'success');
        } catch (error) {
            this.showAlert(`내보내기 실패: ${error.message}`, 'danger');
        }
    }

    async importSettings() {
        const fileInput = document.getElementById('importFileInput');
        const file = fileInput.files[0];
        
        if (!file) {
            this.showAlert('가져올 파일을 선택하세요.', 'warning');
            return;
        }

        try {
            const text = await file.text();
            const data = JSON.parse(text);

            const result = await this.apiCall('/api/import', {
                method: 'POST',
                body: JSON.stringify(data)
            });

            if (result.success) {
                this.showAlert(result.message, 'success');
                this.loadParameters();
                fileInput.value = ''; // 파일 입력 초기화
            } else {
                this.showAlert(result.message, 'danger');
            }
        } catch (error) {
            this.showAlert(`가져오기 실패: ${error.message}`, 'danger');
        }
    }

    async resetSettings() {
        if (!confirm('모든 매개변수를 기본값으로 초기화하시겠습니까?\n기존 설정은 모두 삭제됩니다.')) {
            return;
        }

        try {
            const result = await this.apiCall('/api/reset', {
                method: 'POST'
            });

            if (result.success) {
                this.showAlert(result.message, 'success');
                this.loadParameters();
            } else {
                this.showAlert(result.message, 'danger');
            }
        } catch (error) {
            this.showAlert(`초기화 실패: ${error.message}`, 'danger');
        }
    }
}

// 앱 초기화
const app = new ParameterChecker();