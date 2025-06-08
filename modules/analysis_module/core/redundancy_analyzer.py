"""
중복 정책 분석을 위한 클래스입니다.
"""

import pandas as pd
import logging
from typing import Dict, List, Tuple
from collections import defaultdict

class RedundancyAnalyzer:
    """중복 정책 분석을 위한 클래스"""
    
    def __init__(self):
        """RedundancyAnalyzer 초기화"""
        self.logger = logging.getLogger(__name__)
        self.vendor_columns = {
            'paloalto': ['Enable', 'Action', 'Source', 'User', 'Destination', 'Service', 'Application', 'Security Profile','Category', 'Vsys'],
            'ngf': ['Enable', 'Action', 'Source', 'User', 'Destination', 'Service', 'Application'],
            'default': ['Enable', 'Action', 'Source', 'User', 'Destination', 'Service', 'Application']
        }
        self.extracted_columns = {
            'paloalto': ['Enable', 'Action', 'Extracted Source', 'User', 'Extracted Destination', 'Extracted Service', 'Application', 'Security Profile', 'Category', 'Vsys'],
            'ngf': ['Enable', 'Action', 'Extracted Source', 'User', 'Extracted Destination', 'Extracted Service', 'Application'],
            'default': ['Enable', 'Action', 'Extracted Source', 'User', 'Extracted Destination', 'Extracted Service', 'Application']
        }
    
    def _normalize_policy(self, policy_series: pd.Series) -> tuple:
        """
        정책 데이터를 정규화합니다.
        
        Args:
            policy_series: 정규화할 정책 데이터
        
        Returns:
            정규화된 정책 데이터 튜플
        """
        normalized_policy = policy_series.apply(lambda x: ','.join(sorted(x.split(','))) if isinstance(x, str) else x)
        return tuple(normalized_policy)
    
    def _prepare_data(self, df: pd.DataFrame, vendor: str) -> pd.DataFrame:
        """
        분석을 위해 데이터를 준비합니다.
        
        Args:
            df: 원본 데이터프레임
            vendor: 방화벽 벤더
        
        Returns:
            전처리된 데이터프레임
        """
        # 활성화된 Allow 정책만 필터링

        df_filtered = df[(df['Enable'] == 'Y') & (df['Action'] == 'allow')].copy()

        # 벤더별 특수 처리
        if vendor == 'paloalto':
            df_filtered['Service'] = df_filtered['Service'].str.replace('_', '-')
        
        return df_filtered
    
    def analyze(self, df: pd.DataFrame, vendor: str, **kwargs) -> pd.DataFrame:
        """
        중복 정책을 분석합니다.
        
        Args:
            df: 분석할 정책 데이터프레임
            vendor: 방화벽 벤더
            **kwargs: 추가 매개변수
        
        Returns:
            분석 결과 데이터프레임
        """
        try:
            self.logger.info("중복 정책 분석 시작")
            
            # 데이터 준비
            df_filtered = self._prepare_data(df, vendor)
            # 확장된 데이터인지 점검
            # 분석할 컬럼 선택
            if 'Extracted Source' in df_filtered.columns:
                columns_to_check = self.extracted_columns.get(vendor, self.extracted_columns['default'])
            else:
                columns_to_check = self.vendor_columns.get(vendor, self.vendor_columns['default'])

            df_check = df_filtered[columns_to_check]
            
            # 중복 정책 분석
            policy_map = defaultdict(list)
            results_list = []
            current_no = 1
            total = len(df_filtered)
            
            self.logger.info("정책 중복 여부 확인 중...")
            for i in range(total):
                try:
                    # 진행률 표시 (10% 단위로)
                    if i % (total // 10) == 0 or i == total - 1:
                        progress = (i + 1) / total * 100
                        print(f"\r정책 분석 중: {progress:.1f}% ({i + 1}/{total})", end='', flush=True)
                    
                    current_policy = self._normalize_policy(df_check.iloc[i])
                    if current_policy in policy_map:
                        row = df_filtered.iloc[i].to_dict()
                        row.update({'No': policy_map[current_policy], 'Type': 'Lower'})
                        results_list.append(row)
                    else:
                        policy_map[current_policy] = current_no
                        row = df_filtered.iloc[i].to_dict()
                        row.update({'No': current_no, 'Type': 'Upper'})
                        results_list.append(row)
                        current_no += 1
                except Exception as e:
                    self.logger.warning(f"정책 {i} 분석 중 오류 발생: {e}")
                    continue
            
            print()  # 줄바꿈
            
            # 결과 데이터프레임 생성
            results = pd.DataFrame(results_list)

            # 각 No 그룹에 Upper와 Lower가 모두 포함되도록 필터링
            def ensure_upper_and_lower(df):
                valid_no_groups = []
                grouped = df.groupby('No')
                for name, group in grouped:
                    if 'Upper' in group['Type'].values and 'Lower' in group['Type'].values:
                        valid_no_groups.append(group)
                return pd.concat(valid_no_groups).reset_index(drop=True)

            duplicated_results = ensure_upper_and_lower(results)
            
            # No 재부여
            duplicated_results['No'] = duplicated_results.groupby('No').ngroup() + 1
            
            # 컬럼 순서 재조정
            columns_order = ['No', 'Type'] + [col for col in df.columns]
            duplicated_results = duplicated_results[columns_order]
            
            # No 기준으로, 각 No 내에서 Upper가 상단에 위치하도록 정렬 (내림차순 정렬)
            duplicated_results = duplicated_results.sort_values(by=['No', 'Type'], ascending=[True, False])

            self.logger.info("중복 정책 분석 완료")
            return duplicated_results
            
        except Exception as e:
            self.logger.error(f"중복 정책 분석 중 오류 발생: {e}")
            raise