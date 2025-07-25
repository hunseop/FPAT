import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from datetime import datetime
import os

def save_report_to_excel(report: list, filename: str, hostname: str):
    df = pd.DataFrame(report, columns=["항목", "상태", "현재값", "기대값"])

    tmp_filename = "_tmp_report.xlsx"
    df.to_excel(tmp_filename, index=False, startrow=3, startcol=1) # b열부터 시작

    wb = load_workbook(tmp_filename)
    ws = wb.active
    ws.title = "점검결과"

    #상단요약
    ws["B1"] = f"점검일시: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    ws["B2"] = f"대상장비: {hostname}"
    ws["B1"].font = ws["B2"].font = Font(bold=True)

    ws["A1"] = ""
    ws.column_dimensions["A"].width = 3.0

    header_fill = PatternFill("solid", fgColor="DDDDDD")
    header_font = Font(bold=True)
    border = Border(
        left=Side(style="thin"),
        right=Side(style="thin"),
        top=Side(style="thin"),
        bottom=Side(style="thin")
    )

    for col_num in range(2, 6):
        cell = ws.cell(row=4, coulmn=col_num)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = border
    
    status_color_map = {
        "일치": "C6EFCE",
        "불일치": "FFC7CE",
        "없음": "D9D9D9",
        "명령어 실패": "FFEB9C",
    }

    for row in ws.iter_rows(min_row=5, max_row=ws.max_row, min_col=2, max_col=5):
        for i, cell in enumerate(row):
            if i != 0:
                cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.border = border
        
        status = row[1].value
        fill_color = status_color_map.get(status)
        if fill_color:
            row[1].fill = PatternFill("solid", fgColor=fill_color)
    
    for col in range(2, 6):
        max_len = max(len(str(ws.cell(row=row, column=col).value or "")) for row in range(4, ws.max_row +1 ))
        ws.columns_dimensions[get_column_letter(col)].width = max_len + 4
    
    wb.save(filename)
    os.remove(tmp_filename)