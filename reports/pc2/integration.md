# N02 부모 화면 연결 제안

기준 `3c5e5a3`의 `apps/web/app/page.tsx` / pc1 소유. 이 보고서는 연결 예시이며 실제 공용 페이지를 수정하지 않았다. 최종 메인 통합·API 회귀는 별도 인수 항목이다.

## 확정된 배정 계약과 선택 확장

`CallReview`는 기본 export이며 필수 입력은 `caseData: CaseData`, 선택 입력은 `disabled?: boolean`, `onPlaybackEnded?: () => void`다. 값을 저장하거나 분석 API를 직접 호출하지 않는다. 다음 선택 props는 N02가 분석 중/실패·재시도를 표시하기 위해 제안한 확장으로 메인 검토 대상이다.

| props | 의미 |
|---|---|
| `analysisState?: 'idle' \| 'loading' \| 'error'` | 부모가 가진 분석 상태. 기본 idle |
| `analysisError?: string` | 부모가 분석 요청에서 받은 사용자용 오류 |
| `onRetryAnalysis?: () => void` | 조건 충족 후 부모의 기존 분석 함수를 다시 호출 |
| `transcriptMode?: 'replay' \| 'demo-live'` | 현재 화면의 선택 모드가 아닌, 표시 중인 결과의 출처 |

`transcriptMode` 또는 `caseData.analysisMode`가 없는 대화록은 실제 STT 결과로 확정하지 않는다. 분석 전 fixture는 replay임을 명시해 전달하거나 출처 미확인 표시를 유지한다. `mode` 선택을 바꾼 것만으로 기존 replay 결과를 실제 AI 결과라고 표시하면 안 된다.

## Desk 연결 예시

아래 코드는 pc1이 기존 통화/대화록 영역을 교체할 때 참고한다. `analyze`, 저장 폼, `formRevision`, 서버 권한·revision 처리는 기존 부모가 유지한다. `analysisFailure`는 저장/이관 오류와 분리해 관리하는 분석 전용 상태를 뜻한다.

```tsx
import CallReview from '@/components/CallReview';

// 기존 Desk의 상태에서 새 미디어/사건을 선택하면 audioEnded를 false로 초기화.
// 동일 id라도 audioUrl이 바뀌면 기존 완료 상태를 승계하지 않는다.
useEffect(() => setAudioEnded(false), [c.id, c.audioUrl]);

const reviewCase: CaseData = {
  ...c,
  transcript,
  analysis,
  intake: form, // 아직 저장하지 않은 현재 상담 입력을 읽기 전용으로 비교.
  reviewConfirmed: confirmed, // 저장된 c 값이 아닌 현재 폼의 확인 체크 상태.
  analysisMode: resultMode,
};

<CallReview
  key={`${c.id}:${c.audioUrl ?? ''}`}
  caseData={reviewCase}
  disabled={intakeLocked || busy !== ''}
  onPlaybackEnded={() => setAudioEnded(true)}
  transcriptMode={resultMode}
  analysisState={busy === 'analyze' ? 'loading' : analysisFailure ? 'error' : 'idle'}
  analysisError={analysisFailure}
  onRetryAnalysis={() => {
    if (!fallback && !intakeLocked && !busy && (c.channel !== 'voice' || audioEnded)) {
      void analyze();
    }
  }}
/>
```

부모의 분석 버튼에서도 `c.channel === 'voice' && !audioEnded`를 계속 차단한다. 재시도 함수 안의 게이트도 유지하고 UI disabled만 신뢰하지 않는다. 이 예시가 부모의 현재 `analyze()` 함수를 수정한 것은 아니다. `onPlaybackEnded`는 완료 사실 알림이며 자동으로 API를 호출하는 콜백으로 연결하지 않는다.

현재 접수값 `form`과 확인 체크 `confirmed`는 같은 편집 상태의 한 쌍으로 전달한다. 기존 `c.reviewConfirmed=true`인 접수를 수정하면 부모 `field()`가 `setConfirmed(false)`를 실행하므로, `...c`의 과거 확인값을 승계해서는 안 된다. 반대로 아직 저장하지 않은 확인 체크가 true이면 현재 폼의 상태를 표시한다. 이 표시는 서버 저장·센터 이관 완료를 뜻하지 않으며 기존 저장/이관 함수와 revision 검사를 대체하지 않는다. 분석 성공 후 확인 해제, 부서 편집 후 확인 해제도 동일하게 전달한다.

구간 재생이나 끝으로 건너뛰기는 전체 완료로 처리하지 않는다. 오류·음원 없음·disabled·사건 전환에서 새 완료 콜백이 나오지 않는지 N02 검사로 확인하며, 최종 부모 연결에서도 동일 조건을 검사해야 한다.

## 원문과 상담 입력의 정확한 범위

현재 서버의 `analyze`는 `case.intake`에 새 AI fields를 저장하고 현재 Desk도 `form`을 그 값으로 바꾼다. 따라서 본 컴포넌트가 보존·비교하는 것은 **원문/전사와 AI 제안, 현재 상담 입력**이다. 분석 전 최초 상담 입력의 독립 영구 보존을 이 컴포넌트의 성과로 주장하지 않는다. 과거 입력 감사 이력 확장은 pc1의 데이터 계약 결정 대상이며 N02는 서버/타입을 임의 변경하지 않았다.

기준 서버 결과의 `analysisMode`·requestId와 음원 SHA는 개별 실행 자료다. 음원 v2를 받았다는 이유로 과거 v1 STT 결과를 v2 결과로 바꾸지 않는다. 정규화된 실제 응답의 재사용은 무과금 결과 재생이며 이번 PC가 모델을 새 호출한 것이 아니다.

## 메인 인수 확인

1. N02 branch의 명시 소유 파일과 선택 props를 검토한다.
2. 부모의 분석 전용 오류/실행 상태와 표시 중인 결과 출처를 연결한다.
3. 기존 원문·저장 폼·revision/이관·WMS/TMS 이동을 보존한다.
4. 최종 앱에서 전체 재생→분석→수정/확인→이관, 실패/재시도와 사건 전환을 실제 UI/API로 재검증한다.
5. N02의 별도 렌더 PASS는 최종 서비스 통합 PASS와 구분한다. 사람 청취·정확도 일반화는 별도다.
